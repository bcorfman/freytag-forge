"""Probe the semantic earning boundary for the hidden scene 1B bench clues."""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from scripts.ringer.environment_narration import j1_scope_probe as scope
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.jev import JevClient
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import StoryPackage

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_PATH = ROOT / "data/stories/continuity-initiative"
SAMPLES = 10
ARMS = ("P1", "P0")
INPUTS = (
    ("u1", "Look under the park bench."),
    ("u2", "Feel beneath the park bench."),
    ("n1", "Inspect the park bench."),
    ("n2", "Search the park bench."),
    ("n3", "Examine Michelle's photograph."),
    ("n4", "Inspect the storm drain."),
)
EXPECTED_EVALUATIONS = len(ARMS) * len(INPUTS) * SAMPLES
DISCOVERY = "k_sl_1b_d_r1"
POINTER = "k_sl_1b_e_r1"
STOP_STATUSES = {401: "auth_error", 402: "quota_error", 403: "auth_error", 429: "http_429"}
COST_PER_MILLION_INPUT_TOKENS = scope.COST_PER_MILLION_INPUT_TOKENS
DEFAULT_MAX_CALLS = EXPECTED_EVALUATIONS
DEFAULT_MAX_USD = 0.02


class _StopEvaluation(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _error(message: str) -> int:
    print(f"hidden bench matcher probe: {message}", file=sys.stderr)
    return 1


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _package_state(package: StoryPackage) -> RuntimeState:
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "1B"
    apply_scene_placements(package, state.facts, "1B")
    state.phase = next(scene.metadata.freytag_phase for scene in package.scenes if scene.metadata.scene_id == "1B")
    state._assert_scene_entry_fact("1B")
    state.active_event_ids.update(
        storylet.id for storylet in package.storylet_routes.storylets if storylet.scene_id == "1B"
    )
    return state


def _head_package() -> StoryPackage:
    archive = subprocess.run(
        ["git", "archive", "HEAD", "data/stories/continuity-initiative"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    with tempfile.TemporaryDirectory(prefix="hidden-bench-head-", dir="/tmp") as temporary:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
            tar.extractall(temporary, filter="data")
        return load_story_package(Path(temporary) / "data/stories/continuity-initiative")


@contextmanager
def _semantic_reveal_enabled():
    previous = os.environ.get("FREYTAG_SEMANTIC_REVEAL")
    os.environ["FREYTAG_SEMANTIC_REVEAL"] = "1"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("FREYTAG_SEMANTIC_REVEAL", None)
        else:
            os.environ["FREYTAG_SEMANTIC_REVEAL"] = previous


def _shortlist(provider: CloudflareTurnProvider) -> tuple[str, ...]:
    universe = provider._reveal_universe()
    candidates = provider._eligible_reveal_candidates(universe)
    projection = provider.last_projection
    visible_ids = {candidate.id for candidate in projection.candidates} if projection is not None else set()
    return tuple(
        candidate.id
        for candidate in candidates
        if candidate.id in visible_ids and (candidate.earn_when or candidate.statement)
    )[:6]


def _planned() -> list[dict[str, Any]]:
    return [
        {"arm": arm, "input_id": input_id, "command": command, "sample": sample}
        for arm in ARMS
        for input_id, command in INPUTS
        for sample in range(1, SAMPLES + 1)
    ]


def _answer_scores(answers: object, shortlist: tuple[str, ...]) -> tuple[dict[str, object], bool]:
    if not isinstance(answers, dict):
        return {}, False
    scores: dict[str, object] = {}
    usable = True
    for candidate_id in shortlist:
        answer = answers.get(candidate_id)
        if (
            not isinstance(answer, dict)
            or isinstance(answer.get("noul"), bool)
            or not isinstance(answer.get("noul"), (int, float))
        ):
            usable = False
            continue
        scores[candidate_id] = answer["noul"]
    return scores, usable


def _stop_reason(status: int | None) -> str | None:
    if status in STOP_STATUSES:
        return STOP_STATUSES[status]
    if isinstance(status, int) and status >= 500:
        return "server_error"
    return None


def _evaluate(package: StoryPackage, planned: dict[str, Any], client_factory=None):
    state = _package_state(package)
    if client_factory is None:
        client_factory = JevClient.from_environment
    client = client_factory()
    answers: object = None
    semantic_error: str | None = None
    stop_reason: str | None = None
    provider = None

    def semantic_ask(request_state: object, questions: object) -> dict | None:
        nonlocal answers, semantic_error, stop_reason
        try:
            answers = client.ask(request_state, questions)
        except Exception as error:
            semantic_error = type(error).__name__
            raise
        status = getattr(client, "last_status", None)
        stop_reason = _stop_reason(status)
        if stop_reason is not None:
            semantic_error = stop_reason
            raise _StopEvaluation(stop_reason)
        return answers

    try:
        provider = CloudflareTurnProvider(
            worker_url="",
            token="",
            state=state,
            semantic_ask=semantic_ask,
        )
        provider.last_projection = provider.projector.project(state, "player", planned["command"])
        shortlist = _shortlist(provider)
        handoff = provider._semantic_authored_handoff(planned["command"])
    except _StopEvaluation as error:
        stop_reason = error.reason
        handoff = None
        shortlist = _shortlist(provider) if provider is not None else ()
    except Exception as error:
        semantic_error = type(error).__name__
        handoff = None
        shortlist = _shortlist(provider) if provider is not None else ()

    scores, usable = _answer_scores(answers, shortlist)
    matched_ids = [handoff.candidate.id] if handoff is not None else []
    row = {
        "arm": planned["arm"],
        "input_id": planned["input_id"],
        "command": planned["command"],
        "sample": planned["sample"],
        "shortlist_ids": list(shortlist),
        "raw_scores": scores,
        "matched_ids": matched_ids,
        "http_call_count": getattr(client, "request_count", 0),
        "usable": usable,
        "error": semantic_error,
    }
    return row, stop_reason


def _measure(package_by_arm: dict[str, StoryPackage]) -> tuple[list[dict[str, Any]], int, float]:
    calls: list[dict[str, Any]] = []
    token_chars = 0

    class FakeClient:
        request_count = 0
        last_status = None

        def ask(self, request_state: object, questions: object) -> dict[str, object]:
            nonlocal token_chars
            calls.append({"state": request_state, "questions": questions})
            token_chars += len(
                json.dumps(
                    {"state": request_state, "questions": questions},
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
            self.request_count += 1
            return {candidate_id: {"noul": 0.0} for candidate_id in questions}

    planned_rows = []
    with _semantic_reveal_enabled():
        for item in _planned():
            row, _stop = _evaluate(package_by_arm[item["arm"]], item, lambda: FakeClient())
            planned_rows.append(row)
    tokens = token_chars / 4
    ceiling = tokens / 1_000_000 * COST_PER_MILLION_INPUT_TOKENS * 1.5
    return planned_rows, len(calls), ceiling


def _validate_packages(package_by_arm: dict[str, StoryPackage]) -> list[str]:
    errors = []
    p1_ids = {item.id for item in package_by_arm["P1"].knowledge.knowledge}
    p0_ids = {item.id for item in package_by_arm["P0"].knowledge.knowledge}
    if DISCOVERY not in p1_ids or POINTER not in p1_ids:
        errors.append("P1 package is missing the discovery or pointer knowledge item")
    if DISCOVERY in p0_ids or POINTER in p0_ids:
        errors.append("P0 package unexpectedly contains the discovery or pointer knowledge item")
    return errors


def _load_packages() -> dict[str, StoryPackage]:
    return {"P1": load_story_package(PACKAGE_PATH), "P0": _head_package()}


def _estimate_from_measurement(package_by_arm: dict[str, StoryPackage]) -> tuple[int, float]:
    _rows, calls, ceiling = _measure(package_by_arm)
    return calls, ceiling


def _print_dry_run(package_by_arm: dict[str, StoryPackage], max_calls: int, max_usd: float) -> int:
    rows, call_count, ceiling = _measure(package_by_arm)
    print(f"planned evaluations: {EXPECTED_EVALUATIONS}")
    for arm in ARMS:
        for input_id, _command in INPUTS:
            shortlist = next(row["shortlist_ids"] for row in rows if row["arm"] == arm and row["input_id"] == input_id)
            print(f"{arm} {input_id}: {', '.join(shortlist) or '(none)'}")
    print(f"planned HTTP calls: {call_count}")
    token_estimate = ceiling / COST_PER_MILLION_INPUT_TOKENS / 1.5 * 1_000_000
    print(f"token estimate: {token_estimate:.2f}")
    print(f"USD ceiling: ${ceiling:.6f}")
    if call_count > max_calls:
        return _error(f"planned calls {call_count} exceed --max-calls {max_calls}")
    if ceiling > max_usd:
        return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${max_usd:.6f}")
    return 0


def _run(package_by_arm: dict[str, StoryPackage], out: Path, max_calls: int, max_usd: float) -> int:
    calls, ceiling = _estimate_from_measurement(package_by_arm)
    if calls > max_calls:
        return _error(f"planned calls {calls} exceed --max-calls {max_calls}")
    if ceiling > max_usd:
        return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${max_usd:.6f}")
    token_estimate = ceiling / COST_PER_MILLION_INPUT_TOKENS / 1.5 * 1_000_000
    document: dict[str, Any] = {
        "schema": 1,
        "mode": "run",
        "planned_evaluations": EXPECTED_EVALUATIONS,
        "planned_http_calls": calls,
        "token_estimate": token_estimate,
        "usd_ceiling": ceiling,
        "rows": [],
        "stop_reason": "incomplete",
    }
    _write_json(out, document)
    with _semantic_reveal_enabled():
        for planned in _planned():
            row, stop_reason = _evaluate(package_by_arm[planned["arm"]], planned)
            document["rows"].append(row)
            if stop_reason is not None:
                document["stop_reason"] = stop_reason
                _write_json(out, document)
                print(f"{len(document['rows'])} rows written to {out}")
                return 0
            _write_json(out, document)
    document["stop_reason"] = None
    _write_json(out, document)
    print(f"{len(document['rows'])} rows written to {out}")
    return 0


def _selected(row: dict[str, Any]) -> list[str]:
    value = row.get("matched_ids", row.get("selected_ids", row.get("matched", ())))
    if isinstance(value, str):
        return [value]
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _usable(row: dict[str, Any]) -> bool:
    value = row.get("usable")
    if isinstance(value, bool):
        return value
    return row.get("error") is None


def _input_rows(rows: list[dict[str, Any]], arm: str, input_id: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("arm") == arm and row.get("input_id", row.get("input")) == input_id]


def _count_selected(rows: list[dict[str, Any]], candidate_id: str) -> int:
    return sum(candidate_id in _selected(row) for row in rows)


def _rate_line(input_id: str, candidate_id: str, rows: list[dict[str, Any]], label: str) -> str:
    return f"{input_id}: {label} selected {_count_selected(rows, candidate_id)}/{len(rows)}"


def _report_text(document: dict[str, Any]) -> tuple[str, bool]:
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    expected = EXPECTED_EVALUATIONS
    p1 = {input_id: _input_rows(rows, "P1", input_id) for input_id, _command in INPUTS}
    m1 = all(
        len(p1[input_id]) == SAMPLES and _count_selected(p1[input_id], DISCOVERY) >= 9 for input_id in ("u1", "u2")
    )
    m2 = all(len(p1[input_id]) == SAMPLES and _count_selected(p1[input_id], POINTER) <= 1 for input_id in ("u1", "u2"))
    m3 = all(
        len(p1[input_id]) == SAMPLES and _count_selected(p1[input_id], DISCOVERY) == 0 for input_id in ("n1", "n2")
    )
    m4 = all(
        len(p1[input_id]) == SAMPLES and sum(not _selected(row) for row in p1[input_id]) == SAMPLES
        for input_id in ("n3", "n4")
    )
    usable = sum(_usable(row) for row in rows)
    unusable = len(rows) - usable
    complete = len(rows) == expected and document.get("stop_reason") is None
    m5 = complete and unusable <= expected * 0.10
    m1_counts = f"{_rate_line('u1', DISCOVERY, p1['u1'], 'D')}; {_rate_line('u2', DISCOVERY, p1['u2'], 'D')}"
    m2_counts = f"{_rate_line('u1', POINTER, p1['u1'], 'E')}; {_rate_line('u2', POINTER, p1['u2'], 'E')}"
    m3_counts = f"{_rate_line('n1', DISCOVERY, p1['n1'], 'D')}; {_rate_line('n2', DISCOVERY, p1['n2'], 'D')}"
    n3_nothing = sum(not _selected(row) for row in p1["n3"])
    n4_nothing = sum(not _selected(row) for row in p1["n4"])
    lines = ["# Hidden bench matcher probe report", "", f"Rows rendered: {len(rows)}", ""]
    lines.extend(
        [
            f"- M1: {'PASS' if m1 else 'FAIL'} — {m1_counts}",
            f"- M2: {'PASS' if m2 else 'FAIL'} — {m2_counts}",
            f"- M3: {'PASS' if m3 else 'FAIL'} — {m3_counts}",
            f"- M4: {'PASS' if m4 else 'FAIL'} — n3: nothing selected {n3_nothing}/{len(p1['n3'])}; "
            f"n4: nothing selected {n4_nothing}/{len(p1['n4'])}",
            f"- M5: {'PASS' if m5 else 'FAIL'} — stop_reason={document.get('stop_reason')!r}; "
            f"unusable answers {unusable}/{len(rows)}",
            "",
            "## Informational pointer rates",
            "",
            f"- {_rate_line('n1', POINTER, p1['n1'], 'E')}",
            f"- {_rate_line('n2', POINTER, p1['n2'], 'E')}",
            "",
            "## P0 diagnostic",
            "",
            "| input | D selected | E selected | any selected |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for input_id, _command in INPUTS:
        selected = _input_rows(rows, "P0", input_id)
        any_selected = sum(bool(_selected(row)) for row in selected)
        lines.append(
            f"| {input_id} | {_count_selected(selected, DISCOVERY)}/{len(selected)} | "
            f"{_count_selected(selected, POINTER)}/{len(selected)} | {any_selected}/{len(selected)} |"
        )
    passed = m1 and m2 and m3 and m4 and m5
    lines.extend(["", f"## Overall: {'PASS' if passed else 'FAIL'}", ""])
    return "\n".join(lines), passed


def _report(rows_path: Path, out: Path) -> int:
    document = json.loads(rows_path.read_text(encoding="utf-8"))
    report, passed = _report_text(document)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report)
    return 0 if passed else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    parser.add_argument("--max-usd", type=float, default=DEFAULT_MAX_USD)
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.report:
            if args.rows is None or args.out is None:
                return _error("--report requires --rows and --out")
            return _report(args.rows, args.out)
        if args.max_calls < 1:
            return _error("--max-calls must be at least 1")
        package_by_arm = _load_packages()
        package_errors = _validate_packages(package_by_arm)
        if package_errors:
            return _error("; ".join(package_errors))
        if args.validate:
            print(f"validated {EXPECTED_EVALUATIONS} evaluations across P1 and P0")
            return 0
        if args.dry_run:
            return _print_dry_run(package_by_arm, args.max_calls, args.max_usd)
        if not args.confirm:
            return _error("run mode requires --confirm")
        if args.out is None:
            return _error("run mode requires --out")
        if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_URL")
        if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_TOKEN")
        return _run(package_by_arm, args.out, args.max_calls, args.max_usd)
    except (OSError, ValueError, TypeError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        return _error(type(error).__name__)


if __name__ == "__main__":
    raise SystemExit(main())
