# Copyright (c) 2018 Markus Unterwaditzer and individual contributors.
"""Fixture setup and test calls are sent as segment spans in one trace."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

import pytest
import sentry_sdk

import pytest_sentry

if TYPE_CHECKING:
    from collections.abc import Generator

    from sentry_sdk.envelope import Envelope

spans: list[dict[str, Any]] = []


class _Transport(sentry_sdk.Transport):
    @override
    def capture_envelope(self, envelope: Envelope) -> None:
        for item in envelope.items:
            if item.type == "span" and item.payload.json is not None:
                spans.extend(item.payload.json["items"])


CLIENT = pytest_sentry.Client(transport=_Transport())


@pytest.fixture(scope="module")
def _assert_report() -> Generator[None]:
    yield

    # Spans are sent in the background.
    CLIENT.flush()
    self_span, fixture_span, test_span = spans

    assert self_span["is_segment"]
    assert self_span["name"] == "pytest.fixture.setup _assert_report"
    assert self_span["attributes"]["sentry.op"]["value"] == "pytest.fixture.setup"
    assert self_span["attributes"]["pytest.fixture.scope"]["value"] == "module"

    assert fixture_span["is_segment"]
    assert fixture_span["name"] == "pytest.fixture.setup answer"

    assert test_span["is_segment"]
    assert test_span["name"] == "pytest.runtest.call tests/test_tracing.py::test_basic"
    assert test_span["attributes"]["sentry.op"]["value"] == "pytest.runtest.call"

    trace_ids = {s["trace_id"] for s in (self_span, fixture_span, test_span)}
    assert len(trace_ids) == 1


pytestmark = [
    pytest.mark.sentry_client(CLIENT),
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
