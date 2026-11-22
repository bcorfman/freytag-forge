"""Run the deterministic station-4 worker and apply its checked patch."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from factory.checks.gap_delta import DEFAULT_ROOT
from factory.followups import _safe_id
from factory.line import StationHandler, StationResult
from factory.manifests import TaskSpec, build_manifest, write_manifest
from storygame.story_package.loader import load_story_package

from .fix_plan import lint_plan


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _story_root(repository_root: Path) -> Path:
    try:
        relative = DEFAULT_ROOT.resolve().relative_to(_repository_root().resolve())
    except ValueError:
        relative = Path("data") / "stories" / DEFAULT_ROOT.name
    return repository_root / relative


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _tail(value: object, limit: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    return str(value)[-limit:].strip()


def _output(completed: object) -> str:
    return "".join(
        str(value) for value in (getattr(completed, "stdout", None), getattr(completed, "stderr", None)) if value
    )


def _quote(value: str | Path) -> str:
    return shlex.quote(str(value))


def wiring_spec(plan: dict, story_root_relative: str | Path) -> str:
    """Build the self-contained, story-neutral worker brief for one plan."""

    plan_json = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True)
    scene = plan.get("scene", "<scene from plan.json>")
    if plan.get("kind") == "add_pacing_beat":
        how = f"""HOW:
Use the story CLI from the repository root and read every value from plan.json. First run
`.venv/bin/python -m storygame.story_cli new beat {scene} <id> --say '<text>'`, then use
`.venv/bin/python -m storygame.story_cli set beat:<id>.at_turn <at_turn>`,
`.venv/bin/python -m storygame.story_cli set beat:<id>.when '<when mapping>'`,
`.venv/bin/python -m storygame.story_cli set beat:<id>.sets '<sets mapping>'`,
`.venv/bin/python -m storygame.story_cli set beat:<id>.trailing <trailing>`, and
`.venv/bin/python -m storygame.story_cli set beat:<id>.say[0].verbatim <verbatim>`.
The exact address forms come from storygame/story_cmds/cmd_new.py and cmd_set.py. If the
CLI refuses a field, make the smallest hand edit necessary. Preserve every other record and
file. The authoritative story root is {story_root_relative}."""
    else:
        how = f"""HOW:
Use the story CLI from the repository root, reading the address and replacement text from
plan.json: `.venv/bin/python -m storygame.story_cli set <address> <text>`.
Copy the text character for character; never re-word it. If the CLI refuses, make the
smallest hand edit necessary. Preserve every other record and file. The authoritative story
root is {story_root_relative}."""
    return f"""ROLE AND BOUNDARY:
You are the wiring worker. Apply exactly one already-approved story fix to the two owned
source files for one scene. Never edit tests, Python code, generated files, another scene,
or any other record. Never commit and never use a model or the network. The handler's
plan.json (one directory above the task workdir) is authoritative; the JSON below is a
readable copy of the same plan. Read the file rather than putting story text into a shell
command.

REASON AND EXACT FIELDS:
```json
{plan_json}
```

{how}
"""


def _check_extra(plan_path: Path, story_root_relative: str, ownership: list[str]) -> str:
    quoted_ownership = " ".join(_quote(path) for path in ownership)
    return f"""# Confirm the worker did not change or create an unowned path.
.venv/bin/python - {_quote(plan_path)} {_quote(story_root_relative)} {quoted_ownership} <<'PY'
import json
import subprocess
import sys
from pathlib import Path

from storygame.story_package.loader import load_story_package
from storygame.story_source import check_source_tree
from storygame.story_source.lookup import story_text

plan_path = Path(sys.argv[1])
story_root = Path(sys.argv[2])
owned = set(sys.argv[3:])
status = subprocess.run(
    ["git", "status", "--porcelain", "--untracked-files=all"],
    check=False,
    capture_output=True,
    text=True,
)
if status.returncode:
    raise SystemExit(status.stderr or "git status failed")
changed = set()
for line in status.stdout.splitlines():
    path = line[3:]
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    changed.add(path)
unexpected = sorted(changed - owned)
if unexpected:
    raise SystemExit("files outside task ownership: " + ", ".join(unexpected))

plan = json.loads(plan_path.read_text(encoding="utf-8"))
package = load_story_package(story_root)
diagnostics = check_source_tree(story_root / "source")
if diagnostics:
    raise SystemExit("source diagnostics: " + "; ".join(str(item) for item in diagnostics))

if plan["kind"] == "add_pacing_beat":
    expected = plan["beat"]
    event = next((item for item in package.pacing.events if item.id == expected["id"]), None)
    if event is None:
        raise SystemExit("compiled package is missing the planned beat")
    actual_when = {{item.fact_id: item.equals for item in event.when}}
    actual_sets = {{item.fact_id: item.equals for item in event.effects}}
    if event.at_turn != expected["at_turn"] or actual_when != expected["when"] or actual_sets != expected["sets"]:
        raise SystemExit("compiled beat timing or predicates differ from plan.json")
    if event.trailing != expected["trailing"]:
        raise SystemExit("compiled beat trailing flag differs from plan.json")
    realizations = [item for item in event.realizations if not item.when]
    if len(realizations) != 1 or realizations[0].text != expected["text"]:
        raise SystemExit("compiled beat text differs from plan.json")
    if realizations[0].verbatim != expected["verbatim"]:
        raise SystemExit("compiled beat verbatim flag differs from plan.json")
else:
    address = plan["set_text"]["address"]
    if story_text(address, package=package) != plan["set_text"]["text"]:
        raise SystemExit("compiled claim text differs from plan.json")
PY
.venv/bin/python -m storygame.story_cli fmt --check
start=$(date +%s)
set +e
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_game_path_completion.py
test_status=$?
set -e
took=$(( $(date +%s) - start ))
echo "game-path completion tests took $took s (budget 300 s)"
[ "$test_status" -eq 0 ]
[ "$took" -le 300 ]
"""


def _default_run_ringer(manifest_path: Path, ringer_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ringer_path), "run", str(manifest_path), "--identity", "factory", "--no-dashboard"],
        cwd=manifest_path.parent,
        check=False,
        capture_output=True,
        text=True,
        timeout=3600,
    )


def _run_git(
    run: Callable[..., subprocess.CompletedProcess], command: list[str], cwd: Path
) -> subprocess.CompletedProcess | None:
    try:
        return run(command, cwd=cwd, check=False, capture_output=True, text=True)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _clear_previous(
    repository_root: Path, ticket_dir: Path, run: Callable[..., subprocess.CompletedProcess]
) -> str | None:
    tree = ticket_dir / "tree"
    if tree.exists() or tree.is_symlink():
        completed = _run_git(run, ["git", "worktree", "remove", "--force", str(tree)], repository_root)
        if completed is None or completed.returncode != 0:
            return _tail(_output(completed)) or f"could not remove prior tree: {tree}"
    for path in (ticket_dir / "manifest.json", ticket_dir / "plan.json", ticket_dir / "out", ticket_dir / "ringer"):
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            elif path.exists() or path.is_symlink():
                path.unlink()
        except OSError as error:
            return str(error)
    completed = _run_git(run, ["git", "worktree", "prune"], repository_root)
    if completed is None or completed.returncode != 0:
        return _tail(_output(completed)) or "could not prune prior worktrees"
    return None


def wiring_handler(
    root: Path | None = None,
    run_ringer: Callable[[Path, Path], subprocess.CompletedProcess] | None = None,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    now_fn: Callable[[], datetime] = datetime.now,
    guard_call: Callable[[Callable[[], object]], object] | None = None,
    planner: Callable[[Any, Any, datetime], Any] | None = None,
) -> StationHandler:
    """Return the station-4 handler that runs and applies one checked worker patch."""

    del now_fn
    repository_root = Path(root) if root is not None else _repository_root()

    def handle(ticket, now: datetime) -> StationResult:
        payload = ticket.payload
        working_payload = dict(payload)
        plan = working_payload.get("plan")
        workspace_value = working_payload.get("workspace")
        planner_tokens = 0
        if not isinstance(plan, dict) and planner is None:
            return StationResult(False, "wiring", "missing payload key: plan")
        if not isinstance(workspace_value, str):
            return StationResult(False, "wiring", "missing payload key: workspace")

        story_root = _story_root(repository_root)
        try:
            package = load_story_package(story_root)
            if not isinstance(plan, dict):
                outcome = planner(ticket, package, now)
                planner_tokens = outcome.tokens
                plan = outcome.plan
                if not isinstance(plan, dict):
                    return StationResult(
                        False,
                        "wiring",
                        "\n".join(outcome.problems),
                        tokens=planner_tokens,
                    )
                working_payload["plan"] = plan
            ticket_payload = dict(working_payload)
            ticket_payload.setdefault("scene", ticket.scene)
            problems = lint_plan(plan, ticket_payload, package)
        except (OSError, TypeError, ValueError, KeyError) as error:
            return StationResult(False, "wiring", _tail(str(error) or error.__class__.__name__), tokens=planner_tokens)
        if problems:
            return StationResult(False, "wiring", "\n".join(problems), tokens=planner_tokens)

        workspace = Path(workspace_value).expanduser()
        try:
            workspace = workspace.resolve()
            repository_resolved = repository_root.resolve()
        except (OSError, RuntimeError, ValueError) as error:
            return StationResult(False, "wiring", str(error), tokens=planner_tokens)
        if _inside(workspace, repository_resolved):
            return StationResult(False, "wiring", "workspace must be outside the repository", tokens=planner_tokens)

        safe_id = _safe_id(ticket.id)
        ticket_dir = workspace / safe_id
        cleanup_error = _clear_previous(repository_root, ticket_dir, run)
        if cleanup_error:
            return StationResult(False, "wiring", cleanup_error, tokens=planner_tokens)

        source_dir = story_root / "source" / "scenes"
        ownership = []
        for suffix in (f"{plan['scene']}.yaml", f"{plan['scene']}.match.yaml"):
            candidate = source_dir / suffix
            if candidate.is_file():
                ownership.append(candidate.relative_to(repository_root).as_posix())
        if not ownership:
            return StationResult(
                False, "wiring", "no owned source files exist for the plan scene", tokens=planner_tokens
            )

        try:
            ticket_dir.mkdir(parents=True, exist_ok=True)
            ringer_dir = ticket_dir / "ringer"
            ringer_dir.mkdir()
            plan_path = ticket_dir / "plan.json"
            plan_path.write_text(
                json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            story_root_relative = story_root.relative_to(repository_root).as_posix()
            manifest = build_manifest(
                run_name=f"factory-wiring-{safe_id}",
                repo=str(repository_root),
                workdir=str(ringer_dir),
                tasks=[
                    TaskSpec(
                        key="wire",
                        task_type="code-fix",
                        spec_body=wiring_spec(plan, story_root_relative),
                        verified=(
                            "The compiled package holds the exact plan text, the story source formats cleanly, "
                            "and the game-path completion tests pass."
                        ),
                        ownership=ownership,
                        tests=["tests/test_game_path_completion.py"],
                        check_extra=_check_extra(plan_path, story_root_relative, ownership),
                        engine="codex",
                        effort="medium",
                        max_attempts=2,
                        check_timeout_s=300,
                    )
                ],
            )
            manifest_path = ticket_dir / "manifest.json"
            write_manifest(manifest, manifest_path)
        except (OSError, ValueError, AssertionError, KeyError) as error:
            return StationResult(
                False,
                "wiring",
                _tail(str(error) or error.__class__.__name__),
                tokens=planner_tokens,
            )

        ringer = working_payload.get("ringer", "~/dev/ringer/ringer.py")
        if not isinstance(ringer, str):
            return StationResult(False, "wiring", "ringer must be a path string", tokens=planner_tokens)
        ringer_path = Path(ringer).expanduser()
        runner = run_ringer or _default_run_ringer
        try:

            def invoke() -> subprocess.CompletedProcess:
                return runner(manifest_path, ringer_path)

            completed = guard_call(invoke) if guard_call is not None else invoke()
        except (OSError, subprocess.TimeoutExpired, TypeError, ValueError) as error:
            return StationResult(False, "wiring", _tail(str(error) or error.__class__.__name__), tokens=planner_tokens)
        output = _output(completed)
        returncode = getattr(completed, "returncode", 1)
        patch_path = ringer_dir / "wire.patch"
        if returncode != 0:
            return StationResult(
                False,
                "wiring",
                _tail(output) or f"Ringer exited with status {returncode}",
                tokens=planner_tokens,
            )
        if not patch_path.is_file() or patch_path.stat().st_size == 0:
            return StationResult(
                False,
                "wiring",
                _tail(output) or "Ringer produced a missing or empty patch",
                tokens=planner_tokens,
            )

        tree = ticket_dir / "tree"
        added = _run_git(run, ["git", "worktree", "add", "--detach", str(tree), "HEAD"], repository_root)
        if added is None or added.returncode != 0:
            return StationResult(
                False,
                "wiring",
                _tail(_output(added)) or "could not create ticket worktree",
                tokens=planner_tokens,
            )
        venv_link = tree / ".venv"
        try:
            if not venv_link.exists() and not venv_link.is_symlink():
                venv_link.symlink_to(repository_root / ".venv")
        except OSError as error:
            return StationResult(False, "wiring", str(error), tokens=planner_tokens)
        applied = _run_git(run, ["git", "apply", str(patch_path)], tree)
        if applied is None or applied.returncode != 0:
            return StationResult(
                False,
                "wiring",
                _tail(_output(applied)) or "patch did not apply",
                tokens=planner_tokens,
            )
        return StationResult(True, "wiring", f"tree={tree} patch={patch_path}", tokens=planner_tokens)

    return handle
