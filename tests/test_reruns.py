import json
import os
import subprocess
import sys
import textwrap


INNER_TESTS = textwrap.dedent(
    """
    import json
    import os

    import pytest
    import pytest_sentry
    import sentry_sdk


    class FileTransport(sentry_sdk.Transport):
        def capture_envelope(self, envelope):
            event = envelope.get_event()
            if event is None:
                return
            with open(os.environ["EVENTS_FILE"], "a") as f:
                f.write(json.dumps({
                    "exception": event["exception"]["values"][-1]["value"].splitlines()[0],
                    "tags": {k: v for k, v in event.get("tags", {}).items() if k.startswith("pytest.")},
                }) + "\\n")


    pytestmark = pytest.mark.sentry_client(
        pytest_sentry.Client(transport=FileTransport(), traces_sample_rate=0.0)
    )

    attempts = {"flaky": 0, "broken": 0}


    def test_flaky():
        attempts["flaky"] += 1
        assert attempts["flaky"] > 2, "flaky {}".format(attempts["flaky"])


    def test_broken():
        attempts["broken"] += 1
        assert False, "broken {}".format(attempts["broken"])


    def test_ok():
        pass
    """
)


def run_inner(tmp_path, always_report):
    (tmp_path / "test_inner.py").write_text(INNER_TESTS)
    events_file = tmp_path / "events.jsonl"
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST_")}
    env["EVENTS_FILE"] = str(events_file)
    env["PYTEST_SENTRY_ALWAYS_REPORT"] = "1" if always_report else ""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--reruns=2", "test_inner.py"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    if not events_file.exists():
        return []
    events = [json.loads(line) for line in events_file.read_text().splitlines()]
    return sorted(
        (
            e["exception"],
            e["tags"]["pytest.result"],
            e["tags"]["pytest.attempt"],
            e["tags"]["pytest.final_attempt"],
        )
        for e in events
    )


def test_always_report_sends_each_failed_attempt_once(tmp_path):
    assert run_inner(tmp_path, always_report=True) == [
        ("broken 1", "failed", "1", "false"),
        ("broken 2", "failed", "2", "false"),
        ("broken 3", "failed", "3", "true"),
        ("flaky 1", "failed", "1", "false"),
        ("flaky 2", "failed", "2", "false"),
    ]


def test_default_reports_flaky_tests_once_they_pass(tmp_path):
    assert run_inner(tmp_path, always_report=False) == [
        ("flaky 1", "passed", "3", "true"),
        ("flaky 2", "passed", "3", "true"),
    ]
