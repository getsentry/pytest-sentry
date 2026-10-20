# Copyright (c) 2018 Markus Unterwaditzer and individual contributors.
"""Skipped and xfailed tests are never reported."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

import pytest
import sentry_sdk

import pytest_sentry

if TYPE_CHECKING:
    from collections.abc import Generator

    from sentry_sdk.envelope import Envelope

envelopes: list[Envelope] = []


class _Transport(sentry_sdk.Transport):
    @override
    def capture_envelope(self, envelope: Envelope) -> None:
        envelopes.append(envelope)


def _client() -> pytest_sentry.Client:
    return pytest_sentry.Client(transport=_Transport(), traces_sample_rate=0.0)


@pytest.fixture(scope="module")
def _assert_no_report() -> Generator[None]:
    yield
    assert not envelopes


pytestmark = [pytest.mark.usefixtures("_assert_no_report"), pytest.mark.flaky(reruns=2)]


@pytest.mark.sentry_client(_client())
def test_skip() -> None:
    """`pytest.skip()`."""
    pytest.skip("bye")


@pytest.mark.skipif(condition=True, reason="bye")
@pytest.mark.sentry_client(_client())
def test_skipif() -> None:
    """`@pytest.mark.skipif`."""


@pytest.mark.xfail(condition=True, reason="bye")
@pytest.mark.sentry_client(_client())
def test_mark_xfail() -> None:
    """`@pytest.mark.xfail` on a passing test."""


@pytest.mark.sentry_client(_client())
def test_xfail() -> None:
    """`pytest.xfail()`."""
    pytest.xfail("bye")
