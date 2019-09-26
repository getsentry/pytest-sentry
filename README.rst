=============
pytest-sentry
=============

.. image:: https://travis-ci.com/untitaker/pytest-sentry.svg?branch=master
    :target: https://travis-ci.com/untitaker/pytest-sentry

``pytest-sentry`` is a `pytest <https://pytest.org>`_ plugin that sends error
reports for flaky but ultimately not completely broken tests to `Sentry
<https://sentry.io/>`_.

What and Why
============

Let's say you have a testsuite with some flaky tests that randomly break your
CI build due to network issues, race conditions or other stuff that you don't
want to fix immediately. The known workaround is to retry those tests
automatically, for example using `pytest-rerunfailures
<https://github.com/pytest-dev/pytest-rerunfailures>`_.

One concern against plugins like this is that they just hide the bugs in your
testsuite or even other code. After all your CI build is green and your code
probably works most of the time.

pytest-sentry tries to make that choice a bit easier by tracking flaky test
failures in a place separate from your build status. Sentry is already a
good choice for keeping tabs on all kinds of errors, important or not, in
production, so let's try to use it in testsuites too.

How
===

The prerequisite is that you already make use of ``pytest`` and
``pytest-rerunfailures`` in CI. Now install ``pytest-sentry`` and set the
``PYTEST_SENTRY_DSN`` environment variable to the DSN of a new Sentry project.

Now every test failure that is "fixed" by retrying the test is reported to
Sentry, but still does not break CI. Tests that consistently fail will not be
reported.

Advanced Options
================

``pytest-sentry`` supports marking your tests to use a different DSN, client or
hub per-test. You can use this to provide custom options to the ``Client``
object from the `Sentry SDK for Python
<https://github.com/getsentry/sentry-python>`_::

    import random
    import pytest

    from sentry_sdk import Hub
    from pytest_sentry import Client

    @pytest.mark.sentry_client(None)
    def test_no_sentry():
        # Even though flaky, this test never gets reported to sentry
        assert random.random() > 0.5

    @pytest.mark.sentry_client("MY NEW DSN")
    def test_custom_dsn():
        # Use a different DSN to report errors for this one
        assert random.random() > 0.5

    # Other invocations:

    @pytest.mark.sentry_client(Client("CUSTOM DSN"))
    @pytest.mark.sentry_client(lambda: Client("CUSTOM DSN"))
    @pytest.mark.sentry_client(Hub(Client("CUSTOM DSN")))


The ``Client`` class exposed by ``pytest-sentry`` only has different default
integrations. It disables some of the error-capturing integrations to avoid
sending random expected errors into your project.

Always reporting test failures
==============================

You can always report all test failures to Sentry by setting the environment
variable ``PYTEST_SENTRY_ALWAYS_REPORT=1``.

This can be enabled for builds on the ``master`` or release branch, to catch
certain kinds of tests that are flaky across builds, but consistently fail or
pass within one testrun.

License
=======

Licensed under MIT, see ``LICENSE``.
