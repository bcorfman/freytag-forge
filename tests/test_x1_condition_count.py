import json
from pathlib import Path

from scripts.ringer.environment_narration import x1_condition_count as module


def test_real_corpus_reproduces_known_x1_counts(tmp_path: Path) -> None:
    assert module.main(["--corpus-build-only", "--out", str(tmp_path)]) == 0
    result = json.loads((tmp_path / "x1_count.json").read_text(encoding="utf-8"))

    assert result["labeled_forbidden"] == 18
    assert result["labeled_clean"] == 31
    assert result["forbidden_with_condition"] == 11
    assert result["clean_with_condition"] == 0
    assert result["forbidden_with_undeclared_condition"] == 11
    assert result["clean_with_undeclared_condition"] == 0
    assert result["undeclared_equals_raw"] == {"forbidden": True, "clean": True}
    assert result["breakdown"]["ajar_or_cover"]["labeled"] == 11
    assert result["breakdown"]["ajar_or_cover"]["with_condition"] == 10
    assert result["breakdown"]["contents"]["labeled"] == 7
    assert result["breakdown"]["contents"]["with_condition"] == 1


class _SyntheticWorld:
    def resolve(self, name: str) -> str | None:
        return "thing" if name == "box" else None

    def axis_definitions(self, entity_id: str) -> tuple[dict[str, object], ...]:
        return ({"poles": ("open", "closed"), "aliases": {"shut": "closed"}},)


def test_declared_axis_value_is_not_undeclared() -> None:
    raw, undeclared = module._condition_info(
        {"box": {"condition": ["open"]}, "unknown": {"condition": ["ajar"]}},
        _SyntheticWorld(),
    )

    assert raw
    assert undeclared
    assert module._condition_info({"box": {"condition": ["closed", "shut"]}}, _SyntheticWorld()) == (False, False)
