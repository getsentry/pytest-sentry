# Copyright (c) 2018 Markus Unterwaditzer and individual contributors.
"""The Sentry integration that carries pytest-sentry's options."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, override

import sentry_sdk
from sentry_sdk.integrations import Integration
from sentry_sdk.scope import add_global_event_processor

from pytest_sentry.consts import ENVVARS_AS_TAGS

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sentry_sdk.types import Event, Hint

_TRUTHY = frozenset({"1", "true", "yes"})
_NOT_IN_APP = ("_pytest.", "pytest.", "pluggy.")


def _mark_in_app_frames(stacktrace: Mapping[str, object]) -> None:
    frames = stacktrace.get("frames")
    if not isinstance(frames, list):
        return
    for frame in frames:
        if isinstance(frame, dict):
            module = frame.get("module")
            frame["in_app"] = not (isinstance(module, str) and module.startswith(_NOT_IN_APP))


def environ_tags() -> dict[str, str]:
    """Return the CI environment variables that are set, as tags.

    Returns:
        The tags, keyed by `pytest_environ.<name>`.

    """
    return {
        f"pytest_environ.{key}": value
        for key in ENVVARS_AS_TAGS
        if (value := os.environ.get(key, ""))
    }


def _process_event(event: Event, _hint: Hint) -> Event:
    if sentry_sdk.get_client().get_integration(PytestIntegration) is None:
        return event

    event.setdefault("tags", {}).update(environ_tags())

    for exception in event.get("exception", {}).get("values", []):
        if (stacktrace := exception.get("stacktrace")) is not None:
            _mark_in_app_frames(stacktrace)

    if (stacktrace := event.get("stacktrace")) is not None:
        _mark_in_app_frames(stacktrace)

    return event


class PytestIntegration(Integration):
    """Carries pytest-sentry's options; also used to disable the plugin."""

    identifier = "pytest"

    def __init__(self, *, always_report: bool | None = None) -> None:
        """Create the integration.

        `always_report` defaults to the `PYTEST_SENTRY_ALWAYS_REPORT`
        environment variable.
        """
        if always_report is None:
            always_report = os.environ.get("PYTEST_SENTRY_ALWAYS_REPORT", "").lower() in _TRUTHY
        self.always_report = always_report

    @staticmethod
    @override
    def setup_once() -> None:
        add_global_event_processor(_process_event)
