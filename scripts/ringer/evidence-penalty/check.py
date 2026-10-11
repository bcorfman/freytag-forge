# ruff: noqa: E501
"""Check the evidence-penalty story data against .plans/chatgpt-evidence-penalty-response.md."""

import copy
import subprocess
import sys
from pathlib import Path

import yaml

D = "data/stories/continuity-initiative/"
GAPS = {
    "captives_confirmed_alive": (
        "evidence_gap_processing_numbers",
        "Time runs out before Kristin can copy the full set of prisoner numbers from the processing line.",
    ),
    "brandon_janus_role_known": (
        "evidence_gap_development_record",
        "Time runs out before Kristin can copy the development record bearing Brandon's name.",
    ),
    "detention_locations_secured": (
        "evidence_gap_marked_site_list",
        "Time runs out before Kristin can copy Rebecca's marked site list.",
    ),
}
errors: list[str] = []


def load(path: str, head: bool):
    if head:
        return yaml.safe_load(subprocess.check_output(["git", "show", f"HEAD:{path}"], text=True))
    with open(path) as f:
        return yaml.safe_load(f)


# handoffs
old, new = load(D + "handoffs.yaml", True), load(D + "handoffs.yaml", False)
expect = copy.deepcopy(old)
for d in expect["deliveries"]:
    if d["fact_id"] == "evidence_ready_to_transmit":
        d["fallback_text"] = (
            "Kristin and Brandon obtain enough evidence to expose the conspiracy, leaving the evidence in hand. "
            "It is ready to transmit, but sending proof will reveal their position."
        )
        d.pop("costs", None)
for e, n in zip(expect["deliveries"], new["deliveries"], strict=False):
    if e != n:
        for k in sorted(set(e) | set(n)):
            if e.get(k) != n.get(k):
                errors.append(f"handoffs {e['fact_id']}.{k}: expected {e.get(k)!r}, got {n.get(k)!r}")
if len(expect["deliveries"]) != len(new["deliveries"]):
    errors.append("handoffs: delivery count changed")

# pacing
old, new = load(D + "pacing.yaml", True), load(D + "pacing.yaml", False)
R = {
    "collapse_3c": [
        (
            "evidence_gap_processing_numbers",
            "Water seeps under the outer doors. Kristin could not copy the full set of prisoner numbers from the processing line.",
        ),
        (
            "evidence_gap_development_record",
            "Water seeps under the outer doors. Kristin left without a copy of the development record bearing Brandon's name.",
        ),
    ],
    "routes_collapse_3c": [
        (
            "evidence_gap_marked_site_list",
            "Rising water is closing routes through the facility. Rebecca gave Kristin the locations, but Kristin left without a copy of her marked site list.",
        ),
    ],
}
expect = copy.deepcopy(old)
for ev in expect["events"]:
    if ev["id"] in R:
        default = ev["realizations"][-1]
        ev["realizations"] = [
            {"when": [{"fact_id": f, "equals": True}], "verbatim": True, "text": t} for f, t in R[ev["id"]]
        ] + [default]
if expect != new:
    errors.append("pacing.yaml differs from the expected realizations (or changed elsewhere)")

# declarations: every gap id must be declared in the same places facility_collapse_escalating is
for gap, _ in GAPS.values():
    for fname in ("world.yaml", "knowledge.yaml", "storylet-routes.yaml"):
        text = Path(D + fname).read_text()
        if gap not in text:
            errors.append(f"{gap} not declared in {fname}")

# no gap read by anything but realizations and cost writes
for fname in ("storylet-routes.yaml", "knowledge.yaml", "world.yaml"):
    for line in Path(D + fname).read_text().splitlines():
        if "evidence_gap_" in line and "requires" in line:
            errors.append(f"{fname}: gap used in a requirement: {line.strip()}")

if errors:
    print("EVIDENCE PENALTY CHECK FAILED")
    print("\n".join(errors))
    sys.exit(1)
print("evidence penalty data matches the plan")
