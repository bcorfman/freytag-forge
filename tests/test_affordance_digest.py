import importlib.util
import json
from pathlib import Path

DIGEST_PATH = Path(__file__).parents[1] / "scripts/ringer/affordance/digest.py"
SPEC = importlib.util.spec_from_file_location("affordance_digest", DIGEST_PATH)
digest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(digest)


def run_digest(tmp_path, report, capsys, *args):
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report))
    digest.main([str(path), *args])
    return capsys.readouterr().out


def test_l2_turns_flags_and_truncation(tmp_path, capsys):
    long_text = "x" * 250
    report = {
        "aggregate": {"transition_rate": 1},
        "replicates": [
            {
                "transition_fired": True,
                "transition_turn": 4,
                "stuck_turns": [1],
                "stuck_runs": [],
                "silent_transition": False,
                "affordances": [],
                "l3": {},
                "turns": [
                    {"turn": 1, "input": "Search the room.", "text": long_text},
                    {
                        "turn": 2,
                        "input": "Open the door.",
                        "text": "ignored response",
                        "rejected": True,
                        "rejection": "Use an imperative command.",
                        "semantic_match": {"ran": True, "matched": None},
                    },
                    {
                        "turn": 3,
                        "input": "Inspect the clue.",
                        "text": "A clue is here.",
                        "semantic_match": {"ran": True, "matched": "r2"},
                    },
                    {
                        "turn": 4,
                        "input": "Leave the room.",
                        "text": "The scene changes.",
                        "semantic_match": {"ran": False, "matched": None},
                    },
                ],
            }
        ],
    }

    output = run_digest(tmp_path, report, capsys)

    assert "  t1 [stuck] Search the room. -> " + "x" * 237 + "..." in output
    assert "  t2 [rej,sem:ran] Open the door. -> Use an imperative command." in output
    assert "  t3 [sem:match=r2] Inspect the clue. -> A clue is here." in output
    assert "  t4 [sem:off] Leave the room. -> The scene changes." in output
    assert "x" * 238 not in output

    full_output = run_digest(tmp_path, report, capsys, "--full")
    assert "x" * 250 in full_output


def test_l2_old_report_uses_commands(tmp_path, capsys):
    report = {
        "aggregate": {},
        "replicates": [
            {
                "stuck_turns": [],
                "stuck_runs": [],
                "affordances": [],
                "commands": ["Search the room.", "Open the door."],
            }
        ],
    }

    output = run_digest(tmp_path, report, capsys)

    assert "  t1 [] Search the room. -> (old report: no response text)" in output
    assert "  t2 [] Open the door. -> (old report: no response text)" in output


def test_l2_new_report_prints_exit_fields_and_rates(tmp_path, capsys):
    report = {
        "aggregate": {"play_exit_rate": 0.5, "timer_exit_rate": 0.5},
        "replicates": [
            {
                "exit_cause": "play",
                "transition_turn": 8,
                "handoff_after_turns": 13,
                "stuck_turns": [],
                "stuck_runs": [],
                "affordances": [],
            }
        ],
    }

    output = run_digest(tmp_path, report, capsys)

    assert "L2 exit rates: play=0.5 timer=0.5" in output
    assert "exit: cause=play transition_turn=8 timer_turn=13" in output


def test_l2_old_report_prints_no_exit_fields(tmp_path, capsys):
    report = {"aggregate": {}, "replicates": [{"stuck_turns": [], "stuck_runs": [], "affordances": []}]}

    output = run_digest(tmp_path, report, capsys)

    assert "exit:" not in output
    assert "exit rates:" not in output


def test_l1_output_is_unchanged(tmp_path, capsys):
    report = {
        "scenes": [
            {
                "scene_id": "1A",
                "first_step": [{"name": "door", "first_shown_turn": 1}],
                "later": [],
                "summary": {"shown_by_deadline": 1, "first_step_total": 1, "never_shown": 0},
                "input": "Search the room.",
            }
        ]
    }

    output = run_digest(tmp_path, report, capsys)

    assert output == (
        "L1: 1 scene-replicates (turn 0 = opening; deadline = turn 0 or 1)\n"
        "scene kind       affordance                       r1    \n"
        "1A    first_step door                             1     \n"
        "r1 1A: by deadline 1/1, never shown 0, input 'Search the room.'\n"
    )
