# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18h: a read-only scout diagnoses each of the 21 stuck turns by cause and precedent. FREE: no repo edits.

One Codex task, research with proof. Usage: build_round18h_diagnosis_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/diagnosis-scout"
PACKETS = "/home/bcorfman/dev/ringer-work/packets-18c.copy.json"
CAUSES = ["lead_outside_scene", "prerequisite_step_missing", "talk_without_matching_storylet", "examine_without_matching_reveal", "invented_by_narrator", "match_miss_on_offered_candidate", "other"]

SPEC = """You are a read-only diagnosis scout. NEVER edit, create or delete anything inside @REPO@; never run git commands that change anything; never call a model or the network. You may only read files and write ONE output file: @WORK@/out/diagnosis.json (create the directory if needed).

TASK. Scene 1A of an interactive-fiction story had 21 'stuck turns' in a live test: the player typed a command and the engine matched none of the story's authored outcomes. Diagnose each turn by cause, the way the project's scene-fixing guide asks (read what was offered beside the scene data before proposing anything), and tie each cause to the project's recorded precedents. Read, in full: @PACKETS@ (the 21 stuck turns: `key`, `player_input`, `narration`, `candidates_offered` (claim ids), `matched_candidate`, `match_issues`), @REPO@/data/stories/continuity-initiative/source/scenes/1A.yaml and 1A.match.yaml in the same folder (the claim ids appear there as `claim_id`, with a `says` sentence, `requires` facts and `reach` things), @REPO@/factory/precedents/stuck_turns.md (the project's verified winners, losers and never-do rules) and @REPO@/docs/scene-fixing-guide.md.

OUTPUT. @WORK@/out/diagnosis.json: a JSON list with exactly one object per packet key (21 objects, the `key` copied exactly), each with these string fields: `key`; `player_intent` (one short sentence: what the player was trying to do); `offered` (the `says` sentence of each offered candidate, joined with ` | `, copied verbatim from the scene file, or `none offered`); `cause`, exactly one of: @CAUSES@ (`lead_outside_scene`: the player chased a place or thing outside the scene; `prerequisite_step_missing`: the command needed a step the engine should perform for the player; `talk_without_matching_storylet`: the player talked to someone and no authored outcome fits; `examine_without_matching_reveal`: the player examined something and no authored outcome fits; `invented_by_narrator`: the narration invented an object or event; `match_miss_on_offered_candidate`: an offered candidate plainly fits the command but did not match; `other`); `why` (one or two sentences naming the evidence in the packet and the scene file); `precedent_quote` (a verbatim quote of at least eight words from `factory/precedents/stuck_turns.md` that bears on this cause, or the exact string `none`); `precedent_side` (one of `winner`, `lost`, `never_do`, `rule`, `none`, naming the section of that bullet). Report only what the files show; when the cause is unclear use `other` and say so in `why`. Do not write fixes or advice."""

CHECK = """set -eo pipefail
WORK=@WORK@
OUT="$WORK/out/diagnosis.json"
test -s "$OUT" || { echo "missing $OUT"; exit 1; }
python3 - "$OUT" @PACKETS@ @REPO@ <<'PY'
import json, re, sys
from pathlib import Path
out, packets_path, repo = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
rows = json.loads(out.read_text(encoding="utf-8"))
keys = [p["key"] for p in json.loads(packets_path.read_text(encoding="utf-8"))]
causes = set(@CAUSES_JSON@)
sides = {"winner", "lost", "never_do", "rule", "none"}
def norm(s): return re.sub(r"\\s+", " ", s).strip()
prec = norm((repo / "factory/precedents/stuck_turns.md").read_text(encoding="utf-8"))
scene = norm((repo / "data/stories/continuity-initiative/source/scenes/1A.yaml").read_text(encoding="utf-8"))
bad = []
if sorted(r.get("key") for r in rows) != sorted(keys):
    bad.append("keys do not match the 21 packets exactly")
for r in rows:
    k = r.get("key")
    for f in ("player_intent", "offered", "cause", "why", "precedent_quote", "precedent_side"):
        if not isinstance(r.get(f), str) or not r[f].strip():
            bad.append(f"{k}: empty field {f}")
    if r.get("cause") not in causes: bad.append(f"{k}: bad cause {r.get('cause')}")
    if r.get("precedent_side") not in sides: bad.append(f"{k}: bad precedent_side")
    q = r.get("precedent_quote", "")
    if q != "none" and norm(q) not in prec: bad.append(f"{k}: precedent quote not found")
    if q == "none" and r.get("precedent_side") != "none": bad.append(f"{k}: side without quote")
    off = r.get("offered", "")
    if off != "none offered":
        for part in off.split(" | "):
            if norm(part) not in scene: bad.append(f"{k}: offered sentence not in 1A.yaml: {part[:60]}")
print("rows:", len(rows))
if bad:
    print("PROBLEMS:"); [print(" ", x) for x in bad[:30]]; sys.exit(1)
PY
"""


def build() -> dict:
    def fill(text: str) -> str:
        return (
            text.replace("@REPO@", REPO)
            .replace("@WORK@", WORK)
            .replace("@PACKETS@", PACKETS)
            .replace("@CAUSES_JSON@", json.dumps(CAUSES))
            .replace("@CAUSES@", ", ".join(f"`{c}`" for c in CAUSES))
        )

    return {
        "run_name": "diagnosis-scout",
        "workdir": WORK,
        "max_parallel": 1,
        "repo": REPO,
        "tasks": [
            {
                "key": "diagnosis",
                "task_type": "research",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3000,
                "check_timeout_s": 120,
                "ownership": [],
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [f"{WORK}/out/diagnosis.json"],
                "verified": "Exactly 21 rows, one per stuck turn, each with an allowed cause; every offered sentence exists verbatim in the 1A scene file and every precedent quote exists verbatim in the precedents file.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round18h-diagnosis-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
