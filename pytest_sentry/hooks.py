# Copyright (c) 2018 Markus Unterwaditzer and individual contributors.
"""Pytest hooks that report test runs to Sentry."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

import pytest
import sentry_sdk
import wrapt

from pytest_sentry.helpers import _resolve_scope_marker_value
from pytest_sentry.integration import PytestIntegration

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

        with sentry_sdk.use_isolation_scope(scope):
            gen = wrapped(*args, **kwargs)

        while True:
            try:
                with sentry_sdk.use_isolation_scope(scope):
                    next(gen)
                sent = yield
                with sentry_sdk.use_isolation_scope(scope):
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
    """Run one test (setup, call and teardown) in a span.

    See https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_runtest_protocol
    """
    op = "pytest.runtest.protocol"
    # The full name, including parameters, identifies how often a single test
    # ran as part of the same GITHUB_RUN_ID. The span is purposefully not sent
    # to spare quota; it only exists to give the test a trace ID.
    with sentry_sdk.start_span(op=op, name=f"{op} {item.nodeid}", sampled=False):
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
    with sentry_sdk.continue_trace(headers), sentry_sdk.start_span(op=op, name=name) as span:
        span.set_attribute("pytest-sentry.rerun", is_rerun)
        if is_rerun:
            span.set_attribute("pytest-sentry.execution_count", execution_count)
        yield


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
    with (
        sentry_sdk.continue_trace(headers),
        sentry_sdk.start_span(op=op, name=f"{op} {fixturedef.argname}") as span,
    ):
        span.set_tag("pytest.fixture.scope", fixturedef.scope)
        yield


@_hookwrapper(itemgetter=_item_arg, tryfirst=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pluggy.Result[pytest.TestReport]]:
    """Report failed test attempts to Sentry.

    Called for the setup, call and teardown phases.
    See https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_runtest_makereport
    """
    sentry_sdk.set_tag("pytest.result", "pending")
    outcome = (yield).get_result().outcome
    sentry_sdk.set_tag("pytest.result", outcome)

    if call.when != "call" or outcome == "skipped":
        return

    exc_chain = item.stash.get(_EXC_CHAIN, [])
    if call.excinfo is not None:
        exc_chain = item.stash[_EXC_CHAIN] = [*exc_chain, call.excinfo]

    scope = _resolve_scope_marker_value(item.get_closest_marker("sentry_client"))
    integration = scope.client.get_integration(PytestIntegration)

    attempt = _execution_count(item)
    sentry_sdk.set_tag("pytest.attempt", str(attempt))
    sentry_sdk.set_tag("pytest.final_attempt", str(_is_final_attempt(item, attempt)).lower())

    if integration is not None and integration.always_report:
        # Every failed attempt is reported as it happens, so only report this
        # attempt's exception. Earlier attempts were already sent.
        to_report = [] if call.excinfo is None else [call.excinfo]
    elif call.excinfo is None:
        # The test passed after failing: it's flaky, report what failed.
        to_report = exc_chain
    else:
        to_report = []

    for excinfo in to_report:
        sentry_sdk.capture_exception((excinfo.type, excinfo.value, excinfo.tb))


def _is_final_attempt(item: pytest.Item, attempt: int) -> bool:
    """Whether pytest-rerunfailures won't retry this test after this attempt.

    Without pytest-rerunfailures, or with no reruns configured, every attempt
    is final.

    Returns:
        True if this attempt is the last one.

    """
    # Registered as "rerunfailures" via its entry point, or under the module
    # name when loaded explicitly with `-p pytest_rerunfailures`.
    plugins = item.config.pluginmanager
    rerunfailures = plugins.get_plugin("rerunfailures") or plugins.get_plugin(
        "pytest_rerunfailures"
    )
    if rerunfailures is None:
        return True
    reruns = rerunfailures.get_reruns_count(item)
    return not reruns or attempt > reruns
