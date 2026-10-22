# Copyright (c) 2018 Markus Unterwaditzer and individual contributors.
"""CI environment variables are attached to events as tags and to spans as attributes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

import pytest
import sentry_sdk
from sentry_sdk.scope import use_isolation_scope

import pytest_sentry

if TYPE_CHECKING:
    from sentry_sdk.envelope import Envelope
    from sentry_sdk.types import Event

events: list[Event] = []
spans: list[dict[str, Any]] = []


class _Transport(sentry_sdk.Transport):
    @override
    def capture_envelope(self, envelope: Envelope) -> None:
        if (event := envelope.get_event()) is not None:
            events.append(event)
        for item in envelope.items:
            if item.type == "span" and item.payload.json is not None:
                spans.extend(item.payload.json["items"])


CLIENT = pytest_sentry.Client(transport=_Transport())


@pytest.fixture
def _github_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_RUN_ID", "123abc")
    events.clear()
    spans.clear()


pytestmark = [
    pytest.mark.sentry_client(CLIENT),
    pytest.mark.usefixtures("_github_run_id"),
]


def test_basic(sentry_test_scope: sentry_sdk.Scope) -> None:
    """Error events get the env var tags."""
    with use_isolation_scope(sentry_test_scope):
        sentry_test_scope.capture_message("hi")

    (event,) = events
    assert event["tags"]["pytest_environ.GITHUB_RUN_ID"] == "123abc"


def test_span(request: pytest.FixtureRequest) -> None:
    """Spans get the env var attributes."""

    def check() -> None:
        # Spans are sent in the background.
        CLIENT.flush()
        attributes = {span["name"]: span["attributes"] for span in spans}
        # Spans that end once the env var is set.
        for name in (
            "pytest.fixture.setup _github_run_id",
            "pytest.runtest.call tests/test_envvars.py::test_span",
        ):
            assert attributes[name]["pytest_environ.GITHUB_RUN_ID"]["value"] == "123abc"

    request.addfinalizer(check)
