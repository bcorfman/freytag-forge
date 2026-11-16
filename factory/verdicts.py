"""Worker-safe representations of factory check, judge, and holdout results."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Literal

VerdictSource = Literal["check", "judge", "holdout"]


@dataclass
class Verdict:
    source: VerdictSource
    passed: bool
    exit_code: int | None
    output: str
    reasoning: str | None = None
    scenario_text: str | None = None
    transcript: str | None = None


def report_hash(text: str) -> str:
    """Return the short stable identifier used in worker reports."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _redact(text: str, secrets: list[str | None]) -> str:
    present = sorted({secret for secret in secrets if secret}, key=len, reverse=True)
    for secret in present:
        text = re.sub(re.escape(secret), "[redacted]", text, flags=re.IGNORECASE)
    return text


def _values(report: object):
    if isinstance(report, dict):
        for value in report.values():
            yield from _values(value)
    elif isinstance(report, (list, tuple, set)):
        for value in report:
            yield from _values(value)
    else:
        yield report


def assert_no_leak(report: dict, v: Verdict) -> None:
    """Reject a report containing either sensitive source text."""

    sensitive = [text.casefold() for text in (v.reasoning, v.scenario_text) if text]
    for value in _values(report):
        if isinstance(value, str) and any(secret in value.casefold() for secret in sensitive):
            raise ValueError("worker report contains protected verdict text")


def to_worker_report(v: Verdict) -> dict:
    """Project a verdict to the information a worker is allowed to receive."""

    if v.source == "check":
        report = {
            "source": v.source,
            "passed": v.passed,
            "exit_code": v.exit_code,
            "output": v.output,
        }
    elif v.source == "judge":
        report = {
            "source": v.source,
            "passed": v.passed,
        }
        if not v.passed:
            report["transcript"] = _redact(v.transcript or "", [v.reasoning, v.scenario_text])
        if v.reasoning:
            report["reasoning_hash"] = report_hash(v.reasoning)
    elif v.source == "holdout":
        report = {
            "source": v.source,
            "passed": v.passed,
            "scenario_hash": report_hash(v.scenario_text or ""),
        }
        if not v.passed:
            report["transcript"] = _redact(v.transcript or "", [v.reasoning, v.scenario_text])
    else:
        raise ValueError(f"unsupported verdict source: {v.source}")

    assert_no_leak(report, v)
    return report


def strip_for_worker(records: list[Verdict]) -> list[dict]:
    return [to_worker_report(record) for record in records]
