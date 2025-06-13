import os
import pytest
import pytest_sentry

from .conftest import GLOBAL_CLIENT


pytestmark = pytest.mark.sentry_client(GLOBAL_CLIENT)


def test_dsn_from_envvar(sentry_test_scope):
    os.environ["SENTRY_DSN"] = "https://foo@bar.ingest.sentry.io/123"
    client = pytest_sentry.Client()

    assert client.options["dsn"] == "https://foo@bar.ingest.sentry.io/123"

    del os.environ["SENTRY_DSN"]
