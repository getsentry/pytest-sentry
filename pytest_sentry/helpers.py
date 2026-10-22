# Copyright (c) 2018 Markus Unterwaditzer and individual contributors.
"""Resolve the `sentry_client` marker to the isolation scope to report to."""

from __future__ import annotations

from typing import TYPE_CHECKING

import sentry_sdk
from sentry_sdk.scope import ScopeType

from pytest_sentry.client import Client

if TYPE_CHECKING:
    import pytest

DEFAULT_ISOLATION_SCOPE = sentry_sdk.Scope(ty=ScopeType.ISOLATION)
DEFAULT_ISOLATION_SCOPE.set_client(Client())

_isolation_scope_cache: dict[int, sentry_sdk.Scope] = {}


def _resolve_scope_marker_value(marker: pytest.Mark | None) -> sentry_sdk.Scope:
    """Return the (cached) isolation scope for a `sentry_client` marker.

    Returns:
        The isolation scope to report to.

    """
    key = id(marker)
    if key not in _isolation_scope_cache:
        _isolation_scope_cache[key] = _resolve_uncached(marker)
    return _isolation_scope_cache[key]


def _isolation_scope_with(client: sentry_sdk.client.BaseClient) -> sentry_sdk.Scope:
    scope = sentry_sdk.Scope(ty=ScopeType.ISOLATION)
    scope.set_client(client)
    return scope


def _resolve_uncached(marker: pytest.Mark | None) -> sentry_sdk.Scope:
    # Without a `sentry_client` marker (pytestmark or decorator), use the
    # default scope.
    value: object = DEFAULT_ISOLATION_SCOPE if marker is None else marker.args[0]

    if callable(value):
        # A callable returns the real marker value.
        value = value()

    if value is None:
        # The user explicitly disabled reporting.
        return sentry_sdk.Scope()
    if isinstance(value, str):
        # A DSN string.
        return _isolation_scope_with(Client(value))
    if isinstance(value, dict):
        # Client options.
        return _isolation_scope_with(Client(**value))
    if isinstance(value, Client):
        return _isolation_scope_with(value)
    if isinstance(value, sentry_sdk.Scope):
        return value

    msg = f"The `sentry_client` value must be a client, scope or string, not {type(value)!r}"
    raise RuntimeError(msg)
