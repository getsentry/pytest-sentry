# Copyright (c) 2018 Markus Unterwaditzer and individual contributors.
"""Tests run in the default global and isolation scopes."""

import unittest
from typing import override

import pytest
import sentry_sdk

import pytest_sentry

pytestmark = pytest.mark.sentry_client(pytest_sentry.Client())

_DEFAULT_GLOBAL_SCOPE = sentry_sdk.get_global_scope()
_DEFAULT_ISOLATION_SCOPE = sentry_sdk.get_isolation_scope()


def _assert_right_scopes() -> None:
    assert sentry_sdk.get_global_scope() is _DEFAULT_GLOBAL_SCOPE
    assert sentry_sdk.get_isolation_scope() is _DEFAULT_ISOLATION_SCOPE


def test_basic() -> None:
    """Plain test functions."""
    _assert_right_scopes()


class TestSimpleClass:
    """Test classes, including setup and teardown methods."""

    @staticmethod
    def setup_method() -> None:
        """Set up."""
        _assert_right_scopes()

    @staticmethod
    def test_basic() -> None:
        """Test."""
        _assert_right_scopes()

    @staticmethod
    def teardown_method() -> None:
        """Tear down."""
        _assert_right_scopes()


class TestUnittestClass(unittest.TestCase):
    """unittest test cases, including setUp and tearDown."""

    @override
    def setUp(self) -> None:
        _assert_right_scopes()

    def test_basic(self) -> None:  # ruff: ignore[no-self-use] -- unittest calls test methods on the instance
        """Test."""
        _assert_right_scopes()

    @override
    def tearDown(self) -> None:
        _assert_right_scopes()
