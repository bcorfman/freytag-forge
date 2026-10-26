import json

import pytest

from scripts.ringer.environment_narration import shadow_report


def _turn(
    command="Inspect the alcove.",
    narration="A brass marker rests on the shelf.",
    relations=None,
    shadow=None,
    error=None,
    places_before=None,
    places_after=None,
    observation_request=None,
    scene=None,
):
    return {
        "input": command,
        "narration": narration,
        "error": error,
        "observation_relations": relations,
        "observation_shadow": shadow,
        "places_before": places_before,
        "places_after": places_after,
        "observation_request": observation_request,
        "scene": scene,
    }


def _relation(thing="brass marker", place="shelf", holder="room"):
    return {"thing": thing, "place": place, "holder": holder}


def _shadow(verdict="accept", score=1.0, outcome="ok", elapsed=0.4, requests=1):
    return {
        "outcome": outcome,
        "requests": requests,
        "elapsed_s": elapsed,
        "failure": None,
        "accepted": verdict == "accept",
        "question_version": "q1",
        "verdicts": [{"thing": "brass marker", "verdict": verdict, "score": score}],
    }


def _write_json(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _run(capsys, argv):
    result = shadow_report.main(argv)
    captured = capsys.readouterr()
    return result, captured.out, captured.err


def test_sheet_shows_blind_content_and_lists_no_relation_turns(tmp_path, capsys):
    rows = [
        {
            "turns": [
                _turn(
                    relations=[_relation()],
                    shadow={
                        **_shadow(score=0.8431),
                        "outcome": "verdict-only-outcome-marker",
                        "verdicts": [
                            {
                                "thing": "brass marker",
                                "verdict": "verdict-only-accept-marker",
                                "score": 0.8431,
                            }
                        ],
                    },
                    places_before={"player": "room"},
                    places_after={"player": "room"},
                    observation_request={"kind": "look", "focus": "brass marker"},
                ),
                _turn(command="No relations here.", relations=[]),
                _turn(command="No observation here.", relations=None),
                _turn(command="Failed turn.", relations=[_relation()], error="boom"),
            ]
        }
    ]
    rows_path = _write_json(tmp_path, "rows.json", rows)

    code, output, error = _run(capsys, ["sheet", str(rows_path)])

    assert code == 0
    assert error == ""
    assert "r0t0" in output
    assert "Inspect the alcove." in output
    assert "A brass marker rests on the shelf." in output
    assert "1. brass marker | shelf | room" in output
    assert 'places_before: {"player":"room"}' in output
    assert 'places_after: {"player":"room"}' in output
    assert "Request kind: look" in output
    assert "Request focus: brass marker" in output
    assert "r0t1" in output
    assert "Relations:\n\nnone" in output
    assert "r0t2" in output
    assert "verdict-only-accept-marker" not in output
    assert "verdict-only-outcome-marker" not in output
    assert "0.8431" not in output
    assert "accept" not in output
    assert "reject" not in output
    assert "uncertain" not in output
    assert "score" not in output
    assert "outcome" not in output
    assert "r0t3" not in output


def test_sheet_out_writes_markdown(tmp_path, capsys):
    rows_path = _write_json(
        tmp_path,
        "rows.json",
        [{"turns": [_turn(relations=[_relation()])]}],
    )
    output_path = tmp_path / "sheet.md"

    code, output, error = _run(capsys, ["sheet", str(rows_path), "--out", str(output_path)])

    assert code == 0
    assert output == ""
    assert error == ""
    assert "A brass marker rests on the shelf." in output_path.read_text(encoding="utf-8")


def test_labels_template_has_one_null_per_relation(tmp_path, capsys):
    rows_path = _write_json(
        tmp_path,
        "rows.json",
        [
            {
                "turns": [
                    _turn(relations=[_relation(), _relation("blue bead")]),
                    _turn(command="Second replicate", relations=[_relation()]),
                ]
            }
        ],
    )

    code, output, error = _run(capsys, ["labels-template", str(rows_path)])

    assert code == 0
    assert error == ""
    assert json.loads(output) == {
        "r0t0": {"1": None, "2": None, "acceptable": None, "refind": None, "invented_object": None},
        "r0t1": {"1": None, "acceptable": None, "refind": None, "invented_object": None},
    }


def test_labels_template_includes_acceptable_for_zero_relations(tmp_path, capsys):
    rows_path = _write_json(tmp_path, "rows.json", [{"turns": [_turn(relations=[])]}])

    code, output, error = _run(capsys, ["labels-template", str(rows_path)])

    assert code == 0
    assert error == ""
    assert json.loads(output) == {"r0t0": {"acceptable": None, "refind": None, "invented_object": None}}


def test_join_allows_null_or_absent_defect_tags(tmp_path, capsys):
    rows_path = _write_json(
        tmp_path,
        "rows.json",
        [{"turns": [_turn(relations=[_relation()], command="Inspect the alcove.")]}],
    )
    labels_path = _write_json(
        tmp_path,
        "labels.json",
        {"r0t0": {"acceptable": True, "1": True, "refind": None}},
    )

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "Missing or null labels" not in output
    assert "7 re-find of the held card: INCONCLUSIVE" in output
    assert "8 invented object on the empty seat: INCONCLUSIVE" in output


def test_transition_turn_passes_when_requirement_is_dropped(tmp_path, capsys):
    rows = [
        {
            "turns": [
                _turn(command="Stay here.", relations=None, scene="room"),
                _turn(
                    command="Go outside.",
                    relations=None,
                    scene="yard",
                    shadow={
                        "outcome": "no_narrator_call",
                        "requests": 0,
                        "requirement_dropped": "scene_or_area_changed",
                    },
                ),
            ]
        }
    ]
    rows_path = _write_json(tmp_path, "rows.json", rows)
    labels_path = _write_json(tmp_path, "labels.json", {})

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "5 scene-transition turns drop the requirement: PASS (1/1)" in output


def test_transition_turn_fails_when_it_asked_the_verifier(tmp_path, capsys):
    rows = [
        {
            "turns": [
                _turn(command="Start.", relations=None, scene="room"),
                _turn(
                    command="Go outside.",
                    relations=[_relation()],
                    scene="yard",
                    shadow=_shadow(),
                ),
            ]
        }
    ]
    rows_path = _write_json(tmp_path, "rows.json", rows)
    labels_path = _write_json(tmp_path, "labels.json", {"r0t1": {"acceptable": True, "1": True}})

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "5 scene-transition turns drop the requirement: FAIL (r0t1)" in output
    assert "verifier gate (clauses 1 to 6): FAIL" in output


def test_zero_scene_transitions_are_inconclusive(tmp_path, capsys):
    rows_path = _write_json(
        tmp_path,
        "rows.json",
        [{"turns": [_turn(command="First.", relations=None, scene="room")]}],
    )
    labels_path = _write_json(tmp_path, "labels.json", {})

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "5 scene-transition turns drop the requirement: INCONCLUSIVE (n=0)" in output


def test_held_item_relations_are_reported_by_hand_label(tmp_path, capsys):
    rows = [
        {
            "turns": [
                _turn(
                    relations=[_relation("held card", place="", holder="")],
                    shadow={
                        **_shadow(),
                        "verdicts": [{"thing": "held card", "verdict": "accept", "score": 1.0}],
                    },
                ),
                _turn(
                    relations=[_relation("held card", place="", holder="")],
                    shadow={
                        **_shadow(verdict="reject", score=0.2),
                        "verdicts": [{"thing": "held card", "verdict": "reject", "score": 0.2}],
                    },
                ),
                _turn(
                    relations=[_relation("held card", place="", holder="")],
                    shadow={
                        **_shadow(verdict="uncertain", score=0.5),
                        "verdicts": [{"thing": "held card", "verdict": "uncertain", "score": 0.5}],
                    },
                ),
                _turn(
                    relations=[_relation("held card", place="", holder="")],
                    shadow={**_shadow(), "verdicts": []},
                ),
                _turn(
                    relations=[_relation("held note", place="", holder="")],
                    shadow={
                        **_shadow(),
                        "verdicts": [{"thing": "held note", "verdict": "accept", "score": 1.0}],
                    },
                ),
                _turn(
                    relations=[_relation("not a mention", place="seat", holder="")],
                    shadow={
                        **_shadow(),
                        "verdicts": [{"thing": "not a mention", "verdict": "accept", "score": 1.0}],
                    },
                ),
            ]
        }
    ]
    labels_path = _write_json(
        tmp_path,
        "labels.json",
        {
            "r0t0": {"acceptable": True, "1": True},
            "r0t1": {"acceptable": True, "1": False},
            "r0t2": {"acceptable": True, "1": True},
            "r0t3": {"acceptable": True, "1": False},
            "r0t4": {"acceptable": True, "1": True},
            "r0t5": {"acceptable": True, "1": True},
        },
    )
    rows_path = _write_json(tmp_path, "rows.json", rows)

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    held_section = output.split("## 6 held-item mention relations", 1)[1]
    assert "| thing | labelled true | labelled false | accept | reject | uncertain | unavailable |" in held_section
    assert "| held card | 2 | 2 | 1 | 1 | 1 | 1 |" in held_section
    assert "| held note | 1 | 0 | 1 | 0 | 0 | 0 |" in held_section
    assert "not a mention" not in held_section


def test_refind_clause_passes_at_minimum_with_one_true(tmp_path, capsys):
    turns = []
    labels = {}
    for index in range(15):
        turns.append(
            _turn(
                command="Feel under the drawer.",
                relations=[],
                shadow={"outcome": "no_relations", "requests": 0, "verdicts": []},
            )
        )
        labels[f"r0t{index}"] = {
            "acceptable": True,
            "refind": index == 0,
        }
    rows_path = _write_json(tmp_path, "rows.json", [{"turns": turns}])
    labels_path = _write_json(tmp_path, "labels.json", labels)

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "7 re-find of the held card: PASS (n=15, refind true=1)" in output


def test_refind_clause_fails_with_two_true(tmp_path, capsys):
    turns = [
        _turn(
            command="feel under the drawer",
            relations=[],
            shadow={"outcome": "no_relations", "requests": 0, "verdicts": []},
        )
        for _ in range(15)
    ]
    labels = {f"r0t{index}": {"acceptable": True, "refind": index < 2} for index in range(15)}
    rows_path = _write_json(tmp_path, "rows.json", [{"turns": turns}])
    labels_path = _write_json(tmp_path, "labels.json", labels)

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "7 re-find of the held card: FAIL (n=15, refind true=2)" in output
    assert "product-defect gate (clauses 7 and 8): FAIL" in output


def test_refind_clause_is_inconclusive_below_minimum(tmp_path, capsys):
    turns = [
        _turn(
            command="feel under the drawer",
            relations=[],
            shadow={"outcome": "no_relations", "requests": 0, "verdicts": []},
        )
        for _ in range(14)
    ]
    labels = {f"r0t{index}": {"acceptable": True, "refind": False} for index in range(14)}
    rows_path = _write_json(tmp_path, "rows.json", [{"turns": turns}])
    labels_path = _write_json(tmp_path, "labels.json", labels)

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "7 re-find of the held card: INCONCLUSIVE (n=14, refind true=0)" in output


def test_invented_object_clause_passes_at_minimum_with_one_true(tmp_path, capsys):
    turns = []
    labels = {}
    for index in range(6):
        turns.append(
            _turn(
                command="Inspect the passenger seat.",
                relations=[],
                shadow={"outcome": "no_relations", "requests": 0, "verdicts": []},
                places_before={"laptop": "driver_seat"},
                observation_request={"kind": "look", "focus": "passenger seat"},
            )
        )
        labels[f"r0t{index}"] = {"acceptable": True, "invented_object": index == 0}
    turns.append(
        _turn(
            command="Inspect the passenger seat.",
            relations=[_relation("laptop", place="passenger_seat", holder="")],
            shadow={
                "outcome": "ok",
                "requests": 1,
                "elapsed_s": 0.4,
                "verdicts": [{"thing": "laptop", "verdict": "accept", "score": 1.0}],
            },
            places_before={"laptop": "passenger_seat"},
            observation_request={"kind": "look", "focus": "passenger seat"},
        )
    )
    labels["r0t6"] = {"acceptable": True, "1": True, "invented_object": False}
    rows_path = _write_json(tmp_path, "rows.json", [{"turns": turns}])
    labels_path = _write_json(tmp_path, "labels.json", labels)

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "8 invented object on the empty seat: PASS (n=6, invented_object true=1)" in output


def test_invented_object_clause_fails_with_two_true(tmp_path, capsys):
    turns = [
        _turn(
            command="inspect the passenger seat",
            relations=[],
            shadow={"outcome": "no_relations", "requests": 0, "verdicts": []},
            places_before={"laptop": "driver_seat"},
            observation_request={"kind": "look", "focus": "passenger seat"},
        )
        for _ in range(6)
    ]
    labels = {f"r0t{index}": {"acceptable": True, "invented_object": index < 2} for index in range(6)}
    rows_path = _write_json(tmp_path, "rows.json", [{"turns": turns}])
    labels_path = _write_json(tmp_path, "labels.json", labels)

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "8 invented object on the empty seat: FAIL (n=6, invented_object true=2)" in output


def test_invented_object_clause_is_inconclusive_below_minimum(tmp_path, capsys):
    turns = [
        _turn(
            command="inspect the passenger seat",
            relations=[],
            shadow={"outcome": "no_relations", "requests": 0, "verdicts": []},
            places_before={"laptop": "driver_seat"},
            observation_request={"kind": "look", "focus": "passenger seat"},
        )
        for _ in range(5)
    ]
    labels = {f"r0t{index}": {"acceptable": True, "invented_object": False} for index in range(5)}
    rows_path = _write_json(tmp_path, "rows.json", [{"turns": turns}])
    labels_path = _write_json(tmp_path, "labels.json", labels)

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "8 invented object on the empty seat: INCONCLUSIVE (n=5, invented_object true=0)" in output


def test_join_refuses_missing_label(tmp_path, capsys):
    rows_path = _write_json(
        tmp_path,
        "rows.json",
        [{"turns": [_turn(relations=[_relation(), _relation("blue bead")])]}],
    )
    labels_path = _write_json(tmp_path, "labels.json", {"r0t0": {"acceptable": True, "1": True}})

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 2
    assert output == ""
    assert "r0t0" in error
    assert "2" in error


def test_join_refuses_missing_acceptable_label(tmp_path, capsys):
    rows_path = _write_json(tmp_path, "rows.json", [{"turns": [_turn(relations=[_relation()])]}])
    labels_path = _write_json(tmp_path, "labels.json", {"r0t0": {"1": True}})

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 2
    assert output == ""
    assert "r0t0 acceptable" in error


def test_join_counts_false_accept_and_fails_gate(tmp_path, capsys):
    rows_path = _write_json(
        tmp_path,
        "rows.json",
        [
            {
                "turns": [
                    _turn(
                        relations=[_relation()],
                        shadow=_shadow(verdict="accept", score=0.91),
                    )
                ]
            }
        ],
    )
    labels_path = _write_json(tmp_path, "labels.json", {"r0t0": {"acceptable": True, "1": False}})

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "GATE: FAIL" in output
    assert "false accepts: 1" in output
    assert "r0t0" in output
    assert "brass marker" in output
    assert "0.91" in output
    assert "at least 30 labelled relations" in output


def test_join_passes_clean_gate_with_thirty_relations(tmp_path, capsys):
    turns = []
    labels = {}
    for index in range(30):
        turn_id = f"r0t{index}"
        turns.append(
            _turn(
                command=f"Inspect station {index}.",
                relations=[_relation(f"marker {index}")],
                shadow={
                    **_shadow(elapsed=1.0, requests=2),
                    "verdicts": [{"thing": f"marker {index}", "verdict": "accept", "score": 1.0}],
                },
            )
        )
        labels[turn_id] = {"acceptable": True, "1": True}
    rows_path = _write_json(tmp_path, "rows.json", [{"turns": turns}])
    labels_path = _write_json(tmp_path, "labels.json", labels)

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "GATE: PASS" in output
    assert "labelled relations: 30" in output
    assert "false accepts: 0" in output
    assert "good-turn strict reject rate: 0/30" in output
    assert "p95 elapsed_s: 1.000" in output
    assert "requests: 60" in output
    assert "zero-false-accept upper bound" in output


def test_join_strict_rejections_and_unavailable_outcome_reject(tmp_path, capsys):
    rows = [
        {
            "turns": [
                _turn(
                    command="Good labelled turn",
                    relations=[_relation()],
                    shadow=_shadow(verdict="reject", score=0.2),
                ),
                _turn(
                    command="Unavailable labelled turn",
                    relations=[_relation("blue bead")],
                    shadow=_shadow(verdict="accept", outcome="unavailable", score=None),
                ),
                _turn(
                    command="Mixed labels",
                    relations=[_relation("green pin"), _relation("white pin")],
                    shadow={
                        **_shadow(),
                        "verdicts": [
                            {"thing": "green pin", "verdict": "accept", "score": 1.0},
                            {"thing": "white pin", "verdict": "reject", "score": 0.1},
                        ],
                    },
                ),
            ]
        }
    ]
    labels = {
        "r0t0": {"acceptable": True, "1": True},
        "r0t1": {"acceptable": True, "1": True},
        "r0t2": {"acceptable": True, "1": True, "2": False},
    }
    rows_path = _write_json(tmp_path, "rows.json", rows)
    labels_path = _write_json(tmp_path, "labels.json", labels)

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "strict rejections: 2" in output
    assert "good-turn strict reject rate: 2/2" in output
    assert "good turns would_reject: 2/2" in output
    assert "mixed turns would_reject: 1/1" in output
    assert "GATE: FAIL" in output


def test_join_excludes_zero_relation_shadow_failures_from_good_turn_rejections(tmp_path, capsys):
    rows = [
        {
            "turns": [
                _turn(
                    command="No relations outcome",
                    relations=[],
                    shadow={**_shadow(outcome="no_relations"), "verdicts": []},
                ),
                _turn(
                    command="No relations shadow missing",
                    relations=[],
                    shadow=None,
                ),
                _turn(
                    command="Unavailable with relation",
                    relations=[_relation("blue bead")],
                    shadow=_shadow(verdict="accept", outcome="unavailable", score=None),
                ),
            ]
        }
    ]
    labels = {
        "r0t0": {"acceptable": True},
        "r0t1": {"acceptable": True},
        "r0t2": {"acceptable": True, "1": True},
    }
    rows_path = _write_json(tmp_path, "rows.json", rows)
    labels_path = _write_json(tmp_path, "labels.json", labels)

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "good-turn strict reject rate: 1/3 = 0.333333 (n=3)" in output
    assert "good turns would_reject: 1/3 (n=3)" in output
    assert "mixed turns would_reject: 0/0 (n=0)" in output
    assert "turns without shadow record: 1" in output
    assert "2b acceptable-turn enforcement reject rate: 1/3 = 0.333333 (n=3)" in output


def test_join_reports_zero_false_accept_upper_bound(tmp_path, capsys):
    rows_path = _write_json(
        tmp_path,
        "rows.json",
        [
            {
                "turns": [
                    _turn(
                        relations=[_relation()],
                        shadow=_shadow(verdict="reject", score=0.0),
                    )
                ]
            }
        ],
    )
    labels_path = _write_json(tmp_path, "labels.json", {"r0t0": {"acceptable": True, "1": True}})

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    expected = 1 - 0.05 ** (1 / 1)
    assert f"{expected:.6f}" in output
    assert "1 - 0.05**(1/n)" in output


def test_join_counts_turns_without_shadow_record(tmp_path, capsys):
    rows_path = _write_json(
        tmp_path,
        "rows.json",
        [{"turns": [_turn(relations=[_relation()], shadow=None)]}],
    )
    labels_path = _write_json(tmp_path, "labels.json", {"r0t0": {"acceptable": True, "1": True}})

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "turns without shadow record: 1" in output


@pytest.mark.parametrize("value", [None, "true", 1, []])
def test_join_refuses_non_boolean_labels(tmp_path, capsys, value):
    rows_path = _write_json(
        tmp_path,
        "rows.json",
        [{"turns": [_turn(relations=[_relation()])]}],
    )
    labels_path = _write_json(tmp_path, "labels.json", {"r0t0": {"acceptable": True, "1": value}})

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 2
    assert output == ""
    assert "r0t0" in error


def test_join_computes_2b_and_lists_acceptable_rejections(tmp_path, capsys):
    rows = [
        {
            "turns": [
                _turn(
                    command="Over-demanded observation",
                    relations=[_relation("first item"), _relation("second item")],
                    shadow={
                        **_shadow(),
                        "verdicts": [
                            {"thing": "first item", "verdict": "reject", "score": 0.2},
                            {"thing": "second item", "verdict": "uncertain", "score": 0.3},
                        ],
                    },
                ),
                _turn(
                    command="Unacceptable rejected observation",
                    relations=[_relation("unacceptable item")],
                    shadow=_shadow(verdict="reject", score=0.1),
                ),
                _turn(
                    command="No relation result",
                    relations=[],
                    shadow={**_shadow(outcome="no_relations"), "verdicts": []},
                ),
                _turn(command="No shadow result", relations=[], shadow=None),
            ]
        }
    ]
    labels = {
        "r0t0": {"acceptable": True, "1": True, "2": True},
        "r0t1": {"acceptable": False, "1": True},
        "r0t2": {"acceptable": True},
        "r0t3": {"acceptable": True},
    }
    rows_path = _write_json(tmp_path, "rows.json", rows)
    labels_path = _write_json(tmp_path, "labels.json", labels)

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "2b acceptable-turn enforcement reject rate: 1/3 = 0.333333 (n=3)" in output
    assert "GATE: FAIL" in output
    assert "2b acceptable-turn enforcement reject rate <= 0.10" in output
    assert "| r0t0 | Over-demanded observation | first item (0.2), second item (0.3) |" in output
    rejected_table = output.split("## ACCEPTABLE TURNS REJECTED BY ENFORCEMENT", 1)[-1]
    assert "Unacceptable rejected observation" not in rejected_table
    assert "No relation result" not in rejected_table
    assert "No shadow result" not in rejected_table


def test_join_reports_2b_pass_status(tmp_path, capsys):
    rows_path = _write_json(
        tmp_path,
        "rows.json",
        [{"turns": [_turn(relations=[_relation()], shadow=_shadow())]}],
    )
    labels_path = _write_json(tmp_path, "labels.json", {"r0t0": {"acceptable": True, "1": True}})

    code, output, error = _run(capsys, ["join", str(rows_path), str(labels_path)])

    assert code == 0
    assert error == ""
    assert "2b: PASS (0/1 = 0.000000 <= 0.10)" in output


def test_held_item_table_separator_precedes_the_data_rows():
    rows = [
        {
            "turns": [
                _turn(
                    command="Examine my brass marker.",
                    relations=[{"thing": "brass marker", "place": None, "holder": None}],
                    shadow=_shadow(),
                )
            ]
        }
    ]
    report, missing = shadow_report._join(rows, {"r0t0": {"1": True, "acceptable": True}})

    assert not missing
    lines = report.splitlines()
    header = lines.index("| thing | labelled true | labelled false | accept | reject | uncertain | unavailable |")
    assert lines[header + 1].startswith("| --- |")
    assert lines[header + 2].startswith("| brass marker | 1 | 0 | 1 |")
