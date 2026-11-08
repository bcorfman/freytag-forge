# ruff: noqa: E501
"""Write speaker-text2-manifest.json: one Ringer task (tests first) rewriting the four authored 3A speaker_text entries and adding five more,
with the wording Brandon approved on 2026-11-07 (a speaker never retells Kristin her own action). The speaker_text schema and rendering already exist.
The check uses no bashisms (Ringer runs checks under /bin/sh)."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/shared-narrator-speaker-text-2"
HERE = Path(__file__).parent

ORG_M = "I've been organizing everyone with secret announcements over our stolen radios."
ORG_O = "Dr. McGehee's been organizing everyone with secret announcements over the stolen radios."
A2_M = "Freeing this block doesn't mean much unless we expose the other sites too."
A2_O = "Dr. McGehee says freeing this block means little unless we expose the other sites."
REC = 'Those records prove the "survivors" were planned. They were conditioned to support Charles\'s story.'
MED = "The medical level is where they ran memory, compliance, and resistance experiments on the prisoners."
AUTH = "That authorization opens the emergency surface gates, but only once. It expires when Charles activates his new authority."
PROOF = "The authorization is real, but the panel's brief response shows the one-use code is about to expire."
SIG = "The prisoners have the checkpoints, and they're fighting their way up toward the command and broadcast levels."
C2_M = "Good thing we didn't wait. That authorization was about to run out."
C2_O = "Dr. McGehee didn't wait. The authorization was about to expire."
TEXT = {
    "k_sl_3a_a_r1": (ORG_M, ORG_O, ORG_O),
    "k_sl_3a_a_r2": (A2_M, A2_O, A2_O),
    "k_sl_3a_b_r1": (REC, REC, REC),
    "k_sl_3a_e_r1": (REC, REC, REC),
    "k_sl_3a_b_r2": (MED, MED, MED),
    "k_sl_3a_d_r1": (AUTH, AUTH, AUTH),
    "k_sl_3a_d_r2": (PROOF, PROOF, PROOF),
    "k_sl_3a_c_r1": (f"Your signal worked. {SIG}", f"The signal worked. {SIG}", f"The signal worked. {SIG}"),
    "k_sl_3a_c_r2": (C2_M, C2_O, C2_O),
}
table = "\n".join(
    f"  {kid}:\n    michelle = {m!r}\n    brandon = {b!r}\n    senior_official = {o!r}"
    for kid, (m, b, o) in TEXT.items()
)

TESTS = (
    "tests/test_speaker_text.py tests/test_speaker_lines.py tests/test_cloudflare_transport.py tests/test_knowledge_projection.py "
    "tests/test_voiceable_knowledge.py tests/test_knowledge_narrated_gate.py tests/test_knowledge_leakage_matrix.py "
    "tests/test_package_audit.py tests/test_markdown_story_package.py tests/test_story_package_cache.py tests/test_richer_3a.py "
    "tests/test_world_second_package.py tests/test_act2_knowledge_sources.py tests/test_incidental_package.py tests/test_3c_adopted_package.py"
)

SPEC = f"""You work in the MAIN checkout of the game repo: {REPO} (not a worktree; it holds many uncommitted changes that belong to other work and MUST stay untouched). FIRST run `cd {REPO}`. NEVER git commit, git stash, git checkout/restore/reset, never `uv`, never call a billed model or the network, never run `python -m bench run`, `python -m bench.frozen_prompts replay` or any script that calls a model. Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>`. Ruff: `.venv/bin/python -m ruff check <files>` and `-m ruff format <files>`. Do not edit any file except those listed under OWNERSHIP.

BACKGROUND. The optional per-speaker `speaker_text` field already exists on `KnowledgeDefinition` (storygame/story_package/models.py), is validated by the loader, and is rendered by storygame/runtime/cloudflare.py as `<Name> may say this aloud: <that speaker's text>` instead of the canonical third-person statement. Four 3A entries currently carry the first draft of that text. Brandon rewrote the wording: a speaker must never retell Kristin her own action to Kristin, so the lines say what the event means now, and use first person only where a speaker really speaks about themselves (the organizing line). THIS TASK ONLY CHANGES STORY DATA AND ITS PINNING TESTS: no change to models.py, loader.py or cloudflare.py.

TASK. In data/stories/continuity-initiative/knowledge.yaml set `speaker_text` (key placed right after `delivery_text`; for the four entries that already have it, REPLACE the text) on exactly these NINE entries, so that the loaded strings equal EXACTLY the following (choose any valid YAML quoting; do not edit, re-punctuate or reorder words; speaker ids are michelle, brandon, senior_official; every map lists all three):
{table}
No other entry, statement, fact, delivery_text or file of the story changes. (The first entry's text is unchanged from the draft.)

TESTS FIRST. Before editing the YAML, update tests/test_speaker_text.py (read it first) so its real-package test pins these exact nine entries and strings per speaker, asserts that no other knowledge entry has speaker_text, that each of the nine lists all three speakers, and that canonical `statement` text of all nine is unchanged. Run it and see it fail for the right reason (record the failing summary in your final notes). Then edit the YAML and make it pass. Keep all other tests in that file.

EXISTING TESTS. Run the related suites in the check. If one fails only because it pins the old text of a sayable line, update just that expectation and keep its intent; never delete or weaken a test. List every existing test file you changed and why. If anything else fails, stop and report it.

PAYLOAD MATCH (acceptance test). `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python scripts/ringer/shared-narrator/gu_match.py frozen-GU2.json` must print MATCH for system and user at c4, c5 and c9. Do not edit that script or anything under bench/ or scripts/.

OWNERSHIP. You may edit only: data/stories/continuity-initiative/knowledge.yaml, tests/test_speaker_text.py, and existing files under tests/ whose pinned expectations change as described above. Leave all changes uncommitted in place."""

CHECK = f"""cd {REPO} || exit 1
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
$PY scripts/ringer/shared-narrator/snapshot_tree.py {WORK}/after.json >/dev/null
$PY - <<'PY2' || exit 1
import json, re, sys
before = json.load(open('{WORK}/baseline.json')); after = json.load(open('{WORK}/after.json'))
changed = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
bad = [p for p in changed if p != 'data/stories/continuity-initiative/knowledge.yaml' and not re.fullmatch(r'tests/[A-Za-z0-9_]+\\.py', p)]
print('changed:', changed)
if bad:
    print('WHY: edited files outside ownership:', bad); sys.exit(1)
for need in ('data/stories/continuity-initiative/knowledge.yaml', 'tests/test_speaker_text.py'):
    if need not in changed:
        print('WHY: expected change missing:', need); sys.exit(1)
PY2
[ "$(grep -c 'speaker_text:' data/stories/continuity-initiative/knowledge.yaml)" = 9 ] || {{ echo "WHY: expected exactly 9 speaker_text entries in knowledge.yaml"; exit 1; }}
$PY -m pytest -q -p no:cacheprovider {TESTS} > /tmp/speaker-text2-pytest.txt 2>&1
rc=$?
tail -25 /tmp/speaker-text2-pytest.txt
[ "$rc" = 0 ] || {{ echo "WHY: tests failed"; exit 1; }}
$PY scripts/ringer/shared-narrator/gu_match.py frozen-GU2.json || {{ echo "WHY: engine payload does not match frozen GU2"; exit 1; }}
$PY -m ruff check storygame tests || exit 1
$PY -m ruff format --check storygame tests || exit 1
echo "speaker_text2 check ok"
"""

manifest = {
    "run_name": "shared-narrator-speaker-text-2",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "speaker-text-2",
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 2400,
            "ownership": [
                f"{REPO}/data/stories/continuity-initiative/knowledge.yaml",
                f"{REPO}/tests/test_speaker_text.py",
            ],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [f"{REPO}/tests/test_speaker_text.py"],
            "verified": "pinning tests fail first then pass, related suites pass, engine payload matches the frozen GU2 arm at c4/c5/c9, ruff clean, only owned files changed",
        }
    ],
}
(HERE / "speaker-text2-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("written", len(SPEC), "chars of spec")
