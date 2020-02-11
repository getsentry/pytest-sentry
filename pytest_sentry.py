import os
import pytest

import sentry_sdk
from sentry_sdk.integrations import Integration

from sentry_sdk import Hub, push_scope, capture_exception


class PytestIntegration(Integration):
    # Right now this integration type is only a carrier for options, and to
    # disable the pytest plugin. `setup_once` is unused.

    identifier = "pytest"

    def __init__(self, always_report=None):
        if always_report is None:
            always_report = os.environ.get(
                "PYTEST_SENTRY_ALWAYS_REPORT", ""
            ).lower() in ("1", "true", "yes")

        self.always_report = always_report

    @staticmethod
    def setup_once():
        pass


class Client(sentry_sdk.Client):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("default_integrations", False)

        import logging

        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.stdlib import StdlibIntegration
        from sentry_sdk.integrations.dedupe import DedupeIntegration
        from sentry_sdk.integrations.modules import ModulesIntegration
        from sentry_sdk.integrations.argv import ArgvIntegration

        integrations = kwargs.setdefault("integrations", [])
        names = set(integration.identifier for integration in integrations)

        default_integrations = [
            LoggingIntegration(level=logging.INFO, event_level=None),
            StdlibIntegration(),
            DedupeIntegration(),
            ModulesIntegration(),
            ArgvIntegration(),
            PytestIntegration(),
        ]

        integrations.extend(
            i for i in default_integrations if i.identifier not in names
        )

        kwargs.setdefault("environment", "test")

        sentry_sdk.Client.__init__(self, *args, **kwargs)


def pytest_load_initial_conftests(early_config, parser, args):
    early_config.addinivalue_line(
        "markers",
        "sentry_client(client=None): Use this client instance for reporting tests. You can also pass a DSN string directly, or a `Hub` if you need it.",
    )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    if call.when == "call":
        hub = _resolve_hub_marker_value(item.get_closest_marker("sentry_client"))
        integration = hub.get_integration(PytestIntegration)
        if integration is not None:
            cur_exc_chain = getattr(item, "pytest_sentry_exc_chain", [])

            if call.excinfo is not None:
                item.pytest_sentry_exc_chain = cur_exc_chain = cur_exc_chain + [
                    call.excinfo
                ]

            if (cur_exc_chain and call.excinfo is None) or integration.always_report:
                _report_flaky_test(hub, item, call, cur_exc_chain)
    yield


def _get_default_hub():
    client = None
    dsn = os.environ.get("PYTEST_SENTRY_DSN", None)
    if dsn:
        client = Client(dsn)

    return Hub(client)


DEFAULT_HUB = _get_default_hub()
del _get_default_hub


def _resolve_hub_marker_value(marker_value):
    if marker_value is None:
        marker_value = DEFAULT_HUB
    else:
        marker_value = marker_value.args[0]

    if callable(marker_value):
        marker_value = marker_value()

    if marker_value is None:
        # user explicitly disabled reporting
        return Hub()

    if isinstance(marker_value, str):
        return Hub(Client(marker_value))

    if isinstance(marker_value, Client):
        return Hub(marker_value)

    if isinstance(marker_value, Hub):
        return marker_value

    raise RuntimeError(
        "The `sentry_client` value must be a client, hub or string, not {}".format(
            repr(type(marker_value))
        )
    )


def _report_flaky_test(hub, item, call, exc_infos):
    with hub:
        with push_scope() as scope:
            scope.add_event_processor(_process_event)

            scope.transaction = _transaction_from_item(item)

            for exc_info in exc_infos:
                capture_exception((exc_info.type, exc_info.value, exc_info.tb))


def _transaction_from_item(item):
    return item.nodeid


def _process_event(event, hint):
    if "exception" in event:
        for exception in event["exception"]["values"]:
            if "stacktrace" in exception:
                _process_stacktrace(exception["stacktrace"])

    if "stacktrace" in event:
        _process_stacktrace(event["stacktrace"])

    return event


def _process_stacktrace(stacktrace):
    for frame in stacktrace["frames"]:
        frame["in_app"] = not frame["module"].startswith(
            ("_pytest.", "pytest.", "pluggy.")
        )
