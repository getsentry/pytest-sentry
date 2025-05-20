from __future__ import absolute_import

import pytest
import unittest
from sentry_sdk.opentelemetry.scope import PotelScope as Scope
import pytest_sentry

pytestmark = pytest.mark.sentry_client(pytest_sentry.Client())

_DEFAULT_GLOBAL_SCOPE = Scope.get_global_scope()
_DEFAULT_ISOLATION_SCOPE = Scope.get_isolation_scope()


def _assert_right_scopes():
    global_scope = Scope.get_global_scope()
    assert global_scope is _DEFAULT_GLOBAL_SCOPE

    isolation_scope = Scope.get_isolation_scope()
    assert isolation_scope is _DEFAULT_ISOLATION_SCOPE


def test_basic():
    _assert_right_scopes()


def test_sentry_test_scope(sentry_test_scope):
    # Ensure that we are within a root span (started by the pytest_runtest_call hook)
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
