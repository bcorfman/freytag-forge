from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from factory.checks.gap_delta import DEFAULT_ROOT
from factory.manifests import lint_check
from factory.stations.planner import PlanOutcome
from factory.stations.tree import ticket_tree
from factory.stations.wiring import wiring_handler, wiring_spec
from factory.tickets import Station, Ticket

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def beat_plan(ticket_id: str = "wire-ticket") -> dict:
    return {
        "version": 1,
        "ticket_id": ticket_id,
        "scene": "1A",
        "kind": "add_pacing_beat",
        "reason": "A concrete authored beat is needed before the scene handoff.",
        "evidence_keys": ["turn-1"],
        "beat": {
            "id": "truck_laptop_wire_1a",
            "at_turn": 10,
            "text": "Check the truck and laptop before the patrol returns to the house.",
            "verbatim": True,
            "trailing": True,
            "when": {"drawer_opened": False},
            "sets": {"drawer_opened": True},
        },
    }


def text_plan(ticket_id: str = "wire-ticket") -> dict:
    return {
        "version": 1,
        "ticket_id": ticket_id,
        "scene": "1A",
        "kind": "set_text",
        "reason": "The authored handoff should make the next move explicit.",
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
        plan = json.loads((manifest_path.parent / "plan.json").read_text(encoding="utf-8"))
        scratch = scratch_parent / "worker"
        if scratch.exists():
            shutil.rmtree(scratch)
        shutil.copytree(repository, scratch, symlinks=True)
        (scratch / ".venv").symlink_to(ROOT / ".venv")
        python = str(ROOT / ".venv" / "bin" / "python")
        commands = []
        if plan["kind"] == "add_pacing_beat":
            beat = plan["beat"]
            commands.append(
                [python, "-m", "storygame.story_cli", "new", "beat", plan["scene"], beat["id"], "--say", beat["text"]]
            )
            commands.extend(
                [
                    [python, "-m", "storygame.story_cli", "set", f"beat:{beat['id']}.at_turn", str(beat["at_turn"])],
                    [
                        python,
                        "-m",
                        "storygame.story_cli",
                        "set",
                        f"beat:{beat['id']}.when",
                        json.dumps(beat["when"]),
                    ],
                    [
                        python,
                        "-m",
                        "storygame.story_cli",
                        "set",
                        f"beat:{beat['id']}.sets",
                        json.dumps(beat["sets"]),
                    ],
                    [
                        python,
                        "-m",
                        "storygame.story_cli",
                        "set",
                        f"beat:{beat['id']}.trailing",
                        str(beat["trailing"]).lower(),
                    ],
                    [
                        python,
                        "-m",
                        "storygame.story_cli",
                        "set",
                        f"beat:{beat['id']}.say[0].verbatim",
                        str(beat["verbatim"]).lower(),
                    ],
                ]
            )
        else:
            edit = plan["set_text"]
            commands.append([python, "-m", "storygame.story_cli", "set", edit["address"], edit["text"]])
        for command in commands:
            if any(".when" in item or ".trailing" in item for item in command):
                from storygame.story_source.yamlio import dumps_document, load_document

                scene_path = scratch / "data" / "stories" / DEFAULT_ROOT.name / "source" / "scenes" / "1A.yaml"
                scene_document = load_document(scene_path)
                field = "when" if any(".when" in item for item in command) else "trailing"
                scene_document["beats"][-1][field] = plan["beat"][field]
                scene_path.write_text(dumps_document(scene_document), encoding="utf-8")
            if any(".say[0].verbatim" in item for item in command):
                from storygame.story_source.yamlio import dumps_document, load_document

                scene_path = scratch / "data" / "stories" / DEFAULT_ROOT.name / "source" / "scenes" / "1A.yaml"
                scene_document = load_document(scene_path)
                say = scene_document["beats"][-1]["say"]
                if isinstance(say, str):
                    scene_document["beats"][-1]["say"] = [{"text": say, "verbatim": False}]
                scene_path.write_text(dumps_document(scene_document), encoding="utf-8")
            from storygame import story_cli

            stdout = io.StringIO()
            stderr = io.StringIO()
            old_directory = Path.cwd()
            try:
                os.chdir(scratch)
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    status = story_cli.main(command[3:])
            finally:
                os.chdir(old_directory)
            completed = subprocess.CompletedProcess(command, status, stdout.getvalue(), stderr.getvalue())
            if completed.returncode:
                return completed
        patch = subprocess.run(["git", "diff", "--binary"], cwd=scratch, capture_output=True, check=True)
        patch_path = Path(manifest["workdir"]) / "wire.patch"
        patch_path.write_bytes(patch.stdout)
        return subprocess.CompletedProcess(command, 0, stdout="stub ringer ok", stderr="")

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
