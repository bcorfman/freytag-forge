"""Ringer check: the prompt-comparison rejudge must hold 30 valid verdicts and a faithful new-prompt module.

usage: check_prompt_compare.py <workdir>
"""

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

work = Path(sys.argv[1])
problems = []
for name in ("results.json", "report.md", "judge-simple.js", "simple-prompt.txt"):
    if not (work / name).is_file() or not (work / name).read_text().strip():
        problems.append(f"{name} missing or empty")
if not problems:
    probe = r"""
import { readFileSync } from "node:fs";
const prompt = readFileSync("simple-prompt.txt", "utf8");
const progress = JSON.parse(readFileSync("run5-progress.json", "utf8"));
const data = Object.fromEntries(progress.by_scene)["1A"];
const bodies = {};
for (const [name, file] of [["old", "./roleplay-judge-run5.js"], ["new", "./judge-simple.js"]]) {
  const mod = await import(file);
  const canon = mod.sceneCanon("1A", data.revealedKnowledgeIds, "/home/bcorfman/dev/freytag-forge");
  let body = null;
  const fetchImpl = async (_url, init) => {
    body = JSON.parse(init.body);
    return { ok: true, json: async () => ({ output_text: JSON.stringify({
      verdict: "pass", canon_consistent: true, scene_local: true, progressive: true,
      rich: true, protected_safe: true, exit_motivated: true, rewards_investigation: true,
      missing_or_wrong: [], reasons: []
    }) }) };
  };
  await mod.judgeSceneNarration({
    sceneId: "1A", opening: data.opening, turns: data.turns, revealedKnowledgeIds: data.revealedKnowledgeIds
  }, { environment: { OPENAI_API_KEY: "x" }, fetchImpl, canon });
  bodies[name] = body;
}
const out = [];
if (bodies.new.input[0].content.trim() !== prompt.trim()) out.push("new system prompt differs from simple-prompt.txt");
if (bodies.new.input[1].content !== bodies.old.input[1].content) out.push("user message differs between old and new");
if (JSON.stringify(bodies.new.text) !== JSON.stringify(bodies.old.text))
  out.push("schema/format differs between old and new");
if (bodies.new.model !== bodies.old.model) out.push("model differs between old and new");
console.log(JSON.stringify(out));
"""
    res = subprocess.run(["node", "--input-type=module", "-e", probe], cwd=work, capture_output=True, text=True)
    if res.returncode != 0:
        problems.append("module probe crashed: " + res.stderr[-400:])
    else:
        problems += json.loads(res.stdout.strip().splitlines()[-1])
    data = json.loads((work / "results.json").read_text())
    rows = data["results"] if isinstance(data, dict) else data
    cells = Counter((row.get("scene"), row.get("arm")) for row in rows if isinstance(row.get("exit_motivated"), bool))
    scenes = {"1A", "1C", "2A", "3A", "3B"}
    arms = {"old_prompt", "simple_prompt"}
    for scene in scenes:
        for arm in arms:
            if cells[(scene, arm)] != 3:
                problems.append(f"cell {scene}/{arm} has {cells[(scene, arm)]} valid verdicts, need 3")
    if len(rows) != 30:
        problems.append(f"{len(rows)} result rows, need exactly 30 (one billed call each)")
    text = (work / "report.md").read_text().lower()
    for needed in ("old_prompt", "simple_prompt", "limits"):
        if needed not in text:
            problems.append(f"report never mentions '{needed}'")
if problems:
    sys.exit("FAIL " + "; ".join(problems))
print("prompt comparison complete: faithful new-prompt module, 30 verdicts in 10 cells of 3")
