import sentry_sdk
from sentry_sdk.scope import ScopeType
from sentry_sdk.opentelemetry.scope import setup_scope_context_management

from pytest_sentry.client import Client


setup_scope_context_management()
DEFAULT_ISOLATION_SCOPE = sentry_sdk.Scope(ty=ScopeType.ISOLATION)
DEFAULT_ISOLATION_SCOPE.set_client(Client())
DEFAULT_CURRENT_SCOPE = sentry_sdk.Scope(ty=ScopeType.CURRENT)
DEFAULT_CURRENT_SCOPE.set_client(Client())

_scope_cache = {}


def _resolve_scope_marker_value(marker_value):
    if id(marker_value) not in _scope_cache:
        _scope_cache[id(marker_value)] = rv = _resolve_scope_marker_value_uncached(
            marker_value
        )
        return rv

    return _scope_cache[id(marker_value)]


def _resolve_scope_marker_value_uncached(marker_value):
    if marker_value is None:
        # If no special configuration is provided
        # (like pytestmark or @pytest.mark.sentry_client() decorator)
        # use the default scope
        marker_value = (DEFAULT_ISOLATION_SCOPE, DEFAULT_CURRENT_SCOPE)
    else:
        marker_value = marker_value.args[0]

    if callable(marker_value):
        # If a callable is provided, call it to get the real marker value
        marker_value = marker_value()

    if marker_value is None:
        # The user explicitly disabled reporting
        return (sentry_sdk.Scope(ty=ScopeType.ISOLATION), sentry_sdk.Scope(ty=ScopeType.CURRENT))

    if isinstance(marker_value, str):
        # If a DSN string is provided, create a new client and use that
        isolation_scope = sentry_sdk.get_isolation_scope()
        isolation_scope.set_client(Client(marker_value))
        current_scope = sentry_sdk.get_current_scope()
        current_scope.set_client(Client(marker_value))
        return (isolation_scope, current_scope)

    if isinstance(marker_value, dict):
        # If a dict is provided, create a new client using the dict as Client options
        isolation_scope = sentry_sdk.get_isolation_scope()
        isolation_scope.set_client(Client(**marker_value))
        current_scope = sentry_sdk.get_current_scope()
        current_scope.set_client(Client(**marker_value))
        return (isolation_scope, current_scope)

    if isinstance(marker_value, Client):
        # If a Client instance is provided, use that
        isolation_scope = sentry_sdk.get_isolation_scope()
        isolation_scope.set_client(marker_value)
        current_scope = sentry_sdk.get_current_scope()
        current_scope.set_client(marker_value)
        return (isolation_scope, current_scope)

    if isinstance(marker_value, sentry_sdk.Scope):
        # If a Scope instance is provided, use the client from it
        isolation_scope = sentry_sdk.get_isolation_scope()
        isolation_scope.set_client(marker_value.client)
        current_scope = sentry_sdk.get_current_scope()
        current_scope.set_client(marker_value.client)
        return (isolation_scope, current_scope)

    raise RuntimeError(
        "The `sentry_client` value must be a client, scope or string, not {}".format(
            repr(type(marker_value))
        )
    )
