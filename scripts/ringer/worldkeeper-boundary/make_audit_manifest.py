"""Build the read-only worldkeeper boundary audit manifest (Ringer review swarm)."""

import json
from pathlib import Path

ROOT = "/home/bcorfman/dev/freytag-forge"
OUT = Path(ROOT) / "scripts/ringer/worldkeeper-boundary"

GROUPS = {
    "item-facts": ["storygame/runtime/item_facts.py"],
    "capture-observation": [
        "storygame/runtime/capture.py",
        "storygame/runtime/observation.py",
        "storygame/runtime/cloudflare.py",
        "storygame/web_demo.py",
    ],
    "seating-taking-misc": [
        "storygame/runtime/seating.py",
        "storygame/runtime/taking.py",
        "storygame/runtime/traversal.py",
        "storygame/runtime/narration_safety.py",
        "storygame/runtime/fixed_refusal.py",
        "storygame/runtime/world_model.py",
    ],
}

RULE = (
    "THE RULE BEING AUDITED (Brandon, 2026-10-31, now in docs/contributor-guide.md): world-model logic lives in "
    "packages/worldkeeper, not in storygame. A rule that reads or changes only world state (parents, containment, "
    "kinds, reach, visibility, seats, companions, axes, hidden/unplaced flags, names and aliases of entities) is a "
    "`World` method in packages/worldkeeper/src/worldkeeper/model.py with tests in packages/worldkeeper/tests/. "
    "storygame/runtime/world_model.py only adapts the story package and facts to worldkeeper; other modules call "
    "World methods and never walk the tree themselves. Code that needs the StoryPackage (scenes, NPC labels, "
    "knowledge, "
    "pacing), prose or text matching for narration, or a model call stays in storygame. worldkeeper must stay "
    "story-agnostic: it may not import storygame or know any story's ids or vocabulary."
)


def spec(key: str, files: list[str]) -> str:
    listing = "\n".join(f"- {ROOT}/{f}" for f in files)
    return (
        f"You are a READ-ONLY code auditor in the freytag-forge repository at {ROOT}. Never edit, create, move or "
        "delete "
        "any file in the repository; never run git commands that change anything; never run tests that call a network "
        f"or a model. Your only output is the JSON report /home/bcorfman/dev/ringer-work/worldkeeper-boundary-audit/"
        f"{key}.json.\n\n"
        f"{RULE}\n\n"
        f"FILES YOU AUDIT:\n{listing}\n\n"
        "WHAT TO DO.\n"
        f"1. Read the worldkeeper library first: {ROOT}/packages/worldkeeper/src/worldkeeper/model.py (the `World` "
        "class "
        "and its helpers) and the README in packages/worldkeeper. Know every existing World method so you never "
        "propose "
        "one that already exists under another name.\n"
        "2. In each audited file, find EVERY function or method that calls a World method (world.parent, world.is_a, "
        "world.children, world.area, world.name, world.place, world.companions, etc.) or reads `wk_` facts. Use "
        "`grep -n` to be exhaustive. Read each one in full.\n"
        "3. Give each a verdict:\n"
        "   - move: the whole function depends only on world state (a World plus plain ids/strings as arguments). It "
        "should become a World method (or a worldkeeper helper) and its storygame callers call that instead.\n"
        "   - split: part of it is pure world logic (e.g. a loop that walks parents to find the enclosing container, a "
        "reachability or visibility test, a kind test chain) and part needs the StoryPackage, prose, or a model call. "
        "Name exactly the lines that are pure world logic.\n"
        "   - stay: it only calls existing World methods as a client (no tree walking of its own) or the world logic "
        "is "
        "inseparable from story/prose/model logic. Say why.\n"
        "   Be strict and concrete: a single `world.parent(x)` lookup used to decide narration is a client call "
        "(stay); "
        "a `while` loop over parents, a recursive descent over children, or a reimplementation of a rule World already "
        "has (e.g. its own visibility or containment walk) is world logic. Also flag DUPLICATES: storygame code that "
        "recomputes what an existing World method already computes; say which method.\n"
        "4. For move/split also give: proposed_world_method (a signature such as `World.enclosing_container(self, "
        "entity_id: str) -> str | None` and one sentence on its contract), callers (every `file:line` in storygame "
        "that "
        "calls the function; find them with grep across storygame/ and tests/), and needs_story_package: false (the "
        "moved part must not need the package). If the moved part would need a package concept, say what plain data "
        "could be passed in instead, or mark it stay.\n"
        "5. Note risks: hidden behaviour differences (ordering, None handling, groups, companions, seats, part_of, "
        "under) a mover must preserve.\n\n"
        'OUTPUT CONTRACT: write valid JSON to the report path above, shaped as {"group": "' + key + '", '
        '"findings": [ {"file": "storygame/runtime/x.py" (repo-relative, exactly one of the audited files), '
        '"function": "name as defined in the file (for methods, the method name)", "lines": "start-end", '
        '"verdict": "move|split|stay", "world_state_read": "which world state it reads or changes", '
        '"reason": "why this verdict, citing lines", "pure_world_lines": "for split only", '
        '"duplicates_world_method": "name or empty", "proposed_world_method": "...", "callers": ["file:line"], '
        '"needs_story_package": false, "risks": "..."} ], "summary": "3-6 sentences"}. Every audited file must '
        "have at least one finding (list World-calling functions even when the verdict is stay). Function names must "
        "exist in the file you cite; the check parses the files and rejects invented names.\n"
        "DONE WHEN the report validates: "
        f"`{ROOT}/.venv/bin/python {ROOT}/scripts/ringer/worldkeeper-boundary/check_audit.py "
        f"/home/bcorfman/dev/ringer-work/worldkeeper-boundary-audit/{key}.json "
        + " ".join(files)
        + "` prints PASS. Never use `uv`."
    )


tasks = []
for key, files in GROUPS.items():
    report = f"/home/bcorfman/dev/ringer-work/worldkeeper-boundary-audit/{key}.json"
    tasks.append(
        {
            "task_type": "code-review",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 120,
            "key": key,
            "ownership": [report],
            "expect_files": [report],
            "verified": "executed check: report JSON parses, cites only real functions in the audited files, covers "
            "every file, and move/split entries carry a World method, callers and no package dependency",
            "spec": spec(key, files),
            "check": f"{ROOT}/.venv/bin/python {ROOT}/scripts/ringer/worldkeeper-boundary/check_audit.py {report} "
            + " ".join(files),
        }
    )

manifest = {
    "run_name": "worldkeeper-boundary",
    "workdir": "/home/bcorfman/dev/ringer-work/worldkeeper-boundary-audit",
    "max_parallel": 3,
    "worktrees": False,
    "repo": ROOT,
    "tasks": tasks,
}
(OUT / "audit-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(OUT / "audit-manifest.json")
