from __future__ import annotations

import re
from pathlib import Path

from scripts.audit_copied_prose import _sentences, find_copied_sentences, main
from storygame.story_package.loader import load_story_package
from storygame.story_source.lookup import story_text


def test_finds_sentence_copied_into_a_test(tmp_path: Path) -> None:
    sentence = next(
        part for part in re.split(r"(?<=[.!?])\s+", story_text("claim:k_sl_1a_b_r1.text")) if len(part) >= 45
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_copied.py").write_text(f"copied = {sentence!r}\n", encoding="utf-8")
    (tests_dir / "test_clean.py").write_text("copied = 'nothing from the story'\n", encoding="utf-8")

    package = load_story_package(Path(__file__).parents[1] / "data/stories/continuity-initiative")
    assert find_copied_sentences(package, tests_dir) == {"test_copied.py": [("claim:k_sl_1a_b_r1.text", sentence)]}


def test_audit_test_file_copies_no_authored_prose(capsys) -> None:
    repo = Path(__file__).parents[1]
    assert main(["--json", "--repo", str(repo), "--test", "tests/test_audit_copied_prose.py"]) == 0
    assert capsys.readouterr().out == "{}\n"


def test_finds_sentence_split_across_string_constants(tmp_path: Path) -> None:
    claim_text = story_text("claim:k_sl_1a_b_r1.text")
    sentences = _sentences(claim_text)
    first_sentence, second_sentence = sentences[:2]
    first_split = first_sentence.find(" ", len(first_sentence) // 2)
    second_split = second_sentence.find(" ", len(second_sentence) // 2)
    first_one, first_two = first_sentence[:first_split], first_sentence[first_split + 1 :]
    second_one, second_two = second_sentence[:second_split], second_sentence[second_split + 1 :]

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_split.py").write_text(
        "copied = (\n"
        f"    {(first_one + ' ')!r}\n"
        f"    {first_two!r}\n"
        ")\n"
        f'joined = " ".join(({second_one!r}, {second_two!r}))\n',
        encoding="utf-8",
    )

    package = load_story_package(Path(__file__).parents[1] / "data/stories/continuity-initiative")
    assert find_copied_sentences(package, tests_dir) == {
        "test_split.py": [
            ("claim:k_sl_1a_b_r1.text", first_sentence),
            ("claim:k_sl_1a_b_r1.text", second_sentence),
        ]
    }
