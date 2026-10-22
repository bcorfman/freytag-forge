"""Validate Stage 7 3C probe artifacts without network access."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from three_c_probe import (
    ALL_ARMS,
    ARMS,
    CAPS,
    CARRIED_ATTEMPT_CAP,
    CARRIED_ENTRY_STATE,
    CARRIED_LABEL,
    COMMAND_TURNS,
    DE_R1,
    KRISTIN_PLACES,
    POST8_ATTEMPT_CAP,
    POST8_LABEL,
    POST8_REVEALS,
    POSTA_ATTEMPT_CAP,
    POSTA_LABEL,
    POSTA_REVEALS,
    POSTA_REVEALS_EXPECTED,
    POSTC_ATTEMPT_CAP,
    POSTC_CAPS,
    POSTC_LABEL,
    POSTC_REVEALS,
    recorded_commands,
    source_proof,
)


def scripted_prefix_has_chain_reveals(row: dict[str, object]) -> bool:
    """Return whether the carried scripted prefix contains a 3C chain reveal."""
    prefix = row.get("scripted_prefix")
    if not isinstance(prefix, dict):
        return False
    reveal_ids = prefix.get("committed_reveal_ids", [])
    return any(isinstance(reveal_id, str) and reveal_id.startswith("k_sl_3c_") for reveal_id in reveal_ids)


def check(out: Path, n: int, mode: str) -> list[str]:
    errors: list[str] = []
    for name in ("source.json", "plan.json"):
        if not (out / name).is_file():
            errors.append(f"missing {name}")
    if errors:
        return errors
    source = json.loads((out / "source.json").read_text())
    expected_entry_state = "synthetic: 3C entry facts asserted, no replay of earlier scenes"
    expected_player_screen = (
        "entry text + running transcript of command lines (prefixed with a greater-than sign) "
        "and replies, as the page #transcript"
    )
    if source.get("player_screen") != expected_player_screen:
        errors.append("source does not record the player screen transcript contract")
    if source.get("transcript_note") != (
        "Only accepted turns append to the transcript; rejected turns show no rejection notice in the player screen."
    ):
        errors.append("source does not record the rejected-turn transcript note")
    start = json.loads((out / "plan.json").read_text()).get("start")
    expected_state = CARRIED_ENTRY_STATE if start == "carried" else expected_entry_state
    if source.get("entry_state") != expected_state:
        errors.append("source does not record the synthetic 3C entry state")
    start = plan_start = None
    plan = json.loads((out / "plan.json").read_text())
    source_capture = source.get("capture_item_facts")
    plan_capture = plan.get("capture_item_facts")
    if (source_capture is not None or plan_capture is not None) and (
        source_capture is not True or plan_capture is not True
    ):
        errors.append("capture_item_facts must be true in both source and plan when present")
    arms = tuple(plan.get("arms", ARMS))
    source_world_capture = source.get("world_capture")
    plan_world_capture = plan.get("world_capture")
    if {"item-facts", "no-close"} & set(arms):
        if source_world_capture is not True or plan_world_capture is not True:
            errors.append("world_capture must be true in both source and plan for the item-facts arms")
    elif source_world_capture is not None or plan_world_capture is not None:
        errors.append("world_capture is only valid for the item-facts arm")
    try:
        proof = source_proof(arms)
        if source.get("knowledge_yaml", {}).get("replacement", {}).get("matches") != 1:
            errors.append("replacement proof does not record exactly one match")
        custody_proof = source.get("knowledge_yaml", {}).get("custody_b_r1_replacement", {})
        if custody_proof.get("matches") != 1:
            errors.append("custody B-R1 proof does not record exactly one match")
        if not custody_proof.get("old") or not custody_proof.get("new"):
            errors.append("custody B-R1 proof does not record old and new strings")
        pump_proof = source.get("knowledge_yaml", {}).get("pump_b_r1_replacement", {})
        if "pump" in arms:
            if pump_proof.get("matches") != 1:
                errors.append("pump B-R1 proof does not record exactly one replacement")
            if not pump_proof.get("old") or not pump_proof.get("new"):
                errors.append("pump B-R1 proof does not record old and new strings")
        escape_proof = source.get("knowledge_yaml", {}).get("escape_replacement", {})
        if escape_proof.get("matches") != 1:
            errors.append("escape replacement proof does not record exactly one match")
        if not escape_proof.get("old") or not escape_proof.get("new"):
            errors.append("escape replacement proof does not record old and new statements")
        if source["knowledge_yaml"]["loaded_arms"] != proof["knowledge_yaml"]["loaded_arms"]:
            errors.append("loaded variation proof differs from current package")
        if source.get("plot_md") != proof.get("plot_md"):
            errors.append("plot.md entry_text replacement proof differs from current package")
        if source.get("plot_md", {}).get("replacement", {}).get("matches") != 1:
            errors.append("plot.md entry_text replacement proof does not record exactly one match")
    except Exception as error:
        errors.append(f"source proof failed: {error}")
    start = source.get("start")
    plan_start = plan.get("start")
    if tuple(source.get("arms", arms)) != arms:
        errors.append("source and plan arm selections differ")
    if not {"control", "entry", "custody", "pump", "item-facts", "no-close"} & set(arms):
        errors.append(
            "arm selection must include control, entry, custody, pump, item-facts, or no-close as the baseline"
        )
    if any(arm not in ALL_ARMS for arm in arms):
        errors.append(f"source and plan contain an unknown arm; allowed arms are {', '.join(ALL_ARMS)}")
    if source.get("semantic") not in {"on", "off"} or plan.get("semantic") != source.get("semantic"):
        errors.append("source and plan must record the same semantic setting (on or off)")
    if start not in {"entry", "posta", "post8", "postc", "carried"} or plan_start != start:
        errors.append("source and plan must record the same start arm")
    source_kristin_place = source.get("kristin_place")
    plan_kristin_place = plan.get("kristin_place")
    if source_kristin_place is None and plan_kristin_place is None:
        kristin_place = "chamber"
    elif source_kristin_place == plan_kristin_place and source_kristin_place in KRISTIN_PLACES[1:]:
        kristin_place = source_kristin_place
    else:
        kristin_place = source_kristin_place or plan_kristin_place
        errors.append("source and plan must record the same valid non-default kristin_place")
    if kristin_place != "chamber" and start != "postc":
        errors.append("kristin_place is only valid with postc start")
    if start == "postc" and kristin_place == "chamber" and (source_kristin_place or plan_kristin_place):
        errors.append("default chamber artifacts must omit kristin_place")
    if start == "carried":
        if source.get("start_label") != CARRIED_LABEL or plan.get("start_label") != CARRIED_LABEL:
            errors.append("carried start label is missing or incorrect")
        source_prefix = source.get("scripted_prefix", {})
        plan_prefix = plan.get("scripted_prefix", {})
        if set(source_prefix) != set(arms) or set(plan_prefix) != set(arms):
            errors.append("carried prefix records must exist for every arm")
        for arm in arms:
            prefix = source_prefix.get(arm, {})
            planned = plan_prefix.get(arm, {})
            if prefix != planned:
                errors.append(f"carried {arm} prefix records differ between source and plan")
            if prefix.get("turn_index") != 63 or not prefix.get("committed_reveal_ids"):
                errors.append(f"carried {arm} prefix is missing turn_index 63 or reveal ids")
            if not prefix.get("committed_reveal_ids_hash") or not prefix.get("entry_text"):
                errors.append(f"carried {arm} prefix is missing reveal hash or rendered entry text")
        if source.get("rendered_entry_text") != {
            arm: source.get("scripted_prefix", {}).get(arm, {}).get("entry_text") for arm in arms
        }:
            errors.append("source rendered entry text does not match carried prefix records")
    if start in {"posta", "post8", "postc"}:
        expected_prefix = POSTA_REVEALS if start == "posta" else POSTC_REVEALS if start == "postc" else POST8_REVEALS
        expected_label = POSTA_LABEL if start == "posta" else POSTC_LABEL if start == "postc" else POST8_LABEL
        expected_turn = 1 if start == "posta" else 7 if start == "postc" else 8
        expected_scripted = [item[0] for item in expected_prefix]
        if source.get("start_label") != expected_label or plan.get("start_label") != expected_label:
            errors.append(f"{start} start label is missing or incorrect")
        if source.get("scripted_prefix", {}).get("committed_reveal_ids") != expected_scripted:
            errors.append(f"source does not record the scripted {start} commits")
        if source.get("scripted_prefix", {}).get("turn_index") != expected_turn:
            errors.append(f"source does not record {start} turn_index={expected_turn}")
        if plan.get("scripted_prefix", {}).get("committed_reveal_ids") != expected_scripted:
            errors.append(f"plan does not record the scripted {start} commits")
        if plan.get("scripted_prefix", {}).get("turn_index") != expected_turn:
            errors.append(f"plan does not record {start} turn_index={expected_turn}")
    expected_execution = "dry" if mode == "dry" else "live"
    if plan.get("execution", expected_execution) != expected_execution:
        errors.append(f"plan execution is not {expected_execution}")
    probe_mode = plan.get("mode", plan.get("probe_mode", source.get("mode", "play")))
    if probe_mode == "commands":
        if source.get("mode") != "commands":
            errors.append("commands plan is not labelled mode commands in source")
        if start != "post8":
            errors.append("commands mode must start at post8")
        expected = [
            {"row": i, "rep": rep, "arm": arm, "turn_label": turn_label}
            for i, (rep, arm, turn_label) in enumerate(
                ((rep, arm, turn) for rep in range(1, n + 1) for arm in ARMS for turn in COMMAND_TURNS), 1
            )
        ]
        if plan.get("order") != expected:
            errors.append("commands probes are not interleaved rep/arm with turns 9 through 14")
        expected_caps = {"cloudflare": 3 * (12 * n), "raw_player": 0}
        if plan.get("caps") != expected_caps:
            errors.append("commands caps are not three Cloudflare requests per probe and zero raw-player")
        if source.get("recorded_commands") != recorded_commands():
            errors.append("source recorded commands differ from matcher table")
        if source.get("raw_commands_note") != (
            "These are an explicitly labelled raw-language check, not new player input."
        ):
            errors.append("source is missing the raw-language check note")
    else:
        expected = [{"row": i, "arm": arm} for i in range(1, n + 1) for arm in arms]
        if plan.get("order") != expected:
            errors.append(f"plan rows are not interleaved {', '.join(arms)}")
        expected_caps = POSTC_CAPS[n] if start == "postc" else CAPS[n]
        if plan.get("caps") != expected_caps:
            errors.append("plan caps disagree with required caps")
    if plan.get("entry_state") != expected_state:
        errors.append("plan does not record the synthetic 3C entry state")
    for arm in arms:
        universe = plan.get("reveal_universe_ids", {}).get(arm, [])
        if start in {"posta", "post8", "postc"}:
            expected_universe = (
                POSTA_REVEALS_EXPECTED
                if start == "posta"
                else [DE_R1]
                if start == "post8"
                else ["k_sl_3c_d_r1", "k_sl_3c_d_r2"]
            )
            if universe != expected_universe:
                errors.append(f"{arm} {start} reveal universe is not exactly {expected_universe}")
        if start in {"entry", "carried"} and not {"k_sl_3c_a_r1", "k_sl_3c_a_r2"}.issubset(universe):
            errors.append(f"{arm} plan reveal universe is missing opening reveals")
    if mode == "artifacts" and probe_mode == "commands":
        for name in ("rows.json", "spend.json", "summary.json"):
            if not (out / name).is_file():
                errors.append(f"missing {name}")
        if errors:
            return errors
        rows = json.loads((out / "rows.json").read_text())
        spend = json.loads((out / "spend.json").read_text())
        summary = json.loads((out / "summary.json").read_text())
        expected_count = 12 * n
        if len(rows) != expected_count:
            errors.append(f"expected {expected_count} command probes, found {len(rows)}")
        expected_ids = [
            f"stage7-3c-{rep:02d}-{arm}-turn{turn}" for rep in range(1, n + 1) for arm in ARMS for turn in COMMAND_TURNS
        ]
        if [row.get("row_id") for row in rows] != expected_ids:
            errors.append("command rows are not interleaved rep/arm with turns 9 through 14")
        events = spend.get("events", [])
        if sum(event.get("kind") == "cloudflare" for event in events) > 36 * n:
            errors.append("commands cloudflare spend exceeds cap")
        if sum(event.get("kind") == "raw_player" for event in events) != 0:
            errors.append("commands mode recorded a raw-player event")
        if any(row.get("status") not in {"accepted", "rejected", "clarification"} for row in rows):
            errors.append("every command row must have a valid status")
        if source_capture is True and any("item_facts_capture" not in row for row in rows):
            errors.append("capture-enabled command rows are missing item_facts_capture")
        for arm in ARMS:
            arm_rows = [row for row in rows if row.get("arm") == arm]
            for turn_label in COMMAND_TURNS:
                selected = [row for row in arm_rows if row.get("turn_label") == turn_label]
                actual = {
                    "d_r1_committed": sum(row.get("d_r1_committed") is True for row in selected),
                    "accepted": sum(row.get("status") == "accepted" for row in selected),
                    "rejected": sum(row.get("status") == "rejected" for row in selected),
                    "clarification": sum(row.get("status") == "clarification" for row in selected),
                }
                expected_counts = summary.get("arms", {}).get(arm, {}).get("turns", {}).get(str(turn_label))
                if expected_counts != actual:
                    errors.append(f"summary counts do not reconcile for {arm} turn {turn_label}")
            totals = summary.get("arms", {}).get(arm, {}).get("totals", {})
            actual_totals = {
                "d_r1_committed": sum(row.get("d_r1_committed") is True for row in arm_rows),
                "accepted": sum(row.get("status") == "accepted" for row in arm_rows),
                "rejected": sum(row.get("status") == "rejected" for row in arm_rows),
                "clarification": sum(row.get("status") == "clarification" for row in arm_rows),
            }
            if totals != actual_totals:
                errors.append(f"summary totals do not reconcile for {arm}")
        return errors
    if mode == "artifacts":
        for name in ("rows.json", "spend.json", "summary.json"):
            if not (out / name).is_file():
                errors.append(f"missing {name}")
        if errors:
            return errors
        rows = json.loads((out / "rows.json").read_text())
        spend = json.loads((out / "spend.json").read_text())
        summary = json.loads((out / "summary.json").read_text())
        if len(rows) != len(arms) * n:
            errors.append(f"expected {len(arms) * n} rows, found {len(rows)}")
        expected_ids = [f"stage7-3c-{rep:02d}-{arm}" for rep in range(1, n + 1) for arm in arms]
        if [row.get("row_id") for row in rows] != expected_ids:
            errors.append(f"artifact rows are not interleaved {', '.join(arms)}")
        events = spend.get("events", [])
        cap = POSTC_CAPS[n] if start == "postc" else CAPS[n]
        if sum(event.get("kind") == "cloudflare" for event in events) > cap["cloudflare"]:
            errors.append("cloudflare spend exceeds cap")
        if sum(event.get("kind") == "raw_player" for event in events) > cap["raw_player"]:
            errors.append("raw-player spend exceeds cap")
        allowed = {"earned_complete", "deadline_complete", "no_complete"}
        if any(row.get("outcome") not in allowed for row in rows):
            errors.append("row has an invalid outcome")
        if any(row.get("entry_state") != expected_state for row in rows):
            errors.append("row does not record the synthetic 3C entry state")
        if any(row.get("semantic") != source.get("semantic") for row in rows):
            errors.append("row semantic setting does not match source")
        if any(row.get("start") != start for row in rows):
            errors.append("row start does not match plan start")
        if kristin_place != "chamber":
            if any(row.get("kristin_place_start") != kristin_place for row in rows):
                errors.append("non-default rows must record Kristin's requested starting parent")
        elif any("kristin_place_start" in row for row in rows):
            errors.append("default chamber rows must omit kristin_place_start")
        attempt_cap = (
            POSTA_ATTEMPT_CAP
            if start == "posta"
            else POSTC_ATTEMPT_CAP
            if start == "postc"
            else POST8_ATTEMPT_CAP
            if start == "post8"
            else CARRIED_ATTEMPT_CAP
        )
        if any(row.get("attempts", 0) > attempt_cap for row in rows):
            errors.append(f"row attempts exceed the {attempt_cap}-attempt {start} cap")
        required_row_fields = (
            "a_commit_attempt",
            "a_commit_scene_turn",
            "pre_a_commands",
            "entry_text_shown",
            "acquisition_commands",
            "b_commit_attempt",
            "b_commit_on_first",
            "c_r1_commit_scene_turn",
            "c_r2_commit_scene_turn",
            "both_c_by_turn_10",
            "gate_only_escape",
        )
        if any(field not in row for row in rows for field in required_row_fields):
            errors.append("entry rows must record a commit attempt, scene turn, pre-A commands, and shown entry text")
        if start == "carried":
            if any(row.get("start_label") != CARRIED_LABEL for row in rows):
                errors.append("carried row start label is missing or incorrect")
            if any(row.get("prefix_turn_index") != 63 for row in rows):
                errors.append("carried row is missing prefix turn_index 63")
            if any(not row.get("prefix_committed_reveal_ids_hash") for row in rows):
                errors.append("carried row is missing prefix reveal ids hash")
            if any(row.get("bridge_text_shown") is None or not row.get("entry_text_shown") for row in rows):
                errors.append("carried row is missing rendered entry or bridge text")
            if any(scripted_prefix_has_chain_reveals(row) for row in rows):
                errors.append("carried scripted prefix must not record 3C chain reveals")
            if any(
                row.get("story_complete")
                and not any(reveal_id.startswith("k_sl_3c_") for reveal_id in row.get("committed_reveal_ids", []))
                for row in rows
            ):
                errors.append("carried row recorded no reveals")
            provenance = (
                "d_r1_commit_scene_turn",
                "d_r2_commit_scene_turn",
                "deadline_event_ids",
                "rejections",
                "clarifications",
                "a_commit_scene_turn",
                "b_commit_attempt",
                "acquisition_commands",
                "c_r1_commit_scene_turn",
                "c_r2_commit_scene_turn",
                "both_c_by_turn_10",
            )
            if any(field not in row for row in rows for field in provenance):
                errors.append("carried row is missing ending provenance fields")
        if any(not isinstance(row.get("pre_a_commands"), list) for row in rows):
            errors.append("pre_a_commands must be a list on every row")
        if start in {"posta", "post8", "postc"}:
            expected_scripted = [
                item[0]
                for item in (
                    POSTA_REVEALS if start == "posta" else POSTC_REVEALS if start == "postc" else POST8_REVEALS
                )
            ]
            if any(row.get("scripted_prefix", {}).get("committed_reveal_ids") != expected_scripted for row in rows):
                errors.append(f"row does not record the scripted {start} commits")
            if any(row.get("scripted_prefix", {}).get("turn_index") != expected_turn for row in rows):
                errors.append(f"row does not record the scripted {start} turn index")
            if start != "posta" and any("d_r1_commit_attempt" not in row for row in rows):
                errors.append(f"{start} row is missing d_r1_commit_attempt")
            if start != "posta" and any("first_d_commit_scene_turn" not in row for row in rows):
                errors.append(f"{start} row is missing first_d_commit_scene_turn")
        if source.get("first_command") is not None:
            if any(row.get("first_command") != source["first_command"] for row in rows):
                errors.append("row first command does not match source")
            if any(not row.get("first_command_response") for row in rows):
                errors.append("row is missing the full first-command response")
            if any(
                not row.get("turns")
                or row["turns"][0].get("attempt") != 1
                or row["turns"][0].get("scripted_first") is not True
                for row in rows
            ):
                errors.append("row does not record first command as scripted attempt 1")
        if any(
            "captives_parent" not in turn or "kristin_parent" not in turn or "case_parent" not in turn
            for row in rows
            for turn in row.get("turns", [])
        ):
            errors.append("attempt is missing captives_parent, kristin_parent, or case_parent")
        for row in rows:
            for turn in row.get("turns", []):
                has_capture = "world_capture" in turn
                if row.get("arm") in {"item-facts", "no-close"} and not has_capture:
                    errors.append("item-facts arms are missing world_capture")
                if row.get("arm") not in {"item-facts", "no-close"} and has_capture:
                    errors.append("world_capture is only valid on item-facts arms")
        if source_capture is True and any(
            "item_facts_capture" not in turn for row in rows for turn in row.get("turns", [])
        ):
            errors.append("capture-enabled rows are missing item_facts_capture")
        for arm in arms:
            selected = [row for row in rows if row.get("arm") == arm]
            if len(selected) != n:
                errors.append(f"expected {n} rows for {arm}, found {len(selected)}")
            counts = {outcome: sum(row.get("outcome") == outcome for row in selected) for outcome in allowed}
            if summary.get("arms", {}).get(arm, {}).get("outcomes") != counts:
                errors.append(f"summary outcome counts do not reconcile for {arm}")
            arm_summary = summary.get("arms", {}).get(arm, {})
            expected_metrics = {
                "both_c_by_turn_10": sum(row.get("both_c_by_turn_10") is True for row in selected),
                "c_r1_rows": sum(row.get("c_r1_commit_scene_turn") is not None for row in selected),
                "c_r2_rows": sum(row.get("c_r2_commit_scene_turn") is not None for row in selected),
                "gate_only_escape": sum(row.get("gate_only_escape") is True for row in selected),
                "rejections": sum(row.get("rejections", 0) for row in selected),
                "clarifications": sum(row.get("clarifications", 0) for row in selected),
            }
            if any(arm_summary.get(key) != value for key, value in expected_metrics.items()):
                errors.append(f"summary 3C metrics do not reconcile for {arm}")
        if (out / "run-failure.txt").exists() and len(rows) < len(arms) * n:
            errors.append("run-failure.txt is present before all rows completed")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument("n", type=int, choices=(1, 12))
    parser.add_argument("--mode", choices=("dry", "artifacts"), required=True)
    args = parser.parse_args()
    try:
        errors = check(args.out, args.n, args.mode)
    except Exception as error:
        errors = [f"checker failed: {error}"]
    if errors:
        for error in errors:
            print(f"WHY: {error}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
