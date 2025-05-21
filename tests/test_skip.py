import pytest
import pytest_sentry


events = []


@pytest.mark.flaky(reruns=2)
@pytest.mark.sentry_client(pytest_sentry.Client(transport=events.append, traces_sample_rate=0.0))
def test_skip():
    pytest.skip("bye")


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(True, reason="bye")
@pytest.mark.sentry_client(pytest_sentry.Client(transport=events.append, traces_sample_rate=0.0))
def test_skipif():
    pass


@pytest.mark.flaky(reruns=2)
@pytest.mark.xfail(True, reason="bye")
@pytest.mark.sentry_client(pytest_sentry.Client(transport=events.append, traces_sample_rate=0.0))
def test_mark_xfail():
    pass


@pytest.mark.flaky(reruns=2)
@pytest.mark.sentry_client(pytest_sentry.Client(transport=events.append, traces_sample_rate=0.0))
def test_xfail():
    pytest.xfail("bye")


@pytest.fixture(scope="session", autouse=True)
def assert_report():
    yield
    assert not events
