from __future__ import absolute_import

import pytest

from pytest_sentry import Client

i = 0

events = []


@pytest.mark.flaky(reruns=2)
@pytest.mark.sentry_client(Client(transport=events.append, traces_sample_rate=0.0))
def test_basic(request):
    global i
    i += 1
    if i < 2:
        1 / 0


@pytest.fixture(scope="session", autouse=True)
def assert_report():
    yield
    (event,) = events
    (exception,) = event["exception"]["values"]
    assert exception["type"] == "ZeroDivisionError"
