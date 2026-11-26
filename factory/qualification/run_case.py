"""Run the real diagnosis and planning stations against one sealed case."""

from __future__ import annotations

import argparse
import inspect
import json
import os
import subprocess
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from factory.contract_scene import build_contract_scene
from factory.guard import BudgetExhausted, Caps, LimitSleep, ModelGuard, ModelNotAllowed, ProviderLimit, SpendLedger
from factory.outcome_contract import classify_run
from factory.stations import diagnose as diagnose_station
from factory.stations import planner as planner_station
from factory.stations.diagnose import DIAGNOSE_EFFORT, DIAGNOSE_MODEL_ID
from factory.stations.live_playtest import report_to_packets
from factory.stations.planner import PlanOutcome, build_prompt, make_planner
from factory.tickets import Station, Ticket, TicketClass
from storygame.story_package.loader import load_story_package

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTROL_ROOT = REPOSITORY_ROOT
_BLOCKED_ERRORS = (LimitSleep, ProviderLimit, BudgetExhausted, ModelNotAllowed)
_PLANNER_DEFAULTS = inspect.signature(make_planner).parameters
PLANNER_MODEL_ID = str(_PLANNER_DEFAULTS["model_id"].default)
PLANNER_EFFORT = str(_PLANNER_DEFAULTS["effort"].default)


class CeilingReached(RuntimeError):
    pass


class _CallRecorder:
    def __init__(self, max_calls: int, max_tokens: int) -> None:
        self.max_calls = max_calls
        self.max_tokens = max_tokens
        self.records: list[dict[str, Any]] = []

    @property
    def calls(self) -> int:
        return len(self.records)

    @property
    def tokens(self) -> int:
        return sum(int(record["tokens"]) for record in self.records)

    def run(self, argv: list[str], *, input: str | None = None, **kwargs: Any) -> subprocess.CompletedProcess:
        if self.calls >= self.max_calls or self.tokens >= self.max_tokens:
            raise CeilingReached(
                f"qualification ceiling reached before model call {self.calls + 1} "
                f"(calls={self.calls}/{self.max_calls}, tokens={self.tokens}/{self.max_tokens})"
            )

        started = time.monotonic()
        try:
            completed = subprocess.run(argv, input=input, **kwargs)
        except Exception as exc:
            self._record(argv, input, "", "", None, time.monotonic() - started, 0, str(exc))
            raise
        stdout = _text(getattr(completed, "stdout", ""))
        stderr = _text(getattr(completed, "stderr", ""))
        tokens = planner_station._usage_tokens(planner_station._stream_events(stdout.splitlines())[0])
        self._record(
            argv,
            input,
            stdout,
            stderr,
            getattr(completed, "returncode", None),
            time.monotonic() - started,
            tokens,
            None,
        )
        return completed

    def _record(
        self,
        argv: list[str],
        prompt: str | None,
        stdout: str,
        stderr: str,
        returncode: int | None,
        wall_seconds: float,
        tokens: int,
        error: str | None,
    ) -> None:
        record: dict[str, Any] = {
            "argv": list(argv),
            "prompt": prompt if isinstance(prompt, str) else "",
            "stdout": stdout,
            "stderr": stderr,
            "returncode": returncode,
            "wall_seconds": wall_seconds,
            "tokens": tokens,
        }
        if error is not None:
            record["error"] = error
        self.records.append(record)


def _text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value if isinstance(value, str) else str(value)


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-calls", type=_positive_int, required=True)
    parser.add_argument("--max-tokens", type=_positive_int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--story", dest="story", help="story directory name inside solver/repo/data/stories")
    return parser


def _story_root(repo_root: Path, story: str | None) -> Path:
    stories_root = repo_root / "data" / "stories"
    if story is not None:
        if Path(story).name != story or story in {"", ".", ".."}:
            raise ValueError("--story must be a story directory name")
        return stories_root / story
    candidates = sorted(path for path in stories_root.iterdir() if path.is_dir())
    if len(candidates) != 1:
        raise ValueError("--story is required when solver/repo contains zero or multiple stories")
    return candidates[0]


def _read_case(case_dir: Path, story: str | None) -> tuple[dict[str, Any], dict[str, Any], Any]:
    manifest = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))
    records = json.loads((case_dir / "solver" / "records.json").read_text(encoding="utf-8"))
    runs = records.get("runs") if isinstance(records, dict) else None
    if not isinstance(runs, list) or not runs:
        raise ValueError("solver/records.json must contain a non-empty runs list")
    report = {
        "replicates": [
            {
                "replicate": run["replicate"],
                "scene": run["scene"],
                "turns": run["turns"],
                "stuck_turns": run.get("stuck_turns", []),
                "exit_cause": run.get("exit_cause"),
                "entry_facts": run.get("entry_facts", []),
            }
            for run in runs
        ]
    }
    package = load_story_package(_story_root(case_dir / "solver" / "repo", story))
    complete = all(
        isinstance(turn, dict) and isinstance(turn.get("committed_facts"), list)
        for run in runs
        for turn in run.get("turns", [])
    )
    evidence_basis = "outcome_contract" if complete else "raw_stuck_flags"
    contract = None
    if complete:
        scenes = {run["scene"]: build_contract_scene(package, run["scene"]) for run in runs}
        packets = report_to_packets(report, scenes=scenes)
        contract = []
        for run in runs:
            summary = classify_run(run, scenes[run["scene"]])
            contract.append(
                {
                    "scene": run["scene"],
                    "replicate": run["replicate"],
                    "status": summary["status"],
                    "exit": summary["exit"],
                    "confirmed_stuck": summary["confirmed_stuck"],
                    "unresolved": summary["unresolved"],
                    "provenance_flags": summary["provenance_flags"],
                }
            )
    else:
        packets = report_to_packets(report)
    return (
        manifest,
        {
            "report": report,
            "packets": packets,
            "scene": runs[0]["scene"],
            "evidence_basis": evidence_basis,
            "contract": contract,
        },
        package,
    )


def _ticket(ticket_id: str, scene: str, token_budget: int, payload: dict[str, Any], station: Station) -> Ticket:
    now = datetime.now(UTC).isoformat()
    return Ticket(
        id=ticket_id,
        scene=scene,
        station=station,
        token_budget=token_budget,
        created_at=now,
        updated_at=now,
        ticket_class=TicketClass.STORY_DATA,
        payload=payload,
    )


def _controls(root: Path) -> tuple[ModelGuard, SpendLedger, Caps]:
    config, config_root = planner_station._load_config(root)
    paths = config["paths"]

    def resolve(value: object) -> Path:
        if not isinstance(value, (str, Path)):
            raise ValueError("path must be a string")
        path = Path(value)
        return path if path.is_absolute() else root / path

    allowlist = resolve(paths["allowlist"])
    if not allowlist.is_file():
        allowlist = config_root / paths["allowlist"]
    return ModelGuard.from_file(allowlist), SpendLedger(resolve(paths["ledger"])), Caps.from_dict(config["caps"])


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _write_outputs(
    out_dir: Path,
    packets: list[dict[str, Any]],
    diagnosis: dict[str, Any],
    outcome: PlanOutcome,
    transcript: list[dict[str, Any]],
    result: dict[str, Any],
) -> None:
    _atomic_write(
        out_dir / "transcript.jsonl", "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in transcript)
    )
    _atomic_write(out_dir / "packets.json", json.dumps(packets, ensure_ascii=False, indent=2) + "\n")
    _atomic_write(out_dir / "diagnosis.json", json.dumps(diagnosis, ensure_ascii=False, indent=2) + "\n")
    _atomic_write(out_dir / "plan.json", json.dumps(asdict(outcome), ensure_ascii=False, indent=2) + "\n")
    _atomic_write(out_dir / "result.json", json.dumps(result, ensure_ascii=False, indent=2) + "\n")


def _git_head() -> str | None:
    try:
        process = subprocess.Popen(
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        output, _ = process.communicate()
    except OSError:
        return None
    return _text(output).strip() if process.returncode == 0 else None


def _result_base(manifest: dict[str, Any], max_calls: int, max_tokens: int, calls: int, tokens: int) -> dict[str, Any]:
    return {
        "case": manifest.get("case"),
        "case_id": manifest.get("case"),
        "solver_tree_sha256": manifest.get("solver_tree_sha256"),
        "git_head": _git_head(),
        "model_ids": {"classifier": DIAGNOSE_MODEL_ID, "planner": PLANNER_MODEL_ID},
        "efforts": {"classifier": DIAGNOSE_EFFORT, "planner": PLANNER_EFFORT},
        "ceilings": {"max_calls": max_calls, "max_tokens": max_tokens},
        "calls": calls,
        "tokens": tokens,
        "classifier_prompt": None,
        "planner_prompt": None,
    }


def _run(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], PlanOutcome, _CallRecorder]:
    manifest, case_data, package = _read_case(args.case_dir, args.story)
    packets = case_data["packets"]
    scene = case_data["scene"]
    evidence_basis = case_data["evidence_basis"]
    outcome = PlanOutcome(None, 0, [], 0)
    recorder = _CallRecorder(args.max_calls, args.max_tokens)
    result = _result_base(manifest, args.max_calls, args.max_tokens, 0, 0)
    result["evidence_basis"] = evidence_basis
    if case_data["contract"] is not None:
        result["contract"] = case_data["contract"]
    if not packets:
        result["status"] = "no_change"
        result["classifier_prompt"] = None
        if args.dry_run:
            result["estimated_tokens"] = {"classifier": 0, "planner": 0, "total": 0}
        return result, packets, {"rows": [], "counts": {}}, outcome, recorder

    rule_rows = diagnose_station.diagnose_turns(packets, package)
    rule_counts = diagnose_station._counts(rule_rows)
    classifier_prompt = (
        diagnose_station._prompt(packets, rule_rows, package)
        if any(row.get("cause") == "unclear" for row in rule_rows)
        else None
    )
    diagnosis = {"rows": rule_rows, "counts": rule_counts}
    result["classifier_prompt"] = classifier_prompt

    if args.dry_run:
        planner_payload = {"scene": scene, "failing_turns": packets, "diagnosis": diagnosis}
        planner_ticket = _ticket("qualification-plan", scene, args.max_tokens, planner_payload, Station.WIRING)
        evidence = planner_station.build_evidence(planner_ticket.payload, package)
        planner_prompt = build_prompt(evidence)
        result["planner_prompt"] = planner_prompt
        result["estimated_tokens"] = {
            "classifier": len(classifier_prompt) // 4 if classifier_prompt is not None else 0,
            "planner": len(planner_prompt) // 4,
        }
        result["estimated_tokens"]["total"] = sum(result["estimated_tokens"].values())
        result["status"] = "dry_run"
        return result, packets, diagnosis, outcome, recorder

    controls_root = CONTROL_ROOT
    guard, ledger, caps = _controls(controls_root)
    classifier = diagnose_station.default_classifier(controls_root, run=recorder.run)
    diagnosis_ticket = _ticket(
        "qualification-diagnose",
        scene,
        args.max_tokens,
        {"scene": scene, "failing_turns": packets},
        Station.DIAGNOSE,
    )
    try:
        diagnosis_result = diagnose_station.diagnose_handler(
            REPOSITORY_ROOT,
            classifier=classifier,
            package_loader=lambda _root: package,
        )(diagnosis_ticket, datetime.now(UTC))
        if not diagnosis_result.passed:
            result["status"] = "blocked"
            result["error"] = diagnosis_result.output
            return result, packets, diagnosis, outcome, recorder
        diagnosis = diagnosis_result.payload_updates["diagnosis"]
        result["classifier_prompt"] = classifier_prompt

        planner_payload = {"scene": scene, "failing_turns": packets, "diagnosis": diagnosis}
        planner_ticket = _ticket("qualification-plan", scene, args.max_tokens, planner_payload, Station.WIRING)
        planner = make_planner(
            guard=guard,
            ledger=ledger,
            caps=caps,
            run=recorder.run,
            model_id=PLANNER_MODEL_ID,
            effort=PLANNER_EFFORT,
        )
        evidence = planner_station.build_evidence(planner_ticket.payload, package)
        result["planner_prompt"] = build_prompt(evidence)
        outcome = planner(planner_ticket, package, datetime.now(UTC))
        result["status"] = "complete"
    except CeilingReached as exc:
        result["status"] = "ceiling_reached"
        result["error"] = str(exc)
    except _BLOCKED_ERRORS as exc:
        result["status"] = "blocked"
        result["error"] = str(exc)
    result["calls"] = recorder.calls
    result["tokens"] = recorder.tokens
    return result, packets, diagnosis, outcome, recorder


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    result, packets, diagnosis, outcome, recorder = _run(args)
    args.out.mkdir(parents=True, exist_ok=True)
    _write_outputs(args.out, packets, diagnosis, outcome, recorder.records, result)
    if args.dry_run:
        estimates = result["estimated_tokens"]
        print(f"dry-run case={result['case']} calls=0 estimated_tokens={estimates['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
