from scripts.ringer.environment_narration import enforce_report


def _turn(command, elapsed, call_timings_marker):
    turn = {
        "input": command,
        "narration": "The marker rests on the shelf.",
        "error": None,
        "narration_attempts": 1,
        "verifier_requests": 1,
        "observation_enforce": {},
        "enforce_attempts": [{"accepted": True, "relations": []}],
        "turn_elapsed_s": elapsed,
    }
    if call_timings_marker is not None:
        turn["call_timings"] = call_timings_marker
    return turn


def _labels(rows):
    labels = {}
    for turn_index, _turn_value in enumerate(rows[0]["turns"]):
        labels[f"r0t{turn_index}"] = {
            "presents_required": True,
            "acceptable": True,
            "tags": {
                "refind": False,
                "invented_object": False,
                "leak": False,
                "wrong_custody": False,
                "unrequested_move": False,
            },
            "earlier": [],
        }
    return labels


def _report(rows):
    report, missing = enforce_report._join(rows, _labels(rows))
    assert missing == []
    return report


def _timing(kind, elapsed, keys=None, status=200):
    return {
        "kind": kind,
        "elapsed_s": elapsed,
        "status": status,
        "keys": [] if keys is None else keys,
    }


def _timed_rows():
    return [
        {
            "route": "observe_topup",
            "turns": [
                _turn(
                    "command 0",
                    3.0,
                    [_timing("jev", 0.4, ["a", "b"]), _timing("narration", 1.0), _timing("worker", 0.2, status=204)],
                ),
                _turn(
                    "command 1",
                    5.0,
                    [
                        _timing("jev", 2.0, ["c"]),
                        _timing("jev", 0.5, ["d", "e"]),
                        _timing("narration", 1.5),
                        _timing("worker", 0.5),
                    ],
                ),
                _turn(
                    "command 2",
                    2.5,
                    [
                        _timing("jev", 0.3, ["f"]),
                        _timing("narration", 0.7),
                        _timing("worker", 0.1),
                        _timing("worker", 0.2),
                    ],
                ),
                _turn(
                    "command 3",
                    8.0,
                    [_timing("jev", 3.0, ["slow"]), _timing("narration", 2.0), _timing("worker", 0.5)],
                ),
                _turn(
                    "command 4",
                    4.0,
                    [_timing("jev", 1.2, ["g"]), _timing("narration", 0.8), _timing("worker", 0.4)],
                ),
                _turn(
                    "command 5",
                    1.5,
                    [_timing("jev", 0.1, ["h"]), _timing("narration", 0.4), _timing("worker", 0.1)],
                ),
            ],
        }
    ]


def test_call_timing_block_reports_route_counts_percentiles_and_slowest_calls():
    report = _report(_timed_rows())

    expected = [
        "call timing (turns with call_timings: 6 of 6):",
        "  jev calls: n=7, per turn mean 1.167, call p50 0.500, p95 3.000, max 3.000; per turn sum mean 1.250",
        "  narration calls: n=6, per turn mean 1.000, call p50 0.800, p95 2.000, max 2.000; per turn sum mean 1.067",
        "  worker calls: n=7, per turn mean 1.167, call p50 0.200, p95 0.500, max 0.500; per turn sum mean 0.333",
        "  turn time outside calls (engine and waiting): mean 1.350",
        "  slowest 5 turns:",
        "    r0t3 | command 3 | total 8.000 | jev 3.000 | narration 2.000 | worker 0.500 | narration attempts 1",
        "    r0t1 | command 1 | total 5.000 | jev 2.500 | narration 1.500 | worker 0.500 | narration attempts 1",
        "    r0t4 | command 4 | total 4.000 | jev 1.200 | narration 0.800 | worker 0.400 | narration attempts 1",
        "    r0t0 | command 0 | total 3.000 | jev 0.400 | narration 1.000 | worker 0.200 | narration attempts 1",
        "    r0t2 | command 2 | total 2.500 | jev 0.300 | narration 0.700 | worker 0.300 | narration attempts 1",
        "  slowest 5 jev calls:",
        "    r0t3 | slow | 3.000",
        "    r0t1 | c | 2.000",
        "    r0t4 | g | 1.200",
        "    r0t1 | d+e | 0.500",
        "    r0t0 | a+b | 0.400",
    ]
    start = report.index("call timing (turns with call_timings:")
    end = report.index("enforcement screen:", start)
    assert report[start:end].strip().splitlines() == expected


def test_rows_without_call_timings_print_one_na_line():
    rows = [{"route": "observe_topup", "turns": [_turn("command", 1.0, None)]}]

    report = _report(rows)

    assert "call timing: n/a (rows have no call_timings)" in report
    assert "call timing (turns with call_timings:" not in report
    assert "Clause 1:" in report
    assert "enforcement screen:" in report


def test_call_timings_do_not_change_clause_or_screen_statuses():
    rows = _timed_rows()
    turns_without_timings = [
        {key: value for key, value in turn.items() if key != "call_timings"} for turn in rows[0]["turns"]
    ]
    without_timings = [{**rows[0], "turns": turns_without_timings}]

    with_report = _report(rows)
    without_report = _report(without_timings)
    status_prefixes = ("Clause ", "S1 ", "S2 ", "S3 ", "N", "enforcement screen:", "t9b screen:")
    with_statuses = [line for line in with_report.splitlines() if line.startswith(status_prefixes)]
    without_statuses = [line for line in without_report.splitlines() if line.startswith(status_prefixes)]

    assert with_statuses == without_statuses


def test_malformed_call_timings_do_not_raise():
    rows = [
        {
            "route": "observe_topup",
            "turns": [
                _turn("bad list", 2.0, {"kind": "jev"}),
                _turn("bad entries", 2.0, [{}, {"kind": "jev"}, {"elapsed_s": "slow"}, None]),
            ],
        }
    ]

    report = _report(rows)

    assert "call timing (turns with call_timings: 1 of 2):" in report
