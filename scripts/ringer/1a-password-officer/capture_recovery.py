# ruff: noqa: E501
"""Freeze the offline narration recovery request for the 1A officer greeting."""

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import bench.frozen_prompts as fp  # noqa: E402
from bench.core import load_variation  # noqa: E402
from storygame.runtime.capture import WorldCapture  # noqa: E402
from storygame.runtime.contracts import RuntimeContractError, parse_turn_proposal  # noqa: E402
from storygame.runtime.engine import RuntimeEngine  # noqa: E402

OUT = ROOT / "bench/results/1a-password-officer"
VARIATION_PATH = ROOT / "bench/variations/1a-password-officer.json"
RUN_ROWS = OUT / "run-officer-rows.json"
FROZEN_OFFICER = OUT / "frozen-officer-BIO.json"
NOTES = OUT / "capture-recovery-notes.txt"

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


def _bad_reply() -> tuple[bytes, int]:
    rows = json.loads(RUN_ROWS.read_text(encoding="utf-8"))
    row = next(row for row in rows if row["arm"] == "BIO" and row["n"] == "OFF6")
    malformed = json.loads(row["narration"])
    malformed.pop("item_facts", None)
    try:
        parse_turn_proposal(malformed)
    except RuntimeContractError:
        pass
    else:
        raise AssertionError("the recorded BIO/OFF6 reply must remain invalid without item_facts")
    return json.dumps({"narration": json.dumps(malformed, ensure_ascii=False)}).encode(), row["sample"]


def _capture_recovery(state, command: str, bad_reply: bytes) -> list[dict[str, object]]:
    provider = fp._offline_capture_provider(state)
    calls: list[dict[str, object]] = []
    narration_count = 0

    def send(wire_payload: dict[str, object]) -> bytes:
        nonlocal narration_count
        calls.append(copy.deepcopy(wire_payload))
        if fp._is_narration_payload(wire_payload):
            narration_count += 1
            if narration_count == 1:
                return bad_reply
        return fp._CANNED_REPLY

    provider._send_http = send
    capture = WorldCapture(provider, lambda _state, _questions: None)
    RuntimeEngine(state, provider, capture=capture).turn(command)
    return [payload for payload in calls if fp._is_narration_payload(payload)]


def main() -> None:
    variation = load_variation(VARIATION_PATH)
    variation["scripts"] = {"1A": [{"name": "officer", "inputs": OFFICER_INPUTS}]}
    fp.SCENE = "1A"
    states, inputs = fp._prefix_states(variation, [8])
    state = states[7]
    command = inputs[7]
    assert command == "Greet the officer."

    frozen = json.loads(FROZEN_OFFICER.read_text(encoding="utf-8"))
    first_frozen = next(item for item in frozen["endpoints"] if item["n"] == "OFF6")
    bad_reply, sample = _bad_reply()
    narration = _capture_recovery(state, command, bad_reply)
    if len(narration) < 2:
        observation = f"expected a recovery request after the recorded BIO/OFF6 sample {sample}; found {len(narration)} narration request(s)"
        NOTES.write_text(observation + "\n", encoding="utf-8")
        raise RuntimeError(observation)

    first, recovery = narration[0], narration[1]
    assert first["user"] == first_frozen["wire_payload"]["user"]
    assert recovery["user"] == first["user"]
    assert recovery["system"].startswith(first["system"] + " ")
    assert "Your last answer was not valid" in recovery["system"][len(first["system"]) :]
    assert recovery["max_tokens"] == first["max_tokens"]
    assert recovery["response_format"] == first["response_format"]

    result = {
        "stage": "recovery",
        "arm": "REC",
        "endpoints": [
            {
                "n": "REC8",
                "command": command,
                "wire_payload": recovery,
                "user_sha256": hashlib.sha256(recovery["user"].encode()).hexdigest(),
                "first_user_sha256": hashlib.sha256(first["user"].encode()).hexdigest(),
                "recorded_bad_reply_sample": sample,
            }
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "frozen-recovery-REC.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("captured recovery request REC8")


if __name__ == "__main__":
    main()
