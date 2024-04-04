from __future__ import absolute_import

import pytest
import pytest_sentry

GLOBAL_CLIENT = pytest_sentry.Client()
pytestmark = pytest.mark.sentry_client(GLOBAL_CLIENT)


def test_basic(sentry_test_scope):
    assert sentry_test_scope.client is GLOBAL_CLIENT


@pytest.mark.sentry_client(None)
def test_func(sentry_test_scope):
    assert not sentry_test_scope.client.is_active()
