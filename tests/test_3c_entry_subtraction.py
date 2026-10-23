from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from bench.core import load_variation, package_and_state
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.facts import Fact

ROOT = Path(__file__).resolve().parents[1]
SHIPPED = ROOT / "bench/variations/stage7-3c-item-facts.json"
VARIATION = ROOT / "bench/variations/stage7-3c-entry-world-only.json"
LINE = "- Exposure and escape are both immediate under the collapsing operation."


def _probe_module():
    path = ROOT / "scripts/ringer/stage7/3c_entry_replay_probe.py"
    spec = importlib.util.spec_from_file_location("entry_replay_probe", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _prompt(variation_path: Path) -> tuple[str, str]:
    variation = load_variation(variation_path)
    package, state = package_and_state(variation, "3C")
    for fact_id in (
        "truth_no_longer_containable",
        "rebecca_captured",
        "evacuation_route_open",
        "los_angeles_facility_lost",
    ):
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    provider = CloudflareTurnProvider(worker_url="", token="", state=state, prompt_variant=variation["_prompt_variant"])
    assembled = provider.assemble_turn_prompt("Continue through the maintenance tunnel to the surface.")
    return assembled["system"], provider._section_user_prompt(assembled["context"])


def test_live_replay_requires_confirmation_and_call_cap() -> None:
    module = _probe_module()
    with pytest.raises(SystemExit):
        module.main(["--rows", "missing.json", "--samples", "1", "--out", "/tmp/out"])
    with pytest.raises(SystemExit):
        module.main(["--rows", "missing.json", "--samples", "13", "--confirm", "--out", "/tmp/out"])
