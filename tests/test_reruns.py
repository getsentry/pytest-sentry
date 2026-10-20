# Copyright (c) 2018 Markus Unterwaditzer and individual contributors.
"""Reruns are reported once per failed attempt and tagged with the attempt."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

INNER_TESTS = """
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
        line = json.dumps({
            "exception": event["exception"]["values"][-1]["value"].splitlines()[0],
            "tags": {k: v for k, v in event["tags"].items() if k.startswith("pytest.")},
        })
        with open(os.environ["EVENTS_FILE"], "a") as f:
            f.write(line + "\\n")


pytestmark = pytest.mark.sentry_client(
    pytest_sentry.Client(transport=FileTransport(), traces_sample_rate=0.0)
)

attempts = {"flaky": 0, "broken": 0}


def test_flaky():
    attempts["flaky"] += 1
    assert attempts["flaky"] > 2, f"flaky {attempts['flaky']}"


def test_broken():
    attempts["broken"] += 1
    assert False, f"broken {attempts['broken']}"


def test_ok():
    pass
"""

type _Reported = tuple[str, str, str, str]


def _run_inner(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch, *, always_report: bool
) -> list[_Reported]:
    pytester.makepyfile(test_inner=INNER_TESTS)
    events_file = pytester.path / "events.jsonl"
    monkeypatch.setenv("EVENTS_FILE", str(events_file))
    monkeypatch.setenv("PYTEST_SENTRY_ALWAYS_REPORT", "1" if always_report else "")

    result = pytester.runpytest_subprocess("-p", "no:cacheprovider", "--reruns=2")
    assert result.ret == 1, result.stdout.str()

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


def test_always_report_sends_each_failed_attempt_once(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each failed attempt is reported once; the last one is final."""
    assert _run_inner(pytester, monkeypatch, always_report=True) == [
        ("broken 1", "failed", "1", "false"),
        ("broken 2", "failed", "2", "false"),
        ("broken 3", "failed", "3", "true"),
        ("flaky 1", "failed", "1", "false"),
        ("flaky 2", "failed", "2", "false"),
    ]


def test_default_reports_flaky_tests_once_they_pass(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    """By default only flaky tests are reported, once they pass."""
    assert _run_inner(pytester, monkeypatch, always_report=False) == [
        ("flaky 1", "passed", "3", "true"),
        ("flaky 2", "passed", "3", "true"),
    ]
