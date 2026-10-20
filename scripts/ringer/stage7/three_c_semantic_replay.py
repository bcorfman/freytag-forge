"""Replay the 3C authored-handoff semantic fallback without narration calls."""

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from door_transport import SpendBudget  # noqa: E402

from bench.core import load_variation, package_and_state, provider_for  # noqa: E402
from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff  # noqa: E402
from storygame.runtime.engine import RuntimeEngine  # noqa: E402
from storygame.runtime.facts import Fact  # noqa: E402

OUT = ROOT / "bench/results/stage7-3c-semantic-replay"
VARIATION = ROOT / "bench/variations/stage7-3c-pump-need.json"
CAP = 40
ENTRY_FACTS = ("broadcast_started", "brandon_confession_available", "detention_locations_secured")

CASES = (
    (1, False, "broadcast to the families that the captives are safe and the evidence is public"),
    (2, True, "broadcast to the families that the survivors are safe and the facility is collapsing"),
    (3, True, "send the families the confirmed prisoner lists and locations"),
    (4, True, "Confirm the broadcast reached the families and give them word about the liberated captives."),
    (5, True, "Answer the families' requests with the confirmed news of the liberated captives."),
    (6, True, "Broadcast music to the families."),
)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def package_state() -> tuple[Any, Any]:
    variation = load_variation(VARIATION)
    package, state = package_and_state(variation, "3C")
    state._assert_scene_entry_fact("3C")  # noqa: SLF001
    for fact_id in ENTRY_FACTS:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    return package, state


def scripted_provider(package: Any, knowledge_id: str):
    knowledge = package.knowledge_indexes.by_id[knowledge_id]

    def provide(_command: str) -> dict[str, Any]:
        return {
            "segments": [{"kind": "narration", "text": knowledge.delivery_text or knowledge.statement}],
            "selected_knowledge_ids": [knowledge_id],
        }

    return provide


def build_state(d1_spent: bool) -> tuple[Any, Any]:
    package, state = package_state()
    commands = {
        "k_sl_3c_a_r1": "Send the evidence package.",
        "k_sl_3c_b_r1": "Take the Portable data case from Rebecca.",
        "k_sl_3c_c_r1": "Restore the drainage pumps.",
        "k_sl_3c_c_r2": "Open the surface gates.",
        "k_sl_3c_d_r1": "Read the detention site reports.",
    }
    engine = RuntimeEngine(state, scripted_provider(package, "k_sl_3c_a_r1"))
    for knowledge_id in ("k_sl_3c_a_r1", "k_sl_3c_b_r1", "k_sl_3c_c_r1", "k_sl_3c_c_r2"):
        engine.provider = scripted_provider(package, knowledge_id)
        engine.turn(commands[knowledge_id])
        engine._activate_pacing()  # noqa: SLF001
    if d1_spent:
        engine.provider = scripted_provider(package, "k_sl_3c_d_r1")
        engine.turn(commands["k_sl_3c_d_r1"])
        engine._activate_pacing()  # noqa: SLF001
    return package, engine


def candidate_sentences(provider: Any) -> list[dict[str, str]]:
    universe = provider._reveal_universe()  # noqa: SLF001
    visible_ids = {candidate.id for candidate in provider.last_projection.candidates}
    eligible = provider._eligible_reveal_candidates(universe)  # noqa: SLF001
    eligible = tuple(candidate for candidate in eligible if candidate.id in visible_ids)
    shown = []
    for candidate in eligible[:6]:
        sentence = candidate.earn_when or candidate.statement
        if sentence:
            shown.append({"id": candidate.id, "earn_when": sentence})
    return shown


class SemanticCallFailure(RuntimeError):
    pass


def guarded_semantic(provider: Any, budget: SpendBudget):
    original = provider.semantic_ask
    client = getattr(original, "__self__", None)
    original_opener = getattr(client, "opener", None)
    http_error: list[str] = []

    if client is not None and original_opener is not None:

        def opener(request, timeout=15.0):
            try:
                return original_opener(request, timeout=timeout)
            except Exception as error:
                if type(error).__name__ == "HTTPError":
                    http_error.append(type(error).__name__)
                raise

        client.opener = opener

    def ask(state: object, questions: object) -> dict | None:
        budget.reserve("cloudflare", "semantic_reveal")
        try:
            result = original(state, questions)
        except Exception as error:
            budget.acknowledge("cloudflare", False, type(error).__name__)
            raise SemanticCallFailure(str(error)) from error
        if http_error:
            budget.acknowledge("cloudflare", False, http_error[-1])
            raise SemanticCallFailure("HTTPError from semantic Cloudflare call")
        budget.acknowledge("cloudflare", True)
        return result

    def restore() -> None:
        if client is not None and original_opener is not None:
            client.opener = original_opener

    return ask, restore


def exact_result(provider: Any, command: str) -> str | None:
    projection = provider.projector.project(provider.state, "player", command)
    match = uniquely_matched_authored_handoff(command, projection.reveal_universe)
    return match.candidate.id if match is not None else None


def dry_run() -> None:
    os.environ["FREYTAG_SEMANTIC_REVEAL"] = "1"
    for case_id, d1_spent, command in CASES:
        _package, engine = build_state(d1_spent)
        variation = load_variation(VARIATION)
        provider = provider_for(engine.state, variation)
        provider.semantic_ask = None
        projection = provider.projector.project(engine.state, "player", command)
        match = uniquely_matched_authored_handoff(command, projection.reveal_universe)
        provider.last_projection = projection
        provider.last_reveal_selection["universe_size"] = len(projection.reveal_universe)
        print(
            json.dumps(
                {
                    "case": case_id,
                    "d1_spent": d1_spent,
                    "command": command,
                    "exact_match_result": match.candidate.id if match else None,
                    "eligible_candidates": candidate_sentences(provider),
                },
                sort_keys=True,
            )
        )


def live_run() -> None:
    os.environ["FREYTAG_SEMANTIC_REVEAL"] = "1"
    OUT.mkdir(parents=True, exist_ok=True)
    budget = SpendBudget(CAP, cloudflare_limit=CAP, player_limit=0)
    rows: list[dict[str, Any]] = []
    try:
        for case_id, d1_spent, command in CASES:
            for run in range(1, 4):
                _package, engine = build_state(d1_spent)
                variation = load_variation(VARIATION)
                provider = provider_for(engine.state, variation)
                exact = exact_result(provider, command)
                provider.semantic_ask, restore = guarded_semantic(provider, budget)
                try:
                    with nullcontext(provider):
                        provider.assemble_turn_prompt(command)
                finally:
                    restore()
                rows.append(
                    {
                        "case": case_id,
                        "run": run,
                        "d1_spent": d1_spent,
                        "command": command,
                        "exact_match_result": exact,
                        "last_reveal_selection": {
                            key: provider.last_reveal_selection.get(key)
                            for key in ("outcome", "matched", "shortlist_size", "universe_size")
                        },
                        # An exact handoff bypasses the semantic judge, so it showed no candidates.
                        "candidate_sentences": [] if exact is not None else candidate_sentences(provider),
                    }
                )
                atomic_json(OUT / "results.json", rows)
                atomic_json(OUT / "spend.json", {"cap": CAP, "events": budget.events})
    except Exception as error:
        atomic_json(OUT / "results.json", rows)
        atomic_json(OUT / "spend.json", {"cap": CAP, "events": budget.events})
        (OUT / "run-failure.txt").write_text(f"{type(error).__name__}: {error}\n", encoding="utf-8")
        raise
    atomic_json(OUT / "results.json", rows)
    atomic_json(OUT / "spend.json", {"cap": CAP, "events": budget.events})
    counts: dict[str, int] = {}
    for row in rows:
        outcome = row["last_reveal_selection"]["outcome"]
        counts[outcome] = counts.get(outcome, 0) + 1
    lines = ["# Stage 7 3C semantic replay", "", "| Case | D1 | Exact | Outcomes |", "|---:|:---:|:---|:---|"]
    for case_id, d1_spent, _ in CASES:
        selected = [row for row in rows if row["case"] == case_id]
        exacts = ", ".join(str(row["exact_match_result"]) for row in selected[:1])
        outcomes: dict[str, int] = {}
        for row in selected:
            outcome = row["last_reveal_selection"]["outcome"]
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
        summary = ", ".join(f"{k} {v}" for k, v in sorted(outcomes.items()))
        lines.append(f"| {case_id} | {'spent' if d1_spent else 'open'} | {exacts} | {summary} |")
    lines.extend(["", "Outcome counts: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())) + "."])
    (OUT / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        dry_run()
    else:
        live_run()


if __name__ == "__main__":
    main()
