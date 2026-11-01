"""Coverage for guard retry telemetry and its offline report."""

from pathlib import Path

from bench.guard_retry_report import compute_report
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
LEAK = "Rebecca's secured office can broadcast the evidence."
CLEAN = "Kristin waits for Rebecca's next move."


def _scene_2c_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "2C")
    state.current_scene_id = "2C"
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact("2C")
    return state


class _ScriptedProvider:
    def __init__(self, *texts: str) -> None:
        self.texts = list(texts)
        self.calls = 0

    def __call__(self, _command: str) -> dict[str, object]:
        text = self.texts[self.calls]
        self.calls += 1
        return {"segments": [{"kind": "narration", "text": text}], "selected_knowledge_ids": []}


def test_engine_records_guard_rejection_and_resets_for_next_turn() -> None:
    engine = RuntimeEngine(_scene_2c_state(), _ScriptedProvider(LEAK, CLEAN, CLEAN))

    engine.turn("Assess the cost of transmitting our evidence.")

    assert len(engine.last_guard_rejections) == 1
    rejection = engine.last_guard_rejections[0]
    assert rejection["code"] == "narration_known_term_leak"
    assert rejection["message"]
    assert rejection["rejected_narration"] == LEAK
    engine.turn("Assess the cost of transmitting our evidence.")
    assert engine.last_guard_rejections == []


def test_clean_engine_turn_has_no_guard_rejections() -> None:
    engine = RuntimeEngine(_scene_2c_state(), _ScriptedProvider(CLEAN))

    engine.turn("Assess the cost of transmitting our evidence.")

    assert engine.last_guard_rejections == []


def test_guard_retry_report_classifies_turns_and_rescue_rate() -> None:
    report = compute_report(
        {
            "runs": [
                {
                    "script": "telemetry-script",
                    "replicate": 3,
                    "turns": [
                        {"turn_number": 1, "typed_input": "clean", "narration": CLEAN},
                        {
                            "turn_number": 2,
                            "typed_input": "rescued",
                            "narration": CLEAN,
                            "guard_retry_used": True,
                            "guard_rejections": [
                                {"code": "narration_known_term_leak", "message": "blocked 'protected term'"}
                            ],
                        },
                        {
                            "turn_number": 3,
                            "typed_input": "repeated",
                            "narration": "The protected term remains in the reply.",
                            "guard_retry_used": True,
                            "guard_rejections": [
                                {"code": "narration_known_term_leak", "message": "blocked 'protected term'"}
                            ],
                        },
                    ],
                    "rejected_turns": [
                        {
                            "turn_number": 4,
                            "typed_input": "failed retry",
                            "rejection_code": "narration_known_term_leak",
                            "guard_rejections": [
                                {"code": "narration_known_term_leak", "message": "blocked 'protected term'"}
                            ],
                        },
                        {
                            "turn_number": 5,
                            "typed_input": "failed other",
                            "rejection_code": "INVALID_PROPOSAL",
                            "guard_rejections": [],
                        },
                    ],
                }
            ]
        }
    )

    assert [turn["outcome"] for turn in report["turns"]] == [
        "committed_clean",
        "committed_after_retry",
        "committed_after_retry",
        "failed_after_retry",
        "failed_other",
    ]
    assert report["summary"] == {
        "n_turns": 5,
        "n_first_pass_clean": 1,
        "n_retry_fired": 3,
        "n_rescued": 2,
        "n_failed_after_retry": 1,
        "rescue_rate": 2 / 3,
        "n_second_reply_repeats_term": 1,
    }
    assert report["turns"][1]["final_narration_repeats_term"] is False
    assert report["turns"][2]["final_narration_repeats_term"] is True


def test_guard_retry_report_uses_null_rate_when_zero_retries_fired() -> None:
    report = compute_report({"runs": [{"script": "clean", "turns": [{"narration": CLEAN}]}]})

    assert report["summary"]["n_retry_fired"] == 0
    assert report["summary"]["n_rescued"] == 0
    assert report["summary"]["rescue_rate"] is None
