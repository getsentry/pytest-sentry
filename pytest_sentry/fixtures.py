import pytest

from .helpers import _resolve_scope_marker_value


@pytest.fixture
def sentry_test_scope(request):
    """
    Gives back the current scope.
    """

    item = request.node
    return _resolve_scope_marker_value(item.get_closest_marker("sentry_client"))
