import json

import pytest

from factory.prereg import Prereg, decide, decide_all, validate_prereg


def valid_data() -> dict[str, object]:
    return {
        "id": "probe-1",
        "arms": ["control", "variant"],
        "keep_rule": "all_replicates_pass",
        "stop_rule": "stop_on_first_fail",
    }


def test_validate_prereg_accepts_defaults() -> None:
    assert validate_prereg(valid_data()) == []
    assert Prereg.from_dict(valid_data()).sample_size == 3


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", 4),
        ("arms", []),
        ("sample_size", "3"),
        ("adoption_sample_size", 2),
        ("keep_rule", "any_replicate_passes"),
        ("stop_rule", "never"),
    ],
)
def test_validate_prereg_reports_each_bad_field(field: str, value: object) -> None:
    data = valid_data()
    data[field] = value
    errors = validate_prereg(data)
    assert errors
    assert field in " ".join(errors)


def test_from_dict_joins_validation_errors() -> None:
    with pytest.raises(ValueError, match="id.*arms"):
        Prereg.from_dict({"id": 1, "arms": []})


def test_load_reads_json(tmp_path) -> None:
    path = tmp_path / "prereg.json"
    path.write_text(json.dumps(valid_data()), encoding="utf-8")
    assert Prereg.load(path).id == "probe-1"


def test_decide_continues_before_target() -> None:
    assert decide(Prereg.from_dict(valid_data()), [True]) == "continue"


def test_decide_stops_on_first_false() -> None:
    assert decide(Prereg.from_dict(valid_data()), [True, False]) == "stop_fail"


def test_decide_keeps_at_smoke_size() -> None:
    prereg = Prereg.from_dict(valid_data())
    assert decide(prereg, [True, True, True]) == "keep"


def test_decide_keeps_at_adoption_size() -> None:
    prereg = Prereg.from_dict(valid_data())
    assert decide(prereg, [True] * 12, adoption=True) == "keep"


def test_decide_rejects_extra_outcomes() -> None:
    prereg = Prereg.from_dict(valid_data())
    with pytest.raises(ValueError):
        decide(prereg, [True] * 4)


def test_decide_all_rejects_unknown_arm() -> None:
    prereg = Prereg.from_dict(valid_data())
    with pytest.raises(ValueError, match="unknown"):
        decide_all(prereg, {"other": [True]})


def test_decide_all_includes_unstarted_arm() -> None:
    prereg = Prereg.from_dict(valid_data())
    assert decide_all(prereg, {"control": [True]}) == {"control": "continue", "variant": "continue"}
