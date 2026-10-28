import json

from scripts.ringer.environment_narration import enforce_report

STATEMENT = "Kristin looks over the drawer and is pointed toward the thin gap beneath its lower edge."


def _turn(
    command,
    *,
    kind="look",
    committed=True,
    engine_opened=False,
    committed_open="closed",
    after_open="closed",
    narration=None,
):
    if narration is None:
        narration = "The marker rests on the shelf." if committed else None
    return {
        "input": command,
        "narration": narration,
        "error": None if committed else "verification exhausted",
        "places_before": {"memory_card": "drawer"},
        "places_after": {"memory_card": "drawer"},
        "narration_attempts": 1 if committed else 2,
        "verifier_requests": 1,
        "observation_enforce": {},
        "enforce_attempts": [
            {
                "narration": narration,
                "relations": [{"thing": "brass marker"}],
                "accepted": committed,
            }
        ],
        "provider_responses": [],
        "turn_elapsed_s": 1.0,
        "observation_request": {"kind": kind, "focus": "drawer"},
        "engine_opened": engine_opened,
        "focus_open_state_after": after_open,
        "focus_open_state_committed": committed_open,
        "handoff_id": "k_sl_1a_f_r2",
        "delivered_text": None,
    }


def _label(*, gap=True, contents=True, command_opens=False, card=False):
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


def _rows_and_labels(route, turns):
    rows = [{"route": route, "turns": turns}]
    labels = {}
    for turn_index, turn in enumerate(turns):
        labels[f"r0t{turn_index}"] = _label(
            command_opens=turn["input"] == "search the drawer" or turn["input"] == "open the drawer",
            contents=turn["focus_open_state_committed"] == "open",
        )
    return rows, labels


def _route_c_commands(commands, *, misses=0):
    turns = []
    for command in commands:
        turns.append(_turn(command))
    rows, labels = _rows_and_labels("observe_look_inside_under", turns)
    for index in range(misses):
        labels[f"r0t{index}"]["gap_restated"] = False
    return rows, labels


def _run(tmp_path, capsys, rows, labels):
    rows_path = tmp_path / "rows.json"
    labels_path = tmp_path / "labels.json"
    rows_path.write_text(json.dumps(rows), encoding="utf-8")
    labels_path.write_text(json.dumps(labels), encoding="utf-8")
    code = enforce_report.main(["join", str(rows_path), "--labels", str(labels_path)])
    return code, capsys.readouterr()


def _search_rows(committed_count=15, *, closed_after_commit=False):
    turns = []
    for index in range(15):
        committed = index < committed_count
        turns.append(
            _turn(
                "search the drawer",
                kind="open",
                committed=committed,
                engine_opened=True,
                committed_open="closed" if closed_after_commit and index == 0 else "open",
                after_open="closed",
            )
        )
    rows, labels = _rows_and_labels("observe_look_inside_under", turns)
    for index in range(15):
        labels[f"r0t{index}"]["command_opens"] = True
        labels[f"r0t{index}"]["contents_shown"] = committed_count > index
        if index >= committed_count:
            labels[f"r0t{index}"]["earlier"] = [True]
    return rows, labels


def test_n1_passes_at_43_of_45_and_fails_at_42(tmp_path, capsys):
    commands = [
        command for command in ("inspect the drawer", "examine the drawer", "check the drawer") for _ in range(15)
    ]
    rows, labels = _route_c_commands(commands)
    for index in range(2):
        rows[0]["turns"][index]["narration"] = None
        rows[0]["turns"][index]["error"] = "verification exhausted"
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "N1: PASS (43/45" in captured.out

    rows, labels = _route_c_commands(commands)
    for index in range(3):
        rows[0]["turns"][index]["narration"] = None
        rows[0]["turns"][index]["error"] = "verification exhausted"
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "N1: FAIL (42/45" in captured.out


def test_n1s_passes_at_14_of_15_and_fails_at_13(tmp_path, capsys):
    rows, labels = _search_rows(14)
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "N1s: PASS (14/15" in captured.out
    assert "unsuccessful" in captured.out

    rows, labels = _search_rows(13)
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "N1s: FAIL (13/15" in captured.out


def test_n1s_lists_closed_drawer_after_commit(tmp_path, capsys):
    rows, labels = _search_rows(closed_after_commit=True)
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "N1s: PASS" in captured.out
    assert "closed after commit" in captured.out


def test_n2_passes_at_58_of_60_and_fails_at_57(tmp_path, capsys):
    commands = [
        command
        for command in ("inspect the drawer", "examine the drawer", "search the drawer", "check the drawer")
        for _ in range(15)
    ]
    rows, labels = _route_c_commands(commands, misses=2)
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "N2: PASS (58/60" in captured.out
    assert "handoff_id=" in captured.out

    rows, labels = _route_c_commands(commands, misses=3)
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "N2: FAIL (57/60" in captured.out


def test_n2a_passes_at_9_of_10_and_fails_at_8(tmp_path, capsys):
    turns = [_turn("inspect the drawer") for _ in range(10)]
    rows, labels = _rows_and_labels("observe_topup", turns)
    for index in range(1):
        labels[f"r0t{index}"]["gap_restated"] = False
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "N2a: PASS (9/10" in captured.out

    rows, labels = _rows_and_labels("observe_topup", turns)
    for index in range(2):
        labels[f"r0t{index}"]["gap_restated"] = False
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "N2a: FAIL (8/10" in captured.out


def test_n5_allows_engine_open_on_search_but_rejects_bad_labels_and_look_group(tmp_path, capsys):
    rows, labels = _rows_and_labels(
        "observe_look_inside_under",
        [_turn("search the drawer", kind="open", engine_opened=True, committed_open="open")],
    )
    labels["r0t0"]["command_opens"] = True
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "N5: PASS" in captured.out

    labels["r0t0"]["command_opens"] = False
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "N5: FAIL" in captured.out
    assert "engine_opened with command_opens false" in captured.out

    rows, labels = _rows_and_labels(
        "observe_look_inside_under",
        [_turn("inspect the drawer", kind="look", engine_opened=True)],
    )
    labels["r0t0"]["command_opens"] = True
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "N5: FAIL" in captured.out
    assert "engine_opened on look-group turn" in captured.out


def test_route_a_and_route_b_only_files_keep_old_clauses(tmp_path, capsys):
    rows, labels = _rows_and_labels("observe_topup", [_turn("feel under the drawer", kind="under")])
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "Clause 1:" in captured.out
    assert "S3 card:" in captured.out
    assert "N1:" not in captured.out

    rows, labels = _rows_and_labels("observe_under_first", [_turn("feel under the drawer", kind="under")])
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "Clause 1:" in captured.out
    assert "S3 card:" in captured.out
    assert "N1:" not in captured.out


def test_t9d_information_lines_are_printed(tmp_path, capsys):
    turns = [
        _turn("inspect the drawer", kind="look", committed_open="open", after_open="closed"),
        _turn("examine the drawer", kind="look"),
        _turn("check the drawer", kind="look"),
        _turn("search the drawer", kind="open", committed_open="open", after_open="closed"),
        _turn("look under the drawer", kind="under", narration=STATEMENT),
    ]
    rows, labels = _rows_and_labels("observe_look_inside_under", turns)
    labels["r0t4"]["card_found_in_prose"] = True
    labels["r0t4"]["gap_restated"] = False
    rows[0]["turns"][4]["places_after"] = {"memory_card": "kristin"}
    rows[0]["turns"][4]["handoff_id"] = "k_sl_1a_b_r0"
    rows[0]["turns"][0]["engine_opened"] = False
    rows[0]["turns"][3]["engine_opened"] = False
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "look-group request kinds: look=3/3, open=0/3, under=0/3" in captured.out
    assert "search request kinds: look=0/1, open=1/1, under=0/1" in captured.out
    assert "narrator-opened look-group and search turns: r0t0, r0t3" in captured.out
    assert "engine opens by command: none" in captured.out
    assert "delivered statement text in prose: 1" in captured.out


def test_command_opens_guidance_is_present():
    assert "searches it" in enforce_report.__doc__
    assert "says inside, in, into or through it" in enforce_report.__doc__
