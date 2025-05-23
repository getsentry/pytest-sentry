import os
import sentry_sdk

from .integration import PytestIntegration


class Client(sentry_sdk.Client):
    """
    A client that is used to report errors from tests.
    Configured via `PYTEST_SENTRY_*` environment variables.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "dsn",
            os.environ.get("PYTEST_SENTRY_DSN", None),
        )
        kwargs.setdefault(
            "traces_sample_rate",
            float(os.environ.get("PYTEST_SENTRY_TRACES_SAMPLE_RATE", 1.0)),
        )
        kwargs.setdefault(
            "profiles_sample_rate",
            float(os.environ.get("PYTEST_SENTRY_PROFILES_SAMPLE_RATE", 0.0)),
        )
        kwargs.setdefault(
            "_experiments",
            {},
        ).setdefault(
            "auto_enabling_integrations",
            True,
        )
        kwargs.setdefault(
            "environment",
            os.environ.get("SENTRY_ENVIRONMENT", "test"),
        )
        kwargs.setdefault("integrations", []).append(PytestIntegration())

        debug = os.environ.get("PYTEST_SENTRY_DEBUG", "").lower() in ("1", "true", "yes")
        kwargs.setdefault("debug", debug)

        sentry_sdk.Client.__init__(self, *args, **kwargs)
