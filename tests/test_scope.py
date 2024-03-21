from __future__ import absolute_import

import pytest
import unittest
import sentry_sdk
import pytest_sentry

pytestmark = pytest.mark.sentry_client(pytest_sentry.Client())

_DEFAULT_GLOBAL_SCOPE = sentry_sdk.Scope.get_global_scope()
_DEFAULT_ISOLATION_SCOPE = sentry_sdk.Scope.get_isolation_scope()


def _assert_right_scopes():
    global_scope = sentry_sdk.Scope.get_global_scope()
    isolation_scope = sentry_sdk.Scope.get_isolation_scope()

    assert not global_scope.get_client().is_active()
    assert global_scope is _DEFAULT_GLOBAL_SCOPE

    assert not isolation_scope.get_client().is_active()
    assert isolation_scope is _DEFAULT_ISOLATION_SCOPE


def test_basic():
    _assert_right_scopes()


def test_sentry_test_scope(sentry_test_scope):
    # Ensure that we are within a transaction (started by the fixture)
    assert sentry_test_scope.span is not None


class TestSimpleClass(object):
    def setup_method(self):
        _assert_right_scopes()

    def test_basic(self):
        _assert_right_scopes()

    def teardown_method(self):
        _assert_right_scopes()


class TestUnittestClass(unittest.TestCase):
    def setUp(self):
        _assert_right_scopes()

    def test_basic(self):
        _assert_right_scopes()

    def tearDown(self):
        _assert_right_scopes()
