import pytest
import pytest_sentry


GLOBAL_CLIENT = pytest_sentry.Client()

pytestmark = pytest.mark.sentry_client(GLOBAL_CLIENT)


def test_basic(sentry_test_scope):
    (isolation_scope, current_scope) = sentry_test_scope
    assert isolation_scope.client is GLOBAL_CLIENT
    assert current_scope.client is GLOBAL_CLIENT


@pytest.mark.sentry_client(None)
def test_func(sentry_test_scope):
    (isolation_scope, current_scope) = sentry_test_scope
    assert not isolation_scope.client.is_active()
    assert not current_scope.client.is_active()
