from __future__ import annotations

import difflib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from factory.checks.gap_delta import DEFAULT_ROOT
from factory.manifests import lint_check
from factory.stations.planner import PlanOutcome
from factory.stations.tree import ticket_tree
from factory.stations.wiring import (
    FUN_CHECK_LABEL,
    MAX_REPLANS,
    PROBE_CHECK_LABEL,
    _clear_previous,
    beat_position_error,
    wiring_handler,
    wiring_spec,
)
from factory.tickets import Station, Ticket
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def beat_plan(ticket_id: str = "wire-ticket") -> dict:
    return {
        "version": 1,
        "ticket_id": ticket_id,
        "scene": "1A",
        "kind": "add_pacing_beat",
        "reason": "Precedent: fact-gated pacing beat; a concrete authored beat is needed before the scene handoff.",
        "evidence_keys": ["turn-1"],
        "beat": {
            "id": "truck_laptop_wire_1a",
            "at_turn": 12,
            "text": "Check the truck and laptop before the patrol returns to the house.",
            "verbatim": True,
            "trailing": True,
            "when": {"drawer_opened": False},
            "sets": {"architects_strategy_known": True},
        },
    }


def text_plan(ticket_id: str = "wire-ticket") -> dict:
    return {
        "version": 1,
        "ticket_id": ticket_id,
        "scene": "1A",
        "kind": "set_text",
        "reason": "Precedent: concise handoff wording; the authored handoff should make the next move explicit.",
        "evidence_keys": ["turn-1"],
        "set_text": {
            "address": "claim:k_sl_1a_b_r1.text",
            "text": (
                "The card holds Michelle's saved files and a damaged recording. The recording warns, "
                '"Do not trust the emergency broadcasts." The files name the Continuity Initiative and '
                "point to a dead drop at a bench in the park. The handoff now points toward the waiting vehicle."
            ),
        },
    }


def pacing_event(event_id: str, at_turn: int, scene_id: str = "1A") -> SimpleNamespace:
    return SimpleNamespace(id=event_id, scene_id=scene_id, at_turn=at_turn)


def make_ticket(plan: dict, workspace: Path, ticket_id: str = "wire-ticket") -> Ticket:
    return Ticket(
        id=ticket_id,
        scene="1A",
        station=Station.WIRING,
        token_budget=1000,
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
        payload={
            "plan": plan,
            "workspace": str(workspace),
            "failing_turns": [{"key": "turn-1", "scene": "1A"}],
        },
    )


def test_beat_position_error_places_a_beat_before_the_first_later_turn_event() -> None:
    events = [pacing_event("early", 3), pacing_event("new", 9), pacing_event("later", 10), pacing_event("old", 8)]

    assert beat_position_error(events, "new", "1A") is None


def test_beat_position_error_rejects_a_beat_appended_after_a_later_turn_event() -> None:
    events = [pacing_event("later", 10), pacing_event("new", 9)]

    error = beat_position_error(events, "new", "1A")

    assert error is not None
    assert "beat new (turn 9)" in error
    assert "event later (turn 10)" in error


def test_beat_position_error_uses_the_end_when_no_later_turn_event_exists() -> None:
    earlier_position = [pacing_event("new", 9), pacing_event("early", 8)]
    end_position = [pacing_event("early", 8), pacing_event("new", 9)]

    error = beat_position_error(earlier_position, "new", "1A")

    assert error is not None
    assert "at the end" in error
    assert "position 1" in error
    assert beat_position_error(end_position, "new", "1A") is None


def test_beat_position_error_ignores_events_from_other_scenes() -> None:
    events = [
        pacing_event("early", 3),
        pacing_event("other-scene", 99, scene_id="2A"),
        pacing_event("new", 9),
        pacing_event("later", 10),
    ]

    assert beat_position_error(events, "new", "1A") is None


def test_beat_position_error_reports_a_missing_beat() -> None:
    error = beat_position_error([pacing_event("other", 3)], "missing", "1A")

    assert error == "beat missing is missing from scene 1A"


def test_wiring_spec_add_beat_includes_position_rule_and_other_specs_are_unchanged() -> None:
    beat_text = wiring_spec(beat_plan(), "data/stories/continuity-initiative")
    assert "first other event in this scene whose at_turn is greater than the new beat's" in beat_text
    assert "The CLI appends a new beat at the end" in beat_text
    assert "move only the beat record" in beat_text

    claim_plan = {
        "version": 1,
        "ticket_id": "wire-ticket",
        "scene": "1A",
        "kind": "edit_claim_evidence",
        "reason": "Add one reviewed phrase.",
        "evidence_keys": ["turn-1"],
        "claim_edit": {"claim_id": "claim-1", "group": 0, "phrase": "the phrase"},
    }
    claim_text = wiring_spec(claim_plan, "data/stories/continuity-initiative")
    assert claim_text.endswith(
        "HOW:\n"
        "Use the story CLI from the repository root, reading every value from plan.json: `"
        ".venv/bin/python -m storygame.story_cli set claim:<id>.action_evidence[<group>] --add "
        "'<yaml string of the phrase>'`.\n"
        "Use claim_edit.claim_id, claim_edit.group, and claim_edit.phrase exactly as written. If the CLI refuses,\n"
        "make the smallest hand edit in the owned match file. Preserve every other record and file. The authoritative\n"
        "story root is data/stories/continuity-initiative.\n"
    )

    text_spec = wiring_spec(text_plan(), "data/stories/continuity-initiative")
    assert text_spec.endswith(
        """HOW:
Use the story CLI from the repository root, reading the address and replacement text from
plan.json: `.venv/bin/python -m storygame.story_cli set <address> <text>`.
Copy the text character for character; never re-word it. If the CLI refuses, make the
smallest hand edit necessary. Preserve every other record and file. The authoritative story
root is data/stories/continuity-initiative.\n"""
    )


def test_beat_position_error_matches_the_real_compiled_scene_order() -> None:
    package = load_story_package(DEFAULT_ROOT)
    scene_events = [event for event in package.pacing.events if getattr(event, "scene_id", None) == "1A"]
    first_later = next(event for event in scene_events if getattr(event, "at_turn", None) > 9)
    fake_beat = pacing_event("wire_position_probe_1a", 9)
    insert_at = next(index for index, event in enumerate(scene_events) if event.at_turn > fake_beat.at_turn)

    inserted = [*scene_events]
    inserted.insert(insert_at, fake_beat)
    assert beat_position_error(inserted, fake_beat.id, "1A") is None

    appended = [*scene_events, fake_beat]
    error = beat_position_error(appended, fake_beat.id, "1A")
    assert error is not None
    assert first_later.id in error
    assert f"(turn {first_later.at_turn})" in error


def init_repo(tmp_path: Path) -> Path:
    repository = tmp_path / "repo"
    story = repository / "data" / "stories" / DEFAULT_ROOT.name
    story.parent.mkdir(parents=True)
    shutil.copytree(DEFAULT_ROOT, story)
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "Factory Test"], cwd=repository, check=True)
    subprocess.run(["git", "add", "data"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "seed story"], cwd=repository, check=True)
    return repository


def stub_ringer(repository: Path, scratch_parent: Path):
    def run(manifest_path: Path, _ringer_path: Path) -> subprocess.CompletedProcess:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        relative_scene = Path("data") / "stories" / DEFAULT_ROOT.name / "source" / "scenes" / "1A.yaml"
        scene_path = repository / relative_scene
        original = scene_path.read_text(encoding="utf-8")
        updated = original + ("\n" if not original.endswith("\n") else "") + "# stub ringer patch\n"
        patch = "".join(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile=f"a/{relative_scene}",
                tofile=f"b/{relative_scene}",
            )
        ).encode()
        patch_path = Path(manifest["workdir"]) / "wire.patch"
        patch_path.write_bytes(patch)
        return subprocess.CompletedProcess([], 0, stdout="stub ringer ok", stderr="")

    return run


def test_wiring_spec_and_manifest_are_complete_for_both_kinds(tmp_path: Path) -> None:
    for plan in (beat_plan(), text_plan()):
        text = wiring_spec(plan, "data/stories/continuity-initiative")
        assert json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) in text
        assert "ROLE AND BOUNDARY" in text
        assert "never re-word" in text or plan["kind"] == "add_pacing_beat"

        result = wiring_handler(ROOT, run_ringer=lambda *_: subprocess.CompletedProcess([], 1, "stop", ""))(
            make_ticket(plan, tmp_path), NOW
        )
        assert not result.passed
        manifest_path = tmp_path / "wire-ticket" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        task = manifest["tasks"][0]
        assert task["ownership"] == [
            "data/stories/continuity-initiative/source/scenes/1A.yaml",
            "data/stories/continuity-initiative/source/scenes/1A.match.yaml",
        ]
        assert "memory_card_recovered" not in task["check"]
        if plan["kind"] == "set_text":
            assert plan["set_text"]["text"] not in task["check"]
        assert lint_check(task["check"]) == []


def test_lint_failure_creates_nothing(tmp_path: Path) -> None:
    plan = beat_plan()
    plan["reason"] = ""
    workspace = tmp_path / "workspace"
    result = wiring_handler(ROOT, run_ringer=lambda *_: (_ for _ in ()).throw(AssertionError("not called")))(
        make_ticket(plan, workspace), NOW
    )
    assert result.output.startswith("plan.reason reason must be non-blank and at most 400 characters")
    assert not workspace.exists()


def test_wiring_happy_path_for_both_kinds_and_ticket_tree(tmp_path: Path) -> None:
    repository = init_repo(tmp_path)
    for index, plan in enumerate(beat_plan(f"wire-{index}") for index in range(2)):
        if index == 1:
            plan = text_plan("wire-text")
        workspace = tmp_path / f"workspace-{index}"
        ticket_id = plan["ticket_id"]
        handler = wiring_handler(repository, run_ringer=stub_ringer(repository, tmp_path / f"scratch-{index}"))
        result = handler(make_ticket(plan, workspace, ticket_id), NOW)
        assert result.passed, result.output
        tree = ticket_tree({"workspace": str(workspace)}, ticket_id, repository)
        assert tree == workspace / ticket_id / "tree"
        assert (tree / ".venv").is_symlink()
        assert (tree / "data/stories/continuity-initiative/source/scenes/1A.yaml").is_file()


def test_wiring_plans_missing_payload_plan_and_preserves_ticket(tmp_path: Path) -> None:
    repository = init_repo(tmp_path)
    workspace = tmp_path / "workspace"
    plan = beat_plan("planner-wiring")
    ticket = make_ticket(plan, workspace, "planner-wiring")
    original_payload = dict(ticket.payload)
    del ticket.payload["plan"]
    calls = []

    def planner(received_ticket, package, now):
        calls.append((received_ticket, package, now))
        return PlanOutcome(plan, 23, [], 1)

    result = wiring_handler(
        repository,
        run_ringer=stub_ringer(repository, tmp_path / "scratch-planner"),
        planner=planner,
    )(ticket, NOW)

    assert result.passed, result.output
    assert result.tokens == 23
    assert len(calls) == 1
    assert ticket.payload == {key: value for key, value in original_payload.items() if key != "plan"}
    assert json.loads((workspace / "planner-wiring" / "plan.json").read_text(encoding="utf-8")) == plan


def test_wiring_probe_retry_passes_verdict_feedback_only_to_first_planner_call(tmp_path: Path) -> None:
    repository = init_repo(tmp_path)
    workspace = tmp_path / "workspace"
    feedback_plan = beat_plan("probe-feedback")
    ticket = make_ticket(feedback_plan, workspace, "probe-feedback")
    del ticket.payload["plan"]
    ticket.payload["feedback_plan"] = feedback_plan
    ticket.payload["probe_feedback"] = "verdict reject control 1 2 0 0 0 0 candidate 2 2 0 0 0 0"
    calls = []

    def planner(_ticket, _package, _now, **kwargs):
        calls.append(kwargs)
        return PlanOutcome(feedback_plan, 7, [], 1)

    result = wiring_handler(
        repository,
        run_ringer=stub_ringer(repository, tmp_path / "scratch-probe-feedback"),
        planner=planner,
    )(ticket, NOW)

    assert result.passed, result.output
    assert calls == [
        {
            "feedback_plan": feedback_plan,
            "check_output": ticket.payload["probe_feedback"],
            "check_label": PROBE_CHECK_LABEL,
        }
    ]


def test_wiring_fun_retry_passes_story_editor_feedback_to_planner(tmp_path: Path) -> None:
    assert FUN_CHECK_LABEL == (
        "Fun review feedback (this plan was applied and the story editor blocked it; its failed checks, reasons and "
        "fun_advice follow):"
    )
    repository = init_repo(tmp_path)
    workspace = tmp_path / "workspace"
    feedback_plan = beat_plan("fun-feedback")
    ticket = make_ticket(feedback_plan, workspace, "fun-feedback")
    del ticket.payload["plan"]
    ticket.payload["feedback_plan"] = feedback_plan
    ticket.payload["fun_feedback"] = "Add a small payoff that gives the player a memorable reason to act."
    calls = []

    def planner(_ticket, _package, _now, **kwargs):
        calls.append(kwargs)
        return PlanOutcome(feedback_plan, 7, [], 1)

    result = wiring_handler(
        repository,
        run_ringer=stub_ringer(repository, tmp_path / "scratch-fun-feedback"),
        planner=planner,
    )(ticket, NOW)

    assert result.passed, result.output
    assert calls == [
        {
            "feedback_plan": feedback_plan,
            "check_output": ticket.payload["fun_feedback"],
            "check_label": FUN_CHECK_LABEL,
        }
    ]


def test_wiring_planner_failure_creates_no_tree(tmp_path: Path) -> None:
    repository = init_repo(tmp_path)
    workspace = tmp_path / "workspace"
    ticket = make_ticket(beat_plan(), workspace)
    del ticket.payload["plan"]

    def planner(_ticket, _package, _now):
        return PlanOutcome(None, 17, ["first problem", "second problem"], 3)

    result = wiring_handler(repository, planner=planner)(ticket, NOW)

    assert not result.passed
    assert result.output == "first problem\nsecond problem"
    assert result.tokens == 17
    assert not workspace.exists()


def test_wiring_with_existing_plan_never_calls_planner(tmp_path: Path) -> None:
    repository = init_repo(tmp_path)
    called = False

    def planner(_ticket, _package, _now):
        nonlocal called
        called = True
        raise AssertionError("planner must not run for an existing plan")

    result = wiring_handler(
        repository,
        run_ringer=stub_ringer(repository, tmp_path / "scratch-existing"),
        planner=planner,
    )(make_ticket(beat_plan(), tmp_path / "workspace"), NOW)

    assert result.passed, result.output
    assert not called


def test_wiring_replans_after_check_failure_and_sums_tokens(tmp_path: Path) -> None:
    repository = init_repo(tmp_path)
    workspace = tmp_path / "workspace"
    ticket = make_ticket(beat_plan("first-plan"), workspace, "replan-success")
    del ticket.payload["plan"]
    first_plan = beat_plan("first-plan")
    second_plan = text_plan("second-plan")
    planner_calls = []
    manifests = []
    plans = [first_plan, second_plan]

    def planner(received_ticket, package, now, **kwargs):
        planner_calls.append((received_ticket, package, now, kwargs))
        return PlanOutcome(plans.pop(0), 10 if len(planner_calls) == 1 else 20, [], 1)

    def ringer(manifest_path: Path, _ringer_path: Path) -> subprocess.CompletedProcess:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifests.append(manifest)
        workdir = Path(manifest["workdir"])
        if len(manifests) == 1:
            return subprocess.CompletedProcess([], 3, "CHECK FAILED: first plan was rejected", "")
        (workdir / "wire.patch").write_text("not applied by this stub\n", encoding="utf-8")
        return subprocess.CompletedProcess([], 0, "check passed", "")

    def fake_git(command: list[str], **_kwargs) -> subprocess.CompletedProcess:
        if command[1:3] == ["worktree", "add"]:
            Path(command[-2]).mkdir(parents=True, exist_ok=True)
        return subprocess.CompletedProcess(command, 0, "", "")

    original_payload = dict(ticket.payload)
    result = wiring_handler(repository, run_ringer=ringer, run=fake_git, planner=planner)(ticket, NOW)

    assert result.passed, result.output
    assert result.tokens == 30
    assert len(planner_calls) == 2
    assert planner_calls[0][3] == {}
    assert planner_calls[1][3]["feedback_plan"] == first_plan
    assert "CHECK FAILED: first plan was rejected" in planner_calls[1][3]["check_output"]
    assert json.loads((workspace / "replan-success" / "plan.json").read_text(encoding="utf-8")) == second_plan
    assert manifests[0]["tasks"][0]["max_attempts"] == 1
    assert manifests[1]["tasks"][0]["max_attempts"] == 1
    assert ticket.payload == original_payload


def test_wiring_replans_three_times_then_returns_last_check_output(tmp_path: Path) -> None:
    repository = init_repo(tmp_path)
    workspace = tmp_path / "workspace"
    ticket = make_ticket(beat_plan(), workspace, "replan-failure")
    del ticket.payload["plan"]
    planner_calls = []
    ringer_calls = []

    def planner(_ticket, _package, _now, **kwargs):
        planner_calls.append(kwargs)
        return PlanOutcome(beat_plan(f"plan-{len(planner_calls)}"), 1, [], 1)

    def ringer(_manifest_path: Path, _ringer_path: Path) -> subprocess.CompletedProcess:
        ringer_calls.append(True)
        return subprocess.CompletedProcess([], 7, f"last check output {len(ringer_calls)}", "")

    result = wiring_handler(repository, run_ringer=ringer, planner=planner)(ticket, NOW)

    assert not result.passed
    assert len(ringer_calls) == MAX_REPLANS
    assert len(planner_calls) == MAX_REPLANS
    assert result.output == "last check output 3"
    assert result.tokens == MAX_REPLANS


def test_wiring_payload_plan_keeps_one_round_and_two_worker_attempts(tmp_path: Path) -> None:
    repository = init_repo(tmp_path)
    manifests = []
    planner_called = False

    def planner(*_args, **_kwargs):
        nonlocal planner_called
        planner_called = True
        raise AssertionError("planner must not run for a payload plan")

    def ringer(manifest_path: Path, _ringer_path: Path) -> subprocess.CompletedProcess:
        manifests.append(json.loads(manifest_path.read_text(encoding="utf-8")))
        return subprocess.CompletedProcess([], 4, "payload check failed", "")

    result = wiring_handler(repository, run_ringer=ringer, planner=planner)(
        make_ticket(beat_plan(), tmp_path / "workspace", "payload-failure"), NOW
    )

    assert not result.passed
    assert len(manifests) == 1
    assert manifests[0]["tasks"][0]["max_attempts"] == 2
    assert not planner_called


def test_wiring_stops_when_second_plan_fails_lint(tmp_path: Path) -> None:
    repository = init_repo(tmp_path)
    workspace = tmp_path / "workspace"
    ticket = make_ticket(beat_plan(), workspace, "replan-lint-failure")
    del ticket.payload["plan"]
    planner_calls = []
    ringer_calls = []
    invalid_plan = text_plan("invalid-second-plan")
    invalid_plan["set_text"]["text"] = "too short"

    def planner(_ticket, _package, _now, **kwargs):
        planner_calls.append(kwargs)
        if len(planner_calls) == 1:
            return PlanOutcome(beat_plan("first-plan"), 3, [], 1)
        return PlanOutcome(invalid_plan, 5, [], 1)

    def ringer(_manifest_path: Path, _ringer_path: Path) -> subprocess.CompletedProcess:
        ringer_calls.append(True)
        return subprocess.CompletedProcess([], 3, "check failed before replan", "")

    result = wiring_handler(repository, run_ringer=ringer, planner=planner)(ticket, NOW)

    assert not result.passed
    assert "plan.text replacement text violates the bounded authored-text rules" in result.output
    assert len(ringer_calls) == 1
    assert len(planner_calls) == 2
    assert result.tokens == 8


def test_wiring_rejects_ringer_failure_empty_patch_and_bad_patch(tmp_path: Path) -> None:
    repository = ROOT
    plan = text_plan()
    workspace = tmp_path / "workspace"

    def failed(_manifest: Path, _ringer: Path) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess([], 3, "worker failed", "stderr")

    result = wiring_handler(repository, run_ringer=failed)(make_ticket(plan, workspace), NOW)
    assert not result.passed and "worker failed" in result.output

    def empty(manifest: Path, _ringer: Path) -> subprocess.CompletedProcess:
        Path(json.loads(manifest.read_text())["workdir"]).mkdir(parents=True, exist_ok=True)
        return subprocess.CompletedProcess([], 0, "", "")

    result = wiring_handler(repository, run_ringer=empty)(make_ticket(plan, workspace), NOW)
    assert not result.passed and "empty patch" in result.output

    def bad(manifest: Path, _ringer: Path) -> subprocess.CompletedProcess:
        patch_path = Path(json.loads(manifest.read_text())["workdir"]) / "wire.patch"
        patch_path.parent.mkdir(parents=True, exist_ok=True)
        patch_path.write_text("not a patch\n", encoding="utf-8")
        return subprocess.CompletedProcess([], 0, "", "")

    def fake_git(command: list[str], **_kwargs) -> subprocess.CompletedProcess:
        if command[1:3] == ["worktree", "add"]:
            Path(command[-2]).mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[1:2] == ["apply"]:
            return subprocess.CompletedProcess(command, 1, "", "patch failed")
        return subprocess.CompletedProcess(command, 0, "", "")

    result = wiring_handler(repository, run_ringer=bad, run=fake_git)(make_ticket(plan, workspace), NOW)
    assert not result.passed and "patch" in result.output


def test_wiring_rerun_removes_the_previous_tree(tmp_path: Path) -> None:
    repository = init_repo(tmp_path)
    plan = text_plan("rerun")
    workspace = tmp_path / "workspace"

    def rerun_runner(manifest: Path, _ringer: Path) -> subprocess.CompletedProcess:
        scratch = tmp_path / "rerun-scratch"
        if scratch.exists():
            shutil.rmtree(scratch)
        shutil.copytree(repository, scratch, symlinks=True)
        source_path = scratch / "data/stories/continuity-initiative/source/scenes/1A.yaml"
        source_path.write_text(source_path.read_text(encoding="utf-8") + "\n# rerun\n", encoding="utf-8")
        patch = subprocess.run(["git", "diff", "--binary"], cwd=scratch, capture_output=True, check=True)
        patch_path = Path(json.loads(manifest.read_text(encoding="utf-8"))["workdir"]) / "wire.patch"
        patch_path.parent.mkdir(parents=True, exist_ok=True)
        patch_path.write_bytes(patch.stdout)
        return subprocess.CompletedProcess([], 0, "", "")

    handler = wiring_handler(repository, run_ringer=rerun_runner)
    ticket = make_ticket(plan, workspace, "rerun")
    assert handler(ticket, NOW).passed
    assert handler(ticket, NOW).passed
    assert {path.name for path in (workspace / "rerun").iterdir()} == {"tree", "manifest.json", "plan.json", "ringer"}
    assert (workspace / "rerun" / "tree").is_dir()
    assert (workspace / "rerun" / "ringer" / "wire.patch").is_file()
    assert len(list(workspace.glob("rerun/tree"))) == 1


def test_wiring_cleanup_prunes_leftover_ringer_worktree(tmp_path: Path) -> None:
    repository = init_repo(tmp_path)
    ticket_dir = tmp_path / "workspace" / "leftover"
    ringer_worktree = ticket_dir / "ringer" / "wire"
    ringer_worktree.parent.mkdir(parents=True)
    added = subprocess.run(
        ["git", "worktree", "add", "--detach", str(ringer_worktree), "HEAD"],
        cwd=repository,
        capture_output=True,
        text=True,
    )
    assert added.returncode == 0, added.stderr

    assert _clear_previous(repository, ticket_dir, subprocess.run) is None
    registrations = subprocess.run(
        ["git", "worktree", "list", "--porcelain"], cwd=repository, check=True, capture_output=True, text=True
    ).stdout
    assert str(ringer_worktree) not in registrations
    second = subprocess.run(
        ["git", "worktree", "add", "--detach", str(ringer_worktree), "HEAD"],
        cwd=repository,
        capture_output=True,
        text=True,
    )
    assert second.returncode == 0, second.stderr


def test_ticket_tree_rejects_missing_or_outside_workspaces(tmp_path: Path) -> None:
    repository = ROOT
    assert ticket_tree({}, "ticket", repository) is None
    assert ticket_tree({"workspace": str(tmp_path / "missing")}, "ticket", repository) is None
    workspace = tmp_path / "workspace"
    tree_holder = workspace / "ticket"
    tree_holder.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (tree_holder / "tree").symlink_to(outside, target_is_directory=True)
    assert ticket_tree({"workspace": str(workspace)}, "ticket", repository) is None
