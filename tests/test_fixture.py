# Copyright (c) 2018 Markus Unterwaditzer and individual contributors.
"""The `sentry_test_scope` fixture."""

import pytest
import sentry_sdk

import pytest_sentry

GLOBAL_CLIENT = pytest_sentry.Client()

pytestmark = pytest.mark.sentry_client(GLOBAL_CLIENT)


def test_basic(sentry_test_scope: sentry_sdk.Scope) -> None:
    """The fixture uses the module's client."""
    assert sentry_test_scope.client is GLOBAL_CLIENT


@pytest.mark.sentry_client(None)
def test_func(sentry_test_scope: sentry_sdk.Scope) -> None:
    """`sentry_client(None)` disables reporting."""
    assert not sentry_test_scope.client.is_active()
