"""Bounded Stage 7 door wording screen; dry mode is completely offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from door_continuation import action_groups, score_command  # noqa: E402
from door_prompt import ARMS, PROMPT_FIXTURE, patch_prompt, prompt_plan, recorded_transition, select_prompt  # noqa: E402
from door_transport import RawRequestError, SpendBudget, counted_provider, raw_request  # noqa: E402

from bench.core import (  # noqa: E402
    append_ledger_row,  # noqa: E402
    load_variation,
    package_and_state,
    provider_for,
)
from storygame.runtime.contracts import NarrationSegment, join_narration  # noqa: E402
from storygame.runtime.engine import RuntimeEngine  # noqa: E402

CAPS = {1: {"raw": 4, "cloudflare": 28, "player": 12}, 12: {"raw": 48, "cloudflare": 336, "player": 144}}
VARIATIONS = {
    "control": "stage7-door-control.json",
    "review": "stage7-door-review.json",
    "stale-scene": "stage7-door-stale-scene.json",
    "wording": "stage7-door-wording.json",
    "fixed-control": "stage7-door-control.json",
    "bridge": "stage7-door-bridge.json",
}


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_failed_response(out: Path, error: RawRequestError) -> Path:
    body = json.dumps(error.normalized, default=str, ensure_ascii=False)
    artifact = out / "failed-response.json"
    atomic_json(
        artifact,
        {
            "stage": error.stage,
            "error": error.error_text,
            "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "body": body[:4000],
        },
    )
    return artifact


def bridge_material() -> dict[str, Any]:
    recorded = recorded_transition()
    package, _ = package_and_state(load_variation(ROOT / "bench/variations/stage7-door-control.json"), "2A")
    source = next(s for s in package.scenes if s.metadata.scene_id == "2A")
    target = next(s for s in package.scenes if s.metadata.scene_id == "2B")
    bridge, entry = source.metadata.bridge_text["t_2a_2b"], target.metadata.entry_text
    suffix = join_narration(
        (NarrationSegment(kind="narration", text=bridge), NarrationSegment(kind="narration", text=entry))
    )
    if not recorded["text"].endswith(suffix) or recorded["text"].count(suffix) != 1:
        raise AssertionError("recorded transition does not end in exactly one authored bridge plus entry")
    prefix = recorded["text"][: -len(suffix)]
    if not prefix:
        raise AssertionError("recorded narrator prefix is empty")
    removed = "Beyond those corridors, the records archive waited behind another layer of security."
    if bridge.count(removed) != 1:
        raise AssertionError("expected bridge sentence is not present exactly once")
    shortened = bridge.replace(" " + removed, "", 1)
    return {
        "recorded": recorded["text"],
        "prefix": prefix,
        "bridge": bridge,
        "entry": entry,
        "fixed": suffix,
        "short_bridge": shortened,
        "control_screen": join_narration(
            tuple(NarrationSegment(kind="narration", text=x) for x in (prefix, bridge, entry))
        ),
        "bridge_screen": join_narration(
            tuple(NarrationSegment(kind="narration", text=x) for x in (prefix, shortened, entry))
        ),
    }


def build_source(out: Path) -> dict[str, Any]:
    selection = select_prompt()
    prompts = {arm: patch_prompt(selection, arm) for arm in ("control", "review", "stale-scene", "wording")}
    bridge = bridge_material()
    source = {
        "prompt_fixture": str(PROMPT_FIXTURE),
        "prompt_hash": hashlib.sha256(PROMPT_FIXTURE.read_bytes()).hexdigest(),
        "prompts": prompts,
        "bridge": bridge,
    }
    atomic_json(out / "source-before.json", source)
    atomic_json(out / "source-after.json", source)
    return source


def dry_run(out: Path, n: int) -> None:
    source = build_source(out)
    (out / "prompts").mkdir(exist_ok=True)
    for arm, value in source["prompts"].items():
        atomic_json(out / "prompts" / f"{arm}.json", value)
    groups = action_groups()
    plans = []
    for rep, arm in prompt_plan():
        variation = VARIATIONS[arm]
        if arm in ("fixed-control", "bridge"):
            screen = source["bridge"]["control_screen" if arm == "fixed-control" else "bridge_screen"]
        else:
            screen = f"<generated narrator screen for {arm}>"
        plans.append(
            {
                "row_id": f"stage7-door-{rep:02d}-{arm}",
                "rep": rep,
                "arm": arm,
                "variation": variation,
                "screen": screen,
                "eligible_ids": sorted(groups),
            }
        )
    plans = [x for x in plans if x["rep"] <= n]
    atomic_json(out / "results.json", {"mode": "dry", "rows": plans})
    atomic_json(
        out / "run.json",
        {
            "mode": "dry",
            "n": n,
            "arms": list(ARMS),
            "order": "rep-major",
            "caps": CAPS[n],
            "experiment_id": str(uuid.uuid4()),
        },
    )
    atomic_json(
        out / "summary.json",
        {
            "mode": "dry",
            "planned_rows": len(plans),
            "n": n,
            "caps": CAPS[n],
            "cloudflare_max": CAPS[n]["cloudflare"],
            "raw_player_max": CAPS[n]["player"],
        },
    )
    (out / "spend.jsonl").write_text("", encoding="utf-8")
    (out / "verdicts").mkdir(exist_ok=True)
    notes = (
        "Offline dry run only. Six arms are planned in rep-major order; no provider, player, credentials, or network "
        "call is used. Prompt hashes, exact diffs, fixed bridge reconstruction, bridge deletion, eligible 2B evidence "
        "IDs, and cap arithmetic are recorded in source and plan artifacts. Live execution remains outside this free "
        "artifact.\n"
    )
    (out / "notes.md").write_text(notes, encoding="utf-8")


def _ask_player(screen: str, budget: SpendBudget) -> str:
    budget.reserve("raw_player")
    result = subprocess.run(
        ["node", str(ROOT / "scripts/ringer/stage7/door_ask_player.mjs")],
        input=json.dumps({"transcript": screen, "status": ""}),
        text=True,
        capture_output=True,
        cwd=ROOT,
        env=os.environ.copy(),
        check=False,
    )
    if result.returncode:
        budget.acknowledge("raw_player", False, result.stderr.strip() or "child failed")
        raise RuntimeError(result.stderr.strip() or "player child failed")
    try:
        command = json.loads(result.stdout)["command"]
    except (ValueError, KeyError, TypeError) as error:
        budget.acknowledge("raw_player", False, "malformed child JSON")
        raise RuntimeError(f"malformed player output: {result.stdout!r}") from error
    if not isinstance(command, str) or not command.strip():
        budget.acknowledge("raw_player", False, "empty command")
        raise RuntimeError("player returned an empty command")
    budget.acknowledge("raw_player", True)
    return command


def _continue(
    variation_path: Path,
    commands: list[str],
    budget: SpendBudget,
    recovery_prompt: str | None = None,
) -> dict[str, Any]:
    variation = load_variation(variation_path)
    package, state = package_and_state(variation, "2B")
    provider = provider_for(state, variation)
    previous = getattr(provider, "semantic_ask", None)
    provider.semantic_ask = None
    engine = RuntimeEngine(state, provider)
    try:
        turns = []
        with counted_provider(provider, budget):
            for command in commands:
                turn = score_command(engine, state, command)
                turns.append(turn)
                if turn["status"] == "earned":
                    break
            if turns and turns[-1]["status"] != "earned" and recovery_prompt is not None:
                commands.append(_ask_player(recovery_prompt + "\n\n" + turns[-1].get("response", ""), budget))
                turns.append(score_command(engine, state, commands[-1]))
        return {
            "turns": turns,
            "eligible": turns[0]["eligible"] if turns else [],
            "matched": turns[0]["matched"] if turns else [],
            "request_count": getattr(provider, "request_count", 0),
            "recovery_count": getattr(provider, "recovery_count", 0),
            "initial_facts": turns[0]["before_facts"] if turns else [],
            "final_facts": turns[-1].get("after_facts", []) if turns else [],
            "eligibility_reason": "fresh bare 2B state has no eligible entries"
            if turns and not turns[0]["eligible"]
            else None,
        }
    finally:
        provider.semantic_ask = previous


def live_run(out: Path, n: int) -> None:
    source = build_source(out)
    (out / "prompts").mkdir(exist_ok=True)
    for arm, value in source["prompts"].items():
        atomic_json(out / "prompts" / f"{arm}.json", value)
    budget = SpendBudget(CAPS[n]["cloudflare"], cloudflare_limit=CAPS[n]["cloudflare"], player_limit=CAPS[n]["player"])
    rows = []
    for rep in range(1, n + 1):
        for arm in ARMS:
            if arm in ("fixed-control", "bridge"):
                screen = source["bridge"]["control_screen" if arm == "fixed-control" else "bridge_screen"]
                continuation_path = ROOT / "bench/variations/stage7-door-control.json"
            else:
                prompt = source["prompts"][arm]
                variation_path = ROOT / "bench/variations" / VARIATIONS[arm]
                variation = load_variation(variation_path)
                _, state = package_and_state(variation, "2A")
                try:
                    narrator_provider = provider_for(state, variation)
                    narrator_provider.semantic_ask = None
                    with counted_provider(narrator_provider, budget):
                        raw = raw_request(narrator_provider, prompt["system"], prompt["user"], budget)
                except RawRequestError as error:
                    evidence = write_failed_response(out, error).name
                    failure = f"{error.stage} failure: {error.error_text}; evidence: {evidence}"
                    rows.append(
                        {
                            "row_id": f"stage7-door-{rep:02d}-{arm}",
                            "rep": rep,
                            "arm": arm,
                            "status": "failed",
                            "error": failure,
                        }
                    )
                    atomic_json(out / "results.json", {"mode": "live", "rows": rows})
                    raise RuntimeError(failure) from error
                screen = join_narration(
                    (
                        NarrationSegment(kind="narration", text=raw.proposal.narration),
                        NarrationSegment(kind="narration", text=source["bridge"]["bridge"]),
                        NarrationSegment(kind="narration", text=source["bridge"]["entry"]),
                    )
                )
                continuation_path = variation_path
            commands = [_ask_player(screen, budget)]
            continuation = _continue(continuation_path, commands, budget, screen)
            rows.append(
                {
                    "row_id": f"stage7-door-{rep:02d}-{arm}",
                    "rep": rep,
                    "arm": arm,
                    "screen": screen,
                    "command": commands[0],
                    "commands": commands,
                    "responses": [turn.get("response") for turn in continuation["turns"]],
                    "command_1": commands[0] if commands else None,
                    "command_2": commands[1] if len(commands) > 1 else None,
                    "response_1": continuation["turns"][0].get("response") if continuation["turns"] else None,
                    "response_2": continuation["turns"][1].get("response") if len(continuation["turns"]) > 1 else None,
                    "eligible": continuation["eligible"],
                    "matched": continuation["matched"],
                    "before_facts": continuation["initial_facts"],
                    "after_facts": continuation["final_facts"],
                    "recovery_status": [turn.get("status") for turn in continuation["turns"]],
                    "continuation": continuation,
                    "item_facts": raw.item_facts if arm not in ("fixed-control", "bridge") else None,
                    "status": "ok",
                }
            )
            atomic_json(out / "results.json", {"mode": "live", "rows": rows})
    experiment_id = str(uuid.uuid4())
    ledger_path = Path(os.environ.get("DOOR_LEDGER_PATH", ROOT / "bench/results/ledger.jsonl"))
    atomic_json(
        out / "run.json",
        {
            "mode": "live",
            "n": n,
            "arms": list(ARMS),
            "order": "rep-major",
            "caps": CAPS[n],
            "experiment_id": experiment_id,
            "ledger_path": str(ledger_path),
            "hashes": {
                "source_before": hashlib.sha256((out / "source-before.json").read_bytes()).hexdigest(),
                "source_after": hashlib.sha256((out / "source-after.json").read_bytes()).hexdigest(),
            },
        },
    )
    atomic_json(
        out / "summary.json",
        {
            "mode": "live",
            "n": n,
            "experiment_id": experiment_id,
            "status": "ok",
            "rows": len(rows),
            "planned_rows": len(ARMS) * n,
            "cloudflare_requests": budget.cloudflare_requests,
            "raw_player_attempts": budget.raw_player_attempts,
            "acknowledged": budget.acknowledged,
            "caps": CAPS[n],
            "cap_arithmetic": {
                "cloudflare_remaining": CAPS[n]["cloudflare"] - budget.cloudflare_requests,
                "player_remaining": CAPS[n]["player"] - budget.raw_player_attempts,
            },
            "arms": {arm: {"rows": sum(row["arm"] == arm for row in rows)} for arm in ARMS},
        },
    )
    (out / "spend.jsonl").write_text("\n".join(json.dumps(event) for event in budget.events) + "\n", encoding="utf-8")
    append_ledger_row(
        {
            "experiment_id": experiment_id,
            "variation_name": "stage7-door-probe",
            "status": "ok",
            "scenes_scored": 0,
            "max_score": 0,
            "scores": [],
            "score_metric": "door_prompt_screen",
            "cloudflare_requests": budget.cloudflare_requests,
            "raw_player_attempts": budget.raw_player_attempts,
            "request_cap": CAPS[n]["cloudflare"],
            "player_cap": CAPS[n]["player"],
        },
        ledger_path,
    )
    (out / "verdicts").mkdir(exist_ok=True)
    (out / "notes.md").write_text(
        "Bounded live screen artifact; interpretation requires blinded review and does not establish "
        "hosted adoption.\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    if args.n not in CAPS:
        parser.error("--n must be 1 or 12")
    out = args.out if args.out.is_absolute() else ROOT / args.out
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"output directory must be absent or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        dry_run(out, args.n)
        return 0
    if not args.confirm:
        raise SystemExit("--confirm is mandatory for live execution")
    try:
        live_run(out, args.n)
    except Exception as error:
        (out / "run-failure.txt").write_text(str(error) + "\n", encoding="utf-8")
        raise
    return 0


if __name__ == "__main__":
    main()
