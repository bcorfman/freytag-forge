import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from factory.guard import LimitSleep
from factory.outcome_contract import classify_run
from factory.stations import probe
from factory.stations.probe import (
    PROBE_RULES,
    build_variation,
    judge_probe,
    probe_handler,
    projected_cost_usd,
    runs_from_report,
    summarize_arm,
)
from factory.tickets import Station, Ticket

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/factory/probe_turn_records.json"
OUTCOME_CONTRACT_FIXTURE = ROOT / "tests/fixtures/outcome_contract/cases.json"
NOW = datetime(2026, 11, 22, 12, tzinfo=UTC)
RULES = {**PROBE_RULES, "replicates": 2}
BUDGET = {"day": "2026-11-22", "spent_micro_usd": 100}


def make_ticket(payload: dict, *, scene: str = "synthetic") -> Ticket:
    return Ticket(
        id="probe-ticket",
        scene=scene,
        station=Station.PROBE,
        token_budget=100,
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
        payload=payload,
    )


def report_run(replicate: int, inputs: list[str], scene: str = "synthetic") -> dict:
    return {
        "replicate": replicate,
        "scenes": [
            {
                "scene": scene,
                "turns": [{"turn": index + 1, "raw_input": value} for index, value in enumerate(inputs)],
            }
        ],
    }


def test_runs_from_report_uses_typed_inputs_and_caps() -> None:
    long_inputs = [f"Inspect item {index}." for index in range(35)]
    report = {
        "replicates": [
            report_run(1, ["Inspect the shelf."]),
            report_run(2, long_inputs),
            report_run(3, ["Open the drawer.", "Read the label."]),
            report_run(4, ["Check the window.", "Cross the threshold."]),
            report_run(5, ["Search the cabinet.", "Leave the room."]),
        ]
    }

    runs = runs_from_report(report, "synthetic")

    assert [run["run"] for run in runs] == ["synthetic-r2", "synthetic-r3", "synthetic-r4"]
    assert len(runs[0]["inputs"]) == PROBE_RULES["max_turns_per_run"]
    assert runs[0]["inputs"][0] == "Inspect item 0."


def test_projected_cost_usd_sums_turns_across_runs() -> None:
    rate = 0.0015
    runs = [
        {"inputs": ["Inspect the shelf."] * 16},
        {"inputs": ["Inspect the shelf."] * 13},
        {"inputs": ["Inspect the shelf."] * 15},
    ]

    assert projected_cost_usd(runs, 3, {"estimated_usd_per_turn": rate}) == pytest.approx(0.396)


def test_projected_cost_usd_single_run() -> None:
    rate = 0.0015

    assert projected_cost_usd(
        [{"inputs": ["Inspect the shelf."] * 10}], 1, {"estimated_usd_per_turn": rate}
    ) == pytest.approx(2 * 10 * rate)


def test_projected_cost_usd_empty_runs() -> None:
    assert projected_cost_usd([], 3, {"estimated_usd_per_turn": 0.0015}) == 0


def test_build_variation_is_story_package_only_and_bench_describes(tmp_path: Path) -> None:
    run = {"run": "synthetic-r1", "scene": "synthetic", "inputs": ["Inspect the shelf.", "Open the drawer."]}
    control = build_variation(
        name="control",
        package_path=str(ROOT / "data/stories/continuity-initiative"),
        scene="synthetic",
        run=run,
    )
    candidate = build_variation(
        name="candidate",
        package_path=str(ROOT / "data/stories/continuity-initiative"),
        scene="synthetic",
        run=run,
    )
    candidate["story_package"] = str(tmp_path / "candidate")
    path = tmp_path / "variation.json"
    path.write_text(json.dumps(control), encoding="utf-8")

    completed = subprocess.run(
        [
            ".venv/bin/python",
            "-m",
            "bench",
            "describe",
            "--variation",
            str(path),
            "--json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["name"] == "control"
    assert control["canon_judge"] is False
    assert control["story_package"].startswith("/")
    assert {key: control[key] for key in control if key not in {"name", "story_package"}} == {
        key: candidate[key] for key in candidate if key not in {"name", "story_package"}
    }


def test_summarize_arm_counts_fixture_and_rejects_malformed(tmp_path: Path) -> None:
    summary = summarize_arm([FIXTURE])

    assert summary == {
        "replicates": 2,
        "failed_replicates": 0,
        "turns": 8,
        "stuck_turns": 1,
        "rejected_turns": 0,
        "game_breaks": 0,
        "earned_exits": 0,
        "forced_exits": 0,
        "unknown_exits": 2,
        "provider_features": None,
        "semantic_ask_missing": False,
        "unresolved_turns": 0,
        "contract_runs": 0,
        "raw_runs": 2,
    }

    extra = {
        "runs": [
            {
                "status": "completed",
                "completed": True,
                "turns": [
                    {"turn_number": 1, "rejected": True, "game_break": {}, "left_scene": False},
                    {
                        "turn_number": 2,
                        "selected_knowledge_ids": ["k"],
                        "left_scene": True,
                        "transition_cause": "timer",
                    },
                ],
            },
            {"status": "failed", "completed": False, "turns": []},
        ]
    }
    extra_path = tmp_path / "extra.json"
    extra_path.write_text(json.dumps(extra), encoding="utf-8")
    assert summarize_arm([extra_path]) == {
        "replicates": 1,
        "failed_replicates": 1,
        "turns": 3,
        "stuck_turns": 0,
        "rejected_turns": 1,
        "game_breaks": 1,
        "earned_exits": 0,
        "forced_exits": 1,
        "unknown_exits": 0,
        "provider_features": None,
        "semantic_ask_missing": False,
        "unresolved_turns": 0,
        "contract_runs": 0,
        "raw_runs": 1,
    }

    malformed = tmp_path / "malformed.json"
    malformed.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match=str(malformed)):
        summarize_arm([malformed])


def test_probe_matches_outcome_contract_fixture_cases(tmp_path: Path) -> None:
    cases = json.loads(OUTCOME_CONTRACT_FIXTURE.read_text(encoding="utf-8"))
    covered = []
    summaries = []
    for case in cases:
        expected = case.get("expected", {})
        run = case.get("run", {})
        scene = case.get("scene", {})
        if not isinstance(run, dict) or not isinstance(scene, dict):
            continue
        # Older fixture cases omit empty outcome lists; those mean no marked turns.
        expected = {
            **expected,
            "confirmed_stuck": expected.get("confirmed_stuck", []),
            "unresolved": expected.get("unresolved", []),
        }
        if not isinstance(expected["confirmed_stuck"], list) or not isinstance(expected["unresolved"], list):
            continue
        direct = classify_run(run, scene)
        if any(turn.get("action_outcome") == "unknown_telemetry" for turn in direct["turns"]):
            continue
        case_id = case["id"]
        scene_id = scene["id"]
        probe_run = {**run, "scene": scene_id, "status": "ok"}
        records_path = tmp_path / f"{case_id}.json"
        records_path.write_text(json.dumps({"runs": [probe_run]}), encoding="utf-8")
        summaries.append(summarize_arm([records_path], scenes={scene_id: scene}))
        covered.append((case_id, direct, expected))

    assert len(covered) >= 20, f"expected at least 20 parity cases, covered {len(covered)}"
    assert sum(summary["contract_runs"] for summary in summaries) == len(covered)
    assert sum(summary["raw_runs"] for summary in summaries) == 0
    assert sum(summary["stuck_turns"] for summary in summaries) == sum(
        len(expected["confirmed_stuck"]) for _, _, expected in covered
    )
    assert sum(summary["unresolved_turns"] for summary in summaries) == sum(
        len(expected["unresolved"]) for _, _, expected in covered
    )
    for case_id, direct, expected in covered:
        assert direct["confirmed_stuck"] == expected["confirmed_stuck"], case_id
        assert direct["unresolved"] == expected["unresolved"], case_id


def base_summary(**changes: int) -> dict:
    value = {
        "replicates": 10,
        "failed_replicates": 0,
        "turns": 10,
        "stuck_turns": 0,
        "rejected_turns": 0,
        "game_breaks": 0,
        "earned_exits": 10,
        "forced_exits": 0,
        "unknown_exits": 0,
        "provider_features": None,
        "semantic_ask_missing": False,
    }
    value.update(changes)
    return value


def test_judge_probe_all_branches_and_ratio_boundary() -> None:
    control = base_summary(stuck_turns=10)
    candidate = base_summary(stuck_turns=0)
    assert judge_probe(control, candidate, PROBE_RULES)["verdict"] == "keep"

    assert judge_probe(base_summary(stuck_turns=0), candidate, PROBE_RULES)["verdict"] == "inconclusive"
    assert judge_probe(base_summary(replicates=0), candidate, PROBE_RULES)["verdict"] == "inconclusive"
    assert judge_probe(control, base_summary(stuck_turns=9), PROBE_RULES)["verdict"] == "reject"
    assert judge_probe(control, base_summary(rejected_turns=1), PROBE_RULES)["verdict"] == "reject"
    assert judge_probe(control, base_summary(game_breaks=1), PROBE_RULES)["verdict"] == "reject"
    assert judge_probe(control, base_summary(earned_exits=9), PROBE_RULES)["verdict"] == "reject"
    assert judge_probe(control, base_summary(stuck_turns=8), PROBE_RULES)["verdict"] == "keep"


def test_summarize_arm_counts_failed_run_without_its_turns(tmp_path: Path) -> None:
    path = tmp_path / "failed.json"
    path.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "status": "failed",
                        "completed": False,
                        "turns": [
                            {
                                "rejected": False,
                                "selected_knowledge_ids": [],
                                "left_scene": True,
                                "game_break": {},
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert summarize_arm([path]) == {
        "replicates": 0,
        "failed_replicates": 1,
        "turns": 0,
        "stuck_turns": 0,
        "rejected_turns": 0,
        "game_breaks": 0,
        "earned_exits": 0,
        "forced_exits": 0,
        "unknown_exits": 0,
        "provider_features": None,
        "semantic_ask_missing": False,
        "unresolved_turns": 0,
        "contract_runs": 0,
        "raw_runs": 0,
    }


def test_failed_replicates_force_inconclusive_before_comparison() -> None:
    control = base_summary(stuck_turns=10)
    candidate = base_summary(failed_replicates=1, stuck_turns=0)

    result = judge_probe(control, candidate, PROBE_RULES)

    assert result["verdict"] == "inconclusive"
    assert result["reasons"] == ["Failed replicates: control 0, candidate 1."]
    assert result["control"]["failed_replicates"] == 0
    assert result["candidate"]["failed_replicates"] == 1


def test_all_ok_summary_exposes_zero_failed_replicates(tmp_path: Path) -> None:
    path = tmp_path / "ok.json"
    path.write_text(
        json.dumps({"runs": [{"status": "ok", "completed": True, "turns": []}]}),
        encoding="utf-8",
    )

    assert summarize_arm([path])["failed_replicates"] == 0


def test_summarize_arm_classifies_exit_causes_and_old_records(tmp_path: Path) -> None:
    records = {
        "runs": [
            {
                "status": "completed",
                "completed": True,
                "turns": [
                    {
                        "turn_number": 1,
                        "left_scene": True,
                        "transition_cause": cause,
                        **({} if cause is not None else {}),
                    }
                ],
            }
            for cause in ("earned", "timer", "forced", None)
        ]
    }
    for run, cause in zip(records["runs"], ("earned", "timer", "forced", None), strict=True):
        if cause is None:
            run["turns"][0].pop("transition_cause")
    path = tmp_path / "causes.json"
    path.write_text(json.dumps(records), encoding="utf-8")

    summary = summarize_arm([path])

    assert summary["earned_exits"] == 1
    assert summary["forced_exits"] == 2
    assert summary["unknown_exits"] == 1

    old_path = tmp_path / "old.json"
    old_path.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "status": "ok",
                        "completed": True,
                        "turns": [{"turn_number": 1, "left_scene": True}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    old_summary = summarize_arm([old_path])
    assert old_summary["earned_exits"] == 0
    assert old_summary["unknown_exits"] == 1


def test_probe_result_marks_incomplete_exit_and_missing_semantic_evidence() -> None:
    control = base_summary(unknown_exits=1, semantic_ask_missing=True)
    candidate = base_summary()

    result = judge_probe(control, candidate, PROBE_RULES)

    assert result["exit_evidence"] == "incomplete"
    assert result["semantic_ask_missing"] is True
    assert result["verdict"] == "inconclusive"


def configure_probe_root(tmp_path: Path) -> tuple[Path, Path]:
    (tmp_path / "factory/config").mkdir(parents=True)
    (tmp_path / "factory/state").mkdir(parents=True)
    config = {
        "caps": {
            "total_budget_usd": 1.0,
            "daily_cap_usd": {"openai": 1.0, "cloudflare": 1.0},
            "call_caps": [],
            "rate_window_s": 3600,
            "rate_max_usd": 1.0,
        },
        "paths": {"ledger": "factory/state/ledger.jsonl"},
    }
    (tmp_path / "factory/config/factory.json").write_text(json.dumps(config), encoding="utf-8")
    tree = tmp_path / "tree"
    package = tree / "data/stories/base"
    package.mkdir(parents=True)
    (package / "package.txt").write_bytes(b"base")
    (tmp_path / "data/stories/base").mkdir(parents=True)
    return tmp_path, tree


def make_runner(calls: list[list[str]], records: Path = FIXTURE):
    def run(root: Path, argv: list[str], env: dict[str, str], timeout_s: int):
        calls.append(argv)
        out = Path(argv[argv.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "turn-records.json").write_text(records.read_text(encoding="utf-8"), encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    return run


@pytest.mark.parametrize("text", ['{"quota": null}', "prose mentions QUOTA", '{"quota_label": "QUOTA"}'])
def test_probe_quota_null_or_unstructured_signal_does_not_sleep(text: str) -> None:
    probe._raise_probe_quota(text, NOW)


def test_probe_quota_non_null_summary_sleeps() -> None:
    with pytest.raises(LimitSleep) as raised:
        probe._raise_probe_quota('{"quota": {"error": "AI_DAILY_BUDGET_EXCEEDED"}}', NOW)
    assert raised.value.provider == "cloudflare"


@pytest.mark.parametrize("marker", ["AI_QUOTA_EXCEEDED", "AI_DAILY_BUDGET_EXCEEDED", "HTTP 429"])
def test_probe_quota_provider_markers_still_sleep(marker: str) -> None:
    with pytest.raises(LimitSleep) as raised:
        probe._raise_probe_quota(marker, NOW)
    assert raised.value.provider == "cloudflare"


def test_handler_unreadable_budget_refuses_before_runner(tmp_path: Path, monkeypatch) -> None:
    root, tree = configure_probe_root(tmp_path)
    monkeypatch.setattr(probe, "ticket_tree", lambda payload, ticket_id, root: tree)
    payload = {
        "workspace": str(tmp_path),
        "story_package": "data/stories/base",
        "runs": [{"run": "synthetic-r1", "scene": "synthetic", "inputs": ["Inspect the shelf.", "Open the drawer."]}],
        "billed_run_approved": True,
    }
    calls: list[list[str]] = []

    result = probe_handler(root, runner=make_runner(calls), rules=RULES, read_budget=lambda: None)(
        make_ticket(payload), NOW
    )

    assert result.output == "cannot read the Worker budget: set CLOUDFLARE_WORKER_URL and CLOUDFLARE_WORKER_TOKEN"
    assert calls == []
    assert not (root / "factory/state/staged_run.lock").exists()
    assert not (tmp_path / "probe-ticket/probe").exists()


def test_handler_failures_happen_before_runner_and_payload_stays_unchanged(tmp_path: Path, monkeypatch) -> None:
    calls: list[list[str]] = []
    handler = probe_handler(tmp_path, runner=make_runner(calls), rules=RULES, read_budget=lambda: None)
    assert handler(make_ticket({}), NOW).output == "missing payload key: runs"
    assert handler(make_ticket({"runs": []}), NOW).output == "no recorded runs to replay for scene synthetic"
    monkeypatch.setattr(probe, "ticket_tree", lambda payload, ticket_id, root: None)
    payload = {
        "runs": [{"run": "synthetic-r1", "scene": "synthetic", "inputs": ["Inspect the shelf.", "Open the drawer."]}]
    }
    assert handler(make_ticket(payload), NOW).output == "no ticket tree to probe"
    monkeypatch.setattr(probe, "ticket_tree", lambda payload, ticket_id, root: tmp_path / "tree")
    assert handler(make_ticket(payload), NOW).output == "probe not approved: set billed_run_approved"
    assert calls == []
    assert payload == {
        "runs": [{"run": "synthetic-r1", "scene": "synthetic", "inputs": ["Inspect the shelf.", "Open the drawer."]}]
    }


def test_handler_staged_lock_and_spend_cap_block_runner(tmp_path: Path, monkeypatch) -> None:
    root, tree = configure_probe_root(tmp_path)
    monkeypatch.setattr(probe, "ticket_tree", lambda payload, ticket_id, root: tree)
    payload = {
        "workspace": str(tmp_path),
        "story_package": "data/stories/base",
        "runs": [
            {
                "run": "synthetic-r1",
                "scene": "synthetic",
                "inputs": [f"Inspect item {index}." for index in range(40)],
            },
            {
                "run": "synthetic-r2",
                "scene": "synthetic",
                "inputs": [f"Inspect item {index}." for index in range(45)],
            },
            {
                "run": "synthetic-r3",
                "scene": "synthetic",
                "inputs": [f"Inspect item {index}." for index in range(45)],
            },
        ],
        "billed_run_approved": True,
    }
    calls: list[list[str]] = []
    lock = root / "factory/state/staged_run.lock"
    lock.write_text("active", encoding="utf-8")
    assert (
        probe_handler(root, runner=make_runner(calls), rules=RULES, read_budget=lambda: None)(
            make_ticket(payload), NOW
        ).output
        == "a staged run is in progress"
    )
    lock.unlink()
    config_path = root / "factory/config/factory.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["caps"]["daily_cap_usd"]["cloudflare"] = 1.0
    config_path.write_text(json.dumps(config), encoding="utf-8")
    ledger = root / "factory/state/ledger.jsonl"
    ledger.write_text(
        json.dumps(
            {
                "at": NOW.isoformat(),
                "provider": "cloudflare",
                "model_id": "workers-ai",
                "station": "old",
                "scene": "synthetic",
                "ticket_id": "old",
                "tokens": 0,
                "usd": 0.25,
                "cost_kind": "dollars",
                "limits": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = probe_handler(
        root,
        runner=make_runner(calls),
        rules=RULES,
        read_budget=lambda: dict(BUDGET),
    )(make_ticket(payload), NOW)
    assert not result.passed
    assert result.output == "projected probe cost $0.7800 is above the remaining budget"
    assert calls == []


def test_handler_full_path_reuses_hashes_and_records_spend(tmp_path: Path, monkeypatch) -> None:
    root, tree = configure_probe_root(tmp_path)
    monkeypatch.setattr(probe, "ticket_tree", lambda payload, ticket_id, root: tree)
    payload = {
        "workspace": str(tmp_path),
        "story_package": "data/stories/base",
        "runs": [
            {
                "run": "synthetic-r1",
                "scene": "synthetic",
                "inputs": ["Inspect the shelf."] * 16,
            },
            {
                "run": "synthetic-r2",
                "scene": "synthetic",
                "inputs": ["Inspect the shelf."] * 13,
            },
            {
                "run": "synthetic-r3",
                "scene": "synthetic",
                "inputs": ["Inspect the shelf."] * 15,
            },
        ],
        "billed_run_approved": True,
    }
    calls: list[list[str]] = []

    def improved_runner(root: Path, argv: list[str], env: dict[str, str], timeout_s: int):
        calls.append(argv)
        out = Path(argv[argv.index("--out") + 1])
        out.mkdir(parents=True)
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        if len(calls) == 2:
            for run in value["runs"]:
                for turn in run["turns"]:
                    if turn["turn_number"] == 2:
                        turn["selected_knowledge_ids"] = ["fixed"]
        (out / "turn-records.json").write_text(json.dumps(value), encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    budgets = iter([{"day": "2026-11-22", "spent_micro_usd": 100}, {"day": "2026-11-22", "spent_micro_usd": 125}])
    handler = probe_handler(root, runner=improved_runner, rules=RULES, read_budget=lambda: next(budgets))
    original = dict(payload)
    result = handler(make_ticket(payload), NOW)
    assert not result.passed
    assert result.payload_updates["probe"]["feedback"].startswith("verdict inconclusive")
    assert result.payload_updates["probe"]["exit_evidence"] == "incomplete"
    assert result.payload_updates["billed_run_approved"] is False
    assert result.payload_updates["billed_runs_consumed"] == 1
    assert "Inspect the shelf" not in result.payload_updates["probe"]["feedback"]
    assert len(calls) == 6
    assert (tmp_path / "probe-ticket/probe/control-synthetic-r1.json").is_file()
    assert payload == original
    ledger_rows = [json.loads(line) for line in (root / "factory/state/ledger.jsonl").read_text().splitlines()]
    assert len(ledger_rows) == 1
    assert ledger_rows[0]["station"] == "probe"
    assert ledger_rows[0]["provider"] == "cloudflare"
    expected_estimate = projected_cost_usd(payload["runs"], RULES["replicates"], RULES)
    assert expected_estimate == pytest.approx(0.264)
    assert ledger_rows[0]["estimate_usd"] == expected_estimate
    budget_reads: list[bool] = []

    def saved_budget_reader() -> dict | None:
        budget_reads.append(True)
        return None

    saved_handler = probe_handler(root, runner=make_runner(calls), rules=RULES, read_budget=saved_budget_reader)
    saved = saved_handler(make_ticket(payload), NOW)
    assert not saved.passed
    assert len(calls) == 6
    assert budget_reads == []
    (tree / "data/stories/base/package.txt").write_bytes(b"changed")
    budgets = iter([dict(BUDGET), dict(BUDGET)])
    changed = probe_handler(root, runner=make_runner(calls), rules=RULES, read_budget=lambda: next(budgets))
    changed(make_ticket(payload), NOW)
    assert len(calls) == 12


def test_handler_summarizes_each_arm_with_its_story_scene(tmp_path: Path, monkeypatch) -> None:
    root, tree = configure_probe_root(tmp_path)
    monkeypatch.setattr(probe, "ticket_tree", lambda payload, ticket_id, root: tree)
    payload = {
        "workspace": str(tmp_path),
        "story_package": "data/stories/base",
        "runs": [{"run": "synthetic-r1", "scene": "S", "inputs": ["Open the door."] * 2}],
        "billed_run_approved": True,
    }
    package_paths: list[Path] = []
    scenes_by_path = {}

    def load(package_path: Path):
        package_paths.append(package_path)
        return package_path

    monkeypatch.setattr(probe, "load_story_package", load)
    monkeypatch.setattr(
        probe,
        "build_contract_scene",
        lambda package, scene: scenes_by_path.setdefault(package, {"id": str(package)}),
    )
    captured: list[dict | None] = []
    original_summarize = probe.summarize_arm

    def summarize(files, *, scenes=None):
        captured.append(scenes)
        return original_summarize(files, scenes=scenes)

    monkeypatch.setattr(probe, "summarize_arm", summarize)
    result = probe_handler(root, runner=make_runner([]), rules=RULES, read_budget=lambda: dict(BUDGET))(
        make_ticket(payload, scene="S"), NOW
    )

    assert result.payload_updates is not None
    assert package_paths == [Path(tmp_path / "data/stories/base"), Path(tree / "data/stories/base")]
    assert captured == [
        {"S": {"id": str(package_paths[0])}},
        {"S": {"id": str(package_paths[1])}},
    ]


def test_handler_scene_loading_falls_back_per_arm(tmp_path: Path, monkeypatch) -> None:
    root, tree = configure_probe_root(tmp_path)
    monkeypatch.setattr(probe, "ticket_tree", lambda payload, ticket_id, root: tree)
    payload = {
        "workspace": str(tmp_path),
        "story_package": "data/stories/base",
        "runs": [{"run": "synthetic-r1", "scene": "S", "inputs": ["Open the door."] * 2}],
        "billed_run_approved": True,
    }
    case = json.loads(OUTCOME_CONTRACT_FIXTURE.read_text(encoding="utf-8"))[0]
    records = {"runs": [{**case["run"], "scene": "S", "status": "ok", "completed": True}]}

    def runner(root: Path, argv: list[str], env: dict[str, str], timeout_s: int):
        output = Path(argv[argv.index("--out") + 1])
        output.mkdir(parents=True, exist_ok=True)
        (output / "turn-records.json").write_text(json.dumps(records), encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    def load(package_path: Path):
        if package_path == Path(tmp_path / "data/stories/base"):
            raise ValueError("control package unavailable")
        return package_path

    monkeypatch.setattr(probe, "load_story_package", load)
    monkeypatch.setattr(probe, "build_contract_scene", lambda package, scene: case["scene"])
    captured: list[dict | None] = []
    original_summarize = probe.summarize_arm

    def summarize(files, *, scenes=None):
        captured.append(scenes)
        return original_summarize(files, scenes=scenes)

    monkeypatch.setattr(probe, "summarize_arm", summarize)
    result = probe_handler(root, runner=runner, rules=RULES, read_budget=lambda: dict(BUDGET))(
        make_ticket(payload, scene="S"), NOW
    )

    assert captured[0] is None
    assert captured[1] == {"S": case["scene"]}
    assert result.payload_updates is not None
    assert result.payload_updates["probe"]["verdict"] == "inconclusive"
    assert "different evidence" in result.payload_updates["probe"]["reasons"][0]


def test_handler_resumes_after_limit_sleep_and_reuses_completed_outputs(tmp_path: Path, monkeypatch) -> None:
    root, tree = configure_probe_root(tmp_path)
    monkeypatch.setattr(probe, "ticket_tree", lambda payload, ticket_id, root: tree)
    payload = {
        "workspace": str(tmp_path),
        "story_package": "data/stories/base",
        "runs": [
            {"run": "synthetic-r1", "scene": "synthetic", "inputs": ["Inspect the shelf."] * 2},
            {"run": "synthetic-r2", "scene": "synthetic", "inputs": ["Open the drawer."] * 2},
        ],
        "billed_run_approved": True,
        "billed_run_approval_id": "approval-1",
    }
    calls: list[list[str]] = []

    def flaky_runner(root: Path, argv: list[str], env: dict[str, str], timeout_s: int):
        calls.append(argv)
        if len(calls) == 2:
            raise LimitSleep("cloudflare", NOW)
        out = Path(argv[argv.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "turn-records.json").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    budgets = iter(
        [
            {"day": "2026-11-22", "spent_micro_usd": 100},
            {"day": "2026-11-22", "spent_micro_usd": 125},
            {"day": "2026-11-22", "spent_micro_usd": 125},
            {"day": "2026-11-22", "spent_micro_usd": 175},
        ]
    )
    handler = probe_handler(root, runner=flaky_runner, rules=RULES, read_budget=lambda: next(budgets))

    with pytest.raises(LimitSleep):
        handler(make_ticket(payload), NOW)

    attempt_path = tmp_path / "probe-ticket/probe-attempt.json"
    assert json.loads(attempt_path.read_text(encoding="utf-8"))["resumes"] == 0

    resumed = handler(make_ticket(payload), NOW)

    assert resumed.payload_updates is not None
    assert "probe" in resumed.payload_updates
    assert len(calls) == 5
    output_names = [Path(argv[argv.index("--out") + 1]).name for argv in calls]
    assert output_names.count("control-synthetic-r1") == 1
    assert not attempt_path.exists()
    ledger_rows = [json.loads(line) for line in (root / "factory/state/ledger.jsonl").read_text().splitlines()]
    assert sum(row["usd"] for row in ledger_rows) == pytest.approx(75 / 1_000_000)


def test_handler_resume_requires_standing_approval_and_preserves_attempt(tmp_path: Path, monkeypatch) -> None:
    root, tree = configure_probe_root(tmp_path)
    monkeypatch.setattr(probe, "ticket_tree", lambda payload, ticket_id, root: tree)
    payload = {
        "workspace": str(tmp_path),
        "story_package": "data/stories/base",
        "runs": [{"run": "synthetic-r1", "scene": "synthetic", "inputs": ["Inspect the shelf."] * 2}],
        "billed_run_approved": True,
        "billed_run_approval_id": "approval-1",
    }
    calls: list[list[str]] = []

    def sleeping_runner(root: Path, argv: list[str], env: dict[str, str], timeout_s: int):
        calls.append(argv)
        out = Path(argv[argv.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "turn-records.json").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        if len(calls) == 1:
            raise LimitSleep("cloudflare", NOW)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    handler = probe_handler(root, runner=sleeping_runner, rules=RULES, read_budget=lambda: dict(BUDGET))

    with pytest.raises(LimitSleep):
        handler(make_ticket(payload), NOW)

    attempt_path = tmp_path / "probe-ticket/probe-attempt.json"
    arm_output = tmp_path / "probe-ticket/probe/control-synthetic-r1/turn-records.json"
    assert attempt_path.exists()
    assert arm_output.exists()

    payload["billed_run_approved"] = False
    refused = handler(make_ticket(payload), NOW)

    assert not refused.passed
    assert refused.output == "probe not approved: set billed_run_approved"
    assert len(calls) == 1
    assert attempt_path.exists()
    assert arm_output.exists()

    payload["billed_run_approved"] = True
    resumed = handler(make_ticket(payload), NOW)

    assert resumed.output.startswith("inconclusive:")
    assert len(calls) == 2
    assert not attempt_path.exists()


def test_handler_refuses_a_third_resume_without_runner_call(tmp_path: Path, monkeypatch) -> None:
    root, tree = configure_probe_root(tmp_path)
    monkeypatch.setattr(probe, "ticket_tree", lambda payload, ticket_id, root: tree)
    payload = {
        "workspace": str(tmp_path),
        "story_package": "data/stories/base",
        "runs": [{"run": "synthetic-r1", "scene": "synthetic", "inputs": ["Inspect the shelf."] * 2}],
        "billed_run_approved": True,
        "billed_run_approval_id": "approval-1",
    }
    calls: list[list[str]] = []

    def sleeping_runner(root: Path, argv: list[str], env: dict[str, str], timeout_s: int):
        calls.append(argv)
        raise LimitSleep("cloudflare", NOW)

    handler = probe_handler(root, runner=sleeping_runner, rules=RULES, read_budget=lambda: dict(BUDGET))
    for _ in range(3):
        with pytest.raises(LimitSleep):
            handler(make_ticket(payload), NOW)

    refused = handler(make_ticket(payload), NOW)

    assert not refused.passed
    assert "maximum 2 resumes" in refused.output
    assert len(calls) == 3
    assert json.loads((tmp_path / "probe-ticket/probe-attempt.json").read_text())["resumes"] == 2


def test_handler_changed_input_after_sleep_requires_fresh_approval(tmp_path: Path, monkeypatch) -> None:
    root, tree = configure_probe_root(tmp_path)
    monkeypatch.setattr(probe, "ticket_tree", lambda payload, ticket_id, root: tree)
    payload = {
        "workspace": str(tmp_path),
        "story_package": "data/stories/base",
        "runs": [{"run": "synthetic-r1", "scene": "synthetic", "inputs": ["Inspect the shelf."] * 2}],
        "billed_run_approved": True,
        "billed_run_approval_id": "approval-1",
    }
    calls: list[list[str]] = []

    def sleeping_runner(root: Path, argv: list[str], env: dict[str, str], timeout_s: int):
        calls.append(argv)
        raise LimitSleep("cloudflare", NOW)

    handler = probe_handler(root, runner=sleeping_runner, rules=RULES, read_budget=lambda: dict(BUDGET))
    with pytest.raises(LimitSleep):
        handler(make_ticket(payload), NOW)

    payload["runs"] = [
        {"run": "synthetic-r1", "scene": "synthetic", "inputs": ["Inspect the shelf."] * 3},
    ]
    payload.update(
        {
            "billed_runs_consumed": 1,
            "billed_run_consumed_approval_id": "approval-1",
        }
    )
    refused = probe_handler(root, runner=make_runner(calls), rules=RULES, read_budget=lambda: dict(BUDGET))(
        make_ticket(payload), NOW
    )

    assert not refused.passed
    assert "approval already consumed" in refused.output
    assert len(calls) == 1


def test_handler_unknown_spend_and_runner_errors_do_not_save(tmp_path: Path, monkeypatch) -> None:
    root, tree = configure_probe_root(tmp_path)
    monkeypatch.setattr(probe, "ticket_tree", lambda payload, ticket_id, root: tree)
    payload = {
        "workspace": str(tmp_path),
        "story_package": "data/stories/base",
        "runs": [{"run": "synthetic-r1", "scene": "synthetic", "inputs": ["Inspect the shelf.", "Open the drawer."]}],
        "billed_run_approved": True,
    }

    def failed(root, argv, env, timeout_s):
        return subprocess.CompletedProcess(argv, 7, stdout="", stderr="failure detail" * 100)

    budgets = iter([dict(BUDGET), None])
    result = probe_handler(root, runner=failed, rules=RULES, read_budget=lambda: next(budgets))(
        make_ticket(payload), NOW
    )
    assert not result.passed
    assert "failure detail" in result.output
    assert not (tmp_path / "probe-ticket/probe.json").exists()
    row = json.loads((root / "factory/state/ledger.jsonl").read_text().splitlines()[0])
    assert row["station"] == "probe" and row["cost_kind"] == "unknown"

    def quota(root, argv, env, timeout_s):
        return subprocess.CompletedProcess(
            argv, 1, stdout=json.dumps({"quota": {"error": "AI_QUOTA_EXCEEDED"}}), stderr=""
        )

    with pytest.raises(LimitSleep) as raised:
        probe_handler(
            root,
            runner=quota,
            rules=RULES,
            read_budget=lambda: dict(BUDGET),
        )(make_ticket(payload), NOW)
    assert raised.value.provider == "cloudflare"


def test_billed_approval_is_single_use_and_ceiling_blocks_runner(tmp_path: Path, monkeypatch) -> None:
    root, tree = configure_probe_root(tmp_path)
    monkeypatch.setattr(probe, "ticket_tree", lambda payload, ticket_id, root: tree)
    payload = {
        "workspace": str(tmp_path),
        "story_package": "data/stories/base",
        "runs": [{"run": "synthetic-r1", "scene": "synthetic", "inputs": ["Inspect the shelf."] * 2}],
        "billed_run_approved": True,
    }
    calls: list[list[str]] = []
    handler = probe_handler(root, runner=make_runner(calls), rules=RULES, read_budget=lambda: dict(BUDGET))

    first = handler(make_ticket(payload), NOW)
    assert len(calls) == 2
    payload.update(first.payload_updates or {})
    payload["billed_run_approved"] = True

    refused = handler(make_ticket(payload), NOW)
    assert not refused.passed
    assert "approval already consumed" in refused.output
    assert len(calls) == 2

    ceiling_payload = {
        **payload,
        "workspace": str(tmp_path / "ceiling"),
        "billed_run_approved": True,
        "billed_runs_consumed": 0,
        "billed_usd_ceiling": 0.001,
    }
    ceiling_calls: list[list[str]] = []
    ceiling_result = probe_handler(
        root,
        runner=make_runner(ceiling_calls),
        rules=RULES,
        read_budget=lambda: dict(BUDGET),
    )(make_ticket(ceiling_payload), NOW)
    assert not ceiling_result.passed
    assert "billed_usd_ceiling" in ceiling_result.output
    assert ceiling_calls == []


def test_probe_module_is_story_agnostic_and_rules_have_exact_keys() -> None:
    assert set(json.loads((ROOT / "factory/config/probe_rules.json").read_text())) == {
        "replicates",
        "max_stuck_ratio",
        "min_control_stuck_turns",
        "estimated_usd_per_turn",
        "max_runs_per_probe",
        "max_turns_per_run",
    }
    source = (ROOT / "factory/stations/probe.py").read_text(encoding="utf-8").lower()
    assert "michelle" not in source
    assert "kitchen" not in source
    assert "continuity-initiative" not in source
