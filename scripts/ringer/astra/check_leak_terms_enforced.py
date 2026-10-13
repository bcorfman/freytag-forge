"""Ringer check helper: leak_terms must be authoritative for multi-word phrases and the required tests must exist."""

import os
import re
import sys

sys.path.insert(0, os.getcwd())
t = open("tests/test_leak_terms_enforced.py").read()
need = [
    "test_leak_term_alone_rejects_narration_before_the_item_is_earned",
    "test_single_word_leak_term_is_not_enforced",
    "test_card_phrase_is_rejected_before_the_search_and_allowed_on_the_earning_turn",
    "test_every_multiword_leak_term_in_the_story_is_enforced",
]
missing = [n for n in need if not re.search(rf"def {n}\b", t)]
if missing:
    sys.exit(f"FAIL required tests missing: {missing}")
docs = open("docs/markdown-story-authoring.md").read()
if "complete vocabulary that may be blocked" in docs:
    sys.exit("FAIL docs/markdown-story-authoring.md still says leak_terms may be blocked")
print("leak terms structure ok")
