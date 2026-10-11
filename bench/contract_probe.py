"""Offline or live probe for the optional 2C action contract."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench.jev_use import _ask  # noqa: E402
from storygame.runtime.cloudflare import CloudflareTurnProvider  # noqa: E402
from storygame.runtime.engine import RuntimeEngine  # noqa: E402
from storygame.runtime.facts import Fact  # noqa: E402
from storygame.runtime.jev_questions import reaches_reveal_contract, reaches_reveals  # noqa: E402
from storygame.runtime.state import RuntimeState  # noqa: E402
from storygame.story_package.loader import load_story_package  # noqa: E402

CORPUS = ROOT / "bench" / "variations" / "contract-probe-2c.json"
PACKAGE = load_story_package(ROOT / "data" / "stories" / "continuity-initiative")


def _provider() -> CloudflareTurnProvider:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "2C"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "2C")
    state._assert_scene_entry_fact("2C")
    state.facts.assert_fact(Fact(predicate="janus_evidence", subject="story", value="true"))
    RuntimeEngine(state, lambda _input: {})._activate_pacing()
    return CloudflareTurnProvider(worker_url="", token="", state=state)


def _dry_ask(_state, questions):
    command = _state["command"].casefold()
    answers = {}
    for candidate_id in questions:
        positive = any(word in command for word in ("copy", "save", "check", "transfer"))
        negative = any(word in command for word in ("send", "ask", "open"))
        answers[candidate_id] = {"noul": 1.0 if positive and not negative else 0.0}
    return answers


def _run(command: str, arm: str, samples: int, ask, candidates) -> dict[str, int | str]:
    target = next(candidate for candidate in candidates if candidate.id == "k_sl_2c_c_r1")
    other = [candidate for candidate in candidates if candidate.id != target.id]
    counts = {"grants": 0, "false_grants_on_others": 0, "none": 0, "samples": samples, "arm": arm}
    for _ in range(samples):
        if arm == "current":
            tuples = [
                (
                    candidate.id,
                    candidate.earn_when or candidate.statement,
                    provider._semantic_candidate_names(candidate),
                )
                for candidate in candidates
            ]
            matched = reaches_reveals(ask, command, tuples)
            target_answer = target.id in matched
            other_answer = bool(set(matched) & {candidate.id for candidate in other})
        else:
            target_answer = reaches_reveal_contract(
                ask, command, target.id, target.action_contract, target.earn_when or target.statement
            )
            other_questions = [
                (
                    candidate.id,
                    candidate.earn_when or candidate.statement,
                    provider._semantic_candidate_names(candidate),
                )
                for candidate in other
            ]
            other_answer = bool(reaches_reveals(ask, command, other_questions)) if other_questions else False
        if target_answer is None:
            counts["none"] += 1
        elif target_answer:
            counts["grants"] += 1
        if other_answer:
            counts["false_grants_on_others"] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--arm", choices=("current", "contract", "both"), default="both")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and not (os.environ.get("CLOUDFLARE_ACCOUNT_ID") and os.environ.get("CLOUDFLARE_AI_TOKEN")):
        print("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_AI_TOKEN are required without --dry-run", file=sys.stderr)
        return 2
    global provider
    provider = _provider()
    provider.assemble_turn_prompt("Check the copied JANUS files.")
    candidates = provider._eligible_reveal_candidates(provider._reveal_universe())
    ask = (
        _dry_ask if args.dry_run else _ask(environment=os.environ, opener=__import__("urllib.request").request.urlopen)
    )
    arms = ("current", "contract") if args.arm == "both" else (args.arm,)
    rows = [
        {
            "command": item["command"],
            "label": item["label"],
            "arms": {arm: _run(item["command"], arm, args.samples, ask, candidates) for arm in arms},
        }
        for item in json.load(CORPUS.open())["commands"]
    ]
    report = {"samples": args.samples, "arm": args.arm, "dry_run": args.dry_run, "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print("command | arm | grants/N | other | None")
    for row in rows:
        for arm, values in row["arms"].items():
            print(
                f"{row['command']} | {arm} | {values['grants']}/{args.samples} | "
                f"{values['false_grants_on_others']} | {values['none']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
