import json

from scripts.ringer.environment_narration import enforce_report


def _attempt(*, relations=True, accepted=True):
    return {
        "narration": "The marker rests on the shelf.",
        "relations": [{"thing": "brass marker"}] if relations else [],
        "accepted": accepted,
    }


def _turn(*, kind=None, relations=True, after=None, prompts=None):
    request = None if kind is None else {"kind": kind, "focus": "drawer"}
    return {
        "input": "feel under the drawer" if kind == "under" else "inspect the drawer",
        "narration": "The marker rests on the shelf.",
        "error": None,
        "places_before": {"memory_card": "drawer"},
        "places_after": after or {"memory_card": "drawer"},
        "narration_attempts": 1,
        "verifier_requests": 1,
        "observation_enforce": {},
        "enforce_attempts": [_attempt(relations=relations)],
        "provider_responses": [],
        "turn_elapsed_s": 1.0,
        "observation_request": request,
        "prompts": prompts or [],
    }


def _labels(rows, *, underside=None, card_prose=None, leak=False):
    labels = {}
    for replicate_index, replicate in enumerate(rows):
        for turn_index, turn in enumerate(replicate["turns"]):
            turn_id = f"r{replicate_index}t{turn_index}"
            kind = (turn.get("observation_request") or {}).get("kind")
            labels[turn_id] = {
                "presents_required": True,
                "acceptable": True,
                "underside_search": (kind == "under" if underside is None else underside),
                "card_found_in_prose": card_prose,
                "tags": {
                    "refind": False,
                    "invented_object": False,
                    "leak": leak,
                    "wrong_custody": False,
                    "unrequested_move": False,
                },
                "earlier": [],
            }
    return labels


def _write(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _run(tmp_path, capsys, rows, labels):
    return enforce_report.main(
        [
            "join",
            str(_write(tmp_path, "rows.json", rows)),
            "--labels",
            str(_write(tmp_path, "labels.json", labels)),
        ]
    ), capsys.readouterr()


def _route_a(count=25, *, kind="under", relations=True):
    return [{"route": "observe_topup", "turns": [_turn(kind=kind, relations=relations) for _ in range(count)]}]


def _route_b(pass_count=5, *, leak=False):
    rows = []
    for index in range(5 if pass_count != 3 else 5):
        found = index < pass_count
        rows.append(
            {
                "route": "observe_under_first",
                "turns": [
                    _turn(
                        kind="under",
                        after={"memory_card": "kristin"} if found else {"memory_card": "drawer"},
                    ),
                    _turn(
                        kind="under",
                        after={"memory_card": "kristin"} if found else {"memory_card": "drawer"},
                    ),
                ],
            }
        )
    labels = _labels(rows, card_prose=True, leak=leak)
    for index in range(5):
        labels[f"r{index}t0"]["card_found_in_prose"] = index < pass_count
    return rows, labels


def test_clean_route_a_and_s2_pass(tmp_path, capsys):
    rows = _route_a()
    for turn in rows[0]["turns"][:5]:
        turn["enforce_attempts"] = [_attempt(accepted=False), _attempt()]
        turn["narration_attempts"] = 2
    labels = _labels(rows)
    for index in range(5):
        labels[f"r0t{index}"]["earlier"] = [True]
    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 0
    assert "S1 classification audit: PASS" in captured.out
    assert "S2 non-vacuity: PASS" in captured.out
    assert "t9b screen: PASS" in captured.out


def test_s1_fails_with_false_under_label_and_prints_stop(tmp_path, capsys):
    rows = _route_a(1)
    labels = _labels(rows, underside=False)
    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 0
    assert "S1 classification audit: FAIL" in captured.out
    assert "STOP: coverage was suppressed on a command that is not an underside search" in captured.out
    assert "r0t0" in captured.out


def test_s1_missing_under_label_exits_one(tmp_path, capsys):
    rows = _route_a(1)
    labels = _labels(rows)
    labels["r0t0"]["underside_search"] = None
    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 1
    assert "MISSING LABELS" in captured.err
    assert "r0t0 underside_search" in captured.err


def test_s2_is_inconclusive_with_too_few_under_turns(tmp_path, capsys):
    rows = _route_a(20, kind="look")
    code, captured = _run(tmp_path, capsys, rows, _labels(rows))

    assert code == 0
    assert "S2 non-vacuity: INCONCLUSIVE" in captured.out


def test_s2_is_inconclusive_with_too_few_required_relations(tmp_path, capsys):
    rows = _route_a(20, relations=False)
    code, captured = _run(tmp_path, capsys, rows, _labels(rows))

    assert code == 0
    assert "S2 non-vacuity: INCONCLUSIVE" in captured.out
    assert "non-empty required lists: 0" in captured.out


def test_s3_passes_five_of_five_and_four_of_five(tmp_path, capsys):
    rows, labels = _route_b(5)
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "S3 card: PASS" in captured.out

    rows, labels = _route_b(4)
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "S3 card: PASS" in captured.out


def test_s3_fails_three_of_five_with_per_part_reason(tmp_path, capsys):
    rows, labels = _route_b(3)
    labels["r3t0"]["card_found_in_prose"] = False
    labels["r4t0"]["card_found_in_prose"] = False
    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 0
    assert "S3 card: FAIL" in captured.out
    assert "held by player after second command" in captured.out
    assert "card_found_in_prose" in captured.out


def test_s3_is_inconclusive_below_five_replicates(tmp_path, capsys):
    rows, labels = _route_b(3)
    rows = rows[:3]
    labels = {key: value for key, value in labels.items() if key.startswith(("r0", "r1", "r2"))}
    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 0
    assert "S3 card: INCONCLUSIVE" in captured.out


def test_s3_fails_on_leak_tag(tmp_path, capsys):
    rows, labels = _route_b(5, leak=True)
    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 0
    assert "S3 card: FAIL" in captured.out
    assert "leak" in captured.out


def test_route_b_ignores_design_inconclusives_for_t9b_verdict(tmp_path, capsys):
    rows, labels = _route_b(5)
    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 0
    assert "Clause 1: INCONCLUSIVE" in captured.out
    assert "Clause 6: INCONCLUSIVE" in captured.out
    assert "Clause 7: INCONCLUSIVE" in captured.out
    assert "S2 non-vacuity: INCONCLUSIVE" in captured.out
    assert "t9b screen: PASS" in captured.out


def test_sheet_does_not_leak_observation_kind(tmp_path, capsys):
    rows = [{"route": "observe_topup", "turns": [_turn(kind="under")]}]
    rows[0]["turns"][0]["input"] = "inspect the drawer"
    sheet_path = _write(tmp_path, "rows.json", rows)
    code = enforce_report.main(["sheet", str(sheet_path)])
    sheet = capsys.readouterr().out.casefold()

    assert code == 0
    for forbidden in ("observation_request", "kind", "under", "look", "open", "score", "verdict"):
        assert forbidden not in sheet


def test_scope_template_has_new_null_labels(tmp_path, capsys):
    rows = [{"route": "observe_topup", "turns": [_turn(kind="under")]}]
    code = enforce_report.main(["labels-template", str(_write(tmp_path, "rows.json", rows))])
    template = json.loads(capsys.readouterr().out)

    assert code == 0
    assert template["r0t0"]["underside_search"] is None
    assert template["r0t0"]["card_found_in_prose"] is None


def test_scope_information_reports_kinds_misses_openings_and_jev_prompts(tmp_path, capsys):
    prompts = [{"system": "jev", "user": "searches_underneath"}]
    rows = [
        {
            "route": "observe_topup",
            "turns": [
                _turn(kind="open", prompts=prompts),
                _turn(kind="look", prompts=[{"system": "narrator", "user": "plain"}]),
                _turn(kind="under", prompts=prompts),
            ],
        }
    ]
    labels = _labels(rows, underside=True)
    labels["r0t0"]["underside_search"] = True
    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 0
    assert "kind distribution" in captured.out
    assert "open" in captured.out
    assert "searches_underneath prompts" in captured.out
