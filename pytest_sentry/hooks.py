# Copyright (c) 2018 Markus Unterwaditzer and individual contributors.
"""Pytest hooks that report test runs to Sentry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, cast

import pytest
import sentry_sdk
import sentry_sdk.traces
import wrapt
from sentry_sdk.scope import use_isolation_scope

from pytest_sentry.client import PROTOCOL_OP
from pytest_sentry.helpers import _resolve_scope_marker_value
from pytest_sentry.integration import PytestIntegration, environ_tags

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    import pluggy

type _ItemGetter = Callable[[tuple[object, ...]], pytest.Item]

_EXC_CHAIN = pytest.StashKey[list[pytest.ExceptionInfo[BaseException]]]()


class _HookDecorator(Protocol):
    def __call__[**P, S](
        self, hook: Callable[P, Generator[None, S]], /
    ) -> Callable[P, Generator[None, S]]: ...


def pytest_load_initial_conftests(early_config: pytest.Config) -> None:
    """Register the `sentry_client` marker.

    See https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_load_initial_conftests
    """
    early_config.addinivalue_line(
        "markers",
        "sentry_client(client=None): Use this client instance for reporting tests. You can also "
        "pass a DSN string directly, or a `Scope` if you need it.",
    )


def _item_arg(args: tuple[object, ...]) -> pytest.Item:
    item = args[0]
    if not isinstance(item, pytest.Item):
        msg = f"Expected a pytest.Item, got {type(item)!r}"
        raise TypeError(msg)
    return item


def _fixture_request_item(args: tuple[object, ...]) -> pytest.Item:
    request = args[1]
    if not isinstance(request, pytest.FixtureRequest):
        msg = f"Expected a pytest.FixtureRequest, got {type(request)!r}"
        raise TypeError(msg)
    # The test that requested the fixture. pytest has no public accessor, and
    # `request.node` is the module or session for wider-scoped fixtures.
    return request._pyfuncitem  # ruff: ignore[private-member-access]


def _execution_count(item: pytest.Item) -> int:
    # Set by pytest-rerunfailures before each attempt (1-based).
    count = getattr(item, "execution_count", None)
    return count if isinstance(count, int) else 1


def _hookwrapper(itemgetter: _ItemGetter, *, tryfirst: bool = False) -> _HookDecorator:
    """Wrap a hookwrapper so it runs in the test's isolation scope.

    The hook is skipped if the test's client has no `PytestIntegration`, i.e.
    reporting is disabled. Assumes the hook yields once.

    Returns:
        A decorator for hookwrapper generators.

    """

    @wrapt.decorator
    def with_isolation_scope(
        wrapped: Callable[..., Generator[None, object]],
        _instance: object,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> Generator[None, object]:
        scope = _resolve_scope_marker_value(itemgetter(args).get_closest_marker("sentry_client"))

        if scope.client.get_integration(PytestIntegration) is None:
            yield
            return

        with use_isolation_scope(scope):
            gen = wrapped(*args, **kwargs)

        while True:
            try:
                with use_isolation_scope(scope):
                    next(gen)
                sent = yield
                with use_isolation_scope(scope):
                    gen.send(sent)
            except StopIteration:
                break

    def decorate[**P, S](
        hook: Callable[P, Generator[None, S]],
    ) -> Callable[P, Generator[None, S]]:
        wrapped = cast("Callable[P, Generator[None, S]]", with_isolation_scope(hook))
        return pytest.hookimpl(wrapper=False, hookwrapper=True, tryfirst=tryfirst)(wrapped)

    return decorate


@_hookwrapper(itemgetter=_item_arg)
def pytest_runtest_protocol(item: pytest.Item) -> Generator[None]:
    """Run one test (setup, call and teardown) in its own trace, in a span.

    See https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_runtest_protocol
    """
    sentry_sdk.traces.new_trace()
    # The span is ignored by the client's `ignore_spans` to spare quota.
    with sentry_sdk.traces.start_span(
        name=f"{PROTOCOL_OP} {item.nodeid}",
        attributes={"sentry.op": PROTOCOL_OP},
        parent_span=None,
    ):
        yield


@_hookwrapper(itemgetter=_item_arg)
def pytest_runtest_call(item: pytest.Item) -> Generator[None]:
    """Run the call phase of a test in a span.

    See https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_runtest_call
    """
    op = "pytest.runtest.call"
    execution_count = _execution_count(item)
    is_rerun = execution_count > 1
    rerun = f" (rerun {execution_count - 1})" if is_rerun else ""
    name = f"{op}{rerun} {item.nodeid}"

    headers = dict(sentry_sdk.get_isolation_scope().iter_trace_propagation_headers())
    sentry_sdk.traces.continue_trace(headers)
    # `parent_span=None` keeps spans of the tested code out of the test's trace.
    with sentry_sdk.traces.start_span(
        name=name, attributes={"sentry.op": op}, parent_span=None
    ) as span:
        span.set_attribute("pytest-sentry.rerun", is_rerun)
        if is_rerun:
            span.set_attribute("pytest-sentry.execution_count", execution_count)
        try:
            yield
        finally:
            # Read once the span ends, as the test may set them.
            # A dict literal, as `Attributes` is an invariant `dict[str, AttributeValue]`.
            span.set_attributes({**environ_tags()})


@_hookwrapper(itemgetter=_fixture_request_item)
def pytest_fixture_setup(
    fixturedef: pytest.FixtureDef[object], request: pytest.FixtureRequest
) -> Generator[None]:
    """Set up a fixture in a span.

    See https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_fixture_setup
    """
    del request  # Only used to find the test item.
    op = "pytest.fixture.setup"
    headers = dict(sentry_sdk.get_isolation_scope().iter_trace_propagation_headers())
    sentry_sdk.traces.continue_trace(headers)
    # `parent_span=None` keeps spans of the tested code out of the test's trace.
    with sentry_sdk.traces.start_span(
        name=f"{op} {fixturedef.argname}", attributes={"sentry.op": op}, parent_span=None
    ) as span:
        span.set_attribute("pytest.fixture.scope", fixturedef.scope)
        try:
            yield
        finally:
            # Read once the span ends, as the fixture may set them.
            # A dict literal, as `Attributes` is an invariant `dict[str, AttributeValue]`.
            span.set_attributes({**environ_tags()})


@dataclass
class _Attempt:
    """What one attempt of a test reports, captured once the attempt ends."""

    scope: sentry_sdk.Scope
    reports: list[pytest.TestReport] = field(default_factory=list)
    to_report: list[pytest.ExceptionInfo[BaseException]] = field(default_factory=list)
    tags: dict[str, str] = field(default_factory=dict)


# Keyed by node ID. Attempts of a test run one after another, and an entry is
# removed when its attempt finishes.
_ATTEMPTS: dict[str, _Attempt] = {}


@_hookwrapper(itemgetter=_item_arg, tryfirst=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pluggy.Result[pytest.TestReport]]:
    """Collect what a test attempt reports to Sentry.

    Called for the setup, call and teardown phases. The exceptions are only
    captured in `pytest_runtest_logfinish`, once pytest-rerunfailures has
    decided whether the attempt is retried.
    See https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_runtest_makereport
    """
    sentry_sdk.set_tag("pytest.result", "pending")
    report = (yield).get_result()
    outcome = report.outcome
    sentry_sdk.set_tag("pytest.result", outcome)

    scope = _resolve_scope_marker_value(item.get_closest_marker("sentry_client"))
    if call.when == "setup" or item.nodeid not in _ATTEMPTS:
        _ATTEMPTS[item.nodeid] = _Attempt(scope=scope)
    attempt = _ATTEMPTS[item.nodeid]
    attempt.reports.append(report)

    if call.when != "call" or outcome == "skipped":
        return

    exc_chain = item.stash.get(_EXC_CHAIN, [])
    if call.excinfo is not None:
        exc_chain = item.stash[_EXC_CHAIN] = [*exc_chain, call.excinfo]

    integration = scope.client.get_integration(PytestIntegration)
    execution_count = str(_execution_count(item))
    sentry_sdk.set_tag("pytest.attempt", execution_count)

    if integration is not None and integration.always_report:
        # Every failed attempt is reported as it happens, so only report this
        # attempt's exception. Earlier attempts were already sent.
        attempt.to_report = [] if call.excinfo is None else [call.excinfo]
    elif call.excinfo is None:
        # The test passed after failing: it's flaky, report what failed.
        attempt.to_report = exc_chain
    else:
        attempt.to_report = []
    attempt.tags = {"pytest.result": outcome, "pytest.attempt": execution_count}


def pytest_runtest_logfinish(nodeid: str) -> None:
    """Report the exceptions of a finished test attempt to Sentry.

    pytest-rerunfailures marks the reports of an attempt it retries as
    `rerun` only after all phases ran, taking `--only-rerun`, `--rerun-except`,
    `condition` and `--max-suite-reruns` into account. An attempt without such
    a report is the final one.
    See https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_runtest_logfinish
    """
    attempt = _ATTEMPTS.pop(nodeid, None)
    if attempt is None or not attempt.to_report:
        return

    final_attempt = not any(report.outcome == "rerun" for report in attempt.reports)
    tags = attempt.tags | {"pytest.final_attempt": str(final_attempt).lower()}
    with use_isolation_scope(attempt.scope):
        for excinfo in attempt.to_report:
            sentry_sdk.capture_exception((excinfo.type, excinfo.value, excinfo.tb), tags=tags)
