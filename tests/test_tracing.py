# Copyright (c) 2018 Markus Unterwaditzer and individual contributors.
"""Fixture setup and test calls are sent as transactions in one trace."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

import pytest
import sentry_sdk

import pytest_sentry

if TYPE_CHECKING:
    from collections.abc import Generator

    from sentry_sdk.envelope import Envelope
    from sentry_sdk.types import Event

transactions: list[Event] = []


class _Transport(sentry_sdk.Transport):
    @override
    def capture_envelope(self, envelope: Envelope) -> None:
        if (transaction := envelope.get_transaction_event()) is not None:
            transactions.append(transaction)


@pytest.fixture(scope="module")
def _assert_report() -> Generator[None]:
    yield

    self_transaction, fixture_transaction, test_transaction = transactions

    assert self_transaction["type"] == "transaction"
    assert self_transaction["transaction"] == "pytest.fixture.setup _assert_report"

    assert fixture_transaction["type"] == "transaction"
    assert fixture_transaction["transaction"] == "pytest.fixture.setup answer"

    assert test_transaction["type"] == "transaction"
    assert (
        test_transaction["transaction"] == "pytest.runtest.call tests/test_tracing.py::test_basic"
    )

    trace_ids = {
        t["contexts"]["trace"]["trace_id"]
        for t in (self_transaction, fixture_transaction, test_transaction)
    }
    assert len(trace_ids) == 1


pytestmark = [
    pytest.mark.sentry_client(pytest_sentry.Client(transport=_Transport())),
    pytest.mark.usefixtures("_assert_report"),
]


@pytest.fixture
def answer() -> int:
    """Return a fixture value.

    Returns:
        42

    """
    return 42


def test_basic(answer: int) -> None:
    """A test with a fixture."""
    assert answer == 42
