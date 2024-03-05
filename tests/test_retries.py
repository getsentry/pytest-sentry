from __future__ import absolute_import

import pytest
import sentry_sdk

from pytest_sentry import Client

i = 0

events = []


class MyTransport(sentry_sdk.Transport):
    def capture_event(self, event):
        events.append(event)

    def capture_envelope(self, envelope):
        if envelope.get_event() is not None:
            events.append(envelope.get_event())


@pytest.mark.flaky(reruns=2)
@pytest.mark.sentry_client(Client(transport=MyTransport(), traces_sample_rate=0.0))
def test_basic(request):
    global i
    i += 1
    if i < 2:
        1 / 0


@pytest.fixture(scope="module", autouse=True)
def assert_report():
    yield
    (event,) = events
    (exception,) = event["exception"]["values"]
    assert exception["type"] == "ZeroDivisionError"
