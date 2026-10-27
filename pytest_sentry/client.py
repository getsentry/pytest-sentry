# Copyright (c) 2018 Markus Unterwaditzer and individual contributors.
"""The Sentry client used to report tests."""

import os
from typing import Any, cast

import sentry_sdk

from pytest_sentry.integration import PytestIntegration

_TRUTHY = frozenset({"1", "true", "yes"})

# The op of the span around a whole test, which is ignored to spare quota.
PROTOCOL_OP = "pytest.runtest.protocol"


class Client(sentry_sdk.Client):
    """A client that reports errors from tests.

    Configured via `PYTEST_SENTRY_*` environment variables. Explicitly passed
    options take precedence over the environment.
    """

    def __init__(self, dsn: str | None = None, **options: object) -> None:
        """Create a client, filling in options from the environment."""
        integrations = options.pop("integrations", None)
        ignore_spans = options.pop("ignore_spans", None)
        merged: dict[str, object] = {
            "dsn": dsn if dsn is not None else os.environ.get("PYTEST_SENTRY_DSN"),
            "traces_sample_rate": float(os.environ.get("PYTEST_SENTRY_TRACES_SAMPLE_RATE", "1.0")),
            # The hooks start streamed spans, which need the streaming lifecycle.
            "trace_lifecycle": "stream",
            # Profile each sampled trace, i.e. each test, for sampled sessions.
            "profile_lifecycle": "trace",
            "profile_session_sample_rate": float(
                os.environ.get("PYTEST_SENTRY_PROFILES_SAMPLE_RATE", "0.0")
            ),
            "environment": os.environ.get("SENTRY_ENVIRONMENT", "test"),
            "debug": os.environ.get("PYTEST_SENTRY_DEBUG", "").lower() in _TRUTHY,
        } | options
        merged["integrations"] = [
            *(integrations if isinstance(integrations, list) else []),
            PytestIntegration(),
        ]
        merged["ignore_spans"] = [
            *(ignore_spans if isinstance(ignore_spans, list) else []),
            {"attributes": {"sentry.op": PROTOCOL_OP}},
        ]
        # Options come from users and are forwarded as-is; the SDK validates them.
        sentry_sdk.Client.__init__(self, **cast("dict[str, Any]", merged))
