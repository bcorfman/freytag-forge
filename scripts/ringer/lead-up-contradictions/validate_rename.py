# ruff: noqa: E501
"""Independent check for the rename 'coded announcements' -> 'secret messages' and 'coded words' -> 'code words'.
Every owned file must equal the saved pre-edit copy with exactly that rename applied (Python files: equal as ASTs, so line wrapping may differ)."""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PRE = Path(sys.argv[1])
FILES = [
    "data/stories/continuity-initiative/plot.md",
    "data/stories/continuity-initiative/knowledge.yaml",
    "data/stories/continuity-initiative/handoffs.yaml",
    "tests/test_richer_3a.py",
    "tests/test_1c_closeout.py",
    "tests/test_speaker_text.py",
    "scripts/ringer/lead-up-contradictions/capture_3a.py",
    "scripts/ringer/lead-up-contradictions/build_3a_manifest.py",
    ".plans/lead-up-contradictions-prereg.md",
]
errors = []


def rename(text: str) -> str:
    text = re.sub(r'coded(\s*"\s*\n\s*")announcement', r"secret\1message", text)
    text = text.replace("Coded announcement", "Secret message").replace("coded announcement", "secret message")
    return text.replace("Coded words", "Code words").replace("coded words", "code words")


for rel in FILES:
    pre = (PRE / rel).read_text(encoding="utf-8")
    post = (ROOT / rel).read_text(encoding="utf-8")
    want = rename(pre)
    if rel.endswith(".py"):
        try:
            same = ast.dump(ast.parse(want)) == ast.dump(ast.parse(post))
        except SyntaxError as e:
            errors.append(f"{rel}: does not parse: {e}")
            continue
    else:
        same = want == post
    if not same:
        errors.append(f"{rel}: differs from the saved copy with only the rename applied")
    flat = re.sub(r'"\s*\n\s*"', "", post)
    for m in re.finditer(r"(?i)coded\s+announcement|coded\s+words", flat):
        errors.append(f"{rel}: old phrase still present near {flat[max(0, m.start() - 30) : m.end() + 20]!r}")
if errors:
    print("VALIDATION FAILED:")
    for m in errors:
        print(" -", m)
    sys.exit(1)
print("RENAME VALIDATION OK:", len(FILES), "files")
