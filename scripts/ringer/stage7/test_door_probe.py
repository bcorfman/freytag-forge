from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
from check_door_probe import check
from door_continuation import action_groups, matched_ids, score_command
from door_probe import EXPERIMENTS, _continue, bridge_material, dry_run, write_failed_response
from door_prompt import (
    ARMS,
    COMMAND,
    THINGS_ASSUMPTION,
    PromptSelection,
    grounded_additions,
    patch_prompt,
    prompt_plan,
    select_prompt,
    things_emulation,
)
from door_transport import RawRequestError, SpendBudget, raw_request

from bench.core import load_variation, package_and_state
from storygame.runtime.contracts import RuntimeContractError, parse_turn_proposal


class _ScoreState:
    def snapshot(self):
        return self


class _Turn:
    def __init__(self, narration: str = "Done.", *, clarification: bool = False) -> None:
        self.narration = narration
        self.game_break = None
        if clarification:
            self.clarification = object()


class _ScoreEngine:
    def __init__(self, response: _Turn) -> None:
        self.response = response
        self.calls = []
        self.last_attempt = None
        self.last_reference_resolution = None

    def turn(self, command: str, **kwargs):
        self.calls.append((command, kwargs))
        return self.response


def _score_stub(monkeypatch: pytest.MonkeyPatch, groups: list[dict[str, dict[str, object]]], committed: list[str]):
    import door_continuation

    for group in groups:
        for value in group.values():
            value.setdefault("reason", None)
    monkeypatch.setattr(door_continuation, "eligible_groups", lambda state, command: groups.pop(0))
    monkeypatch.setattr(door_continuation, "committed_reveals", lambda before, after: committed)
    monkeypatch.setattr(door_continuation, "fact_keys", lambda state: [])
    return _ScoreState()


def test_score_target_counts_first_turn_commit_after_empty_pre_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _ScoreEngine(_Turn())
    state = _score_stub(
        monkeypatch,
        [
            {"target": {"evidence": (), "eligible": False, "matched": False}},
            {"target": {"evidence": (), "eligible": True, "matched": True}},
            {"target": {"evidence": (), "eligible": False, "matched": False}},
            {"target": {"evidence": (), "eligible": False, "matched": False}},
        ],
        ["target"],
    )
    targeted = score_command(engine, state, "open the door", target_reveal="target")
    assert targeted["status"] == "earned"
    assert targeted["target_committed"] is True
    assert targeted["eligible"] == []
    assert (
        score_command(
            engine,
            state,
            "open the door",
        )["status"]
        == "unearned"
    )


def test_score_target_ignores_different_matched_reveal(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _ScoreEngine(_Turn())
    state = _score_stub(
        monkeypatch,
        [
            {"other": {"evidence": (), "eligible": True, "matched": True}},
            {"other": {"evidence": (), "eligible": True, "matched": True}},
        ],
        ["other"],
    )
    result = score_command(engine, state, "search", target_reveal="target")
    assert result["status"] == "unearned"
    assert result["target_committed"] is False


def test_target_already_committed_is_not_earned_again(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _ScoreEngine(_Turn())
    state = _score_stub(
        monkeypatch,
        [
            {"target": {"evidence": (), "eligible": True, "matched": True}},
            {"target": {"evidence": (), "eligible": True, "matched": True}},
        ],
        ["target"],
    )
    result = score_command(engine, state, "search", target_reveal="target", already_committed=frozenset({"target"}))
    assert result["status"] == "already_established"
    assert result["target_committed"] is True


def test_clarification_is_scored_and_repair_forwards_original_command(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _ScoreEngine(_Turn("Do you mean the archive terminals?", clarification=True))
    state = _score_stub(
        monkeypatch,
        [
            {"target": {"evidence": (), "eligible": False, "matched": False}},
            {"target": {"evidence": (), "eligible": False, "matched": False}},
        ],
        [],
    )
    result = score_command(engine, state, "search the terminals", target_reveal="target")
    assert result["status"] == "clarification"
    assert result["clarification_question"] == "Do you mean the archive terminals?"

    import door_probe

    calls = []

    def fake_score(engine, state, command, **kwargs):
        calls.append((command, kwargs))
        return {
            "command": command,
            "status": "clarification",
            "response": "Choose one.",
            "eligible": [],
            "matched": [],
            "before_facts": [],
            "after_facts": [],
            "committed_reveals": [],
        }

    class Provider:
        semantic_ask = None

    class Context:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(door_probe, "load_variation", lambda path: object())
    monkeypatch.setattr(door_probe, "package_and_state", lambda variation, scene: (object(), object()))
    monkeypatch.setattr(door_probe, "provider_for", lambda state, variation: Provider())
    monkeypatch.setattr(door_probe, "RuntimeEngine", lambda state, provider: object())
    monkeypatch.setattr(door_probe, "counted_provider", lambda provider, budget: Context())
    monkeypatch.setattr(door_probe, "score_command", fake_score)
    monkeypatch.setattr(door_probe, "_ask_player", lambda prompt, budget: "The archive terminals")
    result = _continue(
        Path("unused"), ["search the terminals"], object(), "screen", target_reveal="target", repair_clarification=True
    )
    assert calls[1][1]["clarifies"] == "search the terminals"
    assert calls[1][1]["clarification_round"] == 1
    assert result["clarification_turns"] == [1, 2]


def test_grounded_config_is_the_only_targeted_experiment() -> None:
    assert EXPERIMENTS["grounded"]["target_reveal"] == "k_sl_2b_a_r1"
    assert EXPERIMENTS["grounded"]["repair_clarification"] is True
    for experiment in ("door", "source", "completion"):
        assert "target_reveal" not in EXPERIMENTS[experiment]
        assert "repair_clarification" not in EXPERIMENTS[experiment]


def test_saved_grounded_replay_artifact_has_structural_turn_fields() -> None:
    path = Path("bench/results/stage7-door-grounded-n12-slotted/results.json")
    if not path.exists():
        pytest.skip("saved grounded replay artifact is absent")
    data = json.loads(path.read_text(encoding="utf-8"))
    for row in data.get("rows", []):
        turns = row.get("continuation", {}).get("turns", [])
        assert len(turns) <= 2
        if "earned_by_command_2" in row:
            assert isinstance(row["earned_by_command_2"], bool)
            assert row["earned_by_command_2"] is any(turn.get("status") == "earned" for turn in turns[:2])
        if "target_commit_turn" in row:
            assert row["target_commit_turn"] in (None, 1, 2)
        if "clarification_turns" in row:
            assert all(turn in (1, 2) for turn in row["clarification_turns"])


def _current_story_constraint_lines() -> tuple[str, ...]:
    """Current story state: update this assertion when plot.md changes."""

    plot = Path("data/stories/continuity-initiative/plot.md").read_text()
    scene = plot.split("## Scene 2A — False Identities\n", 1)[1].split("\n---\n", 1)[0]
    placement = "- cooling-service archive panel is beside the inspection console in the infrastructure corridors."
    facts = tuple(f"- {line}" for line in re.findall(r"^- (.+)$", scene, re.MULTILINE))
    return (placement, *facts)


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
    additions = grounded_additions()
    assert grounded["things_assumption"] == THINGS_ASSUMPTION
    assert (
        grounded["user"]
        .split("THINGS:\n", 1)[1]
        .startswith(additions["THINGS"][0] + "\n- Kristin. Place: service corridors.\n\n")
    )
    assert all(f"+{line}" in grounded["diff"] for lines in additions.values() for line in lines)
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
    constraints = selection.user.split("CONSTRAINTS:\n", 1)[1].split("\n\nPLAYER:", 1)[0]
    missing = PromptSelection(
        selection.system, selection.user.replace(constraints + "\n\n", "", 1), selection.source_path
    )
    with pytest.raises(AssertionError, match="blank line"):
        patch_prompt(missing, "grounded", "grounded")
    duplicate = PromptSelection(
        selection.system,
        selection.user.replace(
            "\n\nPLAYER:",
            "\n" + "\n".join(grounded_additions()["CONSTRAINTS"]) + "\n\nPLAYER:",
            1,
        ),
        selection.source_path,
    )
    with pytest.raises(AssertionError, match="already present"):
        patch_prompt(duplicate, "grounded", "grounded")


def test_grounded_derivation_is_section_scoped_and_nonempty() -> None:
    additions = grounded_additions()
    assert set(additions) <= {"SCENE", "THINGS", "CONSTRAINTS"}
    # Current story state: this is the one obvious update point for plot.md edits.
    assert additions["CONSTRAINTS"] == _current_story_constraint_lines()
    assert additions["THINGS"] == (
        "- cooling-service archive panel. Place: beside the inspection console in the infrastructure corridors. "
        'State: closed. If it changes, give "state": "open".',
    )
    with pytest.raises(AssertionError, match="removed"):
        grounded_additions(
            "CHARACTERS:\n\nSCENE:\n- old\n\nTHINGS:\n\nCONSTRAINTS:\n\nPLAYER:\n",
            "CHARACTERS:\n\nSCENE:\n\nTHINGS:\n\nCONSTRAINTS:\n\nPLAYER:\n",
        )
    with pytest.raises(AssertionError, match="forbidden section"):
        grounded_additions(
            "CHARACTERS:\n- same\n\nSCENE:\n\nTHINGS:\n\nCONSTRAINTS:\n\nPLAYER:\n",
            "CHARACTERS:\n- same\n- extra\n\nSCENE:\n\nTHINGS:\n\nCONSTRAINTS:\n- add\n\nPLAYER:\n",
        )
    with pytest.raises(AssertionError, match="no additions"):
        grounded_additions(
            "CHARACTERS:\n\nSCENE:\n\nTHINGS:\n\nCONSTRAINTS:\n\nPLAYER:\n",
            "CHARACTERS:\n\nSCENE:\n\nTHINGS:\n\nCONSTRAINTS:\n\nPLAYER:\n",
        )


def test_grounded_patch_is_exact_and_things_emulation_is_recorded() -> None:
    selection = select_prompt()
    control = patch_prompt(selection, "control", "grounded")
    grounded = patch_prompt(selection, "grounded", "grounded")
    assert grounded["system"] == control["system"]
    additions = grounded_additions()
    things_body = grounded["user"].split("THINGS:\n", 1)[1].split("\n\nCONSTRAINTS:", 1)[0]
    assert things_body.splitlines()[:2] == [additions["THINGS"][0], "- Kristin. Place: service corridors."]
    assert all(f"{line}\n" in grounded["user"] for lines in additions.values() for line in lines)
    assert things_emulation() == {
        "frozen": ["THINGS:", "- Kristin. Place: infrastructure corridors."],
        "current": [
            "THINGS:",
            "- cooling-service archive panel. Place: beside the inspection console in the infrastructure corridors. "
            'State: closed. If it changes, give "state": "open".',
            "- Kristin. Place: infrastructure corridors.",
        ],
    }


def test_things_emulation_fails_when_current_stub_reply_is_not_consumed(monkeypatch: pytest.MonkeyPatch) -> None:
    from storygame.runtime.item_facts import ItemFactsProvider

    monkeypatch.setattr(ItemFactsProvider, "prepare_turn", lambda self, command: None)
    with pytest.raises(AssertionError, match="stub reply was not consumed"):
        things_emulation()


def test_normal_exit_guard_is_offline_and_current_transition_is_not_panel_gated() -> None:
    frozen = Path("bench/frozen/continuity-pre-2a-panel")
    current = Path("data/stories/continuity-initiative")
    differences = [
        name
        for name in ("pacing.yaml", "knowledge.yaml", "handoffs.yaml", "storylets.md", "storylet-routes.yaml")
        if (frozen / name).read_bytes() != (current / name).read_bytes()
    ]
    assert differences == ["knowledge.yaml"], "unexpected package change in normal-exit guard fixture"
    package, _ = package_and_state(load_variation(Path("bench/variations/stage7-door-grounded.json")), "2A")
    transition = next(item for item in package.pacing.transitions if item.id == "t_2a_2b")
    blob = repr(transition.model_dump()).lower()
    assert "cooling_service_archive_panel" not in blob, "normal-exit guard: t_2a_2b is panel-gated"


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
