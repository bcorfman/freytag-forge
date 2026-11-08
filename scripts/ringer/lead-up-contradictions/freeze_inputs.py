# ruff: noqa: E501
"""Freeze model-free FINAL narrator inputs and exact single-edit candidate arms."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FINAL = ROOT / "bench/results/shared-narrator/live/final-r1/all-turn-records.json"
CONTROL = ROOT / "bench/results/shared-narrator/live/control-r1/all-turn-records.json"
GU2 = ROOT / "bench/results/shared-narrator/g/frozen-GU2.json"
OUT = ROOT / "bench/results/lead-up-contradictions"
LEAD = "- Right after your story, the game will add this: "
BIO = "- Imprisoned senior official is a senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted, observant, and has kept one piece of emergency authority out of Charles's hands."
OLD_FIRST = "Michelle shows Kristin the medical level."
NEW_FIRST = "Michelle leads Kristin through a medical level where prisoners have been subjected to neurological and behavioral experiments."
ORG = [
    "- Dr. Michelle McGehee may say this aloud: I've been organizing everyone with secret announcements over our stolen radios.",
    "- Brandon Corfman may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.",
    "- Imprisoned senior official may say this aloud: Dr. McGehee's been organizing everyone with secret announcements over the stolen radios.",
]


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_file(path):
    return sha_bytes(path.read_bytes())


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def only_line_change(before, after):
    old, new = before.split("\n"), after.split("\n")
    assert len(old) == len(new)
    assert sum(a != b for a, b in zip(old, new, strict=True)) == 1


def exact_arm(base, edit):
    before = base.split("\n")
    after = edit(before[:])
    return before, after, "\n".join(after)


def package_hash():
    package = ROOT / "data/stories/continuity-initiative"
    rows = []
    for path in sorted(p for p in package.rglob("*") if p.is_file()):
        rows.append(f"{path.relative_to(ROOT)}:{sha_file(path)}")
    return sha_bytes(("\n".join(rows) + "\n").encode())


def arm_record(name, turn, user):
    wire = {
        "system": turn["prompt_system"],
        "user": user,
        "max_tokens": SETTINGS["max_tokens"],
        "response_format": SETTINGS["response_format"],
    }
    base = turn["prompt_user"]
    return {
        "n": f"c{turn['turn_number']}",
        "command": turn["player_input"],
        "selected_id": turn.get("authored_handoff_candidate_id"),
        "wire_payload": wire,
        "control_user_sha256": sha_bytes(base.encode()),
        "arm_user_sha256": sha_bytes(user.encode()),
    }


def counts(payload):
    system = len(payload["system"])
    user = len(payload["user"])
    return system, user, system + user


def main():
    global SETTINGS
    final_turns = json.loads(FINAL.read_text())["runs"][0]["turns"]
    control_turns = json.loads(CONTROL.read_text())["runs"][0]["turns"]
    assert len(final_turns) == len(control_turns) == 9
    gu2 = json.loads(GU2.read_text())
    settings = [endpoint["wire_payload"] for endpoint in gu2["endpoints"]]
    assert settings and all(
        payload["max_tokens"] == settings[0]["max_tokens"]
        and payload["response_format"] == settings[0]["response_format"]
        for payload in settings
    )
    SETTINGS = settings[0]

    endpoints = []
    for index, turn in enumerate(final_turns):
        wire = {
            "system": turn["prompt_system"],
            "user": turn["prompt_user"],
            "max_tokens": SETTINGS["max_tokens"],
            "response_format": SETTINGS["response_format"],
        }
        endpoint = {
            "n": f"c{index + 1}",
            "command": turn["player_input"],
            "selected_id": turn.get("authored_handoff_candidate_id"),
            "wire_payload": wire,
        }
        if index < 8:
            delivery = turn["authored_segments"][0]["text"]
            assert turn["narration"].endswith(delivery)
            endpoint["delivery_text"] = delivery
            endpoint["generated_portion"] = turn["narration"][: -len(delivery)].rstrip()
            assert turn["narration"][: -len(delivery)].rstrip() == endpoint["generated_portion"]
            assert LEAD + delivery in turn["prompt_user"]
        else:
            endpoint["authored_segments"] = [
                {"kind": segment["kind"], "text": segment["text"]} for segment in turn["authored_segments"]
            ]
            endpoint["generated_portion"] = turn["narration"]
        endpoints.append(endpoint)

    c0 = {
        "variation": "lead-up-contradictions-final-r1",
        "source": str(FINAL.relative_to(ROOT)),
        "endpoints": endpoints,
    }

    c6 = final_turns[5]
    before, after, user = exact_arm(
        c6["prompt_user"],
        lambda lines: (
            lines[: lines.index(next(x for x in lines if x.startswith("- Brandon Corfman is"))) + 1]
            + [BIO]
            + lines[lines.index(next(x for x in lines if x.startswith("- Brandon Corfman is"))) + 1 :]
        ),
    )
    assert len(after) == len(before) + 1 and after.count(BIO) == 1
    assert after[after.index(BIO) - 1].startswith("- Brandon Corfman is") and after[
        after.index(BIO) + 1 : after.index(BIO) + 3
    ] == ["", "SCENE:"]
    write_arms = [("1A", c6, user)]

    c4 = final_turns[3]
    old_line = next(line for line in c4["prompt_user"].split("\n") if line.startswith(LEAD))
    assert old_line.startswith(LEAD + OLD_FIRST)
    replacement = LEAD + NEW_FIRST + old_line[len(LEAD + OLD_FIRST) :]
    lines = c4["prompt_user"].split("\n")
    assert lines.count(old_line) == 1
    edited = [replacement if line == old_line else line for line in lines]
    user = "\n".join(edited)
    only_line_change(c4["prompt_user"], user)
    write_arms.append(("1B", c4, user))

    lines = c4["prompt_user"].split("\n")
    assert all(lines.count(line) == 1 for line in ORG)
    edited = [line for line in lines if line not in ORG]
    user = "\n".join(edited)
    assert len(edited) == len(lines) - 3 and [line for line in lines if line not in ORG] == edited
    write_arms.append(("2A", c4, user))

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "frozen-C0.json", c0)
    for name, turn, user in write_arms:
        write_json(
            OUT / f"frozen-{name}.json",
            {
                "variation": f"lead-up-contradictions-{name}",
                "control": "C0",
                "endpoints": [arm_record(name, turn, user)],
            },
        )

    diff = subprocess.run(["git", "diff", "HEAD"], cwd=ROOT, capture_output=True, check=True).stdout
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, check=True).stdout
    provenance = {
        "head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip(),
        "dirty_diff_sha256": sha_bytes(diff),
        "status_porcelain_sha256": sha_bytes(status),
        "package_files_sha256": package_hash(),
        "final_records_sha256": sha_file(FINAL),
        "control_records_sha256": sha_file(CONTROL),
        "gu2_envelope_sha256": sha_file(GU2),
        "package_hash_note": "The GU2 envelope's package_hash is stale metadata and is not used.",
        "python": sys.version,
        "model_free": "zero model calls",
    }
    write_json(OUT / "provenance.json", provenance)

    report = []
    payloads = [("C0 c1..c9", endpoint["wire_payload"]) for endpoint in endpoints]
    payloads += [(name, arm_record(name, turn, user)["wire_payload"]) for name, turn, user in write_arms]
    report.append("wire payload character counts: system/user/total")
    for label, payload in payloads:
        system, user, total = counts(payload)
        digest = sha_bytes(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode())[:12]
        report.append(f"{label}: {system}/{user}/{total}; sha256={digest}")
    report.append("\narm deltas vs control endpoint")
    for name, turn, user in write_arms:
        base = counts({"system": turn["prompt_system"], "user": turn["prompt_user"]})
        arm = counts({"system": turn["prompt_system"], "user": user})
        report.append(
            f"{name} vs C0 c{turn['turn_number']}: system/user/total delta {arm[0] - base[0]:+d}/{arm[1] - base[1]:+d}/{arm[2] - base[2]:+d}"
        )
    (OUT / "diff-report.txt").write_text("\n".join(report) + "\n")


if __name__ == "__main__":
    main()
