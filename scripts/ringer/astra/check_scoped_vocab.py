"""Ringer check helper: bare later-scene words must be scoped aliases, and the guard tests must exist."""

import os
import re
import sys

import yaml

sys.path.insert(0, os.getcwd())
w = yaml.safe_load(open("data/stories/continuity-initiative/world.yaml"))
items = {i["id"]: i for i in w["items"]}
bench = items["park_bench"]
drain = items["storm_drain"]
if "bench" in [a.casefold() for a in bench.get("aliases", [])] or "bench" not in [
    a.casefold() for a in bench.get("scoped_aliases", [])
]:
    sys.exit("FAIL park_bench must have scoped_aliases [bench] and no bare 'bench' in aliases")
for word in ("drain", "tunnel"):
    if word in [a.casefold() for a in drain.get("aliases", [])] or word not in [
        a.casefold() for a in drain.get("scoped_aliases", [])
    ]:
        sys.exit(f"FAIL storm_drain must have scoped alias '{word}' and not keep it in aliases")
t = open("tests/test_scene_vocabulary_isolation.py").read()
need = [
    "test_bare_later_scene_words_do_not_reject_earlier_narration",
    "test_specific_later_scene_names_are_still_guarded_earlier",
    "test_scene_words_still_resolve_in_their_own_scene",
    "test_guarded_items_have_no_bare_common_word_aliases",
]
missing = [n for n in need if not re.search(rf"def {n}\b", t)]
if missing:
    sys.exit(f"FAIL required tests missing: {missing}")
print("scoped vocabulary structure ok")
