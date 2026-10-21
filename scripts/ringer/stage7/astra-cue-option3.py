"""Check for the option-3 cue task: chamber-based cue and fallback wording for two 3C handoffs."""

import sys
from pathlib import Path

import yaml

raw = yaml.safe_load(Path("data/stories/continuity-initiative/handoffs.yaml").read_text())
items = raw if isinstance(raw, list) else next(v for v in raw.values() if isinstance(v, list))
by_id = {i["fact_id"]: i for i in items if isinstance(i, dict) and "fact_id" in i}
want = {
    "national_network_fragmenting": (
        "Reports from other detention sites reach the broadcast chamber.",
        "Detention sites surrender or release prisoners as the national network breaks apart.",
    ),
    "community_rescue_efforts_begun": (
        "Families of the missing call the broadcast chamber for word.",
        "Families and communities organize independent rescue efforts. Many of the missing are still alive.",
    ),
}
for fact, (cue, tail) in want.items():
    item = by_id[fact]
    if item["cue_text"] != cue:
        sys.exit(f"FAIL: {fact} cue_text is {item['cue_text']!r}")
    if tail not in item["fallback_text"]:
        sys.exit(f"FAIL: {fact} fallback_text is {item['fallback_text']!r}")
    for group in item["must_convey"]:
        for field in ("cue_text", "fallback_text"):
            if not any(p.lower() in item[field].lower() for p in group):
                sys.exit(f"FAIL: {fact} {field} misses must_convey group {group}")
for fact, item in by_id.items():
    for field in ("cue_text", "fallback_text"):
        if "Michelle's broadcast carries" in item.get(field, "") or "Through Michelle's broadcast" in item.get(
            field, ""
        ):
            sys.exit(f"FAIL: option-1 wording remains in {fact}")
print("ok")
