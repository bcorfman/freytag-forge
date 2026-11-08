# ruff: noqa: E501
"""Freeze 1A narrator payload comparisons without making model calls."""

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import bench.frozen_prompts as fp  # noqa: E402
from bench.core import load_variation  # noqa: E402

OUT = ROOT / "bench/results/1a-password-officer"
PACKAGE = ROOT / "data/stories/continuity-initiative"
VARIATION_PATH = ROOT / "bench/variations/1a-password-officer.json"

OFFICER_INPUTS = [
    "Turn on the phone.",
    "Unlock the phone.",
    "Type in the password.",
    "Type the password into Michelle's phone.",
    "Turn off the phone.",
    "Turn on the phone.",
    "Turn off the phone.",
    "Greet the officer.",
    "Ask the officer where Dr. McGehee is.",
]
RAW_INPUTS = OFFICER_INPUTS[:8] + ["Officer, do you know where Dr. McGehee is?"]
WALT_INPUTS = [
    "Examine the back door.",
    "Look at the wall calendar.",
    "Look at the photograph.",
    "Search the drawer.",
    "Search beneath the drawer.",
    "Go outside.",
    "Ask the neighbor what he saw.",
]
PASSWORD_INPUTS = [
    "Turn on the phone.",
    "Unlock the phone.",
    "Type in the password.",
]
VOICE_INPUTS = [
    "Turn on the phone.",
    "Unlock the phone.",
    "Type in the password.",
    "Type the password into Michelle's phone.",
    "Turn off the phone.",
    "Look at the wall calendar.",
    "Look at the photograph.",
    "Greet the officer.",
    "Ask the officer where Dr. McGehee is.",
]
CASES = {
    "officer": {
        "inputs": OFFICER_INPUTS,
        "arms": {"CTRL": "shipped", "BIO": "officer-bio"},
        # OFF6 and OFF7 are historical endpoint ids; they now identify commands 8 and 9.
        "endpoints": [("OFF6", 8), ("OFF7", 9)],
    },
    "raw": {"inputs": RAW_INPUTS, "arms": {"BIO": "officer-bio", "ALIAS": "officer-alias"}, "endpoints": [("RAW7", 9)]},
    "walt": {"inputs": WALT_INPUTS, "arms": {"CTRL": "shipped", "BIO": "walt-bio"}, "endpoints": [("WALT", 7)]},
    "password": {"inputs": PASSWORD_INPUTS, "arms": {"CTRL": "shipped"}, "endpoints": [("PW", 3)]},
    "voice": {
        "inputs": VOICE_INPUTS,
        "arms": {"CTRL": "officer-bio", "NOVOICE": "officer-novoice"},
        "endpoints": [("VOICE8", 8), ("VOICE9", 9)],
    },
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def package_files(path):
    return {
        str(item.relative_to(path)).replace("\\", "/"): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def prepare_packages():
    package_root = OUT / "pkg"
    if package_root.exists():
        shutil.rmtree(package_root)
    package_root.mkdir(parents=True)
    for name, bio in {
        "officer-bio": "### Officer Reyes\n\nA young, polite federal patrol officer who works from a printed list and does not like what the list asks of him.",
        "officer-novoice": "### Officer Reyes\n\nA young, polite federal patrol officer who works from a printed list and does not like what the list asks of him.",
        "walt-bio": "### Walt Pruitt\n\nA retired bus driver in his seventies whose wife is one of the missing. He is tired, careful with his words, and unsure what he saw.",
        "officer-alias": "### Officer Reyes\n\nA young, polite federal patrol officer who works from a printed list and does not like what the list asks of him.",
    }.items():
        destination = package_root / name
        shutil.copytree(PACKAGE, destination)
        plot = destination / "plot.md"
        text = plot.read_text(encoding="utf-8")
        marker = "# Expanded Scene Outline"
        assert text.count(marker) == 1
        text = text.replace(marker, bio + "\n\n" + marker, 1)
        plot.write_text(text, encoding="utf-8")
        if name == "officer-alias":
            world = destination / "world.yaml"
            text = world.read_text(encoding="utf-8")
            old = "  - Reyes\n  narrator_bio: A young, polite federal patrol officer"
            assert text.count(old) == 1
            world.write_text(
                text.replace(old, "  - Reyes\n  - officer\n  narrator_bio: A young, polite federal patrol officer", 1),
                encoding="utf-8",
            )
        if name == "officer-novoice":
            knowledge = destination / "knowledge.yaml"
            text = knowledge.read_text(encoding="utf-8")
            statement = '  statement: "Kristin reads the kitchen walls as a life interrupted: the calendar with Saturday circled and the photograph of the two of them at a lake."'
            assert text.count(statement) == 1
            knowledge.write_text(text.replace(statement, statement + "\n  voiceable: false", 1), encoding="utf-8")


def capture_one(stage, arm, package_name, inputs, endpoint_id, index):
    variation = load_variation(VARIATION_PATH)
    variation["scripts"] = {"1A": [{"name": stage, "inputs": inputs}]}
    variation["_package_path"] = str(PACKAGE if package_name == "shipped" else OUT / "pkg" / package_name)
    fp.SCENE = "1A"
    states, _ = fp._prefix_states(variation, [index])
    state = states[index - 1]
    payload, _ = fp._capture_wire_payload(state, inputs[index - 1])
    return {
        "n": endpoint_id,
        "command": inputs[index - 1],
        "wire_payload": payload,
        "user_sha256": hashlib.sha256(payload["user"].encode()).hexdigest(),
    }


def counts(payload):
    system, user = len(payload["system"]), len(payload["user"])
    return system, user, system + user


def print_counts(stage, arm, endpoint, payload, control):
    current = counts(payload)
    base = counts(control)
    print(
        f"{stage} {arm} {endpoint} system/user/total {current[0]}/{current[1]}/{current[2]} delta {current[0] - base[0]}/{current[1] - base[1]}/{current[2] - base[2]}"
    )


def ensure_password_context(payload):
    payload = copy.deepcopy(payload)
    lines = payload["user"].split("\n")
    anchors = {
        "phone": "- Michelle's phone is on the kitchen floor.",
        "laptop": "- Kristin's laptop is on the passenger seat of Kristin's truck.",
    }
    storage = "- Michelle's phone stores only Michelle's things. Kristin's laptop stores only Kristin's things."
    assert lines.count(storage) == 1
    insert_at = lines.index(storage) + 1
    for key in ("phone", "laptop"):
        line = anchors[key]
        if lines.count(line) == 0:
            lines.insert(insert_at, line)
            insert_at += 1
        else:
            assert lines.count(line) == 1
    payload["user"] = "\n".join(lines)
    return payload


def derive_password(control):
    sub = copy.deepcopy(control)
    lines = sub["user"].split("\n")
    edits = {
        "- Say who owns a thing the first time you name it: Michelle's phone, Kristin's laptop.": "- Say who owns a thing the first time you name it: Michelle's phone.",
        "- Michelle's phone stores only Michelle's things. Kristin's laptop stores only Kristin's things.": "- Michelle's phone stores only Michelle's things.",
    }
    for old, new in edits.items():
        assert lines.count(old) == 1
        lines[lines.index(old)] = new
    deleted = "- Kristin's laptop is on the passenger seat of Kristin's truck."
    # The current package may already omit this optional location fact.
    assert lines.count(deleted) <= 1
    if deleted in lines:
        lines.remove(deleted)
    sub["user"] = "\n".join(lines)
    add = copy.deepcopy(control)
    line = "- Michelle's phone is on the kitchen floor."
    add_lines = add["user"].split("\n")
    if add_lines.count(line) == 1:
        anchor = line
    else:
        anchor = "- Michelle's phone stores only Michelle's things. Kristin's laptop stores only Kristin's things."
        assert add_lines.count(anchor) == 1
    add_lines.insert(add_lines.index(anchor) + 1, "- Michelle's phone showed a password prompt.")
    add["user"] = "\n".join(add_lines)
    return sub, add


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    prepare_packages()
    frozen = {}
    controls = {}
    try:
        for stage, case in CASES.items():
            frozen[stage] = {}
            for arm, package_name in case["arms"].items():
                endpoints = []
                for endpoint_id, index in case["endpoints"]:
                    try:
                        endpoint = capture_one(stage, arm, package_name, case["inputs"], endpoint_id, index)
                        if stage == "password" and arm == "CTRL":
                            endpoint["wire_payload"] = ensure_password_context(endpoint["wire_payload"])
                            endpoint["user_sha256"] = hashlib.sha256(
                                endpoint["wire_payload"]["user"].encode()
                            ).hexdigest()
                    except Exception as error:
                        if arm == "CTRL":
                            (OUT / "capture-notes.txt").write_text(
                                f"{stage} {arm} {endpoint_id}: {error}\n", encoding="utf-8"
                            )
                            raise
                        raise
                    endpoints.append(endpoint)
                    if arm == "CTRL":
                        controls[(stage, endpoint_id)] = endpoint["wire_payload"]
                frozen[stage][arm] = endpoints
            if stage == "password":
                endpoint = frozen[stage]["CTRL"][0]
                sub, add = derive_password(endpoint["wire_payload"])
                for arm, payload in (("SUB", sub), ("ADD", add)):
                    frozen[stage][arm] = [
                        {
                            "n": "PW",
                            "command": endpoint["command"],
                            "wire_payload": payload,
                            "user_sha256": hashlib.sha256(payload["user"].encode()).hexdigest(),
                        }
                    ]
            for arm, endpoints in frozen[stage].items():
                write_json(OUT / f"frozen-{stage}-{arm}.json", {"stage": stage, "arm": arm, "endpoints": endpoints})
                for endpoint in endpoints:
                    print_counts(
                        stage,
                        arm,
                        endpoint["n"],
                        endpoint["wire_payload"],
                        controls.get((stage, endpoint["n"]), endpoint["wire_payload"]),
                    )
    except Exception:
        raise
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    provenance = {
        "head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip(),
        "dirty_files": status,
        "package_sha256": package_files(PACKAGE),
        "frozen_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(OUT.glob("frozen-*.json"))
        },
        "variation_script": {stage: case["inputs"] for stage, case in CASES.items()},
    }
    write_json(OUT / "provenance.json", provenance)


if __name__ == "__main__":
    main()
