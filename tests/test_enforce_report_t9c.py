import json

from scripts.ringer.environment_narration import enforce_report

GAP_TEXT = "The drawer rides high in its frame. A thin gap beneath its lower edge is wide enough for Kristin's fingers."
LOOK_COMMANDS = {
    "inspect the drawer",
    "examine the drawer",
    "search the drawer",
    "check the drawer",
}


def _turn(
    command,
    *,
    kind,
    card_held=False,
    failed=False,
    engine_opened=False,
    committed_open="closed",
):
    places = {"memory_card": "kristin" if card_held else "drawer"}
    return {
        "input": command,
        "narration": None if failed else "The marker rests on the shelf.",
        "error": "verification exhausted" if failed else None,
        "places_before": {"memory_card": "drawer"},
        "places_after": places,
        "narration_attempts": 2 if failed else 1,
        "verifier_requests": 1,
        "observation_enforce": {},
        "enforce_attempts": [
            {
                "narration": None if failed else "The marker rests on the shelf.",
                "relations": [{"thing": "brass marker"}],
                "accepted": not failed,
            }
        ],
        "provider_responses": [],
        "turn_elapsed_s": 1.0,
        "observation_request": {"kind": kind, "focus": "drawer"},
        "engine_opened": engine_opened,
        "focus_open_state_after": committed_open,
        "focus_open_state_committed": committed_open,
        "handoff_id": None,
        "delivered_text": None,
    }


def _label(*, gap=False, contents=True, command_opens=False, card=False):
    return {
        "presents_required": True,
        "acceptable": True,
        "gap_restated": gap,
        "contents_shown": contents,
        "command_opens": command_opens,
        "card_found_in_prose": card,
        "underside_search": False,
        "tags": {
            "refind": False,
            "invented_object": False,
            "leak": False,
            "wrong_custody": False,
            "unrequested_move": False,
        },
        "earlier": [],
    }


def _good_rows_and_labels():
    rows = []
    labels = {}

    for replicate_index in range(10):
        turns = [_turn("inspect the drawer", kind="look")]
        turns.extend(_turn("feel under the drawer", kind="under") for _ in range(8))
        rows.append({"route": "observe_topup", "turns": turns})
        for turn_index, turn_data in enumerate(turns):
            labels[f"r{replicate_index}t{turn_index}"] = _label(gap=turn_index == 0)
            labels[f"r{replicate_index}t{turn_index}"]["underside_search"] = (
                turn_data["observation_request"]["kind"] == "under"
            )

    for replicate_index in range(5):
        turns = [
            _turn("feel under the drawer", kind="under", card_held=True),
            _turn("open the drawer", kind="open", card_held=True),
            _turn("inspect the drawer", kind="look", card_held=True),
            _turn("pull out the drawer", kind="open", card_held=True),
        ]
        rows.append({"route": "observe_under_first", "turns": turns})
        for turn_index, turn_data in enumerate(turns):
            labels[f"r{10 + replicate_index}t{turn_index}"] = _label(
                gap=turn_index == 2,
                command_opens=turn_index in (1, 3),
                card=turn_index == 0,
            )
            labels[f"r{10 + replicate_index}t{turn_index}"]["underside_search"] = (
                turn_data["observation_request"]["kind"] == "under"
            )

    for replicate_index in range(15):
        turns = [
            _turn("inspect the drawer", kind="look"),
            _turn("examine the drawer", kind="look"),
            _turn("search the drawer", kind="look"),
            _turn("check the drawer", kind="look"),
            _turn(
                "look inside the drawer",
                kind="open",
                engine_opened=True,
                committed_open="open",
            ),
            _turn("look under the drawer", kind="under", card_held=True),
        ]
        rows.append({"route": "observe_look_inside_under", "turns": turns})
        row_index = 15 + replicate_index
        for turn_index, turn in enumerate(turns):
            labels[f"r{row_index}t{turn_index}"] = _label(
                gap=turn_index < 4,
                contents=turn_index == 4,
                command_opens=turn_index == 4,
                card=turn_index == 5,
            )
            labels[f"r{row_index}t{turn_index}"]["underside_search"] = turn_index == 5
            if turn_index < 4:
                turn["handoff_id"] = "k_sl_1a_f_r2"
                turn["delivered_text"] = GAP_TEXT
            elif turn_index == 5:
                turn["handoff_id"] = "k_sl_1a_b_r0"

    return rows, labels


def _run(tmp_path, capsys, rows, labels):
    rows_path = tmp_path / "rows.json"
    labels_path = tmp_path / "labels.json"
    rows_path.write_text(json.dumps(rows), encoding="utf-8")
    labels_path.write_text(json.dumps(labels), encoding="utf-8")
    code = enforce_report.main(["join", str(rows_path), "--labels", str(labels_path)])
    return code, capsys.readouterr()


def test_t9c_all_clauses_pass_and_information_is_printed(tmp_path, capsys):
    rows, labels = _good_rows_and_labels()

    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 0
    assert "N1: PASS" in captured.out
    assert "N2: PASS" in captured.out
    assert "N3: PASS" in captured.out
    assert "N4: PASS" in captured.out
    assert "N5: PASS" in captured.out
    assert "N6: PASS" in captured.out
    assert "look-group request kinds" in captured.out
    assert "narrator-opened look-group turns" in captured.out
    assert "narrator-closed-after-engine-open turns" in captured.out
    assert "handoff outcomes" in captured.out


def test_t9c_n1_lists_four_unsuccessful_look_turns(tmp_path, capsys):
    rows, labels = _good_rows_and_labels()
    for turn in rows[15]["turns"][:4]:
        turn["narration"] = None
        turn["error"] = "verification exhausted"

    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 0
    assert "N1: FAIL" in captured.out
    assert "r15t0" in captured.out
    assert "unsuccessful" in captured.out


def test_t9c_n2_fails_for_four_pooled_gap_misses(tmp_path, capsys):
    rows, labels = _good_rows_and_labels()
    for replicate_index in range(4):
        labels[f"r{replicate_index}t0"]["gap_restated"] = False

    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 0
    assert "N2: FAIL" in captured.out
    assert "r0t0" in captured.out


def test_t9c_n2_fails_for_three_route_c_gap_misses(tmp_path, capsys):
    rows, labels = _good_rows_and_labels()
    for replicate_index in range(3):
        labels[f"r{15 + replicate_index}t0"]["gap_restated"] = False

    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 0
    assert "N2: FAIL" in captured.out
    assert "route C" in captured.out


def test_t9c_n3_lists_route_c_replicate_without_card(tmp_path, capsys):
    rows, labels = _good_rows_and_labels()
    for replicate_index in (15, 16):
        rows[replicate_index]["turns"][5]["places_after"] = {"memory_card": "drawer"}
        labels[f"r{replicate_index}t5"]["card_found_in_prose"] = False

    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 0
    assert "N3: FAIL" in captured.out
    assert "r15t5" in captured.out


def test_t9c_n4_lists_two_closed_look_inside_turns(tmp_path, capsys):
    rows, labels = _good_rows_and_labels()
    for replicate_index in (0, 1):
        turn = rows[15 + replicate_index]["turns"][4]
        turn["focus_open_state_committed"] = "closed"

    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 0
    assert "N4: FAIL" in captured.out
    assert "r15t4" in captured.out


def test_t9c_n5_rejects_engine_open_on_nonopening_look(tmp_path, capsys):
    rows, labels = _good_rows_and_labels()
    turn = rows[15]["turns"][0]
    turn["engine_opened"] = True

    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 0
    assert "N5: FAIL" in captured.out
    assert "r15t0" in captured.out


def test_t9c_n6_requires_failed_engine_open_to_roll_back(tmp_path, capsys):
    rows, labels = _good_rows_and_labels()
    turn = rows[0]["turns"][1]
    turn["input"] = "open the drawer"
    turn["observation_request"] = {"kind": "open", "focus": "drawer"}
    turn["engine_opened"] = True
    turn["focus_open_state_committed"] = "open"
    turn["narration"] = None
    turn["error"] = "verification exhausted"
    turn["enforce_attempts"][0]["accepted"] = False
    labels["r0t1"]["earlier"] = [True]

    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 0
    assert "N6: FAIL" in captured.out
    assert "r0t1" in captured.out


def test_t9c_missing_labels_and_blind_sheet(tmp_path, capsys):
    rows, labels = _good_rows_and_labels()
    labels["r15t0"]["gap_restated"] = None
    code, captured = _run(tmp_path, capsys, rows, labels)

    assert code == 1
    assert "MISSING LABELS" in captured.err
    assert "r15t0 gap_restated" in captured.err

    rows_path = tmp_path / "sheet-rows.json"
    rows_path.write_text(json.dumps(rows), encoding="utf-8")
    sheet_code = enforce_report.main(["sheet", str(rows_path)])
    sheet = capsys.readouterr().out
    assert sheet_code == 0
    for forbidden in (
        "handoff_id",
        "delivered_text",
        "engine_opened",
        "focus_open_state_after",
        "focus_open_state_committed",
    ):
        assert forbidden not in sheet


def test_t9c_labels_template_contains_new_labels(tmp_path, capsys):
    rows, _ = _good_rows_and_labels()
    rows_path = tmp_path / "rows.json"
    rows_path.write_text(json.dumps(rows), encoding="utf-8")

    code = enforce_report.main(["labels-template", str(rows_path)])
    template = json.loads(capsys.readouterr().out)

    assert code == 0
    assert template["r15t0"]["gap_restated"] is None
    assert template["r15t0"]["contents_shown"] is None
    assert template["r15t0"]["command_opens"] is None
