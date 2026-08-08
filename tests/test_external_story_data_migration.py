import hashlib
import json
from pathlib import Path
from random import Random

from storygame.cli import run_turn
from storygame.engine.world import build_default_state
from storygame.evaluation import load_evaluation_fixtures
from storygame.story_data_audit import AUDIT_MANIFEST, audit_story_specific_branches
from tests.narrator_stubs import StubNarrator


def test_phase_zero_story_specific_audit_is_fully_classified():
    root = Path(__file__).resolve().parents[1]
    findings = audit_story_specific_branches(root)

    assert findings, "The Phase 0 audit must report the current migration inventory."
    undocumented = [
        finding
        for finding in findings
        if (finding.path, finding.rule) not in AUDIT_MANIFEST
        or finding.classification == "undocumented"
    ]
    assert not undocumented, "Undocumented story-specific seams:\n" + "\n".join(
        f"{finding.path}:{finding.line} [{finding.rule}] {finding.text}" for finding in undocumented
    )
    assert all(finding.owner_phase.startswith("Phase ") for finding in findings)
    assert all(finding.replacement_schema for finding in findings)
    assert all(finding.removal_phase.startswith("Phase ") for finding in findings)


def test_phase_zero_audit_manifest_has_no_stale_entries():
    root = Path(__file__).resolve().parents[1]
    observed = {(finding.path, finding.rule) for finding in audit_story_specific_branches(root)}
    assert set(AUDIT_MANIFEST) <= observed


def test_phase_zero_package_projections_and_transcripts_match_frozen_baseline():
    root = Path(__file__).resolve().parents[1]
    baseline = json.loads((root / "data" / "phase0_baseline.json").read_text(encoding="utf-8"))
    assert baseline["version"] == "phase0-v1"

    for fixture in load_evaluation_fixtures():
        state = build_default_state(
            seed=fixture["seed"],
            genre=fixture["genre"],
            session_length=fixture["session_length"],
            tone=fixture["tone"],
        )
        expected = baseline["fixtures"][fixture["id"]]
        projection = {
            "outline_id": state.story_outline_id,
            "rooms": list(state.world.rooms),
            "items": list(state.world.items),
            "npcs": [npc.name for npc in state.world.npcs.values()],
            "start_room": state.player.location,
            "inventory": list(state.player.inventory),
        }
        assert projection == expected["projection"]

        rng = Random(fixture["seed"])
        output_hashes: list[str] = []
        turn_indexes: list[int] = []
        for command in fixture["commands"]:
            state, output, *_ = run_turn(state, command, rng, StubNarrator("phase0 baseline"))
            output_hashes.append(hashlib.sha256(json.dumps(output, ensure_ascii=True).encode()).hexdigest())
            turn_indexes.append(state.turn_index)
        assert {
            "commands": fixture["commands"],
            "output_sha256": output_hashes,
            "turn_index": turn_indexes,
            "replay_sha256": hashlib.sha256(repr(state.replay_signature()).encode()).hexdigest(),
        } == expected["transcript"]
