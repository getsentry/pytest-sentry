from __future__ import absolute_import

import pytest
import unittest
import sentry_sdk
import pytest_sentry

pytestmark = pytest.mark.sentry_client(pytest_sentry.Client())

_DEFAULT_HUB = sentry_sdk.Hub.current


def _assert_right_hubs():
    for hub in sentry_sdk.Hub.current, sentry_sdk.Hub.main:
        assert hub.client is None
        assert hub is _DEFAULT_HUB


def test_basic():
    _assert_right_hubs()


class TestSimpleClass(object):
    def setup_method(self):
        _assert_right_hubs()

    def test_basic(self):
        _assert_right_hubs()

    def teardown_method(self):
        _assert_right_hubs()


class TestUnittestClass(unittest.TestCase):
    def setUp(self):
        _assert_right_hubs()

    def test_basic(self):
        _assert_right_hubs()

    def tearDown(self):
        _assert_right_hubs()
