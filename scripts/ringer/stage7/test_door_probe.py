from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from check_door_probe import check
from door_continuation import action_groups, matched_ids
from door_probe import EXPERIMENTS, bridge_material, dry_run, write_failed_response
from door_prompt import ARMS, COMMAND, GROUNDED_LINES, PromptSelection, patch_prompt, prompt_plan, select_prompt
from door_transport import RawRequestError, SpendBudget, raw_request

from bench.core import load_variation, package_and_state
from storygame.runtime.contracts import RuntimeContractError, parse_turn_proposal


def test_selects_unique_target_and_preserves_system() -> None:
    selection = select_prompt()
    assert selection.system == select_prompt().system
    assert selection.user.endswith(COMMAND)


def test_exact_patches_and_credential_occurrences() -> None:
    selection = select_prompt()
    assert selection.user.count("Brandon prepares technical credentials while Kristin chooses") == 2
    control = patch_prompt(selection, "control")
    assert control["user"] == selection.user
    wording = patch_prompt(selection, "wording")
    assert COMMAND not in wording["user"]
    assert wording["user"].endswith("Search the service corridors for a route to the detention area.")
    stale = patch_prompt(selection, "stale-scene")
    assert stale["user"].count("Brandon prepared their technical credentials") == 2


def test_prompt_arms_and_bridge_reconstruct() -> None:
    assert [arm for _, arm in prompt_plan()[:6]] == list(ARMS)
    material = bridge_material()
    assert material["recorded"] == material["control_screen"]
    assert "Beyond those corridors" not in material["bridge_screen"]
    assert material["entry"].rstrip() in material["bridge_screen"]


def test_dry_run_is_complete_and_checker_friendly(tmp_path: Path) -> None:
    dry_run(tmp_path, 1)
    data = json.loads((tmp_path / "results.json").read_text())
    assert len(data["rows"]) == 6
    assert (tmp_path / "spend.jsonl").read_text() == ""


def test_source_experiment_config_prompt_diffs_and_variation_overrides(tmp_path: Path) -> None:
    assert EXPERIMENTS["source"]["arms"] == ("control", "location", "limits")
    assert EXPERIMENTS["source"]["caps"] == {
        1: {"raw": 3, "cloudflare": 15, "player": 6},
        12: {"raw": 36, "cloudflare": 180, "player": 72},
    }
    selection = select_prompt()
    location = patch_prompt(selection, "location", "source")
    limits = patch_prompt(selection, "limits", "source")
    assert location["system"] == selection.system
    assert location["user"].split("PLAYER:\n", 1)[1] == selection.user.split("PLAYER:\n", 1)[1]
    assert location["user"].count("Their false identities have passed the first security checks.") == 1
    assert limits["user"].count("Kristin notes its limits before they move on") == 2
    assert limits["user"].split("PLAYER:\n", 1)[1] == selection.user.split("PLAYER:\n", 1)[1]
    dry_run(tmp_path, 1, "source")
    results = json.loads((tmp_path / "results.json").read_text())
    assert [(row["rep"], row["arm"]) for row in results["rows"]] == [
        (1, "control"),
        (1, "location"),
        (1, "limits"),
    ]
    for arm, filename in EXPERIMENTS["source"]["variations"].items():
        variation = load_variation(Path("bench/variations") / filename)
        package, _ = package_and_state(variation, "2A")
        knowledge = "\n".join(item.statement for item in package.knowledge_indexes.by_id.values())
        if arm == "location":
            assert knowledge.count("Their false identities have passed the first security checks.") == 1
        if arm == "limits":
            assert knowledge.count("Kristin notes its limits before they move on") == 1


def test_completion_system_ablation_is_exact_and_checker_friendly(tmp_path: Path) -> None:
    assert EXPERIMENTS["completion"]["arms"] == ("control", "no-finish")
    assert EXPERIMENTS["completion"]["caps"] == {
        1: {"raw": 2, "cloudflare": 10, "player": 4},
        12: {"raw": 24, "cloudflare": 120, "player": 48},
    }
    selection = select_prompt()
    control = patch_prompt(selection, "control", "completion")
    no_finish = patch_prompt(selection, "no-finish", "completion")
    line = "Finish each action the player gives.\n"
    assert control["system"] == selection.system
    assert control["hashes"]["system"] == control["hashes"]["original_system"]
    assert no_finish["system"] == selection.system.replace(line, "", 1)
    assert no_finish["system_diff"]
    assert no_finish["user"] == control["user"]
    assert no_finish["hashes"]["user"] == control["hashes"]["user"]
    assert no_finish["hashes"]["original_user"] == control["hashes"]["original_user"]
    for system in (selection.system.replace(line, "", 1), selection.system + line):
        synthetic = PromptSelection(system, selection.user, selection.source_path)
        with pytest.raises(AssertionError, match="finish instruction count"):
            patch_prompt(synthetic, "no-finish", "completion")
    dry_run(tmp_path, 1, "completion")
    assert len(json.loads((tmp_path / "results.json").read_text())["rows"]) == 2
    run = json.loads((tmp_path / "run.json").read_text())
    assert run["experiment"] == "completion"
    assert run["caps"] == EXPERIMENTS["completion"]["caps"][1]
    assert check(tmp_path, 1, "dry", "completion") == []


def test_grounded_config_prompt_diff_variations_and_dry_checker(tmp_path: Path) -> None:
    assert EXPERIMENTS["grounded"]["arms"] == ("control", "grounded")
    assert EXPERIMENTS["grounded"]["caps"] == {
        1: {"raw": 2, "cloudflare": 10, "player": 4},
        12: {"raw": 24, "cloudflare": 120, "player": 48},
    }
    selection = select_prompt()
    control = patch_prompt(selection, "control", "grounded")
    grounded = patch_prompt(selection, "grounded", "grounded")
    assert control["user"] == selection.user
    assert control["hashes"]["user"] == control["hashes"]["original_user"]
    assert grounded["system"] == control["system"]
    assert grounded["original_user"] == control["original_user"]
    appended = "".join(f"- {line}\n" for line in GROUNDED_LINES)
    anchor = "- This happens now. Show it in the scene: A second credential check threatens their inspector cover.\n"
    assert grounded["user"] == control["user"].replace(anchor, anchor + appended, 1)
    assert all(f"+- {line}" in grounded["diff"] for line in GROUNDED_LINES)
    for arm, package_path in EXPERIMENTS["grounded"]["variations"].items():
        variation = load_variation(Path("bench/variations") / package_path)
        package, _ = package_and_state(variation, "2A")
        assert variation["_package_path"].endswith(
            "bench/frozen/continuity-pre-2a-panel" if arm == "control" else "data/stories/continuity-initiative"
        )
        assert package.story_id == "continuity_initiative"
    dry_run(tmp_path, 1, "grounded")
    assert [(row["rep"], row["arm"]) for row in json.loads((tmp_path / "results.json").read_text())["rows"]] == [
        (1, "control"),
        (1, "grounded"),
    ]
    assert check(tmp_path, 1, "dry", "grounded") == []


def test_grounded_rejects_missing_or_duplicate_anchor() -> None:
    selection = select_prompt()
    anchor = "- This happens now. Show it in the scene: A second credential check threatens their inspector cover.\n"
    missing = PromptSelection(selection.system, selection.user.replace(anchor, "", 1), selection.source_path)
    with pytest.raises(AssertionError, match="facility-gate anchor"):
        patch_prompt(missing, "grounded", "grounded")
    duplicate = PromptSelection(
        selection.system, selection.user + "\n".join(f"- {line}" for line in GROUNDED_LINES), selection.source_path
    )
    with pytest.raises(AssertionError, match="already present"):
        patch_prompt(duplicate, "grounded", "grounded")


def test_budget_reserves_before_request_and_parser_rejects_bad_envelope() -> None:
    budget = SpendBudget(1)

    class Provider:
        request_count = 1
        recovery_count = 0
        reply_keys_dropped = {}

        def _request(self, payload):
            assert payload["max_tokens"] == 1024
            return {"segments": [{"kind": "narration", "text": "A response."}]}

    result = raw_request(Provider(), "system", "user", budget)
    assert result.proposal.narration == "A response."
    assert budget.sent == budget.acknowledged == 1
    with pytest.raises(RuntimeContractError):
        parse_turn_proposal({"segments": []})


@pytest.mark.parametrize("item_facts", [{"door": {"place": "corridor"}}, {}])
def test_item_facts_are_telemetry_and_do_not_change_the_saved_reply(item_facts: dict[str, object]) -> None:
    body = {
        "segments": [{"kind": "narration", "text": "A response."}],
        "selected_knowledge_ids": [],
        "item_facts": item_facts,
    }

    class Provider:
        request_count = 1
        recovery_count = 0
        reply_keys_dropped = {}

        def _request(self, payload):
            return body

    result = raw_request(Provider(), "system", "user")
    assert result.normalized is body
    assert result.item_facts == item_facts
    assert result.telemetry["item_facts"] == item_facts
    assert result.proposal.narration == "A response."


def test_unknown_reply_key_still_fails_with_evidence(tmp_path: Path) -> None:
    body = {
        "segments": [{"kind": "narration", "text": "A response."}],
        "unexpected": True,
    }

    class Provider:
        def _request(self, payload):
            return body

    with pytest.raises(RawRequestError) as raised:
        raw_request(Provider(), "system", "user")
    assert raised.value.stage == "parse"
    artifact = json.loads(write_failed_response(tmp_path, raised.value).read_text())
    assert json.loads(artifact["body"]) == body


def test_parse_failure_keeps_response_without_retry() -> None:
    budget = SpendBudget(1)
    body = {"segments": [{"kind": "not-a-kind", "text": "returned body"}]}

    class Provider:
        def __init__(self) -> None:
            self.calls = 0

        def _request(self, payload):
            self.calls += 1
            return body

    provider = Provider()
    with pytest.raises(RawRequestError) as raised:
        raw_request(provider, "system", "user", budget)
    assert raised.value.stage == "parse"
    assert raised.value.normalized == body
    assert provider.calls == budget.sent == 1


def test_request_failure_keeps_last_response_and_does_not_retry() -> None:
    budget = SpendBudget(1)

    class Provider:
        last_response = {"provider": "body"}

        def __init__(self) -> None:
            self.calls = 0

        def _request(self, payload):
            self.calls += 1
            raise OSError("connection failed")

    provider = Provider()
    with pytest.raises(RawRequestError) as raised:
        raw_request(provider, "system", "user", budget)
    assert raised.value.stage == "request"
    assert raised.value.normalized == provider.last_response
    assert provider.calls == budget.sent == 1


def test_failed_response_file_contains_full_body_hash_and_truncation(tmp_path: Path) -> None:
    body = {"segments": [{"kind": "bad", "text": "x" * 5000}]}
    error = RawRequestError("parse", ValueError("bad envelope"), body)
    path = write_failed_response(tmp_path, error)
    artifact = json.loads(path.read_text())
    serialized = json.dumps(body, default=str, ensure_ascii=False)
    assert artifact["stage"] == "parse"
    assert artifact["error"] == "bad envelope"
    assert artifact["sha256"] == hashlib.sha256(serialized.encode()).hexdigest()
    assert artifact["body"] == serialized[:4000]


def test_matcher_requires_exactly_one_hit_in_synthetic_groups() -> None:
    groups = {"one": {"matched": True}, "two": {"matched": False}}
    assert matched_ids(groups, "Read the selection files.") == ["one"]
    assert action_groups()


def test_live_checker_rejects_three_commands_and_mixed_spend(tmp_path: Path) -> None:
    dry_run(tmp_path, 1)
    run = json.loads((tmp_path / "run.json").read_text())
    run.update({"mode": "live", "experiment_id": "exp", "ledger_path": str(tmp_path / "ledger.jsonl")})
    (tmp_path / "run.json").write_text(json.dumps(run))
    results = json.loads((tmp_path / "results.json").read_text())
    row = results["rows"][0]
    row.update({"commands": ["one", "two", "three"], "continuation": {"turns": []}})
    results["rows"] = [row] + results["rows"][1:]
    (tmp_path / "results.json").write_text(json.dumps(results))
    summary = json.loads((tmp_path / "summary.json").read_text())
    summary.update(
        {
            "mode": "live",
            "experiment_id": "exp",
            "rows": 6,
            "cloudflare_requests": 1,
            "raw_player_attempts": 1,
            "caps": {"cloudflare": 28, "player": 12},
        }
    )
    (tmp_path / "summary.json").write_text(json.dumps(summary))
    (tmp_path / "spend.jsonl").write_text('{"kind":"cloudflare"}\n{"kind":"raw_player"}\n')
    (tmp_path / "ledger.jsonl").write_text(
        json.dumps({"experiment_id": "exp", "cloudflare_requests": 1, "raw_player_attempts": 1}) + "\n"
    )
    errors = check(tmp_path, 1, "artifacts")
    assert any("more than two" in error for error in errors)
