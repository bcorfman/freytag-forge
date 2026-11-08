# ruff: noqa: E501
"""Build the frozen 1A2 comparison from the frozen 1A control."""

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "bench/results/lead-up-contradictions"
SOURCE = RESULTS / "frozen-1A.json"
TARGET = RESULTS / "frozen-1A2.json"

FULL_LINE = "- Imprisoned senior official is a senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted, observant, and has kept one piece of emergency authority out of Charles's hands."
TRIMMED_LINE = "- Imprisoned senior official is a senior government official whom Charles has publicly blamed for the catastrophe. He is exhausted and observant."


def main():
    frozen_1a = json.loads(SOURCE.read_text(encoding="utf-8"))
    frozen_1a2 = copy.deepcopy(frozen_1a)
    frozen_1a2["variation"] = "lead-up-contradictions-1A2"
    frozen_1a2["control"] = "1A"

    endpoint = next(endpoint for endpoint in frozen_1a2["endpoints"] if endpoint["n"] == "c6")
    user = endpoint["wire_payload"]["user"]
    assert user.splitlines().count(FULL_LINE) == 1
    endpoint["wire_payload"]["user"] = user.replace(FULL_LINE, TRIMMED_LINE)
    control_user = next(endpoint for endpoint in frozen_1a["endpoints"] if endpoint["n"] == "c6")["wire_payload"][
        "user"
    ]
    arm_user = endpoint["wire_payload"]["user"]
    endpoint["control_user_sha256"] = hashlib.sha256(control_user.encode("utf-8")).hexdigest()
    endpoint["arm_user_sha256"] = hashlib.sha256(arm_user.encode("utf-8")).hexdigest()

    TARGET.write_text(json.dumps(frozen_1a2, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for label, payload in (("1A", frozen_1a["endpoints"][0]["wire_payload"]), ("1A2", endpoint["wire_payload"])):
        user_text = payload["user"]
        wire_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        print(label, len(user_text), wire_hash[:12])


if __name__ == "__main__":
    main()
