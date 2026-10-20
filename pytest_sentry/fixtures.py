# Copyright (c) 2018 Markus Unterwaditzer and individual contributors.
"""Fixtures provided by pytest-sentry."""

import pytest
import sentry_sdk

from pytest_sentry.helpers import _resolve_scope_marker_value


@pytest.fixture
def sentry_test_scope(request: pytest.FixtureRequest) -> sentry_sdk.Scope:
    """Give back the isolation scope this test reports to.

    Returns:
        The test's isolation scope.

    """
    return _resolve_scope_marker_value(request.node.get_closest_marker("sentry_client"))
