"""Regenerate the offline narration corpus safety verdict snapshot."""

from __future__ import annotations

import json
from collections import Counter

from tests.test_narration_corpus import VERDICTS_PATH, load_corpus, verdict


def main() -> None:
    verdicts = {entry["id"]: verdict(entry) for entry in load_corpus()}
    VERDICTS_PATH.write_text(json.dumps(dict(sorted(verdicts.items())), indent=2) + "\n")
    counts = Counter(verdicts.values())
    print(f"{counts.get('ok', 0)} ok")
    for code, count in sorted(counts.items()):
        if code != "ok":
            print(f"{count} rejected: {code}")


if __name__ == "__main__":
    main()
