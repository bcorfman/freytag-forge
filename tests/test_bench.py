import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

import bench.cli as bench_cli
import bench.core as core
from bench.core import (
    CRITERIA,
    aggregate_runs,
    append_ledger_row,
    count_example_leakage,
    has_example_leakage,
    ledger_rows,
    load_variation,
    prompt_for,
    score_judgments,
    welch_t_test,
)
from bench.item_facts import _MATCH_SYSTEM
from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from tests._legacy_package import legacy_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "data" / "stories" / "continuity-initiative"
VARIATION = ROOT / "bench" / "variations" / "example.json"
NO_EXAMPLE_VARIATION = ROOT / "bench" / "variations" / "no-output-example.json"
OVERLAY_VARIATION = ROOT / "bench" / "variations" / "drawer-overlay.json"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "bench"
ARCHIVE = FIXTURE_DIR / "arm-c" / "run1"
PLAYER_INPUT = (FIXTURE_DIR / "fixture_player_input.txt").read_text(encoding="utf-8")


def _seed_bench_custody(monkeypatch) -> None:
    original_package_and_state = core.package_and_state

    def package_and_state_with_custody(variation, scene_id=None):
        package, state = original_package_and_state(variation, scene_id)
        state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
        return package, state

    monkeypatch.setattr(core, "package_and_state", package_and_state_with_custody)


def _use_legacy_candidates(monkeypatch, knowledge_ids: set[str]) -> None:
    original_load_story_package = core.load_story_package

    def load_legacy_package(path):
        return legacy_package(original_load_story_package(path), knowledge_ids)

    monkeypatch.setattr(core, "load_story_package", load_legacy_package)


def test_score_matches_archived_acceptance_fixture() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "bench", "score", "--run-dir", str(ARCHIVE)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == {
        "total": 12,
        "per_criterion": {
            "canon_consistent": 0,
            "scene_local": 2,
            "progressive": 0,
            "rich": 1,
            "protected_safe": 5,
            "exit_motivated": 2,
            "rewards_investigation": 2,
        },
    }
    assert result.stderr == ""


def test_resolved_variation_hashes_are_stable_and_distinguish_prompt_configs() -> None:
    example = load_variation(VARIATION)
    example_again = load_variation(VARIATION)
    no_example = load_variation(NO_EXAMPLE_VARIATION)

    assert example["_variation_hash"] == example_again["_variation_hash"]
    assert example["_package_hash"] == example_again["_package_hash"]
    assert example["_variation_hash"] != no_example["_variation_hash"]
    assert example["_package_hash"] == no_example["_package_hash"]


def test_fact_judge_backend_selection_and_jev_artifacts(monkeypatch, tmp_path) -> None:
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "fact.json"
    input_path.write_text(json.dumps({"package_path": str(PACKAGE), "runs": []}), encoding="utf-8")
    calls = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        if "jev-judge.mjs" in command[1]:
            out = Path(command[command.index("--out") + 1])
            (out / "fact-tracking-judgments.json").write_text(
                json.dumps({"judgments": [{"turns": []}], "judge_calls": 4}), encoding="utf-8"
            )
            (out / "jev-raw.json").write_text(json.dumps([{"model": "jev"}]), encoding="utf-8")
        else:
            output = Path(command[command.index("--output") + 1])
            output.write_text(json.dumps({"judgments": [], "judge_calls": 2}), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    result = core.run_fact_tracking_judges(input_path, output_path)
    assert result == {"judgments": [{"turns": []}], "judge_calls": 4, "judge_backend": "jev"}
    assert calls[0][0:2] == ["node", str(ROOT / "bench" / "jev-judge.mjs")]
    assert calls[0][calls[0].index("--judges") + 1] == "fact"
    assert calls[0][calls[0].index("--package") + 1] == str(PACKAGE)
    assert calls[0][calls[0].index("--protagonist") + 1] == "Kristin"
    assert output_path.exists()
    assert (tmp_path / "fact-tracking-jev-raw.json").exists()

    monkeypatch.setenv("BENCH_FACT_JUDGE", "luna")
    result = core.run_fact_tracking_judges(input_path, tmp_path / "luna.json")
    assert result == {"judgments": [], "judge_calls": 2, "judge_backend": "luna"}
    assert calls[-1][1].endswith("fact-tracking-judge.mjs")

    monkeypatch.setenv("BENCH_FACT_JUDGE", "other")
    with pytest.raises(ValueError):
        core.run_fact_tracking_judges(input_path, tmp_path / "invalid.json")
    assert len(calls) == 2


def test_example_leakage_counts_only_distinctive_contiguous_spans() -> None:
    example = "The model should narrate the concrete immediate consequence in this scene."
    leaked = "A response should narrate the concrete immediate consequence in this scene."
    short_overlap = "The model should narrate a different outcome in another scene."

    assert has_example_leakage(leaked, example)
    assert count_example_leakage([leaked, short_overlap], example) == 1
    assert count_example_leakage([leaked], None) == 0


def test_no_example_variation_has_zero_example_leakage() -> None:
    no_example = load_variation(NO_EXAMPLE_VARIATION)

    assert no_example["_resolved_output_example"] is None
    narration = ["She picks up the lantern. She carries it out to the porch."]
    assert count_example_leakage(narration, no_example["_resolved_output_example"]) == 0


def test_custom_output_example_is_resolved_described_and_hashed(tmp_path) -> None:
    source = json.loads(VARIATION.read_text(encoding="utf-8"))
    source["name"] = "custom-example"
    source["system_prompt"]["output_example"] = '{"segments":[],"selected_knowledge_ids":[]}'
    path = tmp_path / "custom.json"
    path.write_text(json.dumps(source), encoding="utf-8")

    custom = load_variation(path)
    example = load_variation(VARIATION)
    assert custom["_resolved_output_example"] == source["system_prompt"]["output_example"]
    assert custom["_variation_hash"] != example["_variation_hash"]
    prompt = prompt_for(custom, "1A", PLAYER_INPUT)
    assert '{"segments":[],"selected_knowledge_ids":[]}' in prompt["system"]


def test_non_string_output_example_is_rejected(tmp_path) -> None:
    source = json.loads(VARIATION.read_text(encoding="utf-8"))
    source["system_prompt"]["output_example"] = {"segments": []}
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(source), encoding="utf-8")

    with pytest.raises(ValueError, match="system_prompt.output_example must be a string"):
        load_variation(path)


def test_runtime_output_example_leaves_the_provider_default_dynamic(tmp_path) -> None:
    source = json.loads(VARIATION.read_text(encoding="utf-8"))
    source["system_prompt"] = {"use_runtime_output_example": True}
    path = tmp_path / "runtime-example.json"
    path.write_text(json.dumps(source), encoding="utf-8")

    variation = load_variation(path)

    assert variation["_resolved_output_example"] is None
    assert "output_example" not in variation["_prompt_variant"]


def test_selection_only_variation_disables_model_grounding(tmp_path) -> None:
    source = json.loads(VARIATION.read_text(encoding="utf-8"))
    source["system_prompt"]["model_grounding"] = False
    path = tmp_path / "selection-only.json"
    path.write_text(json.dumps(source), encoding="utf-8")

    variation = load_variation(path)

    assert variation["_prompt_variant"]["model_grounding"] is False


def test_overlay_changes_effective_package_hash_and_assembled_prompt() -> None:
    example = load_variation(VARIATION)
    overlay = load_variation(OVERLAY_VARIATION)
    assert overlay["_package_hash"] != example["_package_hash"]
    assert "KMS initials carved in drawer" in (PACKAGE / "plot.md").read_text(encoding="utf-8")

    prompt = prompt_for(overlay, "1A", PLAYER_INPUT)
    assert "- KMS initials carved beneath the drawer" in prompt["user"]
    assert "- KMS initials carved in drawer" not in prompt["user"]


def test_ledger_rows_round_trip_through_log(tmp_path, capsys) -> None:
    ledger = tmp_path / "ledger.jsonl"
    row = {"variation_name": "example", "scores": [12], "package_hash": "package"}
    append_ledger_row(row, ledger)
    append_ledger_row({**row, "variation_name": "no-output-example", "scores": [14]}, ledger)
    args = bench_cli.parser().parse_args(["log", "--json", "--variation", "example", "--ledger", str(ledger)])
    assert bench_cli._log(args) == 0
    assert json.loads(capsys.readouterr().out) == [row]
    assert ledger_rows(ledger) == [row, {**row, "variation_name": "no-output-example", "scores": [14]}]


def _comparison_row(name: str, coverage: int, score: int, *, status: str = "ok") -> dict:
    return {
        "variation_name": name,
        "package_hash": "package",
        "scene": "1A",
        "scenes_scored": coverage,
        "max_score": coverage * len(CRITERIA),
        "status": status,
        "scores": [score],
    }


def test_compare_refuses_mismatched_scene_coverage_and_names_values(tmp_path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    append_ledger_row(_comparison_row("focused", 1, 1), ledger)
    append_ledger_row(_comparison_row("full", 9, 9), ledger)
    args = bench_cli.parser().parse_args(["compare", "focused", "full", "--ledger", str(ledger)])

    with pytest.raises(RuntimeError, match=r"scene coverage differs.*1.*9"):
        bench_cli._compare(args)


def test_compare_matching_scene_coverage_succeeds_and_override_allows_mismatch(tmp_path, capsys) -> None:
    ledger = tmp_path / "ledger.jsonl"
    append_ledger_row(_comparison_row("left", 1, 1), ledger)
    append_ledger_row(_comparison_row("right", 1, 2), ledger)
    args = bench_cli.parser().parse_args(["compare", "left", "right", "--ledger", str(ledger)])
    assert bench_cli._compare(args) == 0
    assert "difference (left - right): -1.00" in capsys.readouterr().out

    mismatch = tmp_path / "mismatch.jsonl"
    append_ledger_row(_comparison_row("left", 1, 1), mismatch)
    append_ledger_row(_comparison_row("right", 9, 2), mismatch)
    args = bench_cli.parser().parse_args(
        ["compare", "left", "right", "--ledger", str(mismatch), "--allow-coverage-mismatch"]
    )
    assert bench_cli._compare(args) == 0
    assert "scene coverage was not held constant" in capsys.readouterr().out


def test_compare_displays_example_leakage(tmp_path, capsys) -> None:
    ledger = tmp_path / "ledger.jsonl"
    left = _comparison_row("left", 1, 1)
    right = _comparison_row("right", 1, 2)
    left["example_leakage"] = 3
    right["example_leakage"] = 0
    append_ledger_row(left, ledger)
    append_ledger_row(right, ledger)
    args = bench_cli.parser().parse_args(["compare", "left", "right", "--ledger", str(ledger)])

    assert bench_cli._compare(args) == 0
    assert "example_leakage" in capsys.readouterr().out


@pytest.mark.parametrize("coverage", ["missing", "null"])
def test_compare_excludes_unknown_scale_rows_and_reports_them(tmp_path, capsys, coverage) -> None:
    ledger = tmp_path / "ledger.jsonl"
    unknown = _comparison_row("left", 1, 9)
    if coverage == "missing":
        del unknown["scenes_scored"]
    else:
        unknown["scenes_scored"] = None
    append_ledger_row(unknown, ledger)
    append_ledger_row(_comparison_row("left", 1, 1), ledger)
    append_ledger_row(_comparison_row("left", 1, 2), ledger)
    append_ledger_row(_comparison_row("right", 1, 1), ledger)
    append_ledger_row(_comparison_row("right", 1, 2), ledger)
    args = bench_cli.parser().parse_args(["compare", "left", "right", "--ledger", str(ledger)])

    assert bench_cli._compare(args) == 0
    output = capsys.readouterr().out
    assert "left: n=2 mean=1.50" in output
    assert "skipped 1" in output
    assert "left" in output
    assert "unknown" in output


def test_log_marks_unknown_scale_rows_without_hiding_them(tmp_path, capsys) -> None:
    ledger = tmp_path / "ledger.jsonl"
    missing = _comparison_row("left", 1, 9)
    del missing["scenes_scored"]
    null = _comparison_row("left", 1, 8)
    null["scenes_scored"] = None
    append_ledger_row(missing, ledger)
    append_ledger_row(null, ledger)
    args = bench_cli.parser().parse_args(["log", "--variation", "left", "--ledger", str(ledger)])

    assert bench_cli._log(args) == 0
    output = capsys.readouterr().out
    assert "legacy/unknown-scale" in output
    assert "unknown-scale (null)" in output
    assert output.count("left") == 2


def test_failed_replicate_is_recorded_and_excluded_from_compare(monkeypatch, tmp_path) -> None:
    variation = {
        "name": "broken-arm",
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
    script = {"name": "e2e", "inputs": ["Investigate."]}

    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [script])
    monkeypatch.setattr(
        bench_cli,
        "run_scene",
        lambda *_: (_ for _ in ()).throw(NarrationProviderError("invalid", 502, "INVALID_PROPOSAL")),
    )
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", ledger)
    args = bench_cli.parser().parse_args(
        ["run", "--variation", str(VARIATION), "--scene", "1A", "--replicates", "1", "--out", str(tmp_path)]
    )

    assert bench_cli._run(args) == 2
    row = ledger_rows(ledger)[0]
    assert row["status"] == "failed"
    assert "INVALID_PROPOSAL" in row["failure_reason"]
    assert row["scenes_scored"] == 0
    assert row["max_score"] == 0


def test_run_scene_records_a_narration_safety_rejection_instead_of_crashing(monkeypatch) -> None:
    payload = {
        "segments": [{"kind": "narration", "text": "A quiet detail.", "grounding_ids": ["k_invented_source"]}],
        "selected_knowledge_ids": [],
    }

    class FakeProvider:
        request_count = 0
        recovery_count = 0
        last_projection = None

        def opening(self) -> dict[str, object]:
            return {"segments": [{"kind": "narration", "text": "A quiet house."}]}

        def __call__(self, _: str) -> dict[str, object]:
            return payload

    provider = FakeProvider()
    variation = {
        "name": "grounding-citation-baseline",
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
        "_prompt_variant": {
            "include_output_example": True,
            "output_example": '{"segments": [], "selected_knowledge_ids": []}',
            "beat_delivery": "details",
        },
    }
    monkeypatch.setattr(core, "provider_for", lambda *_: provider)

    result = core.run_scene(variation, "1A", {"name": "repro", "inputs": ["Search the drawer."]})

    assert result["status"] == "failed"
    assert "invalid_grounding_reference" in result["failure_reason"]


def test_run_scene_fixed_turns_completes_without_leaving_and_numbers_turns(monkeypatch) -> None:
    payload = {
        "segments": [{"kind": "narration", "text": "A quiet detail.", "grounding_ids": []}],
        "selected_knowledge_ids": [],
    }

    class FakeProvider:
        request_count = 0
        recovery_count = 0
        last_projection = None

        def opening(self) -> dict[str, object]:
            return {"segments": [{"kind": "narration", "text": "A quiet house."}]}

        def __call__(self, _: str) -> dict[str, object]:
            return payload

    variation = {
        "name": "fixed-turns",
        "_package_path": str(PACKAGE),
        "_fixed_turns": 3,
        "_prompt_variant": {"include_output_example": True, "output_example": "{}", "beat_delivery": "details"},
    }
    monkeypatch.setattr(core, "provider_for", lambda *_: FakeProvider())

    result = core.run_scene(
        variation,
        "1A",
        {"name": "fixed", "inputs": ["Go out to the truck and bring my laptop inside."]},
    )

    assert result["status"] == "ok"
    assert result["fixed_turns"] == 3
    assert [turn["turn_number"] for turn in result["turns"]] == [1, 2, 3]
    assert result["rejected_turns"] == []
    assert all("narrated_command" in turn for turn in result["turns"])
    assert result["turns"][0]["narrated_command"] == "Go out to the truck. Bring my laptop inside."


def test_run_scene_turn_record_keeps_new_item_on_same_turn(monkeypatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "test-token")

    def request(_provider, payload):
        _provider.last_prompt = {"system": payload["system"], "user": payload["user"]}
        if payload["system"] == _MATCH_SYSTEM:
            return {"refers": [], "same_as": {"receipt": "receipt"}}
        return {
            "segments": [{"kind": "narration", "text": "Kristin examines the room."}],
            "selected_knowledge_ids": [],
            "item_facts": {"receipt": {"place": "on the ground", "condition": ["crumpled"]}},
        }

    monkeypatch.setattr(CloudflareTurnProvider, "_request", request)
    variation = load_variation(ROOT / "bench" / "variations" / "item-facts-single.json")
    variation["_fixed_turns"] = 1
    result = core.run_scene(variation, "1A", core.scripts_for(variation, "1A")[0])

    turn = result["turns"][0]
    assert turn["item_facts_after"]["receipt"] == {"place": "on the ground", "condition": ["crumpled"]}
    assert turn["item_facts_held"] == []
    assert turn["item_facts_resolutions"] == {"receipt": "new"}
    assert turn["item_facts_engine_resolutions"] == {}


def test_run_scene_records_narration_prompt_before_item_facts_match(monkeypatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "test-token")

    def request(provider, payload):
        provider.last_prompt = {"system": payload["system"], "user": payload["user"]}
        if payload["system"] == _MATCH_SYSTEM:
            return {"refers": ["Michelle's phone"], "same_as": {}}
        return {
            "segments": [{"kind": "narration", "text": "Kristin pockets the phone."}],
            "selected_knowledge_ids": [],
        }

    monkeypatch.setattr(CloudflareTurnProvider, "_request", request)
    variation = load_variation(ROOT / "bench" / "variations" / "item-facts-single.json")
    variation["_fixed_turns"] = 1
    command = "Pick up Michelle's phone and put it in my pocket."

    result = core.run_scene(variation, "1A", {"name": "prompt", "inputs": [command]})

    turn = result["turns"][0]
    assert "PLAYER:" in turn["prompt_user"]
    assert turn["narrated_command"] in turn["prompt_user"]
    assert turn["prompt_system"] != _MATCH_SYSTEM
    assert "COMMAND:" not in turn["prompt_user"]


def test_run_scene_fixed_turns_records_rejection_and_continues(monkeypatch) -> None:
    rejected_payload = {
        "segments": [{"kind": "narration", "text": "A quiet detail.", "grounding_ids": ["k_invented_source"]}],
        "selected_knowledge_ids": [],
    }
    accepted_payload = {
        "segments": [{"kind": "narration", "text": "A known detail.", "grounding_ids": []}],
        "selected_knowledge_ids": [],
    }

    class FakeProvider:
        request_count = 0
        recovery_count = 0
        last_projection = None

        def __init__(self) -> None:
            self.payloads = iter((rejected_payload, accepted_payload, accepted_payload))

        def opening(self) -> dict[str, object]:
            return {"segments": [{"kind": "narration", "text": "A quiet house."}]}

        def __call__(self, _: str) -> dict[str, object]:
            return next(self.payloads)

    provider = FakeProvider()
    variation = {
        "name": "fixed-rejection",
        "_package_path": str(PACKAGE),
        "_fixed_turns": 3,
        "_prompt_variant": {"include_output_example": True, "output_example": "{}", "beat_delivery": "details"},
    }
    monkeypatch.setattr(core, "provider_for", lambda *_: provider)

    result = core.run_scene(variation, "1A", {"name": "fixed", "inputs": ["Search the drawer."]})

    assert result["status"] == "ok"
    assert [turn["turn_number"] for turn in result["turns"]] == [2, 3]
    rejection = result["rejected_turns"][0]
    assert rejection["turn_number"] == 1
    assert rejection["player_input"] == "Search the drawer."
    assert rejection["rejection_code"] == "invalid_grounding_reference"
    assert rejection["rejection_reason"]
    assert result["rejected_turn_count"] == 1


def test_run_scene_fixed_turns_provider_outage_still_fails(monkeypatch) -> None:
    class FakeProvider:
        request_count = 0
        recovery_count = 0

        def opening(self) -> dict[str, object]:
            return {"segments": [{"kind": "narration", "text": "A quiet house."}]}

        def __call__(self, _: str) -> dict[str, object]:
            raise NarrationProviderError("provider down", 503, "PROVIDER_DOWN")

    variation = {
        "name": "fixed-outage",
        "_package_path": str(PACKAGE),
        "_fixed_turns": 3,
        "_prompt_variant": {"include_output_example": True, "output_example": "{}", "beat_delivery": "details"},
    }
    monkeypatch.setattr(core, "provider_for", lambda *_: FakeProvider())

    result = core.run_scene(variation, "1A", {"name": "fixed", "inputs": ["Search the drawer."]})

    assert result["status"] == "failed"
    assert result["fixed_turns"] == 3
    assert "PROVIDER_DOWN" in result["failure_reason"]


@pytest.mark.parametrize("fixed_turns", [True, 0, -1, "12"])
def test_invalid_fixed_turns_are_rejected(tmp_path, fixed_turns) -> None:
    source = json.loads(VARIATION.read_text(encoding="utf-8"))
    source["fixed_turns"] = fixed_turns
    path = tmp_path / "invalid-fixed-turns.json"
    path.write_text(json.dumps(source), encoding="utf-8")

    with pytest.raises(ValueError, match="fixed_turns must be a positive integer"):
        load_variation(path)


def test_run_scene_records_selection_and_offered_candidates(monkeypatch) -> None:
    payload = {
        "segments": [
            {
                "kind": "narration",
                "text": (
                    "Michelle's damaged memory card recording was under the KMS drawer and warns Kristin not to trust "
                    "emergency broadcasts."
                ),
                "grounding_ids": ["k_sl_1a_b_r2"],
            }
        ],
        "selected_knowledge_ids": ["k_sl_1a_b_r2"],
    }

    class FakeProvider:
        request_count = 0
        recovery_count = 0
        authored_handoff = SimpleNamespace(candidate=SimpleNamespace(id="k_sl_1a_b_r2"))
        model_grounding_ids = ("k_sl_1a_b_r2",)
        model_selected_knowledge_ids = ("k_sl_1a_b_r2",)
        shadow_matched_candidate_id = "k_sl_1a_b_r2"
        prompt_candidate_ids = ("k_sl_1a_b_r2",)
        last_projection = None

        def opening(self) -> dict[str, object]:
            return {"segments": [{"kind": "narration", "text": "A quiet house."}]}

        def __call__(self, _: str) -> dict[str, object]:
            self.last_projection = SimpleNamespace(
                candidates=[SimpleNamespace(id="k_sl_1a_b_r2"), SimpleNamespace(id="k_sl_1a_b_r1")]
            )
            return payload

    provider = FakeProvider()
    variation = {
        "name": "selection-recording",
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
        "_prompt_variant": {
            "include_output_example": True,
            "output_example": '{"segments": [], "selected_knowledge_ids": []}',
            "beat_delivery": "details",
        },
    }

    def provider_for_with_active_storylet(state, _variation):
        state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
        state.active_event_ids.add("SL-1A-B")
        return provider

    monkeypatch.setattr(core, "provider_for", provider_for_with_active_storylet)

    result = core.run_scene(
        variation,
        "1A",
        {"name": "repro", "inputs": ["Search the drawers under her workstation."]},
        max_turns=1,
    )

    assert result["turns"][0]["selected_knowledge_ids"] == ["k_sl_1a_b_r2"]
    assert result["turns"][0]["authored_handoff_candidate_id"] == "k_sl_1a_b_r2"
    assert result["turns"][0]["model_selected_knowledge_ids"] == ["k_sl_1a_b_r2"]
    assert result["turns"][0]["grounding_ids"] == ["k_sl_1a_b_r2"]
    assert result["turns"][0]["model_grounding_ids"] == ["k_sl_1a_b_r2"]
    assert result["turns"][0]["shadow_matched_candidate_id"] == "k_sl_1a_b_r2"
    assert result["turns"][0]["prompt_candidate_ids"] == ["k_sl_1a_b_r2"]
    assert result["turns"][0]["candidates_offered"] == ["k_sl_1a_b_r2", "k_sl_1a_b_r1"]
    assert result["turns"][0]["cue_fact_id"] is None
    assert result["turns"][0]["cue_text"] is None
    assert result["turns"][0]["complication_text"] is None
    assert result["turns"][0]["handoff_staged"] is False


def test_run_baseline_refuses_archived_nine_scene_coverage_before_live_work(monkeypatch, tmp_path) -> None:
    variation = {
        "name": "test",
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [{"name": "e2e", "inputs": ["Investigate."]}])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: pytest.fail("baseline guard ran live work"))
    args = bench_cli.parser().parse_args(
        [
            "run",
            "--variation",
            str(VARIATION),
            "--scene",
            "1A",
            "--replicates",
            "1",
            "--out",
            str(tmp_path),
            "--baseline",
            str(ARCHIVE),
        ]
    )

    with pytest.raises(RuntimeError, match=r"scene coverage differs.*1.*9"):
        bench_cli._run(args)


def test_run_baseline_with_unknown_scale_skips_baseline_statistics(monkeypatch, tmp_path, capsys) -> None:
    variation = {
        "name": "test",
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    (baseline / "summary.json").write_text(json.dumps({"replicate_scores": [99]}), encoding="utf-8")
    script = {"name": "e2e", "inputs": ["Look around."]}
    judgment = {criterion: False for criterion in CRITERIA}
    judgment["missing_or_wrong"] = []
    record = {
        "replicate": 0,
        "script": "e2e",
        "scene_id": "1A",
        "opening": "Opening.",
        "turns": [],
        "completed": True,
        "quota": None,
        "narration_turns": 1,
        "narration_requests": 1,
        "recovery_requests": 0,
        "package": str(PACKAGE),
    }
    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [script])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: record.copy())
    monkeypatch.setattr(bench_cli, "_confirm", lambda *_: None)
    monkeypatch.setattr(bench_cli, "run_judges", lambda *_: {"judgments": [judgment], "judge_calls": 1})
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    args = bench_cli.parser().parse_args(
        [
            "run",
            "--variation",
            str(VARIATION),
            "--scene",
            "1A",
            "--replicates",
            "1",
            "--out",
            str(tmp_path / "run"),
            "--baseline",
            str(baseline),
        ]
    )

    assert bench_cli._run(args) == 0
    output = capsys.readouterr().out
    assert "skipped unknown-scale baseline" in output
    summary = json.loads((tmp_path / "run" / "summary.json").read_text(encoding="utf-8"))
    assert "comparison" not in summary


def test_aggregate_reports_actual_scene_denominator() -> None:
    runs = [{"replicate": 1, "script": "e2e", "scene_id": "1A", "example_leakage": 2}]
    judgments = [{criterion: criterion == "protected_safe" for criterion in CRITERIA}]
    aggregate = aggregate_runs(runs, judgments, 1)
    assert aggregate["scenes_scored"] == 1
    assert aggregate["max_score"] == 7
    assert aggregate["score_metric"].startswith("7-point record")
    assert aggregate["example_leakage"] == 2


def test_failures_only_aggregate_reports_failure_details() -> None:
    failure = {
        "replicate": 1,
        "script": "e2e",
        "scene_id": "1A",
        "failure_reason": "narration provider failed",
    }
    aggregate = aggregate_runs([], [], 1, failures=[failure])
    assert aggregate["failed_replicates"] == 1
    assert aggregate["failures"] == [failure]
    assert aggregate["failures"][0]["failure_reason"] == "narration provider failed"
    assert "entry_state" not in aggregate


def test_entry_state_counts_projected_committed_knowledge() -> None:
    variation = load_variation(VARIATION)
    _, state = core.package_and_state(variation, "1A")
    state.facts.assert_fact(Fact(predicate="patrol_return_pressure", subject="story", value="true"))
    projector = KnowledgeProjector()
    projected_count = len(projector.project(state, "player", "").committed_knowledge)
    earned_count = sum(
        KnowledgeProjector._established(item, state) and KnowledgeProjector._visible_to(item, "player")
        for item in state.package.knowledge.knowledge
    )

    assert core.entry_state(state) == {
        "scene_id": "1A",
        "committed_knowledge_count": projected_count,
        "earned_knowledge_count": earned_count,
        "seeded_by": "bare",
    }
    assert projected_count != len(state.facts.asserted)


def test_score_exposes_graded_missing_entries_without_changing_record_score() -> None:
    result = score_judgments(
        [
            {
                "canon_consistent": False,
                "scene_local": True,
                "progressive": False,
                "rich": False,
                "protected_safe": True,
                "exit_motivated": False,
                "rewards_investigation": False,
                "missing_or_wrong": ["missing detail", {"criterion": "progressive"}],
            }
        ]
    )
    assert result["total"] == 2
    assert result["graded_secondary"]["total"] == 2
    assert result["graded_secondary"]["per_criterion_where_attributable"] == {"progressive": 1}
    assert result["graded_secondary"]["unattributed"] == 1


def test_quota_header_and_app_rate_limit_are_distinguished() -> None:
    quota = HTTPError(
        "https://worker.example",
        429,
        "quota",
        {"X-Narration-Error-Code": "AI_QUOTA_EXCEEDED"},
        io.BytesIO(b'{"detail":"narration service is at capacity"}'),
    )
    rate_limit = HTTPError(
        "https://worker.example",
        429,
        "rate",
        {},
        io.BytesIO(b'{"detail":"rate limit exceeded"}'),
    )
    assert CloudflareTurnProvider._worker_error_code(quota) == "AI_QUOTA_EXCEEDED"
    assert CloudflareTurnProvider._worker_error_code(rate_limit) == "RATE_LIMITED"


def test_welch_report_says_when_difference_is_inside_noise() -> None:
    result = welch_t_test([13, 14, 13, 15], [12, 13, 12, 14])
    assert result["test"] == "two-sided Welch t-test"
    assert result["inside_noise"] is True
    assert "nothing detectable" in result["statement"]


def test_focused_run_allows_one_explicit_replicate_without_calling_live_services(monkeypatch, tmp_path) -> None:
    variation = {
        "name": "test",
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
    script = {"name": "e2e", "inputs": ["Look around."]}
    judgment = {criterion: False for criterion in CRITERIA}
    judgment["missing_or_wrong"] = []
    record = {
        "replicate": 0,
        "script": "e2e",
        "scene_id": "1A",
        "opening": "Opening.",
        "turns": [],
        "completed": True,
        "quota": None,
        "narration_turns": 1,
        "narration_requests": 1,
        "recovery_requests": 0,
        "package": str(PACKAGE),
    }

    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [script])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: record.copy())

    def fake_judges(_input, output):
        result = {"judgments": [judgment], "judge_calls": 1}
        output.write_text(json.dumps(result), encoding="utf-8")
        return result

    monkeypatch.setattr(bench_cli, "run_judges", fake_judges)
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    args = bench_cli.parser().parse_args(
        [
            "run",
            "--variation",
            str(VARIATION),
            "--scene",
            "1A",
            "--replicates",
            "1",
            "--out",
            str(tmp_path),
        ]
    )

    assert bench_cli._run(args) == 0
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["replicates"] == 1
    assert summary["pooled"]["score_points"]["n"] == 1
    assert summary["pooled"]["score_points"]["standard_deviation"] is None
    assert summary["budget"]["actual_openai_judge_calls"] == 1
    assert summary["judge_failure_reason"] is None


def test_main_judge_failure_is_recorded_on_summary_and_failures(monkeypatch, tmp_path) -> None:
    variation = {
        "name": "judge-failure",
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
    record = {
        "status": "ok",
        "replicate": 0,
        "script": "e2e",
        "scene_id": "1A",
        "opening": "Opening.",
        "turns": [],
        "completed": True,
        "quota": None,
        "narration_turns": 1,
        "narration_requests": 1,
        "recovery_requests": 0,
        "package": str(PACKAGE),
    }
    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [{"name": "e2e", "inputs": ["Look around."]}])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: record.copy())

    def fail_judges(*_):
        raise RuntimeError("HTTP 429 quota")

    monkeypatch.setattr(bench_cli, "run_judges", fail_judges)
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    args = bench_cli.parser().parse_args(
        ["run", "--variation", str(VARIATION), "--scene", "1A", "--replicates", "1", "--out", str(tmp_path)]
    )

    assert bench_cli._run(args) == 2
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["judge_failure_reason"] == "HTTP 429 quota"
    assert summary["failures"][0]["status"] == "failed"
    assert summary["failures"][0]["failure_reason"] == "HTTP 429 quota"


def test_fact_tracking_judge_failure_is_recorded_on_summary_and_failures(monkeypatch, tmp_path) -> None:
    variation = {
        "name": "fact-tracking-failure",
        "fact_tracking_judge": True,
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
    judgment = {criterion: False for criterion in CRITERIA} | {"missing_or_wrong": []}
    record = {
        "status": "ok",
        "replicate": 0,
        "script": "e2e",
        "scene_id": "1A",
        "opening": "Opening.",
        "turns": [],
        "completed": True,
        "quota": None,
        "narration_turns": 1,
        "narration_requests": 1,
        "recovery_requests": 0,
        "package": str(PACKAGE),
    }
    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [{"name": "e2e", "inputs": ["Look around."]}])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: record.copy())
    monkeypatch.setattr(bench_cli, "run_judges", lambda *_: {"judgments": [judgment], "judge_calls": 1})

    def fail_fact_tracking_judges(*_):
        raise RuntimeError("HTTP 429 quota")

    monkeypatch.setattr(bench_cli, "run_fact_tracking_judges", fail_fact_tracking_judges)
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    args = bench_cli.parser().parse_args(
        ["run", "--variation", str(VARIATION), "--scene", "1A", "--replicates", "1", "--out", str(tmp_path)]
    )

    assert bench_cli._run(args) == 2
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["judge_failure_reason"] == "HTTP 429 quota"
    assert summary["failures"][0]["status"] == "failed"
    assert summary["failures"][0]["failure_reason"] == "HTTP 429 quota"


def test_escalation_judge_is_opt_in_and_added_to_summary_ledger_and_spend(monkeypatch, tmp_path) -> None:
    variation = {
        "name": "escalation-arm",
        "escalation_judge": True,
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
    script = {"name": "e2e", "inputs": ["Inspect the drawer."]}
    judgment = {criterion: False for criterion in CRITERIA}
    judgment["missing_or_wrong"] = []
    escalation_judgment = {
        "cue_points_to_missing_thread": "yes",
        "complication_creates_pressure_without_unearned_knowledge": "no",
        "no_pre_reveal_disclosure": "not_applicable",
        "reasons": [],
    }
    record = {
        "replicate": 0,
        "script": "e2e",
        "scene_id": "1A",
        "opening": "Opening.",
        "turns": [],
        "completed": True,
        "quota": None,
        "narration_turns": 1,
        "narration_requests": 1,
        "recovery_requests": 0,
        "package": str(PACKAGE),
    }

    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [script])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: record.copy())
    monkeypatch.setattr(bench_cli, "_confirm", lambda *_: None)
    monkeypatch.setattr(bench_cli, "run_judges", lambda *_: {"judgments": [judgment], "judge_calls": 1})
    monkeypatch.setattr(
        bench_cli,
        "run_escalation_judges",
        lambda *_: {"judgments": [escalation_judgment], "judge_calls": 2},
    )
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", ledger)
    args = bench_cli.parser().parse_args(
        [
            "run",
            "--variation",
            str(VARIATION),
            "--scene",
            "1A",
            "--replicates",
            "1",
            "--out",
            str(tmp_path / "run"),
        ]
    )

    assert bench_cli._run(args) == 0
    summary = json.loads((tmp_path / "run" / "summary.json").read_text(encoding="utf-8"))
    assert summary["escalation"]["cue_points_to_missing_thread"] == {"yes": 1, "no": 0, "not_applicable": 0}
    assert summary["budget"]["actual_openai_judge_calls"] == 3
    row = ledger_rows(ledger)[0]
    assert row["escalation"] == summary["escalation"]
    assert row["spend"]["judge_calls"] == 3


def test_escalation_judge_absent_is_not_called_and_not_recorded(monkeypatch, tmp_path) -> None:
    variation = {
        "name": "ordinary-arm",
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
    script = {"name": "e2e", "inputs": ["Inspect the drawer."]}
    judgment = {criterion: False for criterion in CRITERIA}
    judgment["missing_or_wrong"] = []
    record = {
        "replicate": 0,
        "script": "e2e",
        "scene_id": "1A",
        "opening": "Opening.",
        "turns": [],
        "completed": True,
        "quota": None,
        "narration_turns": 1,
        "narration_requests": 1,
        "recovery_requests": 0,
        "package": str(PACKAGE),
    }
    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [script])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: record.copy())
    monkeypatch.setattr(bench_cli, "_confirm", lambda *_: None)
    monkeypatch.setattr(bench_cli, "run_judges", lambda *_: {"judgments": [judgment], "judge_calls": 1})
    monkeypatch.setattr(bench_cli, "run_escalation_judges", lambda *_: pytest.fail("opt-in judge was called"))
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", ledger)
    args = bench_cli.parser().parse_args(
        [
            "run",
            "--variation",
            str(VARIATION),
            "--scene",
            "1A",
            "--replicates",
            "1",
            "--out",
            str(tmp_path / "run"),
        ]
    )

    assert bench_cli._run(args) == 0
    summary = json.loads((tmp_path / "run" / "summary.json").read_text(encoding="utf-8"))
    assert "escalation" not in summary
    assert "escalation" not in ledger_rows(ledger)[0]


@pytest.mark.parametrize(
    "judge_key, invalid_path, error_message",
    [
        pytest.param(
            "escalation_judge",
            "invalid-escalation.json",
            "escalation_judge must be a boolean",
            id="non_boolean_escalation_judge_is_rejected",
        ),
        pytest.param(
            "continuity_judge",
            "invalid-continuity.json",
            "continuity_judge must be a boolean",
            id="non_boolean_continuity_judge_is_rejected",
        ),
    ],
)
def test_non_boolean_judge_is_rejected(tmp_path, judge_key, invalid_path, error_message) -> None:
    source = json.loads(VARIATION.read_text(encoding="utf-8"))
    source[judge_key] = "yes"
    path = tmp_path / invalid_path
    path.write_text(json.dumps(source), encoding="utf-8")

    with pytest.raises(ValueError, match=error_message):
        load_variation(path)


def test_continuity_judge_is_opt_in_and_added_to_summary_ledger_and_spend(monkeypatch, tmp_path) -> None:
    variation = {
        "name": "continuity-arm",
        "continuity_judge": True,
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
    script = {"name": "e2e", "inputs": ["Inspect the drawer."]}
    judgment = {criterion: False for criterion in CRITERIA}
    judgment["missing_or_wrong"] = []
    continuity_judgment = {
        "turns": [
            {
                "turn": 1,
                "contradicts_stated_fact": "yes",
                "protagonist_acts_beyond_command": "no",
                "restarts_scene": "no",
                "reason": "The phone is cracked.",
            }
        ]
    }
    record = {
        "replicate": 0,
        "script": "e2e",
        "scene_id": "1A",
        "opening": "Opening.",
        "turns": [{"player_input": "Inspect the drawer.", "narration": "The drawer catches."}],
        "completed": True,
        "quota": None,
        "narration_turns": 1,
        "narration_requests": 1,
        "recovery_requests": 0,
        "package": str(PACKAGE),
    }
    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [script])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: record.copy())
    monkeypatch.setattr(bench_cli, "_confirm", lambda *_: None)
    monkeypatch.setattr(bench_cli, "run_judges", lambda *_: {"judgments": [judgment], "judge_calls": 1})
    monkeypatch.setattr(
        bench_cli,
        "run_continuity_judges",
        lambda *_: {"judgments": [continuity_judgment], "judge_calls": 2},
    )
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", ledger)
    args = bench_cli.parser().parse_args(
        [
            "run",
            "--variation",
            str(VARIATION),
            "--scene",
            "1A",
            "--replicates",
            "1",
            "--out",
            str(tmp_path / "run"),
        ]
    )

    assert bench_cli._run(args) == 0
    summary = json.loads((tmp_path / "run" / "summary.json").read_text(encoding="utf-8"))
    assert summary["continuity"]["contradicts_stated_fact"] == {"yes": 1, "no": 0}
    assert summary["continuity"]["turns_judged"] == 1
    assert summary["budget"]["actual_openai_judge_calls"] == 3
    row = ledger_rows(ledger)[0]
    assert row["continuity"] == summary["continuity"]
    assert row["spend"]["judge_calls"] == 3


def test_continuity_judge_absent_is_not_called_and_not_recorded(monkeypatch, tmp_path) -> None:
    variation = {
        "name": "ordinary-arm",
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
    script = {"name": "e2e", "inputs": ["Inspect the drawer."]}
    judgment = {criterion: False for criterion in CRITERIA} | {"missing_or_wrong": []}
    record = {
        "replicate": 0,
        "script": "e2e",
        "scene_id": "1A",
        "opening": "Opening.",
        "turns": [],
        "completed": True,
        "quota": None,
        "narration_turns": 1,
        "narration_requests": 1,
        "recovery_requests": 0,
        "package": str(PACKAGE),
    }
    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [script])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: record.copy())
    monkeypatch.setattr(bench_cli, "_confirm", lambda *_: None)
    monkeypatch.setattr(bench_cli, "run_judges", lambda *_: {"judgments": [judgment], "judge_calls": 1})
    monkeypatch.setattr(bench_cli, "run_continuity_judges", lambda *_: pytest.fail("opt-in judge was called"))
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", ledger)
    args = bench_cli.parser().parse_args(
        [
            "run",
            "--variation",
            str(VARIATION),
            "--scene",
            "1A",
            "--replicates",
            "1",
            "--out",
            str(tmp_path / "run"),
        ]
    )
    assert bench_cli._run(args) == 0
    summary = json.loads((tmp_path / "run" / "summary.json").read_text(encoding="utf-8"))
    assert "continuity" not in summary
    assert "continuity" not in ledger_rows(ledger)[0]


def test_run_writes_failed_turns_to_all_turn_records_without_changing_judged_records(monkeypatch, tmp_path) -> None:
    variation = {
        "name": "failed-selection",
        "_package_path": str(PACKAGE),
        "_variation_hash": "variation-hash",
        "_package_hash": "package-hash",
    }
    script = {"name": "e2e", "inputs": ["Search the drawer."]}
    failed_turn = {
        "player_input": "Search the drawer.",
        "narration": "The drawer catches.",
        "left_scene": False,
        "beats_projected": [],
        "selected_knowledge_ids": ["k_sl_1a_b_r2"],
        "candidates_offered": ["k_sl_1a_b_r2"],
    }
    record = {
        "status": "failed",
        "replicate": 0,
        "script": "e2e",
        "scene_id": "1A",
        "opening": "Opening.",
        "turns": [failed_turn],
        "completed": False,
        "quota": None,
        "failure_reason": "scene did not leave",
        "narration_turns": 1,
        "narration_requests": 1,
        "recovery_requests": 0,
        "package": str(PACKAGE),
    }

    monkeypatch.setattr(bench_cli, "load_variation", lambda _: variation)
    monkeypatch.setattr(bench_cli, "scripts_for", lambda *_: [script])
    monkeypatch.setattr(bench_cli, "run_scene", lambda *_: record.copy())
    monkeypatch.setattr(bench_cli, "_confirm", lambda *_: None)
    monkeypatch.setattr(bench_cli, "LEDGER_PATH", tmp_path / "ledger.jsonl")
    args = bench_cli.parser().parse_args(
        [
            "run",
            "--variation",
            str(VARIATION),
            "--scene",
            "1A",
            "--replicates",
            "1",
            "--out",
            str(tmp_path),
        ]
    )

    assert bench_cli._run(args) == 2
    all_records = json.loads((tmp_path / "all-turn-records.json").read_text(encoding="utf-8"))
    assert all_records["runs"][0]["status"] == "failed"
    assert all_records["runs"][0]["turns"] == [failed_turn]
    assert all_records["runs"][0]["turns"][0]["selected_knowledge_ids"] == ["k_sl_1a_b_r2"]
    assert all_records["runs"][0]["turns"][0]["candidates_offered"] == ["k_sl_1a_b_r2"]
    turn_records = json.loads((tmp_path / "turn-records.json").read_text(encoding="utf-8"))
    assert turn_records["runs"] == []


def test_chat_contract_accepts_variation_argument() -> None:
    args = bench_cli.parser().parse_args(["chat", "--variation", str(VARIATION)])
    assert args.command == "chat"
    assert args.variation == VARIATION


def test_judge_bridge_imports_both_existing_judge_exports() -> None:
    result = subprocess.run(
        [
            "node",
            "-e",
            "import('./frontend/e2e/roleplay-judge.js').then(({judgeSceneNarration, sceneCanon}) => { "
            "if (typeof judgeSceneNarration !== 'function' || typeof sceneCanon !== 'function') process.exit(1); })",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_a_prompt_can_be_inspected_without_writing_a_variation_file() -> None:
    """A variation holds one side of a comparison; seeing the shipped prompt needs neither."""

    from bench.core import default_variation, prompt_for

    variation = default_variation()
    prompts = prompt_for(variation, "1A", "Look around the kitchen.")

    assert prompts["user"].startswith("CHARACTERS:")
    assert "PLAYER:\n- Look around the kitchen." in prompts["user"]
    assert variation["_prompt_variant"]["beat_delivery"] == "details"


def test_variation_records_harness_selection_switch() -> None:
    from bench.core import resolve_variation

    variation = resolve_variation(
        {
            "name": "harness-switch",
            "story_package": "data/stories/continuity-initiative",
            "system_prompt": {"auto_select_unambiguous_candidates": False},
        },
        PACKAGE / "variation.json",
    )

    assert variation["_prompt_variant"]["auto_select_unambiguous_candidates"] is False


def test_entering_a_scene_with_no_action_yet_renders_no_player_section() -> None:
    """The scene-entry prompt has no player action, so it must not show an empty heading."""

    from bench.core import default_variation, prompt_for

    prompts = prompt_for(default_variation(), "1A", "")

    assert "PLAYER:" not in prompts["user"]
    assert prompts["user"].startswith("CHARACTERS:")


def test_a_named_beat_reaches_the_prompt(monkeypatch) -> None:
    """Naming a beat shows the turn that presents it, not the one pacing chose."""

    from bench.core import default_variation, prompt_for

    _use_legacy_candidates(monkeypatch, {"k_sl_1a_d_r1"})
    _seed_bench_custody(monkeypatch)
    variation = default_variation()
    entered = prompt_for(variation, "1A", "Search the drawers.")
    with_beat = prompt_for(default_variation(), "1A", "Search the drawers.", "1A.2")

    assert "taped drawer" not in entered["user"]
    assert "population stabilization centers" in with_beat["user"]
    assert "k_sl_1a_d_r1 in selected_knowledge_ids" in with_beat["user"]


def test_a_beat_may_be_named_by_id_ordinal_or_anchor() -> None:
    from bench.core import default_variation, package_and_state, resolve_beat

    package, _ = package_and_state(default_variation(), "1A")

    assert resolve_beat(package, "1A", "1A.2").id == "1A.2"
    assert resolve_beat(package, "1A", "2").id == "1A.2"
    assert resolve_beat(package, "1A", "scene-1a2--michelles-last-investigation").id == "1A.2"


def test_an_unknown_beat_names_the_beats_the_scene_actually_has() -> None:
    """A bad id must not send the caller reading plot.md to find the right one."""

    from bench.core import default_variation, package_and_state, resolve_beat

    package, _ = package_and_state(default_variation(), "1A")

    with pytest.raises(ValueError, match=r"1A\.1 \(Michelle Is Gone\)"):
        resolve_beat(package, "1A", "9Z")


def test_a_beat_carries_the_progress_of_the_beats_before_it(monkeypatch) -> None:
    """Beat N must show beats 1..N-1 as knowledge already held, not reveals still owed.

    Offering an earlier beat's reveal again tells the narrator the player has yet
    to learn something they learned two beats ago, which is how a scene stalls.
    """

    from bench.core import default_variation, prompt_for

    _use_legacy_candidates(monkeypatch, {"k_sl_1a_c_r2"})
    prompts = prompt_for(default_variation(), "1A", "Inspect the gate after the patrol leaves.", "1A.4")
    scene = prompts["user"].split("SCENE:")[1].split("CONSTRAINTS:")[0]
    constraints = prompts["user"].split("CONSTRAINTS:")[1]

    earlier = "to a removal too deliberate to be looting"
    assert earlier in scene, "beat 1A.1's reveal must be established knowledge by beat 1A.4"
    assert "k_sl_1a_a_r1" not in constraints, "an established reveal must not still be offered"
    assert "k_sl_1a_c_r2 in selected_knowledge_ids" in constraints, "1A.4's own reveal stays on offer"
    # SL-1A-D is optional and gated on memory_card_recovered, which is
    # not established by naming beat 1A.4 alone.
    assert "Taped beneath a drawer" not in scene


def test_the_first_beat_of_a_scene_establishes_nothing_before_it() -> None:
    from bench.core import beats_for, default_variation, establish_prior_beats, package_and_state

    variation = default_variation()
    package, state = package_and_state(variation, "1A")
    first = beats_for(package, "1A")[0]

    assert establish_prior_beats(package, state, "1A", first) == ()


def test_a_storylet_spanning_into_the_named_beat_is_not_treated_as_finished() -> None:
    """SL-1A-A presents both 1A.1 and 1A.2, so at 1A.2 it is still live."""

    from bench.core import beats_for, default_variation, establish_prior_beats, package_and_state

    variation = default_variation()
    package, state = package_and_state(variation, "1A")
    second = next(item for item in beats_for(package, "1A") if item.id == "1A.2")

    assert "SL-1A-A" not in establish_prior_beats(package, state, "1A", second)


def test_one_storylet_can_be_read_in_isolation(monkeypatch) -> None:
    """Beats are shared between storylets, so a narrower view has to exist."""

    from bench.core import default_variation, prompt_for

    _use_legacy_candidates(monkeypatch, {"k_sl_1a_d_r1"})
    _seed_bench_custody(monkeypatch)
    narrow = prompt_for(default_variation(), "1A", "Feel under the drawer.", None, "SL-1A-D")
    wide = prompt_for(default_variation(), "1A", "Feel under the drawer.", "1A.2")

    assert "k_sl_1a_d_r1" in narrow["user"]
    assert "Michelle's phone on the kitchen floor" not in narrow["user"], (
        "a neighbouring storylet's beat must not bleed in"
    )
    assert "Michelle's phone on the kitchen floor" in wide["user"], (
        "the beat view keeps every storylet that presents it"
    )


def test_a_beat_and_a_storylet_cannot_be_named_together() -> None:
    from bench.core import default_variation, prompt_for

    with pytest.raises(ValueError, match="name only one"):
        prompt_for(default_variation(), "1A", "Look.", "1A.2", "SL-1A-D")


def test_the_player_character_is_not_listed_as_a_speaker_of_scene_statements() -> None:
    """The protagonist's sayable list mirrored SCENE and grew with every beat."""

    from bench.core import default_variation, prompt_for

    prompts = prompt_for(default_variation(), "1A", "Play back the recording.", "1A.3")

    assert "Kristin Schweitzer may say this aloud" not in prompts["user"]


def test_an_optional_storylet_is_excluded_once_its_rival_has_fired() -> None:
    """SL-1A-B and SL-1A-D are both gated on continuity_initiative_known being unset.

    Only one of them can ever fire in a real playthrough, so a reconstructed
    history that contains both is a history no player could have had.
    """

    from bench.core import beats_for, default_variation, establish_prior_beats, package_and_state

    package, state = package_and_state(default_variation(), "1A")
    last = next(item for item in beats_for(package, "1A") if item.id == "1A.4")
    fired = establish_prior_beats(package, state, "1A", last)

    assert "SL-1A-B" in fired
    assert "SL-1A-D" not in fired, "a storylet its rival excluded must not also fire"


def test_a_fact_set_true_does_not_satisfy_a_gate_requiring_it_false() -> None:
    """The engine gates storylet activation on these predicates (engine.py:199).

    An absent fact is the ordinary false state, but a fact that is present and
    true must fail 'equals: false' - otherwise a gate meant to exclude a rival
    storylet never excludes anything.
    """

    from storygame.runtime.facts import Fact, FactStore
    from storygame.runtime.validation import predicate_matches
    from storygame.story_package.models import FactPredicate

    wants_unset = FactPredicate(fact_id="continuity_initiative_known", equals=False)
    wants_set = FactPredicate(fact_id="continuity_initiative_known", equals=True)
    facts = FactStore()

    assert predicate_matches(wants_unset, facts) is True
    assert predicate_matches(wants_set, facts) is False

    facts.assert_fact(Fact(predicate="continuity_initiative_known", subject="story", value="true"))

    assert predicate_matches(wants_unset, facts) is False
    assert predicate_matches(wants_set, facts) is True
