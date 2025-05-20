from __future__ import absolute_import

import os
import pytest

import wrapt

import sentry_sdk
from sentry_sdk.opentelemetry.scope import PotelScope as Scope, use_scope
from sentry_sdk import capture_exception
from sentry_sdk.integrations import Integration
from sentry_sdk.scope import add_global_event_processor


_ENVVARS_AS_TAGS = frozenset(
    [
        "GITHUB_WORKFLOW",  # The name of the workflow.
        "GITHUB_RUN_ID",  # A unique number for each run within a repository. This number does not change if you re-run the workflow run.
        "GITHUB_RUN_NUMBER",  # A unique number for each run of a particular workflow in a repository. This number begins at 1 for the workflow's first run, and increments with each new run. This number does not change if you re-run the workflow run.
        "GITHUB_ACTION",  # The unique identifier (id) of the action.
        "GITHUB_ACTOR",  # The name of the person or app that initiated the workflow. For example, octocat.
        "GITHUB_REPOSITORY",  # The owner and repository name. For example, octocat/Hello-World.
        "GITHUB_EVENT_NAME",  # The name of the webhook event that triggered the workflow.
        "GITHUB_EVENT_PATH",  # The path of the file with the complete webhook event payload. For example, /github/workflow/event.json.
        "GITHUB_WORKSPACE",  # The GitHub workspace directory path. The workspace directory is a copy of your repository if your workflow uses the actions/checkout action. If you don't use the actions/checkout action, the directory will be empty. For example, /home/runner/work/my-repo-name/my-repo-name.
        "GITHUB_SHA",  # The commit SHA that triggered the workflow. For example, ffac537e6cbbf934b08745a378932722df287a53.
        "GITHUB_REF",  # The branch or tag ref that triggered the workflow. For example, refs/heads/feature-branch-1. If neither a branch or tag is available for the event type, the variable will not exist.
        "GITHUB_HEAD_REF",  # Only set for pull request events. The name of the head branch.
        "GITHUB_BASE_REF",  # Only set for pull request events. The name of the base branch.
        "GITHUB_SERVER_URL",  # Returns the URL of the GitHub server. For example: https://github.com.
        "GITHUB_API_URL",  # Returns the API URL. For example: https://api.github.com.
        # Gitlab CI variables, as defined here https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
        "CI_COMMIT_REF_NAME",  # Branch or tag name
        "CI_JOB_ID",  # Unique job ID
        "CI_JOB_URL",  # Job details URL
        "CI_PIPELINE_ID",  # Unique pipeline ID
        "CI_PROJECT_NAME",
        "CI_PROJECT_PATH",
        "CI_SERVER_URL",
        "GITLAB_USER_NAME",  # The name of the user who started the job.
        # CircleCI variables, as defined here https://circleci.com/docs/variables/#built-in-environment-variables
        "CIRCLE_BRANCH", # The name of the Git branch currently being built.
        "CIRCLE_BUILD_NUM", # The number of the current job. Job numbers are unique for each job.
        "CIRCLE_BUILD_URL", # The URL for the current job on CircleCI.
        "CIRCLE_JOB", # The name of the current job.
        "CIRCLE_NODE_INDEX", # For jobs that run with parallelism enabled, this is the index of the current parallel run.
        "CIRCLE_PR_NUMBER", # The number of the associated GitHub or Bitbucket pull request.
        "CIRCLE_PR_REPONAME", # The name of the GitHub or Bitbucket repository where the pull request was created.
        "CIRCLE_PR_USERNAME", # The GitHub or Bitbucket username of the user who created the pull request.
        "CIRCLE_PROJECT_REPONAME", # The name of the repository of the current project.
        "CIRCLE_PROJECT_USERNAME", # The GitHub or Bitbucket username of the current project.
        "CIRCLE_PULL_REQUEST", # The URL of the associated pull request.
        "CIRCLE_REPOSITORY_URL", # The URL of your GitHub or Bitbucket repository.
        "CIRCLE_SHA1", # The SHA1 hash of the last commit of the current build.
        "CIRCLE_TAG", # The name of the git tag, if the current build is tagged.
        "CIRCLE_USERNAME", # The GitHub or Bitbucket username of the user who triggered the pipeline.
        "CIRCLE_WORKFLOW_ID", # A unique identifier for the workflow instance of the current job.
        "CIRCLE_WORKFLOW_JOB_ID", # A unique identifier for the current job.
        "CIRCLE_WORKFLOW_WORKSPACE_ID", # An identifier for the workspace of the current job.
    ]
)


class PytestIntegration(Integration):
    # Right now this integration type is only a carrier for options, and to
    # disable the pytest plugin. `setup_once` is unused.

    identifier = "pytest"

    def __init__(self, always_report=None):
        if always_report is None:
            always_report = os.environ.get(
                "PYTEST_SENTRY_ALWAYS_REPORT", ""
            ).lower() in ("1", "true", "yes")

        self.always_report = always_report

    @staticmethod
    def setup_once():
        @add_global_event_processor
        def procesor(event, hint):
            if Scope.get_client().get_integration(PytestIntegration) is None:
                return event

            for key in _ENVVARS_AS_TAGS:
                value = os.environ.get(key)
                if not value:
                    continue
                event.setdefault("tags", {})["pytest_environ.{}".format(key)] = value

            if "exception" in event:
                for exception in event["exception"]["values"]:
                    if "stacktrace" in exception:
                        _process_stacktrace(exception["stacktrace"])

            if "stacktrace" in event:
                _process_stacktrace(event["stacktrace"])

            return event


class Client(sentry_sdk.Client):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("dsn", os.environ.get("PYTEST_SENTRY_DSN", None))
        kwargs.setdefault(
            "traces_sample_rate",
            float(os.environ.get("PYTEST_SENTRY_TRACES_SAMPLE_RATE", 1.0)),
        )
        kwargs.setdefault("profiles_sample_rate", float(os.environ.get("PYTEST_SENTRY_PROFILES_SAMPLE_RATE", 0.0)))
        kwargs.setdefault("_experiments", {}).setdefault(
            "auto_enabling_integrations", True
        )
        kwargs.setdefault("environment", os.environ.get("SENTRY_ENVIRONMENT", "test"))
        kwargs.setdefault("integrations", []).append(PytestIntegration())

        sentry_sdk.Client.__init__(self, *args, **kwargs)


def hookwrapper(itemgetter, **kwargs):
    """
    A version of pytest.hookimpl that sets the current scope to the correct one
    and skips the hook if the integration is disabled.

    Assumes the function is a hookwrapper, ie yields once
    """

    @wrapt.decorator
    def _with_scope(wrapped, instance, args, kwargs):
        item = itemgetter(*args, **kwargs)
        scope = _resolve_scope_marker_value(item.get_closest_marker("sentry_client"))

        if scope.client.get_integration(PytestIntegration) is None:
            yield
        else:
            with use_scope(scope):
                gen = wrapped(*args, **kwargs)

            while True:
                try:
                    with use_scope(scope):
                        chunk = next(gen)

                    y = yield chunk

                    with use_scope(scope):
                        gen.send(y)

                except StopIteration:
                    break

    def inner(f):
        return pytest.hookimpl(hookwrapper=True, **kwargs)(_with_scope(f))

    return inner


def pytest_load_initial_conftests(early_config, parser, args):
    early_config.addinivalue_line(
        "markers",
        "sentry_client(client=None): Use this client instance for reporting tests. You can also pass a DSN string directly, or a `Scope` if you need it.",
    )


def _start_transaction(**kwargs):
    with sentry_sdk.continue_trace(dict(Scope.get_current_scope().iter_trace_propagation_headers())):
        with sentry_sdk.start_span(**kwargs) as root_span:
            return root_span


@hookwrapper(itemgetter=lambda item: item)
def pytest_runtest_protocol(item):
    op = "pytest.runtest.protocol"

    name = item.nodeid

    # We use the full name including parameters because then we can identify
    # how often a single test has run as part of the same GITHUB_RUN_ID.
    # Purposefully drop transaction to spare quota. We only created it to
    # have a trace_id to correlate by.
    with _start_transaction(op=op, name="{} {}".format(op, name), sampled=False) as tx:
        yield


@hookwrapper(itemgetter=lambda item: item)
def pytest_runtest_call(item):
    op = "pytest.runtest.call"

    name = item.nodeid

    # We use the full name including parameters because then we can identify
    # how often a single test has run as part of the same GITHUB_RUN_ID.

    with _start_transaction(op=op, name="{} {}".format(op, name)):
        yield


@hookwrapper(itemgetter=lambda fixturedef, request: request._pyfuncitem)
def pytest_fixture_setup(fixturedef, request):
    op = "pytest.fixture.setup"
    with _start_transaction(
        op=op, name="{} {}".format(op, fixturedef.argname)
    ) as transaction:
        transaction.set_tag("pytest.fixture.scope", fixturedef.scope)
        yield


@hookwrapper(tryfirst=True, itemgetter=lambda item, call: item)
def pytest_runtest_makereport(item, call):
    sentry_sdk.set_tag("pytest.result", "pending")
    report = yield
    outcome = report.get_result().outcome
    sentry_sdk.set_tag("pytest.result", outcome)

    if call.when == "call" and outcome != "skipped":
        cur_exc_chain = getattr(item, "pytest_sentry_exc_chain", [])

        if call.excinfo is not None:
            item.pytest_sentry_exc_chain = cur_exc_chain = cur_exc_chain + [
                call.excinfo
            ]

        integration = Scope.get_client().get_integration(PytestIntegration)

        if (cur_exc_chain and call.excinfo is None) or integration.always_report:
            for exc_info in cur_exc_chain:
                capture_exception((exc_info.type, exc_info.value, exc_info.tb))


DEFAULT_SCOPE = Scope(client=Client())

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
        return Scope()

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

    if isinstance(marker_value, Scope):
        return marker_value

    raise RuntimeError(
        "The `sentry_client` value must be a client, scope or string, not {}".format(
            repr(type(marker_value))
        )
    )


@pytest.fixture
def sentry_test_scope(request):
    """
    Gives back the current scope.
    """

    item = request.node
    return _resolve_scope_marker_value(item.get_closest_marker("sentry_client"))


def _process_stacktrace(stacktrace):
    for frame in stacktrace["frames"]:
        frame["in_app"] = not frame["module"].startswith(
            ("_pytest.", "pytest.", "pluggy.")
        )
