import json

from bench.failure_report import build_section


def _fact(turn, **values):
    return {"turn": turn, "reason": f"fact {turn}", **values}


def _cont(turn, **values):
    return {"turn": turn, "reason": f"continuity {turn}", **values}


def _write_results(path, record_turns, fact_turns, cont_turns):
    path.mkdir()
    runs = [
        {
            "replicate": 1,
            "turns": [
                {
                    "turn_number": turn,
                    "scene_id": "1A",
                    "player_input": "Check the item.",
                    "narration": "The item is here.",
                }
                for turn in record_turns
            ],
        }
    ]
    (path / "all-turn-records.json").write_text(json.dumps({"runs": runs}))
    (path / "fact-tracking-judgments.json").write_text(json.dumps({"judgments": [{"turns": fact_turns}]}))
    (path / "continuity-judgments.json").write_text(json.dumps({"judgments": [{"turns": cont_turns}]}))


def _report(path):
    lines = []
    counts = []
    build_section(
        "sample",
        path,
        {1: json.loads((path / "fact-tracking-judgments.json").read_text())["judgments"][0]["turns"]},
        lines,
        counts,
    )
    return "\n".join(counts + lines)


def test_matches_verdicts_by_turn_number_across_a_gap(tmp_path):
    path = tmp_path / "results"
    _write_results(
        path,
        [1, 2, 3, 5],
        [_fact(1), _fact(2), _fact(3), _fact(5, facts_after_correct="no")],
        [_cont(5, contradicts_stated_fact="yes")],
    )
    report = _report(path)
    assert "### r1 turn 5" in report
    assert "### r1 turn 3" not in report
    assert "- CONTINUITY JUDGE: continuity 5" in report


def test_falls_back_to_positions_for_old_judgments(tmp_path):
    path = tmp_path / "results"
    _write_results(
        path,
        [1, 2, 3, 5],
        [_fact(1), _fact(2), _fact(3), _fact(4, facts_after_correct="no")],
        [_cont(1), _cont(2), _cont(3), _cont(4, restarts_scene="yes")],
    )
    report = _report(path)
    assert "### r1 turn 5 (1A) - facts_after_wrong, restarts_scene" in report
    assert "- CONTINUITY JUDGE: continuity 4" in report


def test_every_listed_turn_has_continuity_reason_and_renamed_failure(tmp_path):
    path = tmp_path / "results"
    _write_results(path, [1], [_fact(1, facts_after_correct="no")], [_cont(1, contradicts_stated_fact="yes")])
    report = _report(path)
    assert "- FACT JUDGE: fact 1\n- CONTINUITY JUDGE: continuity 1" in report
    assert "facts_after_wrong: 1" in report
    assert "facts_after_correct" not in report
