import pytest
import pytest_sentry

import sentry_sdk


transactions = []


class MyTransport(sentry_sdk.Transport):
    def __init__(self):
        pass

    def capture_envelope(self, envelope):
        transactions.append(envelope.get_transaction_event())


GLOBAL_TRANSPORT = MyTransport()
GLOBAL_CLIENT = pytest_sentry.Client(transport=GLOBAL_TRANSPORT)

pytestmark = pytest.mark.sentry_client(GLOBAL_CLIENT)


@pytest.fixture
def foo_fixture():
    return 42


def test_basic(foo_fixture):
    assert foo_fixture == 42


@pytest.fixture(scope="module", autouse=True)
def assert_report():
    yield

    self_transaction, fixture_transaction, test_transaction = transactions

    assert self_transaction["type"] == "transaction"
    assert self_transaction["transaction"] == "pytest.fixture.setup assert_report"

    assert fixture_transaction["type"] == "transaction"
    assert fixture_transaction["transaction"] == "pytest.fixture.setup foo_fixture"

    assert test_transaction["type"] == "transaction"
    assert (
        test_transaction["transaction"]
        == "pytest.runtest.call tests/test_tracing.py::test_basic"
    )

    assert (
        fixture_transaction["contexts"]["trace"]["trace_id"]
        == test_transaction["contexts"]["trace"]["trace_id"]
    )
    assert (
        self_transaction["contexts"]["trace"]["trace_id"]
        == fixture_transaction["contexts"]["trace"]["trace_id"]
    )
