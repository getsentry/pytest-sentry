# Copyright (c) 2018 Markus Unterwaditzer and individual contributors.
"""CI environment variables are attached to events as tags."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

import pytest
import sentry_sdk

import pytest_sentry

if TYPE_CHECKING:
    from sentry_sdk.envelope import Envelope
    from sentry_sdk.types import Event

events: list[Event] = []
envelopes: list[Envelope] = []


class _Transport(sentry_sdk.Transport):
    @override
    def capture_envelope(self, envelope: Envelope) -> None:
        envelopes.append(envelope)
        if (event := envelope.get_event()) is not None:
            events.append(event)


@pytest.fixture
def _github_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_RUN_ID", "123abc")
    events.clear()
    envelopes.clear()


pytestmark = [
    pytest.mark.sentry_client(pytest_sentry.Client(transport=_Transport())),
    pytest.mark.usefixtures("_github_run_id"),
]


def test_basic(sentry_test_scope: sentry_sdk.Scope) -> None:
    """Error events get the env var tags."""
    with sentry_sdk.use_isolation_scope(sentry_test_scope):
        sentry_test_scope.capture_message("hi")

    (event,) = events
    assert event["tags"]["pytest_environ.GITHUB_RUN_ID"] == "123abc"


def test_transaction(request: pytest.FixtureRequest) -> None:
    """Transactions get the env var tags."""

    def check() -> None:
        for envelope in envelopes:
            transaction = envelope.get_transaction_event()
            assert transaction is not None
            assert transaction["tags"]["pytest_environ.GITHUB_RUN_ID"] == "123abc"

    request.addfinalizer(check)
