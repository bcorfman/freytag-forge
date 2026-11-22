# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18f: a read-only scout collects the project's proven and failed fixes for stuck turns. FREE: no repo edits.

One Codex task, research with proof: every quote it reports is verified verbatim against the cited file.
Usage: build_round18f_precedents_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/precedents-scout"
SOURCES = [
    ".plans/1a-transcript-continuity-plan.md",
    ".plans/1a-opening-and-truck-feedback-plan.md",
    ".plans/astra-1a-plan.md",
    ".plans/1a-password-and-officer-plan.md",
    ".plans/astra-3c-stuck-turns-prereg.md",
    ".plans/world-model.md",
    ".plans/game-reimagination/whole-story-pacing.md",
    "docs/scene-fixing-guide.md",
    "docs/story-gap-guide.md",
    "docs/world-model-grounding.md",
    "docs/contributor-guide.md",
]

SPEC = """You are a read-only research scout. NEVER edit, create or delete anything inside @REPO@; never run git commands that change anything; never call a model or the network. You may only read files and write ONE output file: @WORK@/out/precedents.md (create the directory if needed).

TASK. This project (an interactive-fiction engine and its Continuity Initiative story) has fixed 'stuck turns' (player commands that match nothing) and 'players leave the scene early or chase a lead the scene cannot deliver' in several scenes. An automated planner is about to propose story-data changes for scene 1A and must not repeat failed ideas or damage the engine. Read these files IN FULL (each path is relative to @REPO@): @SOURCES@. They are long; read them all, do not sample.

OUTPUT. @WORK@/out/precedents.md with exactly these five second-level headings, in this order, each followed by bullets:
## Winners (techniques that were adopted because evidence showed they worked)
## Lost or rejected (tried and dropped, with the reason)
## Never do (rules about what must not be done to the engine, story facts, pacing events, transitions, exits or world state, including anything that corrupts state or creates stuck states)
## Pacing events and effect facts (rules about how a pacing event and the fact it sets must be designed)
## Transitions and exits (rules about when and how a transition, exit trigger or exit dependency may be changed)
Every bullet has this shape, on ONE line: `- <what it is, which scene, the evidence in numbers or the test or probe name> "<a verbatim quote of at least six words from the source>" [source: <path relative to @REPO@>:<line number where the quote starts>]`. Use only quotes that really appear in the cited file on the cited line (whitespace differences are tolerated; any invented or altered quote fails the check). Report only what the sources say; mark a point `(unresolved)` when the sources leave the outcome open; if a section has nothing in the sources, write one bullet `- none found [source: none]`. Aim for completeness: every distinct technique, rule and outcome you find, up to 60 bullets in total. Do not add a conclusions or advice section."""

CHECK = """set -eo pipefail
WORK=@WORK@
OUT="$WORK/out/precedents.md"
test -s "$OUT" || { echo "missing $OUT"; exit 1; }
python3 - "$OUT" @REPO@ <<'PY'
import re, sys
from pathlib import Path
out, repo = Path(sys.argv[1]), Path(sys.argv[2])
text = out.read_text(encoding="utf-8")
heads = [h.strip() for h in re.findall(r"^## (.+)$", text, re.M)]
want = ["Winners", "Lost or rejected", "Never do", "Pacing events and effect facts", "Transitions and exits"]
for w in want:
    if not any(h.startswith(w) for h in heads):
        print("missing section:", w); sys.exit(1)
bullets = [l for l in text.splitlines() if l.startswith("- ")]
if len(bullets) < 12:
    print("too few bullets:", len(bullets)); sys.exit(1)
def norm(s): return re.sub(r"\\s+", " ", s).strip()
bad, checked = [], 0
for b in bullets:
    if "[source: none]" in b: continue
    m = re.search(r'"([^"]{20,})"\\s*\\[source: ([^:\\]]+):(\\d+)\\]', b)
    if not m:
        bad.append("no quote/source shape: " + b[:110]); continue
    quote, path, line = norm(m.group(1)), m.group(2), int(m.group(3))
    f = repo / path
    if not f.is_file():
        bad.append("no such file: " + path); continue
    body = norm(f.read_text(encoding="utf-8", errors="replace"))
    if quote not in body:
        bad.append("quote not found in " + path + ": " + quote[:80]); continue
    checked += 1
print("bullets:", len(bullets), "verified quotes:", checked)
if bad:
    print("PROBLEMS:"); [print(" ", x) for x in bad[:25]]; sys.exit(1)
PY
"""


def build() -> dict:
    def fill(text: str) -> str:
        return (
            text.replace("@REPO@", REPO)
            .replace("@WORK@", WORK)
            .replace("@SOURCES@", ", ".join(SOURCES))
        )

    return {
        "run_name": "precedents-scout",
        "workdir": WORK,
        "max_parallel": 1,
        "repo": REPO,
        "tasks": [
            {
                "key": "precedents",
                "task_type": "research",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3000,
                "check_timeout_s": 120,
                "ownership": [],
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [f"{WORK}/out/precedents.md"],
                "verified": "Every bullet carries a quote of six or more words that exists verbatim in the cited project file, under the five required sections.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round18f-precedents-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
