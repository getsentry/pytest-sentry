import pytest

from .conftest import GLOBAL_CLIENT


pytestmark = pytest.mark.sentry_client(GLOBAL_CLIENT)


def test_fixture(sentry_test_scope):
    assert sentry_test_scope.client is GLOBAL_CLIENT


@pytest.mark.sentry_client(None)
def test_func(sentry_test_scope):
    assert not sentry_test_scope.client.is_active()
