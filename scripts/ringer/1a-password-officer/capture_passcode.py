# ruff: noqa: E501
"""Freeze the offline 1A passcode narrator payloads."""

import copy
import difflib
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
from storygame.runtime.capture import WorldCapture  # noqa: E402
from storygame.runtime.engine import RuntimeEngine  # noqa: E402
from storygame.runtime.world_model import world_for  # noqa: E402

OUT = ROOT / "bench/results/1a-passcode-round2"
PACKAGE = ROOT / "data/stories/continuity-initiative"
VARIATION_PATH = ROOT / "bench/variations/1a-passcode-round2.json"
INPUTS = ["Pick up Michelle's phone.", "Turn on the phone."]
ENDPOINTS = [
    ("PW1", "Type in the password."),
    ("PW2", "Type in the passcode."),
    ("PW3", "Type the passcode into Michelle's phone."),
]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def package_files(path):
    return {
        str(item.relative_to(path)).replace("\\", "/"): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def capture_one(package_path, command):
    """Freeze the narrator request with Michelle's phone held by Kristin.

    The stub prefix cannot move the phone, so the held state is a plain World.move (the operation a
    captured pickup applies). The offline matcher answers that the command refers to the phone; this
    is an assumption of the frozen screen, not a measured matcher decision.
    """
    variation = load_variation(VARIATION_PATH)
    variation["scripts"] = {"1A": [{"name": "passcode-round2", "inputs": INPUTS + [command]}]}
    variation["_package_path"] = str(package_path)
    fp.SCENE = "1A"
    states, _ = fp._prefix_states(variation, [3])
    state = states[2]
    world_for(state.package, state.facts).move("michelle_phone", "kristin")
    provider = fp._offline_capture_provider(state)
    calls = []

    def send(wire_payload):
        calls.append(copy.deepcopy(wire_payload))
        if fp._is_narration_payload(wire_payload):
            return fp._CANNED_REPLY
        return json.dumps({"narration": json.dumps({"refers": ["Michelle's phone"], "same_as": {}})}).encode()

    provider._send_http = send
    RuntimeEngine(state, provider, capture=WorldCapture(provider, lambda _state, _questions: None)).turn(command)
    narration = [payload for payload in calls if fp._is_narration_payload(payload)]
    if len(narration) != 1:
        raise RuntimeError(f"expected one narrator payload, found {len(narration)}")
    return narration[0]


def section_lines(user, section):
    lines = user.splitlines()
    try:
        start = lines.index(section + ":")
    except ValueError:
        return []
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].endswith(":") and lines[index].isupper():
            end = index
            break
    return lines[start:end]


def placement_line(payload):
    return next((line for line in payload["user"].splitlines() if line.startswith("- Michelle's phone.")), None)


def prepare_access_package():
    destination = OUT / "pkg/access"
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(PACKAGE, destination)
    knowledge = destination / "knowledge.yaml"
    text = knowledge.read_text(encoding="utf-8")
    record = """- id: k_1a_michelle_phone_access
  statement: Michelle's phone uses a passcode. Kristin knows it because Michelle is her best friend.
  entity_ids: [michelle_phone]
  aliases: [Michelle's phone passcode]
  leak_terms: []
  voiceable: false
  audience: {kind: public, player_visible: true}
  available_in_scenes: [1A]
  establishes: [{op: assert, fact_id: scene_1a_entry_known, value: true}]
  source: {kind: scene_entry}
"""
    marker = "- id: k_scene_1a_entry"
    start = text.index(marker)
    next_record = text.find("- id: ", start + len(marker))
    assert text.count(marker) == 1 and next_record != -1
    knowledge.write_text(text[:next_record] + record + text[next_record:], encoding="utf-8")


def counts(payload):
    system, user = len(payload["system"]), len(payload["user"])
    return system, user, system + user


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    control = {}
    first_payload = None
    try:
        for endpoint, command in ENDPOINTS:
            payload = capture_one(PACKAGE, command)
            control[endpoint] = payload
            if first_payload is None:
                first_payload = payload
                print(f"CTRL phone placement: {placement_line(payload)}")
                print("CTRL SCENE section:")
                print("\n".join(section_lines(payload["user"], "SCENE")))
    except Exception as error:
        (OUT / "capture-notes.txt").write_text(f"CTRL capture failed: {error}\n", encoding="utf-8")
        raise

    prepare_access_package()
    access = {endpoint: capture_one(OUT / "pkg/access", command) for endpoint, command in ENDPOINTS}
    notes = [
        "Observed prefix state from the CTRL payload:",
        f"phone placement line: {placement_line(first_payload)}",
        "State: the stub prefix cannot move the phone, so Michelle's phone is moved to Kristin with World.move after the prefix and the offline matcher is set to answer that the command refers to it (an assumption, not a measured matcher decision). No lock axis exists; the locked condition is carried only by the ACCESS statement.",
        "device lines:",
    ]
    notes.extend(
        line for line in first_payload["user"].splitlines() if "phone" in line.lower() or "laptop" in line.lower()
    )
    notes.append("")
    for endpoint, _ in ENDPOINTS:
        ctrl_lines = control[endpoint]["user"].splitlines()
        access_lines = access[endpoint]["user"].splitlines()
        statement_lines = [line for line in access_lines if "Michelle's phone uses a passcode" in line]
        notes.append(f"{endpoint} ACCESS statement placement:")
        notes.append(
            f"section: {next((name for name in ('SCENE', 'CHARACTERS', 'THINGS') if any(line == name + ':' for line in access_lines[: access_lines.index(statement_lines[0]) + 1])), 'elsewhere')}"
        )
        notes.extend(statement_lines)
        diff = list(
            difflib.unified_diff(
                ctrl_lines, access_lines, fromfile=f"CTRL-{endpoint}", tofile=f"ACCESS-{endpoint}", lineterm=""
            )
        )
        meaningful = [line for line in diff if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))]
        other = [line for line in meaningful if "Michelle's phone uses a passcode" not in line]
        if other:
            print(f"{endpoint} full line diff:")
            print("\n".join(diff))
            notes.append(f"{endpoint} full line diff:")
            notes.extend(diff)
        for arm, payload in (("CTRL", control[endpoint]), ("ACCESS", access[endpoint])):
            item = {
                "arm": arm,
                "endpoint": {
                    "n": endpoint,
                    "command": dict(ENDPOINTS)[endpoint],
                    "wire_payload": payload,
                    "user_sha256": hashlib.sha256(payload["user"].encode()).hexdigest(),
                },
            }
            write_json(OUT / f"frozen-{arm}-{endpoint}.json", item)
            base = counts(control[endpoint])
            current = counts(payload)
            print(
                f"{endpoint} {arm} system/user/total {current[0]}/{current[1]}/{current[2]} delta {current[0] - base[0]}/{current[1] - base[1]}/{current[2] - base[2]}"
            )
    (OUT / "state-notes.txt").write_text("\n".join(notes) + "\n", encoding="utf-8")
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    provenance = {
        "head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip(),
        "dirty_files": status,
        "package_sha256": {"shipped": package_files(PACKAGE), "access": package_files(OUT / "pkg/access")},
        "frozen_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(OUT.glob("frozen-*.json"))
        },
        "prefix_inputs": INPUTS,
        "endpoints": [{"n": n, "command": command} for n, command in ENDPOINTS],
    }
    write_json(OUT / "provenance.json", provenance)


if __name__ == "__main__":
    main()
