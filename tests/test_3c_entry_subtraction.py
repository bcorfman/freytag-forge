from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from bench.core import load_variation, package_and_state
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector

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


def test_variation_loader_changes_only_the_entry_audience() -> None:
    shipped = load_variation(SHIPPED)
    candidate = load_variation(VARIATION)
    assert candidate["name"] == "stage7-3c-entry-world-only"
    shipped_root = Path(shipped["_package_path"])
    candidate_root = Path(candidate["_package_path"])
    for path in shipped_root.rglob("*"):
        if path.is_file() and path.name != "knowledge.yaml":
            relative = path.relative_to(shipped_root)
            assert path.read_bytes() == candidate_root.joinpath(relative).read_bytes()
    old = "  audience: {kind: public, player_visible: true}"
    new = "  audience: {kind: world_only, player_visible: false}"
    shipped_yaml = shipped_root.joinpath("knowledge.yaml").read_text(encoding="utf-8")
    candidate_yaml = candidate_root.joinpath("knowledge.yaml").read_text(encoding="utf-8")
    block_old = (
        "- id: k_scene_3c_entry\n"
        "  statement: Exposure and escape are both immediate under the collapsing operation.\n"
        "  entity_ids: [kristin, facility_escape]\n"
        "  aliases: [escape route, exposure]\n"
        "  leak_terms: []\n"
        f"{old}"
    )
    block_new = block_old.replace(old, new)
    assert candidate_yaml == shipped_yaml.replace(block_old, block_new, 1)
    assert shipped_yaml.count(old) > 1
    assert candidate_yaml.count(block_new) == 1


def test_payload_proof_removes_exactly_one_line() -> None:
    shipped_system, shipped_user = _prompt(SHIPPED)
    candidate_system, candidate_user = _prompt(VARIATION)
    assert candidate_system == shipped_system
    assert shipped_user.count(LINE) == 1
    assert candidate_user == shipped_user.replace(LINE + "\n", "", 1)


def test_entry_fact_and_reveal_projection_remain_intact() -> None:
    facts_by_point = {
        "fresh entry": (),
        "after C1+C2": (
            "truth_no_longer_containable",
            "rebecca_captured",
            "evacuation_route_open",
            "los_angeles_facility_lost",
        ),
        "after D1+D2": (
            "truth_no_longer_containable",
            "rebecca_captured",
            "evacuation_route_open",
            "los_angeles_facility_lost",
            "national_network_fragmenting",
            "community_rescue_efforts_begun",
        ),
    }
    for label, facts in facts_by_point.items():
        results = {}
        for path in (SHIPPED, VARIATION):
            variation = load_variation(path)
            package, state = package_and_state(variation, "3C")
            assert any(fact.predicate == "scene_3c_entry_known" for fact in state.facts.asserted)
            for fact_id in facts:
                state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
            results[path] = {}
            for audience in ("player", "michelle", "rebecca", "brandon"):
                projection = KnowledgeProjector().project(state, audience, "Inspect the maintenance network.")
                results[path][audience] = (
                    {item.id for item in projection.reveal_universe},
                    {item.id for item in projection.committed_knowledge},
                    {item.id for item in projection.candidates},
                )
        for audience in results[SHIPPED]:
            shipped = results[SHIPPED][audience]
            candidate = results[VARIATION][audience]
            assert shipped[0] - {"k_scene_3c_entry"} == candidate[0] - {"k_scene_3c_entry"}, (label, audience)
            assert shipped[1] - {"k_scene_3c_entry"} == candidate[1] - {"k_scene_3c_entry"}, (label, audience)
            assert shipped[2] == candidate[2], (label, audience)


def test_dry_replay_writes_one_line_subtraction(tmp_path: Path) -> None:
    source = ROOT / "bench/results/stage7-3c-escape-close-smoke/rows.json"
    module = _probe_module()
    out = tmp_path / "dry"
    module.main(["--rows", str(source), "--samples", "12", "--dry", "--out", str(out)])
    control = out.joinpath("control.user.txt").read_text(encoding="utf-8")
    subtraction = out.joinpath("subtraction.user.txt").read_text(encoding="utf-8")
    assert subtraction == control.replace(LINE + "\n", "", 1)
    diff = out.joinpath("prompt.diff").read_text(encoding="utf-8")
    assert sum(line.startswith("-- ") for line in diff.splitlines()) == 1
    assert sum(line.startswith("+- ") for line in diff.splitlines()) == 0
    plan = json.loads(out.joinpath("plan.json").read_text(encoding="utf-8"))
    assert plan["call_count"] == 24
    assert plan["call_cap"] == 24
    assert {"control", "subtraction"} == set(plan["arms"])


def test_saved_a11_prompt_contains_entry_line_once() -> None:
    source = ROOT / "bench/results/stage7-3c-escape-close-smoke/rows.json"
    prompt, _, _ = _probe_module().saved_prompt(source)
    assert prompt["user"].count(LINE) == 1


def test_live_replay_requires_confirmation_and_call_cap() -> None:
    module = _probe_module()
    with pytest.raises(SystemExit):
        module.main(["--rows", "missing.json", "--samples", "1", "--out", "/tmp/out"])
    with pytest.raises(SystemExit):
        module.main(["--rows", "missing.json", "--samples", "13", "--confirm", "--out", "/tmp/out"])


def test_live_replay_records_replies_without_retry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = ROOT / "bench/results/stage7-3c-escape-close-smoke/rows.json"
    module = _probe_module()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"narration":"{\\"segments\\":[{\\"text\\":\\"Done.\\"}]}"}'

    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return Response()

    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid")
    out = tmp_path / "live"
    module.main(["--rows", str(source), "--samples", "1", "--confirm", "--out", str(out)])
    rows = json.loads(out.joinpath("rows.json").read_text(encoding="utf-8"))
    assert len(calls) == 2
    assert [row["arm"] for row in rows] == ["control", "subtraction"]
    assert all(row["error"] is None and row["text"] for row in rows)
