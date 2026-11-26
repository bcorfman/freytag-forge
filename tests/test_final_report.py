import json

from factory.checks.final_report import validate_final_report

SCENES = ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C")


def good_report():
    reports = []
    for number in range(1, 13):
        scenes = []
        previous = ""
        for index, name in enumerate(SCENES):
            current = f"{number}{index}"
            scenes.append(
                {
                    "scene": name,
                    "entry": {"source": "fresh" if index == 0 else "carried", "facts_sha256": previous},
                    "exit_facts_sha256": current,
                    "transition_cause": "none" if index == 8 else "earned",
                    "turns": 1,
                    "contract": {
                        "confirmed_stuck": [],
                        "unresolved": [],
                        "provenance_flags": [],
                        "exit": "ending" if index == 8 else "earned",
                        "status": "healthy",
                        "epilogue": {"offered": index == 8, "taken": False},
                    },
                }
            )
            previous = current
        reports.append(
            {
                "replicate": number,
                "profile": "canonical",
                "status": "complete",
                "scenes": scenes,
                "ending_reached": True,
                "epilogue": {"offered": True, "taken": False},
                "continuity": {"passed": True},
                "fun": {"passed": True},
            }
        )
    return {"candidate_sha": "x", "turn_ceiling": 200, "total_turns": 108, "replicates": reports}


def test_good_report_is_valid():
    report = good_report()
    assert validate_final_report(report)["ok"]
    fixture = "tests/fixtures/final_report/good.json"
    with open(fixture) as stream:
        assert json.load(stream) == report


def test_required_problem_codes():
    mutations = {
        "failed_replicate": lambda r: r["replicates"][0].update(status="failed"),
        "partial_scenes": lambda r: r["replicates"][0]["scenes"].pop(1),
        "substituted_snapshot": lambda r: r["replicates"][0]["scenes"][1]["entry"].update(facts_sha256="bad"),
        "forced_exit": lambda r: r["replicates"][0]["scenes"][0].update(transition_cause="forced"),
        "stuck_turns": lambda r: r["replicates"][0]["scenes"][0]["contract"].update(confirmed_stuck=[1]),
        "unresolved": lambda r: r["replicates"][0]["scenes"][0]["contract"].update(unresolved=[1]),
        "false_terminal": lambda r: r["replicates"][0].update(ending_reached=False),
        "epilogue_not_offered": lambda r: r["replicates"][0]["epilogue"].update(offered=False),
        "continuity_failed": lambda r: r["replicates"][0]["continuity"].update(passed=False),
        "fun_failed": lambda r: r["replicates"][0]["fun"].update(passed=False),
        "turn_ceiling": lambda r: r.update(turn_ceiling=1),
    }
    for code, mutate in mutations.items():
        report = good_report()
        mutate(report)
        assert code in {problem["code"] for problem in validate_final_report(report)["problems"]}


def test_malformed_never_raises():
    assert "malformed" in {p["code"] for p in validate_final_report(None)["problems"]}
    assert "malformed" in {p["code"] for p in validate_final_report({"replicates": {}})["problems"]}
