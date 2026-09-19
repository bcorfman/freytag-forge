import json

import pytest

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


def _report(path, *, all_turns=False):
    lines = []
    counts = []
    build_section(
        "sample",
        path,
        {1: json.loads((path / "fact-tracking-judgments.json").read_text())["judgments"][0]["turns"]},
        lines,
        counts,
        all_turns=all_turns,
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


@pytest.mark.parametrize("narrated_command", [None, "Check the item."])
def test_narrated_command_is_omitted_when_missing_or_unchanged(tmp_path, narrated_command):
    path = tmp_path / "results"
    _write_results(path, [1], [_fact(1, facts_after_correct="no")], [])
    records = json.loads((path / "all-turn-records.json").read_text())
    if narrated_command is None:
        records["runs"][0]["turns"][0].pop("narrated_command", None)
    else:
        records["runs"][0]["turns"][0]["narrated_command"] = narrated_command
    (path / "all-turn-records.json").write_text(json.dumps(records))

    assert "- NARRATED COMMAND:" not in _report(path)


def test_narrated_command_is_printed_when_different(tmp_path):
    path = tmp_path / "results"
    _write_results(path, [1], [_fact(1, facts_after_correct="no")], [])
    records = json.loads((path / "all-turn-records.json").read_text())
    records["runs"][0]["turns"][0]["narrated_command"] = "Go out to your truck. Bring your laptop inside."
    (path / "all-turn-records.json").write_text(json.dumps(records))

    assert "- NARRATED COMMAND: Go out to your truck. Bring your laptop inside." in _report(path)


def test_all_turns_includes_clean_turn_with_full_body_and_count(tmp_path):
    path = tmp_path / "results"
    _write_results(path, [1, 2], [_fact(1), _fact(2, facts_after_correct="no")], [_cont(1), _cont(2)])
    records = json.loads((path / "all-turn-records.json").read_text())
    records["runs"][0]["turns"][0].update(
        {
            "narrated_command": "Inspect the item.",
            "item_facts_before": {"item": {"place": "table"}},
            "item_facts_raw": {"item": {"place": "hands"}},
            "item_facts_after": {"item": {"place": "hands", "condition": []}},
            "item_facts_issues": ["issue"],
        }
    )
    (path / "all-turn-records.json").write_text(json.dumps(records))

    report = _report(path, all_turns=True)

    assert "  - clean turns: 1" in report
    assert (
        "### r1 turn 1 (1A) - clean\n"
        "- COMMAND: Check the item.\n"
        "- NARRATED COMMAND: Inspect the item.\n"
        "- NARRATION: The item is here.\n"
        '- GIVEN: {"item": {"place": "table"}}\n'
        '- REPLY: {"item": {"place": "hands"}}\n'
        '- AFTER: {"item": {"place": "hands", "condition": []}}\n'
        '- ISSUES: ["issue"]\n'
        "- FACT JUDGE: fact 1\n"
        "- CONTINUITY JUDGE: continuity 1\n"
    ) in report
    assert "### r1 turn 2 (1A) - facts_after_wrong" in report


def test_clean_turns_are_omitted_without_all_turns(tmp_path):
    path = tmp_path / "results"
    _write_results(path, [1, 2], [_fact(1), _fact(2, facts_after_correct="no")], [_cont(1), _cont(2)])

    report = _report(path)

    assert "clean" not in report
    assert "clean turns:" not in report
