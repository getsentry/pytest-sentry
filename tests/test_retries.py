import pytest
import pytest_sentry

from .conftest import GLOBAL_TRANSPORT


i = 0


@pytest.mark.flaky(reruns=2)
@pytest.mark.sentry_client(pytest_sentry.Client(transport=GLOBAL_TRANSPORT, traces_sample_rate=0.0))
def test_basic(request):
    global i
    i += 1
    if i < 2:
        1 / 0


@pytest.fixture(scope="module", autouse=True)
def assert_reporting_worked():
    # Run the test
    yield

    # Check if reporting to Sentry was correctly done
    (event,) = GLOBAL_TRANSPORT.events
    (exception,) = event["exception"]["values"]
    assert exception["type"] == "ZeroDivisionError"
