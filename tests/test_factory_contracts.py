from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path

import pytest

from factory.contracts import lint_contract, load_rules

ROOT = Path(__file__).resolve().parents[1]
OK_PATH = ROOT / "tests/fixtures/factory_contracts/ok.json"


def read_ok() -> dict:
    with OK_PATH.open(encoding="utf-8") as contract_file:
        return json.load(contract_file)


def rule_ids(contract: dict, rules: dict | None = None) -> set[str]:
    return {problem.rule_id for problem in lint_contract(contract, rules)}


def set_placeholder(contract: dict) -> None:
    contract["scenes"][0]["feeling"] = "TODO"


def shorten_harm_ladder(contract: dict) -> None:
    del contract["harm_ladder"][1:]


def test_ok_contract_is_clean_and_is_a_three_scene_act() -> None:
    contract = read_ok()

    assert contract["scenes"] and [scene["scene_id"] for scene in contract["scenes"]] == ["1A", "1B", "1C"]
    assert rule_ids(contract) == set()


@pytest.mark.parametrize(
    ("rule_id", "mutate"),
    [
        ("contract.shape", lambda contract: contract["scenes"][0]["clock"].pop("running_out")),
        ("contract.placeholder", set_placeholder),
        ("contract.harm_ladder", shorten_harm_ladder),
        ("contract.beats", lambda contract: contract["scenes"][0]["beats"][-1].update(turn=9)),
        ("contract.first_pressure", lambda contract: contract["scenes"][0]["beats"][1].update(turn=5)),
        ("contract.pacing", lambda contract: contract["scenes"][0]["beats"][2].update(turn=4)),
        ("contract.setpiece", lambda contract: contract["scenes"][0]["beats"][4]["outcomes"][0].update(verb="read")),
        ("contract.npc", lambda contract: contract["scenes"][0]["npc_in_the_way"].update(named_in_entry=False)),
        ("contract.clock", lambda contract: contract["scenes"][0]["clock"].update(running_out="")),
        ("contract.delay_cost", lambda contract: contract["scenes"][0]["delay_costs"][0].update(passage_id="")),
        ("contract.protected", lambda contract: contract["scenes"][0]["delay_costs"][0].update(harmed=["michelle"])),
        ("contract.bond", lambda contract: contract["scenes"][0]["delay_costs"][0].update(harmed=["unbonded"])),
        ("contract.world_need", lambda contract: contract["scenes"][0]["world_needs"][0].pop("object")),
        ("contract.feeling", lambda contract: contract["scenes"][0].update(feeling="")),
    ],
)
def test_one_minimal_mutation_reports_its_rule(rule_id: str, mutate) -> None:
    contract = read_ok()
    mutate(contract)

    assert rule_id in rule_ids(contract)


def test_rules_are_loaded_for_protected_characters_and_cost_kinds() -> None:
    contract = read_ok()
    rules = load_rules()
    rules["protected_characters"] = ["porter"]
    assert "contract.protected" in rule_ids(contract, rules)

    custom_rules = copy.deepcopy(rules)
    custom_rules["cost_kinds"] = ["custom_cost"]
    for rung in contract["harm_ladder"]:
        rung["kind"] = "custom_cost"
    for scene in contract["scenes"]:
        for cost in scene["delay_costs"]:
            cost["cost_kind"] = "custom_cost"
    assert "contract.shape" not in rule_ids(contract, custom_rules)
    assert "contract.delay_cost" not in rule_ids(contract, custom_rules)


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [str(ROOT / ".venv/bin/python"), "-m", "factory.contracts.lint", *args],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_reports_ok_and_failure(tmp_path: Path) -> None:
    ok_result = run_cli(str(OK_PATH))
    assert ok_result.returncode == 0
    assert ok_result.stdout.strip() == "ok"

    mutated = read_ok()
    mutated["act"] = ""
    mutated_path = tmp_path / "mutated.json"
    mutated_path.write_text(json.dumps(mutated), encoding="utf-8")
    failed_result = run_cli(str(mutated_path))
    assert failed_result.returncode == 1
    assert "contract.shape" in failed_result.stdout


def test_cli_returns_two_for_non_json(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("not json", encoding="utf-8")

    result = run_cli(str(invalid_path))

    assert result.returncode == 2


def test_template_parses_and_reports_placeholders() -> None:
    template_path = ROOT / "factory/contracts/template.json"
    with template_path.open(encoding="utf-8") as template_file:
        template = json.load(template_file)

    assert "contract.placeholder" in rule_ids(template)


@pytest.mark.parametrize("field", ["subject_kind", "object_kind"])
def test_world_need_optional_kind_must_be_non_empty_string(field: str) -> None:
    contract = read_ok()
    contract["scenes"][0]["world_needs"][0][field] = ""

    assert "contract.world_need" in rule_ids(contract)


def test_world_need_optional_kind_rejects_non_string() -> None:
    contract = read_ok()
    contract["scenes"][0]["world_needs"][0]["subject_kind"] = 42

    assert "contract.world_need" in rule_ids(contract)


def test_world_need_role_uses_rules_and_rejects_unknown_value() -> None:
    contract = read_ok()
    contract["scenes"][0]["world_needs"][0]["role"] = "depends_on"

    assert "contract.world_need" in rule_ids(contract)


def test_world_need_roles_accept_both_declared_values() -> None:
    for role in ("relies_on", "creates"):
        contract = read_ok()
        contract["scenes"][0]["world_needs"][0]["role"] = role

        assert "contract.world_need" not in rule_ids(contract)
