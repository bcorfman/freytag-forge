# ruff: noqa: E501
"""Capture the current and candidate 3A reunion narrator payloads offline."""

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import bench.frozen_prompts as fp  # noqa: E402
from bench.core import load_variation  # noqa: E402

OUT = ROOT / "bench/results/lead-up-contradictions"
LEAD = "- Right after your story, the game will add this: "
VARIATION_PATH = ROOT / "bench/variations/richer-3a-live.json"
COMMANDS = {"R1": "Free the captives.", "R2": "Ask Michelle about the other sites."}
CANDIDATES = {
    "R1": 'Michelle pulls Kristin close and holds her there. "You\'re here," she says, her voice breaking. "You\'re really here." Kristin holds on just as hard. For one unhurried moment nobody asks anything of either of them. When they let go, Michelle wipes her eyes and turns back to the captives. They are awake: the dose they were given is for the trip, and it wears off in the detention block. She returns to sending her coded messages, and she points toward the medical level where the experiment records await.',
    "R2": 'Michelle pulls Kristin close and holds her there. "You\'re here," she says, her voice breaking. "You\'re really here." Kristin holds on just as hard. For one unhurried moment nobody asks anything of either of them. When they let go, Michelle wipes her eyes and explains that freeing this block means little without exposing the other sites. She points toward the medical level, where the experiment records wait.',
}


def _candidate_payload(payload, text):
    candidate = copy.deepcopy(payload)
    lines = candidate["user"].split("\n")
    matches = [index for index, line in enumerate(lines) if line.startswith(LEAD)]
    assert len(matches) == 1
    lines[matches[0]] = LEAD + text
    candidate["user"] = "\n".join(lines)
    return candidate


def main():
    fp.SCENE = "3A"
    variation = load_variation(VARIATION_PATH)
    states, _ = fp._prefix_states(variation, [1, 2])
    arms = {"CUR": [], "CAND": []}
    for n, command in COMMANDS.items():
        cur, _ = fp._capture_wire_payload(copy.deepcopy(states[0]), command)
        matches = [line for line in cur["user"].split("\n") if line.startswith(LEAD)]
        assert len(matches) == 1
        cand = _candidate_payload(cur, CANDIDATES[n])
        for arm, payload in (("CUR", cur), ("CAND", cand)):
            arms[arm].append(
                {
                    "n": n,
                    "command": command,
                    "wire_payload": payload,
                    "user_sha256": hashlib.sha256(payload["user"].encode()).hexdigest(),
                }
            )
        cur_counts = (len(cur["system"]), len(cur["user"]))
        cand_counts = (len(cand["system"]), len(cand["user"]))
        cur_total = sum(cur_counts)
        cand_total = sum(cand_counts)
        print(
            f"{n} CUR system/user/total {cur_counts[0]}/{cur_counts[1]}/{cur_total}; "
            f"CAND {cand_counts[0]}/{cand_counts[1]}/{cand_total}; "
            f"delta {cand_counts[0] - cur_counts[0]}/{cand_counts[1] - cur_counts[1]}/{cand_total - cur_total}"
        )
    for arm, endpoints in arms.items():
        (OUT / f"frozen-3A-{arm}.json").write_text(
            json.dumps(
                {"variation": "richer-3a-live", "arm": arm, "endpoints": endpoints}, ensure_ascii=False, indent=2
            )
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
