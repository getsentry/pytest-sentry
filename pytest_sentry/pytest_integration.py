import os

import sentry_sdk
from sentry_sdk.integrations import Integration
from sentry_sdk.scope import add_global_event_processor

from .consts import _ENVVARS_AS_TAGS


def _process_stacktrace(stacktrace):
    for frame in stacktrace["frames"]:
        frame["in_app"] = not frame["module"].startswith(
            ("_pytest.", "pytest.", "pluggy.")
        )


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
        @add_global_event_processor
        def processor(event, hint):
            if sentry_sdk.get_client().get_integration(PytestIntegration) is None:
                return event

            for key in _ENVVARS_AS_TAGS:
                value = os.environ.get(key)
                if not value:
                    continue
                event.setdefault("tags", {})["pytest_environ.{}".format(key)] = value

            if "exception" in event:
                for exception in event["exception"]["values"]:
                    if "stacktrace" in exception:
                        _process_stacktrace(exception["stacktrace"])

            if "stacktrace" in event:
                _process_stacktrace(event["stacktrace"])

            return event
