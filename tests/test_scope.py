from __future__ import absolute_import

import pytest
import unittest
import sentry_sdk
import pytest_sentry

pytestmark = pytest.mark.sentry_client(pytest_sentry.Client())

_DEFAULT_SCOPE = sentry_sdk.Scope.get_isolation_scope()


def _assert_right_scopes():
    for scope in (
        sentry_sdk.Scope.get_global_scope(),
        sentry_sdk.Scope.get_isolation_scope(),
    ):
        assert not scope.get_client().is_active()
        assert scope is _DEFAULT_SCOPE


def test_basic():
    _assert_right_scopes()


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
