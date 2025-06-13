import pytest
import pytest_sentry

from .conftest import GLOBAL_TRANSPORT


@pytest.mark.flaky(reruns=2)
@pytest.mark.sentry_client(pytest_sentry.Client(transport=GLOBAL_TRANSPORT, traces_sample_rate=0.0))
def test_skip():
    pytest.skip("bye")


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(True, reason="bye")
@pytest.mark.sentry_client(pytest_sentry.Client(transport=GLOBAL_TRANSPORT, traces_sample_rate=0.0))
def test_skipif():
    pass


@pytest.mark.flaky(reruns=2)
@pytest.mark.xfail(True, reason="bye")
@pytest.mark.sentry_client(pytest_sentry.Client(transport=GLOBAL_TRANSPORT, traces_sample_rate=0.0))
def test_mark_xfail():
    pass


@pytest.mark.flaky(reruns=2)
@pytest.mark.sentry_client(pytest_sentry.Client(transport=GLOBAL_TRANSPORT, traces_sample_rate=0.0))
def test_xfail():
    pytest.xfail("bye")


@pytest.fixture(scope="session", autouse=True)
def assert_reporting_worked():
    # Run the test
    yield

    # Check if reporting to Sentry was correctly done
    assert len(GLOBAL_TRANSPORT.events) == 0
