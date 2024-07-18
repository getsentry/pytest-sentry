import pytest
import sentry_sdk
from sentry_sdk.scope import use_scope
import pytest_sentry

events = []
envelopes = []


class MyTransport(sentry_sdk.Transport):
    def capture_event(self, event):
        events.append(event)

    def capture_envelope(self, envelope):
        envelopes.append(envelope)
        if envelope.get_event() is not None:
            events.append(envelope.get_event())


@pytest.fixture(autouse=True)
def clear_events(monkeypatch):
    monkeypatch.setenv("GITHUB_RUN_ID", "123abc")
    events.clear()
    envelopes.clear()


pytestmark = pytest.mark.sentry_client(pytest_sentry.Client(transport=MyTransport()))


def test_basic(sentry_test_scope):
    with use_scope(sentry_test_scope):
        sentry_test_scope.capture_message("hi")

    (event,) = events
    assert event["tags"]["pytest_environ.GITHUB_RUN_ID"] == "123abc"


def test_transaction(request):
    @request.addfinalizer
    def _():
        for transaction in envelopes:
            assert (
                transaction.get_transaction_event()["tags"][
                    "pytest_environ.GITHUB_RUN_ID"
                ]
                == "123abc"
            )
