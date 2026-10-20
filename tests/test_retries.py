# Copyright (c) 2018 Markus Unterwaditzer and individual contributors.
"""A flaky test that passes on retry is reported once."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

import pytest
import sentry_sdk

import pytest_sentry

if TYPE_CHECKING:
    from collections.abc import Generator

    from sentry_sdk.envelope import Envelope
    from sentry_sdk.types import Event

attempts: list[int] = []
events: list[Event] = []


class _Transport(sentry_sdk.Transport):
    @override
    def capture_envelope(self, envelope: Envelope) -> None:
        if (event := envelope.get_event()) is not None:
            events.append(event)


@pytest.fixture(scope="module")
def _assert_report() -> Generator[None]:
    yield
    (event,) = events
    (exception,) = event["exception"]["values"]
    assert exception["type"] == "ZeroDivisionError"


pytestmark = pytest.mark.usefixtures("_assert_report")


@pytest.mark.flaky(reruns=2)
@pytest.mark.sentry_client(pytest_sentry.Client(transport=_Transport(), traces_sample_rate=0.0))
def test_basic() -> None:
    """Fail on the first attempt only.

    Raises:
        ZeroDivisionError: On the first attempt.

    """
    attempts.append(1)
    if len(attempts) < 2:
        raise ZeroDivisionError
