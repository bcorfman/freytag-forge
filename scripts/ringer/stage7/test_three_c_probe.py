from __future__ import annotations

import re
from pathlib import Path
from urllib.error import HTTPError

import pytest
import three_c_probe as probe
from door_transport import SpendBudget

from bench.core import load_variation, package_and_state
from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.cloudflare import NarrationProviderError
from storygame.runtime.engine import RuntimeEngine


def test_outcome_classifier() -> None:
    all_ids = set(probe.REQUIRED) | {"k_sl_3c_e_r1"}
    assert probe.classify_outcome(True, all_ids, all_ids, []) == "earned_complete"
    assert probe.classify_outcome(True, all_ids, all_ids, ["resolution_deadline"]) == "deadline_complete"
    assert probe.classify_outcome(True, all_ids - {probe.DE_R1}, all_ids, []) == "deadline_complete"
    assert probe.classify_outcome(False, all_ids, all_ids, []) == "no_complete"


@pytest.mark.parametrize(
    ("attempts", "accepted", "complete", "extra", "expected"),
    [
        (14, 14, False, False, False),
        (15, 14, False, True, True),
        (20, 2, False, False, True),
        (2, 2, True, False, True),
    ],
)
def test_stop_rule_boundaries(attempts: int, accepted: int, complete: bool, extra: bool, expected: bool) -> None:
    assert probe.should_stop(attempts, accepted, complete, extra) is expected


def test_interleaving() -> None:
    assert [(i, arm) for i in range(1, 3) for arm in probe.ARMS] == [
        (1, "control"),
        (1, "pre667"),
        (2, "control"),
        (2, "pre667"),
    ]


def test_entry_arm_is_registered() -> None:
    assert probe.variation_paths(("entry",))["entry"].name == "stage7-3c-entry-package.json"
    assert "entry" in probe.ALL_ARMS


def test_custody_arm_is_registered() -> None:
    assert probe.variation_paths(("custody",))["custody"].name == "stage7-3c-custody-result.json"
    assert "custody" in probe.ALL_ARMS


def test_pump_arm_is_registered_and_custody_is_a_baseline(tmp_path: Path) -> None:
    assert probe.variation_paths(("pump",))["pump"].name == "stage7-3c-pump-need.json"
    assert "pump" in probe.ALL_ARMS
    assert (
        probe.main(["--n", "1", "--dry-run", "--start", "posta", "--arms", "custody,pump", "--out", str(tmp_path)]) == 0
    )


def test_families_v2_arm_is_registered_and_only_d2_evidence_differs() -> None:
    pump = load_variation(probe.variation_paths(("pump",))["pump"])
    families_v2 = load_variation(probe.variation_paths(("families-v2",))["families-v2"])
    pump_package, _ = package_and_state(pump, "3C")
    v2_package, _ = package_and_state(families_v2, "3C")
    assert "families-v2" in probe.ALL_ARMS
    assert probe.variation_paths(("families-v2",))["families-v2"].name == "stage7-3c-families-v2.json"
    pump_entries = pump_package.knowledge_indexes.by_id
    v2_entries = v2_package.knowledge_indexes.by_id
    assert set(pump_entries) == set(v2_entries)
    for knowledge_id in pump_entries:
        if knowledge_id == "k_sl_3c_d_r2":
            assert pump_entries[knowledge_id].action_evidence != v2_entries[knowledge_id].action_evidence
        else:
            assert pump_entries[knowledge_id].action_evidence == v2_entries[knowledge_id].action_evidence
    plan = (probe.ROOT / ".plans/chatgpt-3c-stuck-turns-plan.md").read_text(encoding="utf-8")
    old = re.search(r"^Old:\n```yaml\n(.*?)\n```", plan, re.MULTILINE | re.DOTALL)
    assert old is not None
    source = (probe.ROOT / "data/stories/continuity-initiative/knowledge.yaml").read_text(encoding="utf-8")
    assert source.count(old.group(1)) == 1
    replacement = families_v2["overrides"]["knowledge.yaml"]["replacements"][1]
    assert replacement["old"] == old.group(1)


def test_escape_arm_is_registered() -> None:
    assert probe.variation_paths(("escape",))["escape"].name == "stage7-3c-escape-result.json"
    assert "escape" in probe.ALL_ARMS


def test_exactly_once_replacement_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "data/stories/continuity-initiative/knowledge.yaml"
    source.parent.mkdir(parents=True)
    source.write_text("x\n", encoding="utf-8")
    monkeypatch.setattr(probe, "ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="exactly once"):
        probe.source_proof()


def test_run_row_uses_live_state_with_real_engine() -> None:
    variation_path = probe.ROOT / "bench/variations/stage7-3c-control.json"
    variation = load_variation(variation_path)
    package, expected_state = package_and_state(variation, "3C")
    assert package.story_id == expected_state.package.story_id

    class FakeProvider:
        semantic_ask = None

        def __call__(self, _command: str) -> dict[str, object]:
            return {"segments": [{"kind": "narration", "text": "The evidence package is ready."}]}

    provider = FakeProvider()

    def provider_factory(state: object, loaded_variation: dict[str, object]) -> FakeProvider:
        assert state.package.story_id == expected_state.package.story_id
        assert loaded_variation["_package_hash"] == variation["_package_hash"]
        return provider

    row = probe.run_row(
        "control",
        variation_path,
        SpendBudget(10),
        ask=lambda _screen, _budget: "Send the evidence package.",
        provider_factory=provider_factory,
    )

    assert row["attempts"] >= 3
    assert row["turns"]
    for turn in row["turns"][:3]:
        assert turn["status"] in {"accepted", "clarification", "rejected"}
        assert set(turn["story_fact_delta"]) == {"added", "removed"}
        assert all(isinstance(fact, str) for fact in turn["story_fact_delta"]["added"])
        assert all(isinstance(fact, str) for fact in turn["story_fact_delta"]["removed"])
        assert isinstance(turn["committed_reveals"], list)
        assert all(isinstance(reveal_id, str) for reveal_id in turn["committed_reveals"])
        assert isinstance(turn["deadline_event_ids"], list)
        assert all(isinstance(event_id, str) for event_id in turn["deadline_event_ids"])


@pytest.mark.parametrize("arm", (*probe.ARMS, "escape"))
def test_row_start_real_engine_has_opening_reveal_universe(arm: str) -> None:
    paths = probe.variation_paths((arm,))
    variation = load_variation(paths[arm])
    _, state = package_and_state(variation, "3C")
    probe.assert_3c_entry_facts(state)
    universe = probe.preflight_reveal_universe(RuntimeEngine(state, None), state)
    assert {"k_sl_3c_a_r1", "k_sl_3c_a_r2"}.issubset(universe)


def test_missing_entry_facts_fails_before_ask(monkeypatch: pytest.MonkeyPatch) -> None:
    variation_path = probe.variation_paths()["control"]
    monkeypatch.setattr(probe, "assert_3c_entry_facts", lambda state: state)
    asked = False

    class FakeProvider:
        semantic_ask = None

    def ask(_screen: str, _budget: SpendBudget) -> str:
        nonlocal asked
        asked = True
        return "Send the evidence package."

    with pytest.raises(RuntimeError, match="entry preflight failed"):
        probe.run_row(
            "control",
            variation_path,
            SpendBudget(10),
            ask=ask,
            provider_factory=lambda _state, _variation: FakeProvider(),
        )
    assert asked is False


@pytest.mark.parametrize("arm", probe.ARMS)
def test_post8_universe_is_only_d_r1(arm: str) -> None:
    variation = load_variation(probe.variation_paths()[arm])
    package, state = package_and_state(variation, "3C")
    probe.assert_3c_entry_facts(state)
    probe.apply_post8_prefix(package, state)
    assert probe.preflight_reveal_universe(RuntimeEngine(state, None), state, "post8") == [probe.DE_R1]


@pytest.mark.parametrize(("start", "expected_turn"), [("posta", 1), ("post8", 8), ("postc", 7)])
def test_scripted_prefix_row_records_checker_turn_index(start: str, expected_turn: int) -> None:
    variation = load_variation(probe.variation_paths()["control"])
    package, state = package_and_state(variation, "3C")
    probe.assert_3c_entry_facts(state)

    prefix = probe.apply_start_prefix(package, state, start)
    row = {"scripted_prefix": prefix}

    assert row["scripted_prefix"]["turn_index"] == expected_turn
    assert row["scripted_prefix"]["turn_index"] == state.turn_index


def test_post8_player_reveals_earn_completion_and_prefix_is_local() -> None:
    variation_path = probe.variation_paths()["pre667"]
    provider_factory_calls: list[tuple[int, int]] = []

    class FakeProvider:
        semantic_ask = None

        def __init__(self, package: object) -> None:
            self.package = package

        def __call__(self, command: str) -> dict[str, object]:
            knowledge_id = probe.DE_R1 if command == "Check reports from other detention sites." else "k_sl_3c_e_r1"
            return probe._scripted_provider(self.package, knowledge_id)(command)

    def provider_factory(state: object, _variation: dict[str, object]) -> FakeProvider:
        provider_factory_calls.append((state.turn_index, len(state.turn_records)))
        return FakeProvider(state.package)

    commands = iter(("Check reports from other detention sites.", "Open the recovered document."))
    row = probe.run_row(
        "pre667",
        variation_path,
        SpendBudget(10),
        ask=lambda _screen, _budget: next(commands),
        provider_factory=provider_factory,
        start="post8",
    )

    assert provider_factory_calls == [(8, 5)]
    assert row["scripted_prefix"]["committed_reveal_ids"] == [item[0] for item in probe.POST8_REVEALS]
    assert row["committed_reveal_ids"] == [probe.DE_R1, "k_sl_3c_e_r1"]
    assert row["d_r1_commit_attempt"] == 1
    assert row["first_d_commit_scene_turn"] == row["d_r1_commit_scene_turn"]
    assert row["outcome"] == "earned_complete"
    assert all(not turn["deadline_event_ids"] for turn in row["turns"])


def test_post8_first_player_screen_contains_scripted_transcript() -> None:
    screens: list[str] = []

    class FakeProvider:
        semantic_ask = None

        def __call__(self, _command: str) -> dict[str, object]:
            return {"segments": [{"kind": "narration", "text": "A fresh reply."}]}

    def ask(screen: str, _budget: SpendBudget) -> str:
        screens.append(screen)
        return "Keep watch."

    probe.run_row(
        "control",
        probe.variation_paths()["control"],
        SpendBudget(25),
        ask=ask,
        provider_factory=lambda _state, _variation: FakeProvider(),
        start="post8",
    )

    assert screens
    first = screens[0]
    assert all(f"> {command}" in first for _knowledge_id, command in probe.POST8_REVEALS)
    package, _state = package_and_state(load_variation(probe.variation_paths()["control"]), "3C")
    knowledge = package.knowledge_indexes.by_id[probe.POST8_REVEALS[-1][0]]
    last_reply = knowledge.delivery_text or knowledge.statement
    assert last_reply in first


def test_entry_second_player_screen_contains_first_accepted_turn() -> None:
    screens: list[str] = []

    class FakeProvider:
        semantic_ask = None

        def __call__(self, command: str) -> dict[str, object]:
            return {"segments": [{"kind": "narration", "text": f"Reply to {command}."}]}

    def ask(screen: str, _budget: SpendBudget) -> str:
        screens.append(screen)
        return "Inspect the evidence."

    probe.run_row(
        "control",
        probe.variation_paths()["control"],
        SpendBudget(25),
        ask=ask,
        provider_factory=lambda _state, _variation: FakeProvider(),
    )

    assert len(screens) >= 2
    assert "> Inspect the evidence." in screens[1]
    assert "Reply to Inspect the evidence." in screens[1]


def test_rejected_turn_is_not_added_to_next_player_screen() -> None:
    screens: list[str] = []
    calls = 0

    class FakeProvider:
        semantic_ask = None

        def __call__(self, command: str) -> dict[str, object]:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("rejected turn text")
            return {"segments": [{"kind": "narration", "text": "Accepted reply."}]}

    def ask(screen: str, _budget: SpendBudget) -> str:
        screens.append(screen)
        return "Rejected command." if len(screens) == 1 else "Accepted command."

    probe.run_row(
        "control",
        probe.variation_paths()["control"],
        SpendBudget(25),
        ask=ask,
        provider_factory=lambda _state, _variation: FakeProvider(),
    )

    assert len(screens) >= 2
    assert "Rejected command." not in screens[1]
    assert "rejected turn text" not in screens[1]


def test_mid_row_http_failure_keeps_provider_error_and_attempt_context() -> None:
    class FakeProvider:
        semantic_ask = None

        def __init__(self) -> None:
            self.calls = 0

        def _request(self, _payload: dict[str, object]) -> dict[str, object]:
            self.calls += 1
            if self.calls == 2:
                try:
                    raise HTTPError("https://example.invalid", 503, "Service Unavailable", {}, None)
                except HTTPError as error:
                    raise NarrationProviderError("narration service rejected the turn", 503) from error
            return {"segments": [{"kind": "narration", "text": "A reply."}]}

        def __call__(self, _command: str) -> dict[str, object]:
            return self._request({"_request_budget": "narration"})

    provider = FakeProvider()
    with pytest.raises(probe.ProbeRunFailure) as raised:
        probe.run_row(
            "control",
            probe.variation_paths()["control"],
            SpendBudget(25),
            ask=lambda _screen, _budget: "Continue.",
            provider_factory=lambda _state, _variation: provider,
        )

    failure = raised.value
    assert type(failure.error).__name__ == "NarrationProviderError"
    assert failure.attempt == 2
    assert "http_status=503" in probe.failure_message(failure)
    assert "http_reason=Service Unavailable" in probe.failure_message(failure)


def test_player_screen_cap_drops_oldest_turns_whole_and_keeps_entry() -> None:
    transcript = [(f"command-{index}", "x" * 4000) for index in range(4)]
    screen, transcript_chars = probe._player_screen("ENTRY TEXT", transcript)

    assert "ENTRY TEXT" in screen
    assert transcript_chars <= probe.TRANSCRIPT_CHAR_CAP
    assert "> command-0" not in screen
    assert "> command-3" in screen


def test_post8_preflight_fails_before_ask(monkeypatch: pytest.MonkeyPatch) -> None:
    variation_path = probe.variation_paths()["control"]
    asked = False

    def ask(_screen: str, _budget: SpendBudget) -> str:
        nonlocal asked
        asked = True
        return "Check reports from other detention sites."

    original = probe.preflight_reveal_universe

    def wrong_universe(engine: RuntimeEngine, state: object, start: str = "entry") -> list[str]:
        if start == "post8":
            raise RuntimeError("3C post8 preflight failed: expected reveal universe ['k_sl_3c_d_r1'], got []")
        return original(engine, state, start)

    monkeypatch.setattr(probe, "preflight_reveal_universe", wrong_universe)
    with pytest.raises(RuntimeError, match="post8 preflight failed"):
        probe.run_row(
            "control",
            variation_path,
            SpendBudget(10),
            ask=ask,
            provider_factory=lambda _state, _variation: object(),
            start="post8",
        )
    assert asked is False


@pytest.mark.parametrize("arm", ("control", "surface", "escape"))
def test_postc_preflight_is_exactly_d_r1_and_d_r2(arm: str) -> None:
    variation = load_variation(probe.variation_paths((arm,))[arm])
    package, state = package_and_state(variation, "3C")
    probe.assert_3c_entry_facts(state)
    probe.apply_postc_prefix(package, state)
    assert probe.preflight_reveal_universe(RuntimeEngine(state, None), state, "postc") == [
        "k_sl_3c_d_r1",
        "k_sl_3c_d_r2",
    ]


def test_postc_first_command_is_attempt_one_and_keeps_full_response() -> None:
    class FakeProvider:
        semantic_ask = None

        def __call__(self, command: str) -> dict[str, object]:
            return {"segments": [{"kind": "narration", "text": f"FULL RESPONSE: {command}"}]}

    asked: list[str] = []

    def ask(screen: str, _budget: SpendBudget) -> str:
        asked.append(screen)
        return "Continue watching."

    row = probe.run_row(
        "control",
        probe.variation_paths()["control"],
        SpendBudget(20),
        ask=ask,
        provider_factory=lambda _state, _variation: FakeProvider(),
        start="postc",
        first_command="Follow Michelle and the captives through the surface gates.",
    )
    assert row["turns"][0]["attempt"] == 1
    assert row["turns"][0]["scripted_first"] is True
    assert row["first_command_response"].startswith("FULL RESPONSE:")
    assert asked
    assert row["first_d_commit_scene_turn"] is None


def test_posta_first_command_records_b_commit_and_acquisition_commands() -> None:
    class FakeProvider:
        semantic_ask = None

        def __init__(self, package: object) -> None:
            self.package = package

        def __call__(self, command: str) -> dict[str, object]:
            knowledge_id = "k_sl_3c_b_r1" if command == "Follow Rebecca." else "k_sl_3c_b_r2"
            return probe._scripted_provider(self.package, knowledge_id)(command)

    row = probe.run_row(
        "custody",
        probe.variation_paths(("custody",))["custody"],
        SpendBudget(25),
        ask=lambda _screen, _budget: "Take the Portable data case from Rebecca.",
        provider_factory=lambda state, _variation: FakeProvider(state.package),
        start="posta",
        first_command="Follow Rebecca.",
    )

    assert row["opening_reveal_universe"] == ["k_sl_3c_b_r1", "k_sl_3c_b_r2"]
    assert row["turns"][0]["attempt"] == 1
    assert row["b_commit_on_first"] is True
    assert row["b_commit_attempt"] == 1
    assert row["acquisition_commands"] >= 1
    assert all("case_parent" in turn for turn in row["turns"])


def test_surface_arm_loads_its_override_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Path] = []
    original = probe.load_variation

    def load(path: Path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(probe, "load_variation", load)

    class FakeProvider:
        semantic_ask = None

        def __call__(self, _command: str) -> dict[str, object]:
            return {"segments": [{"kind": "narration", "text": "reply"}]}

    probe.run_row(
        "surface",
        probe.variation_paths(("surface",))["surface"],
        SpendBudget(20),
        ask=lambda _screen, _budget: "Continue.",
        provider_factory=lambda _state, _variation: FakeProvider(),
        start="postc",
    )
    assert calls == [probe.variation_paths(("surface",))["surface"]]


@pytest.mark.parametrize(("n", "expected"), [(1, probe.POSTC_CAPS[1]), (12, probe.POSTC_CAPS[12])])
def test_postc_plan_uses_postc_caps(tmp_path: Path, n: int, expected: dict[str, int]) -> None:
    probe.plan_for(tmp_path, n, "dry", "postc", arms=("control", "surface"))
    assert __import__("json").loads((tmp_path / "plan.json").read_text())["caps"] == expected


def test_commands_mode_generates_six_probes_per_arm_per_rep_and_fresh_states(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[int, str, int]] = []

    def fake_probe(
        arm: str,
        rep: int,
        turn_label: int,
        command: str,
        variation_path: Path,
        budget: SpendBudget,
        semantic: str = "off",
        provider_factory: object | None = None,
    ) -> dict[str, object]:
        calls.append((rep, arm, turn_label))
        return {
            "row_id": f"stage7-3c-{rep:02d}-{arm}-turn{turn_label}",
            "arm": arm,
            "rep": rep,
            "turn_label": turn_label,
            "command": command,
            "status": "accepted",
            "committed_reveals": [],
            "d_r1_committed": False,
        }

    monkeypatch.setattr(probe, "run_command_probe", fake_probe)
    monkeypatch.setattr(probe, "source_proof", lambda: {"knowledge_yaml": {"loaded_arms": {}}})
    monkeypatch.setattr(
        probe,
        "recorded_commands",
        lambda: [{"turn_label": turn, "command": f"command {turn}"} for turn in probe.COMMAND_TURNS],
    )
    probe.commands_live_run(tmp_path, 1, "on", "post8")
    assert calls == [(1, arm, turn) for arm in probe.ARMS for turn in probe.COMMAND_TURNS]
    assert len(calls) == 12


def test_command_probe_fresh_state_and_matcher_owns_d_r1_selection() -> None:
    command = "Continue broadcasting the reports from all remaining detention sites and coordinate their rescue."

    class FakeProvider:
        semantic_ask = None

        def __init__(self, package: object, select: bool) -> None:
            self.package = package
            self.select = select

        def __call__(self, _command: str) -> dict[str, object]:
            knowledge = self.package.knowledge_indexes.by_id[probe.DE_R1]
            return {
                "segments": [{"kind": "narration", "text": knowledge.delivery_text, "grounding_ids": [probe.DE_R1]}],
                "selected_knowledge_ids": [probe.DE_R1] if self.select else [],
            }

    def provider_factory(state: object, variation: dict[str, object]) -> FakeProvider:
        return FakeProvider(
            state.package,
            variation["_package_hash"] == load_variation(probe.variation_paths()["control"])["_package_hash"],
        )

    rows = [
        probe.run_command_probe(
            arm,
            1,
            13,
            command,
            probe.variation_paths()[arm],
            SpendBudget(3, cloudflare_limit=3, player_limit=0),
            provider_factory=provider_factory,
        )
        for arm in probe.ARMS
    ]
    assert rows[0]["matched_authored_handoff"] == probe.DE_R1
    assert rows[0]["d_r1_committed"] is True
    assert rows[1]["matched_authored_handoff"] is None
    assert rows[1]["d_r1_committed"] is False
    assert rows[0]["scripted_prefix"]["committed_reveal_ids"] == rows[1]["scripted_prefix"]["committed_reveal_ids"]

    variation = load_variation(probe.variation_paths()["control"])
    package, state = package_and_state(variation, "3C")
    probe.assert_3c_entry_facts(state)
    probe.apply_post8_prefix(package, state)
    projection = RuntimeEngine(state, None).projector.project(state, "player", command)
    assert uniquely_matched_authored_handoff(command, projection.candidates).candidate.id == probe.DE_R1


def test_commands_mode_never_calls_raw_player(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(probe, "_ask_player", lambda *_args: pytest.fail("raw player called"))
    monkeypatch.setattr(
        probe,
        "run_command_probe",
        lambda *args, **kwargs: {
            "row_id": "x",
            "arm": args[0],
            "rep": args[1],
            "turn_label": args[2],
            "command": args[3],
            "status": "rejected",
            "d_r1_committed": False,
            "committed_reveals": [],
        },
    )
    probe.commands_live_run(tmp_path, 1, "off", "post8")


def test_commands_mode_refuses_entry_start(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="requires --start post8"):
        probe.main(["--n", "1", "--mode", "commands", "--start", "entry", "--dry-run", "--out", str(tmp_path)])
