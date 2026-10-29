import json

import pytest

from scripts.ringer.environment_narration import enforce_report

ROUTES = (
    "observe_supporters_1a",
    "observe_park_bench_1b",
    "observe_executive_desk_3b",
)
COMMANDS = {
    ROUTES[0]: (
        "inspect the workstation",
        "search the workstation",
        "look under the workstation",
        "examine the workstation chair",
        "check the workstation chair",
        "look under the workstation chair",
    ),
    ROUTES[1]: (
        "inspect the park bench",
        "look under the park bench",
        "search the park bench",
        "check the park bench",
        "look under the park bench",
        "inspect the storm drain",
    ),
    ROUTES[2]: (
        "inspect the executive desk",
        "search the executive desk",
        "look under the executive desk",
        "examine the executive desk",
        "check the executive desk",
        "look under the executive desk",
    ),
}


def _turn(command, *, failed=False, elapsed=1.0, engine_opened=False, rejected=False):
    narration = None if failed else "The surface is quiet and undisturbed."
    attempts = [{"accepted": not rejected, "relations": []}]
    if rejected and not failed:
        attempts.append({"accepted": True, "relations": []})
    return {
        "input": command,
        "narration": narration,
        "error": "verification exhausted" if failed else None,
        "places_before": {"marker": "surface"},
        "places_after": {"marker": "surface"},
        "narration_attempts": 2 if failed or rejected else 1,
        "verifier_requests": 1,
        "observation_enforce": {},
        "enforce_attempts": attempts,
        "provider_responses": [],
        "turn_elapsed_s": elapsed,
        "observation_request": {"kind": "under" if "under" in command else "look", "focus": "target"},
        "engine_opened": engine_opened,
    }


def _label(*, tag=None, earlier=None, presents=True, officer_quoted_gap=None):
    tags = {
        "refind": False,
        "invented_object": False,
        "leak": False,
        "wrong_custody": False,
        "unrequested_move": False,
    }
    if tag is not None:
        tags[tag] = True
    entry = {
        "presents_required": presents,
        "acceptable": True,
        "tags": tags,
        "earlier": [] if earlier is None else earlier,
        "underside_search": False,
        "card_found_in_prose": False,
        "gap_restated": False,
        "contents_shown": False,
        "command_opens": False,
    }
    if officer_quoted_gap is not None:
        entry["officer_quoted_gap"] = officer_quoted_gap
    return entry


def _rows_and_labels(route, count=20):
    commands = COMMANDS[route]
    turns = [_turn(commands[index % len(commands)]) for index in range(count)]
    rows = [{"route": route, "turns": turns}]
    labels = {f"r0t{index}": _label() for index in range(count)}
    return rows, labels


def _run(tmp_path, capsys, rows, labels):
    rows_path = tmp_path / "rows.json"
    labels_path = tmp_path / "labels.json"
    rows_path.write_text(json.dumps(rows), encoding="utf-8")
    labels_path.write_text(json.dumps(labels), encoding="utf-8")
    code = enforce_report.main(["join", str(rows_path), "--labels", str(labels_path)])
    return code, capsys.readouterr()


def _assert_gate(tmp_path, capsys, route, gate, expected, mutate):
    rows, labels = _rows_and_labels(route)
    mutate(rows, labels)
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert f"{gate}: {expected}" in captured.out


@pytest.mark.parametrize("route", ROUTES)
def test_t9h_g1_passes_and_fails(tmp_path, capsys, route):
    _assert_gate(tmp_path, capsys, route, "G1", "PASS", lambda rows, labels: None)

    def fail(rows, labels):
        for index in (0, 1):
            rows[0]["turns"][index]["narration"] = None
            rows[0]["turns"][index]["error"] = "verification exhausted"

    _assert_gate(tmp_path, capsys, route, "G1", "FAIL", fail)


@pytest.mark.parametrize("route", ROUTES)
def test_t9h_g2_passes_and_fails(tmp_path, capsys, route):
    _assert_gate(tmp_path, capsys, route, "G2", "PASS", lambda rows, labels: None)

    def fail(rows, labels):
        labels["r0t0"]["presents_required"] = False

    _assert_gate(tmp_path, capsys, route, "G2", "FAIL", fail)


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("tag", ("leak", "wrong_custody", "unrequested_move", "refind", "invented_object"))
def test_t9h_g3_passes_and_fails_at_each_limit(tmp_path, capsys, route, tag):
    _assert_gate(tmp_path, capsys, route, "G3", "PASS", lambda rows, labels: None)

    def fail(rows, labels):
        labels["r0t0"]["tags"][tag] = True
        labels["r0t1"]["tags"][tag] = True
        if tag in ("leak", "wrong_custody", "unrequested_move"):
            labels["r0t1"]["tags"][tag] = False
            labels["r0t2"]["tags"][tag] = True

    _assert_gate(tmp_path, capsys, route, "G3", "FAIL", fail)


@pytest.mark.parametrize("route", ROUTES)
def test_t9h_g4_passes_and_fails(tmp_path, capsys, route):
    _assert_gate(tmp_path, capsys, route, "G4", "PASS", lambda rows, labels: None)

    def fail(rows, labels):
        rows[0]["turns"][0]["narration"] = None
        rows[0]["turns"][0]["error"] = "verification exhausted"
        rows[0]["turns"][0]["places_after"] = {"marker": "moved"}

    _assert_gate(tmp_path, capsys, route, "G4", "FAIL", fail)


@pytest.mark.parametrize("route", ROUTES)
def test_t9h_g5_passes_and_fails(tmp_path, capsys, route):
    _assert_gate(tmp_path, capsys, route, "G5", "PASS", lambda rows, labels: None)

    def fail(rows, labels):
        rows[0]["turns"][0]["narration_attempts"] = 3

    _assert_gate(tmp_path, capsys, route, "G5", "FAIL", fail)


@pytest.mark.parametrize("route", ROUTES)
def test_t9h_g6_passes_and_fails(tmp_path, capsys, route):
    _assert_gate(tmp_path, capsys, route, "G6", "PASS", lambda rows, labels: None)

    def fail(rows, labels):
        for turn in rows[0]["turns"]:
            turn["turn_elapsed_s"] = 11.0

    _assert_gate(tmp_path, capsys, route, "G6", "FAIL", fail)


@pytest.mark.parametrize("route", ROUTES)
def test_t9h_g7_passes_and_fails(tmp_path, capsys, route):
    def pass_case(rows, labels):
        for index in range(5):
            turn = rows[0]["turns"][index]
            turn["enforce_attempts"] = [{"accepted": False, "relations": []}, {"accepted": True}]
            turn["narration_attempts"] = 2
            labels[f"r0t{index}"]["earlier"] = [index != 0]

    _assert_gate(tmp_path, capsys, route, "G7", "PASS", pass_case)

    def fail_case(rows, labels):
        pass_case(rows, labels)
        labels["r0t1"]["earlier"] = [False]

    _assert_gate(tmp_path, capsys, route, "G7", "FAIL", fail_case)


@pytest.mark.parametrize("route", ROUTES)
def test_t9h_g8_passes_and_fails(tmp_path, capsys, route):
    _assert_gate(tmp_path, capsys, route, "G8", "PASS", lambda rows, labels: None)

    def fail(rows, labels):
        rows[0]["turns"][0]["engine_opened"] = True

    _assert_gate(tmp_path, capsys, route, "G8", "FAIL", fail)


def test_t9h_g9_passes_and_fails_and_is_na_on_other_routes(tmp_path, capsys):
    _assert_gate(tmp_path, capsys, ROUTES[1], "G9", "PASS", lambda rows, labels: None)

    def fail(rows, labels):
        rows[0]["turns"][5]["engine_opened"] = True
        labels["r0t5"]["tags"]["invented_object"] = True

    _assert_gate(tmp_path, capsys, ROUTES[1], "G9", "FAIL", fail)
    _assert_gate(tmp_path, capsys, ROUTES[0], "G9", "n/a", lambda rows, labels: None)


def test_t9h_g10_pass_fail_and_inconclusive(tmp_path, capsys):
    rows, labels = _rows_and_labels(ROUTES[0], 1)
    rows.append({"route": "observe_look_inside_under", "turns": [_turn("inspect the drawer")]})
    labels["r1t0"] = _label(officer_quoted_gap=False)
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "G10: PASS" in captured.out

    labels["r1t0"]["officer_quoted_gap"] = True
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "G10: FAIL" in captured.out

    labels["r1t0"].pop("officer_quoted_gap")
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "G10: INCONCLUSIVE" in captured.out


def test_t9h_g10_is_na_on_non_route_c(tmp_path, capsys):
    rows, labels = _rows_and_labels(ROUTES[0], 1)
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "G10: n/a" in captured.out


def test_t9h_labels_template_and_sheet_are_route_aware(tmp_path, capsys):
    rows, _ = _rows_and_labels(ROUTES[0], 1)
    rows.append({"route": "observe_look_inside_under", "turns": [_turn("inspect the drawer")]})
    template_path = tmp_path / "rows.json"
    template_path.write_text(json.dumps(rows), encoding="utf-8")

    assert enforce_report.main(["labels-template", str(template_path)]) == 0
    template = json.loads(capsys.readouterr().out)
    assert "officer_quoted_gap" not in template["r0t0"]
    assert template["r1t0"]["officer_quoted_gap"] is None

    new_route_path = tmp_path / "new-route-rows.json"
    new_route_path.write_text(json.dumps(rows[:1]), encoding="utf-8")
    assert enforce_report.main(["sheet", str(new_route_path)]) == 0
    sheet = capsys.readouterr().out
    assert "drawer" not in sheet


def test_t9h_prints_command_kind_distribution_and_engine_count(tmp_path, capsys):
    rows, labels = _rows_and_labels(ROUTES[0], 2)
    rows[0]["turns"][0]["engine_opened"] = True
    code, captured = _run(tmp_path, capsys, rows, labels)
    assert code == 0
    assert "request kinds by command (observe_supporters_1a):" in captured.out
    assert "inspect the workstation: look=1" in captured.out
    assert "engine_opened count (observe_supporters_1a): 1" in captured.out
