# ruff: noqa: E501
"""Independent offline check of the frozen 1A password/officer arms and their replay. No network, no billing.

Prints "1A FREEZE VALIDATION OK" only if every arm differs from its control by exactly the planned bytes.
Plan: .plans/1a-password-and-officer-plan.md; preregistration: .plans/1a-password-officer-prereg.md.
"""

import difflib
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "bench/results/1a-password-officer"
PKG = ROOT / "data/stories/continuity-initiative"
errors: list[str] = []
notes: list[str] = []


def need(condition, message):
    if not condition:
        errors.append(message)


# stage -> (control arm, other arms, endpoint ids)
STAGES = {
    "officer": ("CTRL", ["BIO"], ["OFF6", "OFF7"]),
    "raw": ("BIO", ["ALIAS"], ["RAW7"]),
    "walt": ("CTRL", ["BIO"], ["WALT"]),
    "password": ("CTRL", ["SUB", "ADD"], ["PW"]),
    "voice": ("CTRL", ["NOVOICE"], ["VOICE8", "VOICE9"]),
    "recovery": ("REC", [], ["REC8"]),
}
COMMANDS = {
    "OFF6": "Greet the officer.",
    "OFF7": "Ask the officer where Dr. McGehee is.",
    "RAW7": "Officer, do you know where Dr. McGehee is?",
    "WALT": "Ask the neighbor what he saw.",
    "PW": "Type in the password.",
    "VOICE8": "Greet the officer.",
    "VOICE9": "Ask the officer where Dr. McGehee is.",
    "REC8": "Greet the officer.",
}
VOICE_STATEMENT = '  statement: "Kristin reads the kitchen walls as a life interrupted: the calendar with Saturday circled and the photograph of the two of them at a lake."'
VOICE_LINE = "- Officer Reyes may say this aloud: Kristin reads the kitchen walls as a life interrupted: the calendar with Saturday circled and the photograph of the two of them at a lake."
REYES_LINE = "- Officer Reyes is a young, polite federal patrol officer who works from a printed list and does not like what the list asks of him."
REYES_BLOCK = [
    "### Officer Reyes",
    "",
    "A young, polite federal patrol officer who works from a printed list and does not like what the list asks of him.",
    "",
]
WALT_BLOCK = [
    "### Walt Pruitt",
    "",
    "A retired bus driver in his seventies whose wife is one of the missing. He is tired, careful with his words, and unsure what he saw.",
    "",
]
OWN_RULE = "- Say who owns a thing the first time you name it: Michelle's phone, Kristin's laptop."
OWN_RULE_SUB = "- Say who owns a thing the first time you name it: Michelle's phone."
STORES = "- Michelle's phone stores only Michelle's things. Kristin's laptop stores only Kristin's things."
STORES_SUB = "- Michelle's phone stores only Michelle's things."
PHONE_LINE = "- Michelle's phone is on the kitchen floor."
LAPTOP_LINE = "- Kristin's laptop is on the passenger seat of Kristin's truck."
ADD_LINE = "- Michelle's phone showed a password prompt."


def load(stage, arm):
    path = OUT / f"frozen-{stage}-{arm}.json"
    need(path.exists(), f"missing {path.name}")
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    need(data.get("arm") == arm and data.get("stage") == stage, f"{path.name}: wrong stage/arm fields")
    return {e["n"]: e for e in data["endpoints"]}


def line_diff(a, b):
    added, removed = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a.split("\n"), b=b.split("\n"), autojunk=False).get_opcodes():
        if tag != "equal":
            removed += a.split("\n")[i1:i2]
            added += b.split("\n")[j1:j2]
    return added, removed


def same_envelope(c, k, label):
    for key in sorted(set(c["wire_payload"]) | set(k["wire_payload"])):
        if key != "user":
            need(
                c["wire_payload"].get(key) == k["wire_payload"].get(key),
                f"{label}: wire field {key!r} differs from control",
            )


ANCHOR = "# Expanded Scene Outline"
ALIAS_OLD = "  - Reyes\n  narrator_bio: A young, polite federal patrol officer"
ALIAS_NEW = "  - Reyes\n  - officer\n  narrator_bio: A young, polite federal patrol officer"


def package_diff(name, rel, block=None, alias=False, also=()):
    """Arm package file must equal the shipped file plus exactly the planned insertion."""
    base = (PKG / rel).read_text(encoding="utf-8")
    arm = OUT / "pkg" / name / rel
    need(arm.exists(), f"missing arm package file pkg/{name}/{rel}")
    if not arm.exists():
        return
    if alias:
        need(base.count(ALIAS_OLD) == 1, "shipped world.yaml no longer has the expected Reyes alias anchor")
        expected = base.replace(ALIAS_OLD, ALIAS_NEW)
    else:
        # The Reyes heading was later added to the shipped plot.md (PR #753); the arm packages were built from the
        # file as it was, so compare against the pre-change file (shipped minus that block).
        base = base.replace("\n".join(REYES_BLOCK) + "\n", "") if "\n".join(REYES_BLOCK) in base else base
        need(base.count("\n" + ANCHOR + "\n") == 1, "shipped plot.md no longer has the expected anchor")
        expected = base.replace("\n" + ANCHOR + "\n", "\n" + "\n".join(block) + "\n" + ANCHOR + "\n")
    actual = arm.read_text(encoding="utf-8")
    need(
        actual == expected,
        f"pkg/{name}/{rel}: not the shipped file plus exactly the planned insertion; diff {[ln for ln in difflib.unified_diff(expected.split(chr(10)), actual.split(chr(10)), lineterm='', n=0)][:12]}",
    )
    # every other package file is byte-identical to the shipped package
    for path in sorted(PKG.rglob("*")):
        if path.is_file() and path.relative_to(PKG).as_posix() not in {rel, *also}:
            twin = OUT / "pkg" / name / path.relative_to(PKG)
            need(
                twin.exists() and twin.read_bytes() == path.read_bytes(),
                f"pkg/{name}: {path.relative_to(PKG)} differs from shipped",
            )


frozen = {}
for stage, (control, others, endpoints) in STAGES.items():
    for arm in [control, *others]:
        frozen[(stage, arm)] = load(stage, arm)
    for arm, eps in ((a, frozen[(stage, a)]) for a in [control, *others]):
        need(sorted(eps) == sorted(endpoints), f"{stage}-{arm}: endpoints {sorted(eps)} != {sorted(endpoints)}")
        for n, e in eps.items():
            need(e["command"] == COMMANDS[n], f"{stage}-{arm}-{n}: command {e['command']!r} != {COMMANDS[n]!r}")
            user = e["wire_payload"].get("user", "")
            need(hashlib.sha256(user.encode()).hexdigest() == e["user_sha256"], f"{stage}-{arm}-{n}: user_sha256 stale")
            need(
                user.rstrip().endswith(COMMANDS[n]) or COMMANDS[n] in user,
                f"{stage}-{arm}-{n}: PLAYER command missing from user text",
            )
            need(bool(e["wire_payload"].get("system")), f"{stage}-{arm}-{n}: empty system text")

    # arms compared with their control
    for arm in others:
        for n in endpoints:
            if n not in frozen[(stage, control)] or n not in frozen[(stage, arm)]:
                continue
            c, k = frozen[(stage, control)][n], frozen[(stage, arm)][n]
            label = f"{stage}-{arm}-{n}"
            same_envelope(c, k, label)
            added, removed = line_diff(c["wire_payload"]["user"], k["wire_payload"]["user"])
            if stage == "officer" or (stage == "walt"):
                name = "Officer Reyes" if stage == "officer" else "Walt Pruitt"
                keyword = "printed list" if stage == "officer" else "bus driver"
                if not added and not removed:
                    notes.append(
                        f"{label}: NO PROMPT DIFFERENCE (bio line not introduced); cell carries no comparison and is dropped from billing"
                    )
                else:
                    need(not removed, f"{label}: removes control lines {removed[:3]}")
                    need(
                        len(added) == 1 and added[0].startswith(f"- {name}") and keyword in added[0],
                        f"{label}: expected exactly one added CHARACTERS line for {name}, got {added[:3]}",
                    )
                    # the added line must sit in CHARACTERS (before SCENE:)
                    user = k["wire_payload"]["user"]
                    if added:
                        need(
                            added[0] in user and user.index(added[0]) < user.index("SCENE:"),
                            f"{label}: added line is not in CHARACTERS",
                        )
            elif stage == "voice":
                cu, ku = c["wire_payload"]["user"], k["wire_payload"]["user"]
                need(
                    cu.count(VOICE_LINE + "\n") == 1,
                    f"{label}: control lacks the earned-knowledge speaker line (the probe precondition)",
                )
                need(
                    cu.count(REYES_LINE + "\n") == 1 and ku.count(REYES_LINE + "\n") == 1,
                    f"{label}: the Reyes bio line must be in both arms",
                )
                need(
                    ku == cu.replace(VOICE_LINE + "\n", ""),
                    f"{label}: NOVOICE is not the control minus exactly the one speaker line; diff +{added[:3]} -{removed[:3]}",
                )
            elif stage == "raw":
                notes.append(
                    f"{label}: alias effect on prompt: +{len(added)} -{len(removed)} lines {added[:2]} {removed[:2]}"
                )
            elif stage == "password":
                cu, ku = c["wire_payload"]["user"], k["wire_payload"]["user"]
                if arm == "SUB":
                    need(
                        cu.count(OWN_RULE) == 1 and cu.count(STORES) == 1 and cu.count(LAPTOP_LINE + "\n") == 1,
                        f"{label}: control lacks the exact laptop lines",
                    )
                    expected = (
                        cu.replace(OWN_RULE, OWN_RULE_SUB).replace(STORES, STORES_SUB).replace(LAPTOP_LINE + "\n", "")
                    )
                    need(
                        ku == expected,
                        f"{label}: user text is not control minus exactly the three laptop mentions; diff +{added[:4]} -{removed[:4]}",
                    )
                    need("laptop" not in ku.lower(), f"{label}: 'laptop' remains in the SUB prompt")
                    need("Michelle's phone is on the kitchen floor." in ku, f"{label}: phone line was removed")
                if arm == "ADD":
                    need(cu.count(PHONE_LINE + "\n") == 1, f"{label}: control lacks the phone placement line")
                    expected = cu.replace(PHONE_LINE + "\n", PHONE_LINE + "\n" + ADD_LINE + "\n")
                    need(
                        ku == expected,
                        f"{label}: user text is not control plus exactly the one context line after the phone line; diff +{added[:4]} -{removed[:4]}",
                    )
                    need("password prompt" not in cu.lower(), f"{label}: control already mentions a password prompt")

# control sanity (diagnostics the reviewer reads)
for key, label in (("PW", "password"), ("OFF6", "officer"), ("OFF7", "officer"), ("WALT", "walt")):
    stage = label
    ctrl = frozen[(stage, STAGES[stage][0])].get(key)
    if ctrl:
        u = ctrl["wire_payload"]["user"]
        notes.append(
            f"{stage}-{key}: control user {len(u)} chars; Reyes={u.count('Reyes')} Walt={u.count('Walt')} Jenkins={u.count('Jenkins')} laptop={u.lower().count('laptop')}"
        )

# arm package edits
package_diff("officer-bio", "plot.md", REYES_BLOCK)
package_diff("walt-bio", "plot.md", WALT_BLOCK)
package_diff("officer-alias", "plot.md", REYES_BLOCK, also=("world.yaml",))
package_diff("officer-novoice", "plot.md", REYES_BLOCK, also=("knowledge.yaml",))
_kn = (PKG / "knowledge.yaml").read_text(encoding="utf-8")
_nv = OUT / "pkg/officer-novoice/knowledge.yaml"
need(_kn.count(VOICE_STATEMENT + "\n") == 1, "shipped knowledge.yaml lost the k_sl_1a_g_r2 statement anchor")
need(
    _nv.exists()
    and _nv.read_text(encoding="utf-8")
    == _kn.replace(VOICE_STATEMENT + "\n", VOICE_STATEMENT + "\n  voiceable: false\n"),
    "pkg/officer-novoice/knowledge.yaml is not the shipped file plus exactly `voiceable: false` after the k_sl_1a_g_r2 statement",
)
# the alias package edits world.yaml too; plot.md above is checked with the other file identical, so verify world.yaml separately
alias_world = OUT / "pkg/officer-alias/world.yaml"
need(
    alias_world.exists()
    and alias_world.read_text(encoding="utf-8")
    == (PKG / "world.yaml").read_text(encoding="utf-8").replace(ALIAS_OLD, ALIAS_NEW),
    "pkg/officer-alias/world.yaml is not the shipped file plus exactly the `officer` alias",
)

# recovery stage: the provider's recovery request for the recorded fused-segment reply at the officer greeting
_rec = frozen[("recovery", "REC")].get("REC8")
_first = frozen[("officer", "BIO")].get("OFF6")
if _rec and _first:
    rp, fp0 = _rec["wire_payload"], _first["wire_payload"]
    need(rp["user"] == fp0["user"], "recovery: the user text must equal the frozen officer-BIO greeting request")
    need(rp["system"].startswith(fp0["system"] + " "), "recovery: system must be the frozen system text plus a suffix")
    need(
        "Your last answer was not valid" in rp["system"][len(fp0["system"]) :],
        "recovery: suffix lacks the provider's correction instruction",
    )
    need(
        all(rp.get(k) == fp0.get(k) for k in ("max_tokens", "response_format")),
        "recovery: max_tokens/response_format differ from the first request",
    )
    need(
        _rec.get("first_user_sha256") == hashlib.sha256(fp0["user"].encode()).hexdigest(),
        "recovery: first_user_sha256 missing or wrong",
    )
    notes.append(f"recovery: suffix = {rp['system'][len(fp0['system']) :][:260]!r}")

# provenance
prov_path = OUT / "provenance.json"
need(prov_path.exists(), "missing provenance.json")
if prov_path.exists():
    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    for key in ("head", "dirty_files", "package_sha256", "frozen_sha256", "variation_script"):
        need(key in prov, f"provenance.json missing {key!r}")

# replay: dry-run guard, caps, order, no network
replay = ROOT / "scripts/ringer/1a-password-officer/replay.py"
need(replay.exists(), "missing replay.py")
if replay.exists():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "rows.json"
        dry = subprocess.run(
            [sys.executable, str(replay), "password", str(target), "1", "12"], capture_output=True, text=True, cwd=ROOT
        )
        need(
            dry.returncode == 0
            and "requests 36" in dry.stdout
            and "dry run: nothing sent" in dry.stdout
            and not target.exists(),
            f"replay dry run wrong (rc {dry.returncode}): {dry.stdout[-200:]} {dry.stderr[-200:]}",
        )
        voice = subprocess.run(
            [sys.executable, str(replay), "voice", str(target), "0", "0"], capture_output=True, text=True, cwd=ROOT
        )
        need(
            "requests 4" in voice.stdout and voice.returncode == 0,
            f"replay voice stage count wrong: {voice.stdout[-200:]}",
        )
        rec = subprocess.run(
            [sys.executable, str(replay), "recovery", str(target), "1", "12"], capture_output=True, text=True, cwd=ROOT
        )
        need(
            "requests 12" in rec.stdout and rec.returncode == 0,
            f"replay recovery stage count wrong: {rec.stdout[-200:]}",
        )
        smoke = subprocess.run(
            [sys.executable, str(replay), "officer", str(target), "0", "0"], capture_output=True, text=True, cwd=ROOT
        )
        need("requests 4" in smoke.stdout and smoke.returncode == 0, f"replay smoke count wrong: {smoke.stdout[-200:]}")
        over = subprocess.run(
            [sys.executable, str(replay), "password", str(target), "1", "13"], capture_output=True, text=True, cwd=ROOT
        )
        need(over.returncode != 0, "replay accepted sample 13")
        # stub transport: order and cap, no network
        import importlib.util

        spec = importlib.util.spec_from_file_location("replay_1a", replay)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sent = []

        def stub(payload):
            sent.append(payload)
            return json.dumps({"narration": json.dumps({"segments": [{"kind": "narration", "text": "ok"}]})}).encode()

        rows_path = Path(tmp) / "stub-rows.json"
        rows = module.run("password", rows_path, 1, 2, send=stub)
        order = [(r["sample"], r["n"], r["arm"]) for r in rows]
        need(
            order == [(s, "PW", a) for s in (1, 2) for a in ("CTRL", "SUB", "ADD")], f"replay row order wrong: {order}"
        )
        need(len(sent) == 6 and all(r["error"] is None for r in rows), "replay stub run wrong")
        try:
            module.run("password", rows_path, 1, 1, send=stub)
            errors.append("replay overwrote an existing rows file")
        except FileExistsError:
            pass

        def boom(payload):
            raise RuntimeError("transport down")

        rows = module.run("password", Path(tmp) / "err-rows.json", 1, 1, send=boom)
        need(
            len(rows) == 3 and all(r["error"] and r["narration"] is None for r in rows),
            "replay did not keep transport errors as rows",
        )

for note in notes:
    print("NOTE", note)
if errors:
    print("1A FREEZE VALIDATION FAILED")
    for message in errors:
        print(" -", message)
    sys.exit(1)
print("1A FREEZE VALIDATION OK")
