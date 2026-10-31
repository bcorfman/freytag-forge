from __future__ import annotations

import copy
import importlib.util
import json
import threading
from pathlib import Path
from types import SimpleNamespace

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.observation_verifier import ObservationVerifier
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements, world_for
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")
PROBE_PATH = ROOT / "scripts/ringer/environment_narration/drain_condition_judge_probe.py"
PROBE_SPEC = importlib.util.spec_from_file_location("opening_condition_probe", PROBE_PATH)
assert PROBE_SPEC is not None and PROBE_SPEC.loader is not None
PROBE = importlib.util.module_from_spec(PROBE_SPEC)
PROBE_SPEC.loader.exec_module(PROBE)


def _state_1b() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1B"
    apply_scene_placements(PACKAGE, state.facts, "1B")
    assert world_for(PACKAGE, state.facts).move("kristin", "los_angeles_park").ok
    return state


def _answers(questions: object, score: float = 1.0) -> dict[str, dict[str, float]]:
    return {key: {"noul": score} for key in questions} if isinstance(questions, dict) else {}


def test_runtime_state_shape_is_unchanged_and_question_is_variant_e() -> None:
    from storygame.runtime.opening_check import opening_payload

    case = {
        "narration": "The drain remains outside.",
        "thing": "storm drain",
        "command": "inspect the storm drain",
        "declared": "the storm drain has no open or closed value, no declared contents, and is fixed in place.",
    }

    expected_state, _expected_questions = PROBE.variant_b_payload(case)
    state, questions = opening_payload(case["narration"], case["thing"], case["command"])
    pinned = json.loads(
        (ROOT / "scripts/ringer/environment_narration/drain_condition_judge/variant-e-question.json").read_text()
    )

    assert state == expected_state
    assert questions["condition_consistent"] == pinned


def test_story_text_is_appended_only_when_nonblank() -> None:
    from storygame.runtime.opening_check import opening_state

    base = "the back door has no open or closed value, no declared contents, and is fixed in place."
    state = opening_state(
        "Narration.", "back door", "inspect the back door", story_text="  The back door was forced.  "
    )
    assert state["declared"] == f"{base} The story states: The back door was forced."
    assert opening_state("Narration.", "back door", "inspect the back door", story_text="  ")["declared"] == base


def test_flag_off_keeps_the_old_request_and_report_shape() -> None:
    calls: list[tuple[object, object]] = []

    def ask(state: object, questions: object) -> dict[str, dict[str, float]]:
        calls.append((state, questions))
        return _answers(questions)

    verifier = ObservationVerifier(ask)
    report = verifier.verify(
        "The drain remains outside.",
        (),
        opening_subjects=("storm drain",),
        command="Inspect the storm drain.",
    )

    assert report.outcome == "no_relations"
    assert report.opening_verdicts == ()
    assert report.opening_requests == 0
    assert calls == []


def test_real_scene_match_exposes_only_an_opening_referent(monkeypatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda _provider, _payload: {"refers": ["storm drain"], "same_as": {}},
    )
    provider = build_capture_provider(_state_1b())
    provider.observe_automatically = False
    provider.prepare_turn("Inspect the storm drain.")

    assert provider.opening_subjects() == ("storm drain",)
    calls: list[tuple[object, object]] = []
    report = ObservationVerifier(
        lambda state, questions: calls.append((state, questions)) or _answers(questions),
        opening_check=True,
    ).verify(
        "The storm drain is visible.",
        (),
        opening_subjects=provider.opening_subjects(),
        command="Inspect the storm drain.",
    )

    assert report.accepted
    assert len(calls) == 1
    assert calls[0][0] == {
        "narration": "The storm drain is visible.",
        "thing": "storm drain",
        "command": "Inspect the storm drain.",
        "declared": "the storm drain has no open or closed value, no declared contents, and is fixed in place.",
    }


def test_container_and_plain_referents_are_not_opening_subjects() -> None:
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=_state_1b(),
        item_facts={},
        mode="single_call",
        seed_from_package=True,
    )
    provider._referred_names = ["drawer", "park bench"]

    assert provider.opening_subjects() == ()


def test_opening_only_check_runs_and_fail_closed_verdicts() -> None:
    for score, accepted, verdict in ((1.0, True, "accept"), (0.0, False, "reject"), (0.5, False, "uncertain")):
        calls: list[tuple[object, object]] = []

        def ask(state: object, questions: object, *, score=score, calls=calls):
            calls.append((state, questions))
            return _answers(questions, score)

        report = ObservationVerifier(
            ask,
            opening_check=True,
        ).verify(
            "The drain remains outside.",
            (),
            opening_subjects=("storm drain",),
            command="Inspect the storm drain.",
        )
        assert report.accepted is accepted
        assert report.opening_verdicts[0].verdict == verdict
        assert report.opening_requests == 1
        assert len(calls) == 1


def test_opening_budget_is_separate_and_capped_at_two() -> None:
    calls: list[tuple[object, object]] = []
    verifier = ObservationVerifier(
        lambda state, questions: calls.append((state, questions)) or _answers(questions),
        opening_check=True,
    )

    report = verifier.verify(
        "The openings remain outside.",
        (),
        opening_subjects=("one hatch", "two gates", "three drains"),
        command="Inspect them.",
    )

    assert report.opening_requests == 2
    assert len(calls) == 2
    assert [verdict.verdict for verdict in report.opening_verdicts] == ["accept", "accept", "unavailable"]
    assert not report.accepted


def test_background_opening_call_receives_prebuilt_payload_only() -> None:
    main_thread = threading.current_thread()
    calls: list[tuple[object, object, threading.Thread]] = []

    def ask(state: object, questions: object) -> dict[str, dict[str, float]]:
        calls.append((state, questions, threading.current_thread()))
        return _answers(questions)

    report = ObservationVerifier(ask, opening_check=True).verify(
        "The drain remains outside.",
        (),
        opening_subjects=("storm drain",),
        command="Inspect the storm drain.",
    )

    assert report.accepted
    assert calls[0][2] is not main_thread
    assert calls[0][0]["thing"] == "storm drain"


def test_capture_enforcing_and_shadow_paths_forward_opening_subjects() -> None:
    for path in ("enforcing", "shadow"):
        state = _state_1b()
        provider = ItemFactsProvider(
            worker_url="",
            token="",
            state=state,
            item_facts={},
            mode="single_call",
            seed_from_package=True,
        )
        provider.opening_subjects = lambda: ("storm drain",)
        provider.authored_handoff = SimpleNamespace(delivery_text="The back door was forced.")
        provider._pending_item_facts_present = True
        calls: list[tuple[object, object]] = []

        def ask(request_state: object, questions: object, *, calls=calls) -> dict[str, dict[str, float]]:
            calls.append((request_state, questions))
            return _answers(questions)

        capture = WorldCapture(provider, ask)
        verifier = ObservationVerifier(ask, opening_check=True)
        if path == "enforcing":
            capture.enforcing_verifier = verifier
            preview = capture.preview_commit(
                "Inspect the storm drain.",
                "The storm drain remains outside.",
                copy.deepcopy(state),
                entered_scene=False,
            )
            assert preview.accepted
            assert preview.outcome == "ok"
        else:
            capture.shadow_verifier = verifier
            record = capture.after_commit(
                "Inspect the storm drain.",
                "The storm drain remains outside.",
                entered_scene=False,
            )
            assert record["observation_shadow"]["accepted"] is True
            assert record["observation_shadow"]["opening_verdicts"][0]["thing"] == "storm drain"
        assert any(request[0]["thing"] == "storm drain" for request in calls)
        assert any(request[0]["declared"].endswith("The story states: The back door was forced.") for request in calls)
