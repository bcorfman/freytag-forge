"""Check a progressive-disclosure split of one long doc.

Usage: check_doc_split.py <original snapshot> <summary .md> <detail dir> <summary max words> <detail max words>

Passes when: the summary is short; every detail file is linked from the summary and is under its budget;
every sentence of five or more words in the original appears verbatim (whitespace and markdown
markers ignored) somewhere in the summary or detail files, except at most 2% that are printed for review;
and every relative markdown link in this doc's files, and in docs that mention it, resolves (file and #anchor).
"""

import re
import sys
from pathlib import Path

ROOT = Path("/home/bcorfman/dev/freytag-forge")
LINK = re.compile(r"\]\(([^)\s]+)\)")


def norm(text: str) -> str:
    text = re.sub(r"`|\*\*|\*|^#+\s*|^\s*[-*]\s+|^\s*\d+\.\s+|^\s*>\s*|\|", " ", text, flags=re.M)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def sentences(text: str) -> list[str]:
    out = []
    in_code = False
    block = []
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            if len(line.split()) >= 3:
                out.append(norm(line))
            continue
        block.append(norm(line) if line.strip() else ".")
    para = re.sub(r"\s+", " ", " ".join(block))
    for s in re.split(r"(?<=[.!?:])\s+", para):
        s = s.strip(" .")
        if len(s.split()) >= 5:
            out.append(s)
    return out


def slug(heading: str) -> str:
    h = heading.strip().lower()
    h = re.sub(r"[^\w\- ]", "", h)
    return h.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    found = set()
    in_code = False
    for line in path.read_text().splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
        if not in_code and line.startswith("#"):
            found.add(slug(line.lstrip("#").replace("`", "")))
    return found


def words(path: Path) -> int:
    return len(path.read_text().split())


def main() -> int:
    original, summary, detail_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    max_summary, max_detail = int(sys.argv[4]), int(sys.argv[5])
    errors = []
    if not summary.exists():
        print(f"FAIL: {summary} missing")
        return 1
    details = sorted(detail_dir.rglob("*.md")) if detail_dir.is_dir() else []
    if not details:
        errors.append(f"no detail files under {detail_dir}")
    if words(summary) > max_summary:
        errors.append(f"summary {summary.name} has {words(summary)} words; budget {max_summary}")
    summary_text = summary.read_text()
    for d in details:
        if words(d) > max_detail:
            errors.append(f"detail {d.relative_to(ROOT)} has {words(d)} words; budget {max_detail}")
        rel = d.relative_to(summary.parent).as_posix()
        if rel not in summary_text:
            errors.append(f"summary does not link {rel}")
    combined = norm("\n".join(p.read_text() for p in [summary, *details]))
    wanted = sentences(original.read_text())
    missing = [s for s in wanted if s not in combined]
    allowed = int(len(wanted) * 0.02)
    if len(missing) > allowed:
        errors.append(
            f"{len(missing)} of {len(wanted)} original sentences are missing (allowed {allowed}); keep the original "
            "wording, only move it. Missing:\n  - " + "\n  - ".join(missing)
        )
    elif missing:
        print(f"NOTE: {len(missing)} reworded sentences (within the 2% allowance):\n  - " + "\n  - ".join(missing))
    others = [*ROOT.joinpath("docs").rglob("*.md"), ROOT / "AGENTS.md", ROOT / "README.md"]
    inbound = [d for d in others if summary.stem in d.read_text() and d not in details and d != summary]
    for doc in [summary, *details, *inbound]:
        text = re.sub(r"```.*?```", "", doc.read_text(), flags=re.S)
        for target in LINK.findall(text):
            if re.match(r"^[a-z]+:", target):
                continue
            path_part, _, anchor = target.partition("#")
            dest = doc if not path_part else (doc.parent / path_part).resolve()
            if not dest.exists():
                errors.append(f"broken link in {doc.relative_to(ROOT)}: {target}")
            elif anchor and dest.suffix == ".md" and anchor not in anchors(dest):
                errors.append(f"broken anchor in {doc.relative_to(ROOT)}: {target}")
    if errors:
        print("FAIL:\n" + "\n".join(errors))
        return 1
    print(f"PASS: summary {words(summary)} words, {len(details)} detail files, {len(wanted)} sentences kept")
    return 0


if __name__ == "__main__":
    sys.exit(main())
