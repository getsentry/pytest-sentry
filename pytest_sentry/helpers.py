import sentry_sdk

from pytest_sentry.client import Client


DEFAULT_SCOPE = sentry_sdk.Scope(client=Client())

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
        marker_value = DEFAULT_SCOPE
    else:
        marker_value = marker_value.args[0]

    if callable(marker_value):
        marker_value = marker_value()

    if marker_value is None:
        # user explicitly disabled reporting
        return sentry_sdk.Scope()

    if isinstance(marker_value, str):
        scope = sentry_sdk.get_current_scope()
        scope.set_client(Client(marker_value))
        return scope

    if isinstance(marker_value, dict):
        scope = sentry_sdk.get_current_scope()
        scope.set_client(Client(**marker_value))
        return scope

    if isinstance(marker_value, Client):
        scope = sentry_sdk.get_current_scope()
        scope.set_client(marker_value)
        return scope

    if isinstance(marker_value, sentry_sdk.Scope):
        scope = sentry_sdk.get_current_scope()
        scope.set_client(marker_value.client)
        return marker_value

    raise RuntimeError(
        "The `sentry_client` value must be a client, scope or string, not {}".format(
            repr(type(marker_value))
        )
    )
