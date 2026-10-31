"""Build the Ringer manifest that splits long docs into a short summary plus detail files."""

import json
from pathlib import Path

ROOT = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/doc-split"
CHECK = f"{ROOT}/scripts/ringer/worldkeeper-boundary/check_doc_split.py"
DOCS = {
    "testing-runbook": (400, "how to verify freytag-forge: which command checks which boundary"),
    "world-model-grounding": (400, "how to ground story things, places and people in the world model"),
    "markdown-story-authoring": (400, "the Markdown story-package format and its fields"),
    "jev-guard-rules": (400, "the Jev guard rules"),
    "contributor-guide": (300, "repository-wide engineering rules"),
}
DETAIL_MAX = 900


def spec(name: str, budget: int, topic: str) -> str:
    return (
        f"You are a documentation worker in the freytag-forge repository at {ROOT}, branch "
        "docs-progressive-disclosure, "
        "already checked out with other uncommitted work on it. Do NOT git commit, push, switch branches, stash or "
        "revert. "
        f"Edit ONLY docs/{name}.md and files you create under docs/{name}/. Never touch any other file: other workers "
        "are "
        "splitting other docs at the same time.\n\n"
        f"GOAL: progressive disclosure. docs/{name}.md ({topic}) is too long for an LLM agent to load every time. "
        "Turn it "
        f"into a short summary file at the SAME path (AGENTS.md and other docs link to it) plus detail files under "
        f"docs/{name}/, so an agent reads the summary and opens only the detail file its task needs.\n\n"
        "THE SUMMARY FILE must contain, in this order: the existing title; one or two sentences on what the doc "
        "covers; "
        "the few rules that apply to EVERY task this doc governs (keep their original wording; these are the lines an "
        "agent must not miss even if it opens nothing else); and an index with one line per detail file in the form "
        "`- [Title](" + name + "/<file>.md): read this when <the task that needs it>.` The 'read this when' trigger is "
        "the key part: say concretely which task or question sends the reader there. "
        f"Hard limit: {budget} words.\n"
        f"DETAIL FILES: docs/{name}/<kebab-topic>.md, each one coherent topic (group the original sections by the task "
        f"that needs them, not one file per heading), each at most {DETAIL_MAX} words, each starting with a `# Title` "
        "and "
        f"a one-line `Part of [the ...](../{name}.md).` back link. Prefer 4 to 8 detail files for a long doc; fewer "
        "for "
        "a short one.\n\n"
        "PRESERVE CONTENT: move text, do not rewrite it. Every sentence of the original must survive verbatim in the "
        "summary or a detail file (line wrapping, list markers and headings may change). You may change only: "
        "headings, "
        "the order of sections, and cross-references that the split breaks (e.g. 'See section 8' becomes a link to the "
        "detail file that now holds it). Do not drop, summarise away or merge rules. Code blocks keep every line.\n"
        "LINKS: fix every relative link and #anchor in the moved text for its new location (a link like "
        "`(PRD.md)` in a file under docs/" + name + "/ becomes `(../PRD.md)`; `(../bench/README.md)` becomes "
        "`(../../bench/README.md)`). Every relative link in docs/, AGENTS.md and README.md must still resolve.\n\n"
        f"The original is snapshotted at {WORK}/orig/{name}.md; work from it.\n"
        "HOW TO CHECK (never use `uv`): "
        f"`{ROOT}/.venv/bin/python {CHECK} {WORK}/orig/{name}.md {ROOT}/docs/{name}.md {ROOT}/docs/{name} {budget} "
        f"{DETAIL_MAX}`. It prints every missing sentence, oversize file, unlinked detail file and broken link. "
        "It checks links in your files and in docs that link to yours. DONE WHEN it prints PASS."
    )


tasks = []
for name, (budget, topic) in DOCS.items():
    tasks.append(
        {
            "task_type": "docs",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 120,
            "key": name,
            "ownership": [f"{ROOT}/docs/{name}.md", f"{ROOT}/docs/{name}/"],
            "expect_files": [f"{ROOT}/docs/{name}.md"],
            "verified": "executed check: summary under budget, every detail file linked and under budget, every "
            "original sentence kept, every doc link and anchor resolves",
            "spec": spec(name, budget, topic),
            "check": f"{ROOT}/.venv/bin/python {CHECK} {WORK}/orig/{name}.md {ROOT}/docs/{name}.md {ROOT}/docs/{name} "
            f"{budget} {DETAIL_MAX}",
        }
    )

manifest = {
    "run_name": "docs-progressive-disclosure",
    "workdir": WORK,
    "max_parallel": 5,
    "worktrees": False,
    "repo": ROOT,
    "tasks": tasks,
}
out = Path(ROOT) / "scripts/ringer/worldkeeper-boundary/doc-split-manifest.json"
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
