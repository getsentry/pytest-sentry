import pytest
import wrapt

import sentry_sdk

from .helpers import _resolve_scope_marker_value
from .integration import PytestIntegration


def pytest_load_initial_conftests(early_config, parser, args):
    """
    Pytest hook that is called when pytest starts.
    See https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_load_initial_conftests
    """
    early_config.addinivalue_line(
        "markers",
        "sentry_client(client=None): Use this client instance for reporting tests. You can also pass a DSN string directly, or a `Scope` if you need it.",
    )


def hookwrapper(itemgetter, **kwargs):
    """
    A version of pytest.hookimpl that sets the current scope to the correct one
    and skips the hook if the integration is disabled.

    Assumes the function is a hookwrapper, ie yields once
    """

    @wrapt.decorator
    def _with_scope(wrapped, instance, args, kwargs):
        item = itemgetter(*args, **kwargs)
        scope = _resolve_scope_marker_value(item.get_closest_marker("sentry_client"))

        if scope.client.get_integration(PytestIntegration) is None:
            yield
        else:
            with sentry_sdk.use_scope(scope):
                gen = wrapped(*args, **kwargs)

            while True:
                try:
                    with sentry_sdk.use_scope(scope):
                        chunk = next(gen)

                    y = yield chunk

                    with sentry_sdk.use_scope(scope):
                        gen.send(y)

                except StopIteration:
                    break

    def inner(f):
        return pytest.hookimpl(hookwrapper=True, **kwargs)(_with_scope(f))

    return inner


@hookwrapper(itemgetter=lambda item: item)
def pytest_runtest_protocol(item):
    """
    Pytest hook that is called when one test is run.
    The runtest protocol includes setup phase, call phase and teardown phase.
    See https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_runtest_protocol
    """
    op = "pytest.runtest.protocol"
    name = "{} {}".format(op, item.nodeid)

    # We use the full name including parameters because then we can identify
    # how often a single test has run as part of the same GITHUB_RUN_ID.
    # Purposefully drop transaction to spare quota. We only created it to
    # have a trace_id to correlate by.
    with sentry_sdk.start_span(op=op, name=name, sampled=False):
        yield


@hookwrapper(itemgetter=lambda item: item)
def pytest_runtest_call(item):
    """
    Pytest hook that is called when the call phase of a test is run.
    See https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_runtest_call
    """
    op = "pytest.runtest.call"
    is_rerun = hasattr(item, "execution_count") and item.execution_count is not None and item.execution_count > 1
    if is_rerun:
        name = "{} (rerun {}) {}".format(op, item.execution_count - 1, item.nodeid)
    else:
        name = "{} {}".format(op, item.nodeid)

    # We use the full name including parameters because then we can identify
    # how often a single test has run as part of the same GITHUB_RUN_ID.
    with sentry_sdk.continue_trace(dict(sentry_sdk.get_current_scope().iter_trace_propagation_headers())):
        with sentry_sdk.start_span(op=op, name=name) as span:
            span.set_attribute("pytest-sentry.rerun", is_rerun)
            if is_rerun:
                span.set_attribute("pytest-sentry.execution_count", item.execution_count)

            yield


@hookwrapper(itemgetter=lambda fixturedef, request: request._pyfuncitem)
def pytest_fixture_setup(fixturedef, request):
    """
    Pytest hook that is called when the fixtures are initially set up.
    See: https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_fixture_setup
    """
    op = "pytest.fixture.setup"
    name = "{} {}".format(op, fixturedef.argname)

    with sentry_sdk.continue_trace(dict(sentry_sdk.get_current_scope().iter_trace_propagation_headers())):
        with sentry_sdk.start_span(op=op, name=name) as root_span:
            root_span.set_tag("pytest.fixture.scope", fixturedef.scope)
            yield


@hookwrapper(tryfirst=True, itemgetter=lambda item, call: item)
def pytest_runtest_makereport(item, call):
    """
    Pytest hook that is called when the report is made for a test.
    This is executed for the setup, call and teardown phases.
    See: https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_runtest_makereport
    """
    sentry_sdk.set_tag("pytest.result", "pending")

    report = yield
    outcome = report.get_result().outcome

    sentry_sdk.set_tag("pytest.result", outcome)

    if call.when == "call" and outcome != "skipped":
        cur_exc_chain = getattr(item, "pytest_sentry_exc_chain", [])

        if call.excinfo is not None:
            item.pytest_sentry_exc_chain = cur_exc_chain = cur_exc_chain + [
                call.excinfo
            ]

        scope = _resolve_scope_marker_value(item.get_closest_marker("sentry_client"))
        integration = scope.client.get_integration(PytestIntegration)

        if (cur_exc_chain and call.excinfo is None) or (integration is not None and integration.always_report):
            for exc_info in cur_exc_chain:
                sentry_sdk.capture_exception((exc_info.type, exc_info.value, exc_info.tb))
