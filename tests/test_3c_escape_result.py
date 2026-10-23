from __future__ import annotations

from pathlib import Path

import three_c_probe as probe

from bench.core import load_variation, package_and_state
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.world_model import world_for

ROOT = Path(__file__).resolve().parents[1]
ARM_FILES = {
    "control": "stage7-3c-control.json",
    "escape": "stage7-3c-escape-result.json",
}
COMMANDS = {
    "k_sl_3c_a_r1": "Send the evidence package.",
    "k_sl_3c_b_r1": "Take the Portable data case from Rebecca.",
    "k_sl_3c_c_r1": "Restore the drainage pumps.",
    "k_sl_3c_c_r2": "Open the surface gates.",
}
C_ORDERS = (
    ("k_sl_3c_c_r1", "k_sl_3c_c_r2"),
    ("k_sl_3c_c_r2", "k_sl_3c_c_r1"),
)


def _package(arm: str):
    variation = load_variation(ROOT / "bench/variations" / ARM_FILES[arm])
    return package_and_state(variation, "3C")


def _engine(arm: str) -> tuple[object, RuntimeEngine]:
    package, state = _package(arm)
    probe.assert_3c_entry_facts(state)
    return package, RuntimeEngine(state, None)


def _reveal(engine: RuntimeEngine, package: object, knowledge_id: str) -> None:
    engine.provider = probe._scripted_provider(package, knowledge_id)
    engine.turn(COMMANDS[knowledge_id])
    engine._activate_pacing()  # noqa: SLF001 - inspect deterministic reveal eligibility.


def _finish_a_and_b(arm: str) -> tuple[object, RuntimeEngine]:
    package, engine = _engine(arm)
    _reveal(engine, package, "k_sl_3c_a_r1")
    _reveal(engine, package, "k_sl_3c_b_r1")
    return package, engine


def _parents(package: object, engine: RuntimeEngine) -> dict[str, str | None]:
    world = world_for(package, engine.state.facts)
    return {person: world.parent(person) for person in ("captives", "kristin", "michelle", "brandon")}


def _eligibility(engine: RuntimeEngine) -> list[str]:
    projection = engine.projector.project(engine.state, "player", "Check reports from other detention sites.")
    return sorted(candidate.id for candidate in projection.reveal_universe)


def test_escape_source_proof_records_one_statement_replacement() -> None:
    proof = probe.source_proof(("control", "escape"))
    replacement = proof["knowledge_yaml"]["escape_replacement"]
    assert replacement["matches"] == 1
    assert replacement["old"].startswith("statement: 'Kristin restores power")
    assert replacement["new"] == "statement: 'The drainage pumps have power. The evacuation route is open.'"
