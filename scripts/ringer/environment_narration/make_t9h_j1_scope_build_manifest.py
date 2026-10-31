"""Write build-t9h-j1-scope.json: the free build of the J1c scope screen (cases, probe and tests)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
ENV = f"{REPO}/scripts/ringer/environment_narration"
PREREG = f"{REPO}/.plans/grounded-llm-environment-narration/t9h-j1-scope-prereg.md"
CASES = f"{ENV}/j1_scope/cases.jsonl"
PROBE = f"{ENV}/j1_scope_probe.py"
TESTS = f"{REPO}/tests/test_j1_scope_probe.py"

CASE_SPEC = (
    f"You are the CASE AUTHOR. Working directory: {REPO}. You write ONE data file and nothing else: {CASES} "
    "(create the directory if needed). Never touch any other file, never run a model or any network call, do not "
    "git commit. NO regular expressions in anything you write. "
    "BACKGROUND. A judge model is asked whether a short story narration shows a named thing as a present fact at "
    "its permitted place. We test whether giving the judge extra scene context is safe. You author 60 fresh test "
    "cases in 6 fresh stories. A case's relation place is either SCENE-LEVEL (the whole location of the scene, for "
    "example 'the market square') or SPECIFIC (a named spot inside the scene, for example 'the stone fountain' or "
    "'the loading dock'). "
    "OUTPUT: exactly 60 lines of JSON, one case per line, keys: id, story, scene, scene_place, group "
    "('scene_level' or 'specific_place'), kind ('positive' or 'negative'), negative_type ('missing', 'remembered', "
    "'elsewhere', 'lookalike', or null for positives), contrast (true or false for lookalike negatives, null for "
    "everything else), label ('accept' for positives, 'reject' for negatives), narration, relation (an object "
    '{"thing": str, "place": str, "holder": null}), note (one short sentence on why the label holds). '
    "STRUCTURE: 6 stories, 10 cases each, ids f-<story 1-6>-<case 01-10>. Use six fresh genres and settings that "
    "are NOT any of: frontier town, the Los Angeles park, a drawer, a truck, an office, a Victorian country-house "
    "mystery, a 1940s noir detective story, a high-fantasy tavern and dungeon, a space-station maintenance story, "
    "a roadside search, a hospital night shift, a coastal lighthouse ferry, a lighthouse island, a space station "
    "hub, a medieval market square, a rainforest research camp, an abandoned theatre. Suggested: a mountain "
    "observatory, a river barge, a desert caravan stop, a cannery, a school gymnasium, a monastery garden. Each "
    "story has one scene (a single 2 to 5 word title in 'scene', same on all 10 lines of the story) and one "
    "scene location string in 'scene_place' (a short noun phrase for the whole location, same on all 10 lines of "
    "the story). Per story: "
    "(a) 2 positives with group scene_level: relation.place EQUALS scene_place exactly; the narration shows the "
    "thing present and NEVER writes the scene_place string (not even in different capitalisation, and not with "
    "or without a leading 'the'). "
    "(b) 2 lookalike negatives with group scene_level (relation.place equals scene_place): one with contrast "
    "false (a similar but different thing is shown in the scene instead, and the narration simply describes the "
    "similar thing) and one with contrast true (the narration shows a similar thing and SAYS in words that it is "
    "not the named thing, for example that it is not a <thing>, or lacks the defining feature of the <thing>). "
    "(c) 1 other negative with group scene_level, whose negative_type depends on the story number: stories 1 and 4 "
    "'missing', stories 2 and 5 'remembered', stories 3 and 6 'elsewhere'. "
    "(d) 2 positives with group specific_place: relation.place is a named spot inside the scene, DIFFERENT from "
    "scene_place; the narration shows the thing present AT that spot and writes the spot's name (the place string "
    "without a leading 'the' appears in the narration, case-insensitive). "
    "(e) 2 lookalike negatives with group specific_place: the narration shows a similar but different object AT the "
    "named spot (writes the spot's name); one with contrast false and one with contrast true (same meaning as in "
    "(b)). "
    "(f) 1 other negative with group specific_place, negative_type by story number: stories 1 and 4 'remembered', "
    "stories 2 and 5 'elsewhere', stories 3 and 6 'missing'. "
    "Every case in a story uses a DIFFERENT thing (a physical object or fixture that would plausibly sit in the "
    "scene, such as a well, a lamp, a crate, a notice board, a bell); never reuse a thing within a story. Never "
    "name an item or character from the project's own games (Kristin, Brandon, Michelle, a transit card, a "
    "photograph, a number sequence, a storm drain). "
    "NARRATION RULES (plain third-person past tense, 3 to 5 sentences, about one named protagonist; vary the "
    "protagonist across stories; concrete plain words; each narration stands alone): "
    "'missing': the narration never mentions the thing or any synonym; it is about something else in the scene. "
    "'remembered': the thing appears only as a memory, a story about the past, or as gone; it is not present now. "
    "'elsewhere': the narration shows the named thing present at a different, named place in the same story and "
    "says or shows it is not at the relation's place. For a scene_level case that other place is a second named "
    "place outside the scene; for a specific_place case it is a different named spot. "
    "'lookalike': as in (b) and (e). The narration must not state a label or hint at a test. Do not write "
    "positives trivially ('there was a', 'present'); write them as game narration would. Write every "
    "explicit-contrast narration fresh in your own words; never reuse a sentence from any other file. Never use "
    "the things 'copper locket' or 'silver badge'. "
    "SELF-CHECK before finishing: run the project python "
    f"({REPO}/.venv/bin/python -c ...) to load the file and assert the structure above (60 lines, 10 per story, "
    "counts per group, kind, negative_type and contrast, unique ids, scene-level positives do not contain "
    "scene_place case-insensitively, 'missing' narrations do not contain the thing's name lowercased). Print the "
    "result of that check."
)

CASE_CHECK = (
    f"cd {REPO} && set -o pipefail && .venv/bin/python - <<'PY'\n"
    "import json, collections\n"
    "from pathlib import Path\n"
    f"p = Path('{CASES}')\n"
    "cases = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]\n"
    "assert len(cases) == 60, len(cases)\n"
    "assert len({c['id'] for c in cases}) == 60, 'duplicate ids'\n"
    "keys = {'id','story','scene','scene_place','group','kind',"
    "'negative_type','contrast','label','narration','relation','note'}\n"
    "def strip_the(s):\n"
    "    s = s.lower()\n"
    "    return s[4:] if s.startswith('the ') else s\n"
    "prior = set()\n"
    "for f in ('scripts/ringer/environment_narration/j1_screen/heldout.jsonl',):\n"
    "    for l in Path(f).read_text().splitlines():\n"
    "        if l.strip(): prior.add(json.loads(l)['story'].lower())\n"
    "for f in sorted(Path('scripts/ringer/environment_narration/verifier_corpus').glob('cases-*.jsonl')):\n"
    "    for l in f.read_text().splitlines():\n"
    "        if l.strip(): prior.add(json.loads(l)['story'].lower())\n"
    "prior |= {'frontier town','los angeles park','the lead in the park'}\n"
    "corpus_sentences = set()\n"
    "for f in sorted(Path('scripts/ringer/environment_narration/verifier_corpus').glob('cases-*.jsonl')):\n"
    "    for l in f.read_text().splitlines():\n"
    "        if l.strip():\n"
    "            for s in json.loads(l)['narration'].replace('!','.').replace('?','.').split('.'):\n"
    "                if s.strip(): corpus_sentences.add(s.strip().lower())\n"
    "for c in cases:\n"
    "    assert set(c) == keys, (c['id'], sorted(set(c) ^ keys))\n"
    "    r = c['relation']\n"
    "    assert r.keys() == {'thing','place','holder'} and r['holder'] is None, c['id']\n"
    "    assert c['group'] in {'scene_level','specific_place'}, c['id']\n"
    "    assert (c['kind'], c['label']) in {('positive','accept'),('negative','reject')}, c['id']\n"
    "    assert (c['negative_type'] is None) == (c['kind'] == 'positive'), c['id']\n"
    "    assert (c['contrast'] is None) == (c['negative_type'] != 'lookalike'), (c['id'], 'contrast field')\n"
    "    n = c['narration']; nl = n.lower()\n"
    "    sents = [s for s in n.replace('!','.').replace('?','.').split('.') if s.strip()]\n"
    "    assert 3 <= len(sents) <= 5, (c['id'], len(sents))\n"
    "    thing = r['thing'].lower(); place = r['place']; sp = c['scene_place']\n"
    "    assert thing not in {'copper locket','silver badge'}, c['id']\n"
    "    if c['group'] == 'scene_level': assert place == sp, (c['id'], 'scene-level place differs from scene_place')\n"
    "    else:\n"
    "        assert place.lower() != sp.lower(), (c['id'], 'specific place equals scene_place')\n"
    "        assert strip_the(place) in nl, (c['id'], 'specific-place narration never names its spot')\n"
    "    if c['kind'] == 'positive':\n"
    "        assert thing in nl, (c['id'], 'positive never names the thing')\n"
    "        if c['group'] == 'scene_level':\n"
    "            assert strip_the(sp) not in nl, (c['id'], 'scene-level positive names the scene place')\n"
    "    if c['negative_type'] == 'missing': assert thing not in nl, (c['id'], 'missing case names the thing')\n"
    "    for s in sents: assert s.strip().lower() not in corpus_sentences, "
    "(c['id'], 'sentence copied from the corpus')\n"
    "stories = collections.defaultdict(list)\n"
    "for c in cases: stories[c['story']].append(c)\n"
    "assert len(stories) == 6, list(stories)\n"
    "order = []\n"
    "for c in cases:\n"
    "    if c['story'] not in order: order.append(c['story'])\n"
    "other_scene = {1:'missing',2:'remembered',3:'elsewhere',4:'missing',5:'remembered',6:'elsewhere'}\n"
    "other_spec = {1:'remembered',2:'elsewhere',3:'missing',4:'remembered',5:'elsewhere',6:'missing'}\n"
    "for i, s in enumerate(order, 1):\n"
    "    cs = stories[s]\n"
    "    assert s.lower() not in prior, (s, 'story reused')\n"
    "    assert len(cs) == 10, (s, len(cs))\n"
    "    assert len({c['scene'] for c in cs}) == 1 and len({c['scene_place'] for c in cs}) == 1, s\n"
    "    assert len({c['relation']['thing'].lower() for c in cs}) == 10, (s, 'thing reused')\n"
    "    kinds = collections.Counter((c['group'], c['kind'], c['negative_type'], c['contrast']) for c in cs)\n"
    "    want = collections.Counter({\n"
    "        ('scene_level','positive',None,None):2,\n"
    "        ('scene_level','negative','lookalike',False):1, ('scene_level','negative','lookalike',True):1,\n"
    "        ('scene_level','negative',other_scene[i],None):1,\n"
    "        ('specific_place','positive',None,None):2,\n"
    "        ('specific_place','negative','lookalike',False):1, ('specific_place','negative','lookalike',True):1,\n"
    "        ('specific_place','negative',other_spec[i],None):1})\n"
    "    assert kinds == want, (s, kinds)\n"
    "    assert [c['id'] for c in cs] == ['f-%d-%02d' % (i, k) for k in range(1, 11)] or all("
    "c['id'].startswith('f-%d-' % i) for c in cs), s\n"
    "print('scope cases ok')\n"
    "PY"
)

PROBE_SPEC = (
    f"You are the PROBE worker. Working directory: {REPO} (Python 3.12). export PYTHONPATH={REPO} TMPDIR=/tmp; run "
    "`.venv/bin/python` (never uv). Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN "
    ".venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. No network, no live model call, no billed "
    "call, no Worker: you build and test the probe, you NEVER run it with `--run`. Do not git commit. NEVER print "
    "or write any credential. NO regular expressions. Keep the code in the style of the surrounding files (comment "
    "density, naming, idiom). METHOD: write the tests FIRST, watch them fail for the right reason, then implement. "
    f"You own ONLY {PROBE} and a NEW test file {TESTS}. Never touch storygame/, packages/, data/, the plan files, "
    "the corpus, any other script or test. Another worker is writing the cases file "
    f"{CASES} right now: it may not exist when you start, so your tests use small hand-made fixture files in a "
    f"temp dir and never read the real cases file; the lock file {ENV}/j1_scope/lock.json is NOT yours: the "
    "probe's `--lock` mode writes it later when the orchestrator runs it. "
    f"BACKGROUND. Read the preregistration FIRST and follow it exactly: {PREREG}. The probe asks two arms, V0 (the "
    "product's request) and J1m (same question; state gains 'scene' and a 'starting_places' map thing -> place), "
    "on 60 fresh cases (single relation per case) and on two regression cases taken from the frozen T7 corpus "
    "(ids a-022 and d-009). J1c is NOT an arm: its verdict for a fresh case is read from the J1m row when the case "
    "is scene-level and from the V0 row when it is specific-place. TEMPLATE: "
    f"{ENV}/j1_screen_probe.py (read it fully) and its test file {REPO}/tests/test_j1_screen_probe.py. IMPORT "
    "shared helpers from j1_screen_probe (and from verifier_calibration through it) rather than copying: "
    "_request_payload(case, arm, set_name) already builds the V0 and J1m payloads for a corpus case "
    "(set_name 'corpus') and for a single-relation case with `scene` and `relation` (set_name 'heldout'), "
    "plus the client ask path, redaction, stop-reason code, percentile and lock helpers. Do not edit those files. "
    "Reuse the same refusals, fixed-seed order with arms interleaved, atomic rows (temp file then os.replace, "
    "stop_reason 'incomplete' until the last row is written, then null), stop after 3 consecutive unusable replies "
    "and on HTTP 429/5xx, credential redaction. "
    "CASES (schema): id, story, scene, scene_place, group ('scene_level' or 'specific_place'), kind, "
    "negative_type, contrast (true/false for lookalikes, null otherwise), label, narration, relation "
    "{thing, place, holder: null}, note. Validation (`--validate`) checks: exactly these keys; label/kind pairs; "
    "negative_type/kind consistency; contrast only on lookalikes; group consistent with relation.place == "
    "scene_place (scene_level) or != (specific_place); relation holder null; no scene-level positive contains "
    "scene_place (case-insensitive, with or without a leading 'the'); a 'missing' narration does not contain the "
    "thing. It prints counts per group, kind and negative_type, and refuses on any violation. It also checks that "
    "the corpus lock matches and that regression ids a-022 and d-009 exist in the corpus. "
    "J1c RULE (put in one small function and test it): `j1c_arm(case)` returns 'J1m' when relation.holder is "
    "None and relation.place == scene_place (exact string compare), else 'V0'. Add a test that the J1c payload "
    "equals the V0 payload (`_request_payload(case, 'V0', 'heldout')`) when place differs from scene_place and "
    "equals the J1m payload otherwise, and that the V0 and J1m question texts are identical. "
    "MODES: `--validate`; `--lock` (writes the lock json with the cases SHA-256, case count and corpus combined "
    "hash; refuses if validation fails); `--dry-run` (prints: case count, regression case count 2, planned requests "
    "= fresh cases x 2 arms x --samples (default 5) + 2 regression cases x 2 arms x --samples, giving 620 at "
    "60 cases, token estimate, USD ceiling at 1.5x margin); `--run --confirm` (refuses without --confirm, without "
    "--out, with a bad or missing lock, when planned calls exceed --max-calls (default 640), when the ceiling "
    "exceeds --max-usd (default 0.03), or when either Cloudflare environment variable is missing); "
    "`--report --rows F --out F [--carried-rows F]` (markdown report; exit 1 when J1c fails any gate). "
    "Rows carry set 'scope' for fresh cases and 'regression' for the two corpus cases (regression scene = the "
    "case's story, as in the J1 screen). "
    "REPORT. J1c verdict per fresh case sample i = the J1m row's verdict when j1c_arm(case) is 'J1m', else the V0 "
    "row's verdict. Gates, with V0 printed beside each: "
    "F1 zero accepts among all negative samples of J1c (36 cases x 5 = 180); uncertain is not an accept. "
    "F2 at least 54 of the 60 scene-level positive samples are 'accept' for J1c, and no fewer than V0's count "
    "on the same samples. "
    "F3 at least 54 of the 60 specific-place positive samples are 'accept' for J1c. "
    "Carried: from the J1 screen rows file (default bench/results/environment-narration/j1-screen-rows.json, "
    "override with --carried-rows; if absent print 'carried gates: rows file missing' and treat as FAIL) compute "
    "the V0 corpus C1 (zero false accepts over reject-labelled relation samples) and C2 (false rejects <= 5% and "
    "strict failures <= 5% of accept-labelled relation samples excluding category invention_unreported), using the "
    "same definitions as j1_screen_probe's metrics (import them), and compare the carried rows' jev_model with "
    "the fresh rows' jev_model: a mismatch is a FAIL line 'carried gates void: Jev model changed'. Overall PASS "
    "only if F1, F2, F3 and the carried gates all hold. "
    "Also report (not gating): per group and per negative_type, every J1c negative sample that was not a reject "
    "with its score and case id; sample-to-sample disagreement; latency p50 and p95; model and version; the "
    "MECHANISM CHECK: J1m's accept count and mean score on the 12 specific-place lookalike cases against V0's "
    "(print a line saying whether J1m accepted at least one); the regression rows a-022 and d-009 per arm with "
    "score ranges. "
    "TESTS in tests/test_j1_scope_probe.py, hermetic with a fake client (never a live worker): the J1c rule and "
    "payload equalities above; `--validate` on a good and a bad fixture (one violation per rule you implemented); "
    "`--lock` then `--run` refuses on a changed fixture; planned-call arithmetic (620 for 60 cases) and "
    "deterministic seeded order; run refusals (no --confirm, no --out, bad lock, over --max-calls, over --max-usd, "
    "missing environment); a fake-client run writes all rows with a final null stop_reason, stops on three unusable "
    "replies, and leaves an 'incomplete' document if the client raises; the report on hand-made rows for a pass and "
    "for a fail of each of F1, F2, F3, the carried-gate void on a model mismatch and a missing carried file; no "
    "credential value in dry-run output. Add only tests that cover real behavior; no redundant ones. "
    "Finally run the new tests plus tests/test_j1_screen_probe.py, then `.venv/bin/python -m ruff check --fix` and "
    "`ruff format` on your owned files, and report the test counts."
)

PROBE_CHECK = (
    f"cd {REPO} && export PYTHONPATH={REPO} TMPDIR=/tmp && set -o pipefail "
    "&& env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q "
    "-p no:cacheprovider --no-cov tests/test_j1_scope_probe.py tests/test_j1_screen_probe.py "
    "2>&1 | tee /tmp/j1-scope-tests.out | tail -15 "
    "&& ! grep -Eq '[0-9]+ failed|FAILED|ERROR' /tmp/j1-scope-tests.out "
    "&& grep -Eq '[0-9]+ passed' /tmp/j1-scope-tests.out "
    f"&& .venv/bin/python -m ruff check {PROBE} {TESTS} "
    f"&& .venv/bin/python -m ruff format --check {PROBE} {TESTS} "
    f"&& ! grep -n 'import re$' {PROBE} && grep -q 'os.replace' {PROBE} && grep -q 'def j1c_arm' {PROBE}"
)


def _task(key: str, task_type: str, owned: list[str], verified: str, spec: str, check: str, timeout: int) -> dict:
    return {
        "key": key,
        "task_type": task_type,
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "full_access": True,
        "max_attempts": 2,
        "timeout_s": timeout,
        "check_timeout_s": 1800 if task_type == "code-feature" else 300,
        "ownership": owned,
        "expect_files": owned,
        "verified": verified,
        "spec": spec,
        "check": check,
    }


MANIFEST = {
    "run_name": "t9h-j1-scope-build",
    "workdir": "/home/bcorfman/dev/ringer-work/t9h-j1-scope-build",
    "max_parallel": 2,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        _task(
            "j1-scope-cases",
            "docs",
            [CASES],
            "60 fresh scope cases in 6 stories, structure and naming rules checked by script",
            CASE_SPEC,
            CASE_CHECK,
            2400,
        ),
        _task(
            "j1-scope-probe",
            "code-feature",
            [PROBE, TESTS],
            "V0/J1m probe with J1c reading, lock, atomic rows, F1-F3 and carried gates, hermetic tests; nothing billed",
            PROBE_SPEC,
            PROBE_CHECK,
            3600,
        ),
    ],
}

if __name__ == "__main__":
    out = Path(__file__).with_name("build-t9h-j1-scope.json")
    out.write_text(json.dumps(MANIFEST, indent=2) + "\n")
    print(out)
