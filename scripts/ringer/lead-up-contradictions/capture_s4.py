# ruff: noqa: E501
"""Capture the offline S4 lead-up narrator payloads."""

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

import bench.frozen_prompts as fp  # noqa: E402
from bench.core import load_variation  # noqa: E402
from storygame.runtime.capture import WorldCapture  # noqa: E402
from storygame.runtime.engine import RuntimeEngine  # noqa: E402

OUT = ROOT / "bench/results/lead-up-contradictions"
LIVE = ROOT / "bench/results/shared-narrator/live/final-r1/all-turn-records.json"
C0 = OUT / "frozen-C0.json"
BASELINE_VARIATION = ROOT / "bench/results/shared-narrator/baseline/variation-1C.json"
KNOWLEDGE = ROOT / "data/stories/continuity-initiative/knowledge.yaml"
ENDPOINT_INDICES = {"c1": 0, "c2": 1, "c5": 4, "c6": 5, "c8": 7}
ENDPOINTS = ("c1", "c2", "c5", "c6", "c8", "h2")
LEAD = "- Write only what leads up to it. Do not have Kristin find anything else."
CANDIDATE_LEAD = (
    "- Write the lead-up to the text above. Stop before its first action or spoken words. "
    "Leave its discoveries for that text."
)


def _wire(payload):
    return {key: payload[key] for key in ("system", "user", "max_tokens", "response_format")}


def _replace_line(user, predicate, replacement):
    lines = user.split("\n")
    matches = [i for i, line in enumerate(lines) if predicate(line)]
    assert len(matches) == 1
    lines[matches[0]] = replacement
    return "\n".join(lines)


def _final_user(user, n):
    lines = user.split("\n")
    matches = [i for i, line in enumerate(lines) if line.startswith("- Brandon Corfman is")]
    assert len(matches) == 1
    lines.insert(
        matches[0] + 1,
        "- Imprisoned senior official is a senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted and observant.",
    )
    user = "\n".join(lines)
    if n == "c2":
        knowledge = yaml.safe_load(KNOWLEDGE.read_text(encoding="utf-8"))
        entries = knowledge["knowledge"]
        entry = next(item for item in entries if item.get("id") == "k_sl_3a_f_r1")
        variant = next(item for item in entry["delivery_variants"] if "held_transfers_seen" in item["requires"])
        prefix = "- Right after your story, the game will add this: "
        user = _replace_line(user, lambda line: line.startswith(prefix), prefix + variant["text"].strip())
    for old, new in (
        ("Coded announcement", "Secret message"),
        ("coded announcement", "secret message"),
        ("Coded words", "Code words"),
        ("coded words", "code words"),
    ):
        user = user.replace(old, new)
    return user


def _capture_h2():
    variation = load_variation(BASELINE_VARIATION)
    fp.SCENE = "1C"
    states, inputs = fp._prefix_states(variation, [1, 2])
    provider = fp._offline_capture_provider(copy.deepcopy(states[0]))
    calls = []

    def send(wire):
        calls.append(copy.deepcopy(wire))
        return fp._CANNED_REPLY

    provider._send_http = send
    capture = WorldCapture(provider, lambda _s, _q: None)
    engine = RuntimeEngine(copy.deepcopy(states[0]), provider, capture=capture)
    engine.turn(inputs[1])
    narration = [call for call in calls if fp._is_narration_payload(call)]
    assert narration
    assert getattr(provider.authored_handoff, "candidate", None).id == "k_sl_1c_a_r1"
    return _wire(narration[0]), inputs[1]


def _candidate(payload):
    result = copy.deepcopy(payload)
    result["user"] = _replace_line(result["user"], lambda line: line == LEAD, CANDIDATE_LEAD)
    return result


def main():
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    c0 = json.loads(C0.read_text(encoding="utf-8"))
    settings = {
        (e["wire_payload"]["max_tokens"], json.dumps(e["wire_payload"]["response_format"], sort_keys=True))
        for e in c0["endpoints"]
    }
    assert len(settings) == 1
    max_tokens, response_format_json = next(iter(settings))
    response_format = json.loads(response_format_json)
    turns = live["runs"][0]["turns"]
    payloads = {}
    commands = {}
    for n, index in ENDPOINT_INDICES.items():
        turn = turns[index]
        commands[n] = turn["player_input"]
        payloads[n] = {
            "system": turn["prompt_system"],
            "user": _final_user(turn["prompt_user"], n),
            "max_tokens": max_tokens,
            "response_format": copy.deepcopy(response_format),
        }
    payloads["h2"], commands["h2"] = _capture_h2()
    for n in ENDPOINTS:
        assert payloads[n]["user"].split("\n").count(LEAD) == 1
    arms = {"CUR": [], "CAND": []}
    for n in ENDPOINTS:
        cur = payloads[n]
        cand = _candidate(cur)
        for arm, payload in (("CUR", cur), ("CAND", cand)):
            arms[arm].append(
                {
                    "n": n,
                    "command": commands[n],
                    "wire_payload": payload,
                    "user_sha256": hashlib.sha256(payload["user"].encode()).hexdigest(),
                }
            )
        cur_counts = (len(cur["system"]), len(cur["user"]))
        cand_counts = (len(cand["system"]), len(cand["user"]))
        print(
            f"{n} CUR system/user/total {cur_counts[0]}/{cur_counts[1]}/{sum(cur_counts)}; "
            f"CAND {cand_counts[0]}/{cand_counts[1]}/{sum(cand_counts)}; "
            f"delta {cand_counts[0] - cur_counts[0]}/{cand_counts[1] - cur_counts[1]}/{sum(cand_counts) - sum(cur_counts)}"
        )
    for arm, endpoints in arms.items():
        (OUT / f"frozen-S4-{arm}.json").write_text(
            json.dumps({"variation": "lead-up-s4", "arm": arm, "endpoints": endpoints}, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
