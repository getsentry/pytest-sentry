import pytest
from .conftest import GLOBAL_CLIENT


pytestmark = pytest.mark.sentry_client(GLOBAL_CLIENT)


@pytest.fixture
def foo_fixture():
    return 42


def test_basic(foo_fixture):
    assert foo_fixture == 42


@pytest.fixture(scope="module", autouse=True)
def assert_reporting_worked():
    GLOBAL_CLIENT.transport.flush()

    # Run the test
    yield

    # Check if reporting to Sentry was correctly done
    self_transaction, fixture_transaction, test_transaction = GLOBAL_CLIENT.transport.transactions

    assert self_transaction["type"] == "transaction"
    assert self_transaction["transaction"] == "pytest.fixture.setup assert_reporting_worked"

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
