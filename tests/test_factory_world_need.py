from __future__ import annotations

import json
from pathlib import Path

import pytest
from worldkeeper import WorldSchema

from factory.checks.world_need import NeedResult, check_needs, main, tickets_for
from storygame.runtime.world_model import world_schema_data
from storygame.story_package.dependencies import consumers, producers
from storygame.story_source import compile_source_tree
from tests.story_source.helpers import copy_fixture

RULES = {"scene_ids": ["1A", "2C"], "need_roles": ["relies_on", "creates"]}


@pytest.fixture
def package(tmp_path: Path):
    return compile_source_tree(copy_fixture("mini_ok", tmp_path))


def ids_for(package) -> dict[str, str]:
    schema = WorldSchema.from_data(world_schema_data(package))
    entities = schema.entities
    return {
        "item": next(entity_id for entity_id, entity in entities.items() if entity.kind == "thing"),
        "npc": next(entity_id for entity_id, entity in entities.items() if entity.kind == "character"),
        "location": next(entity_id for entity_id, entity in entities.items() if entity.kind == "area"),
        "seat": next(entity_id for entity_id, entity in entities.items() if entity.kind == "seat"),
        "fact_with_producer": next(fact_id for fact_id in package.fact_ids if producers(package, fact_id)),
        "fact_without_producer": next(fact_id for fact_id in package.fact_ids if not producers(package, fact_id)),
        "fact_with_consumer": next(fact_id for fact_id in package.fact_ids if consumers(package, fact_id)),
    }


def need(need_id: str, relation: str, subject: str, object_id: str | None = None, **extra) -> dict:
    result = {"id": need_id, "relation": relation, "subject": subject, **extra}
    if object_id is not None:
        result["object"] = object_id
    return result


def contract(*scenes: tuple[str, list[dict]]) -> dict:
    return {"scenes": [{"scene_id": scene_id, "world_needs": needs} for scene_id, needs in scenes]}


def result_for(results: list[NeedResult], need_id: str) -> NeedResult:
    return next(result for result in results if result.need_id == need_id)


def test_each_relation_has_a_representable_need(package) -> None:
    ids = ids_for(package)
    needs = [
        need("hold", "hold", ids["item"], ids["npc"]),
        need("know", "know", ids["npc"], ids["fact_with_producer"]),
        need("reach", "reach", ids["npc"], ids["location"]),
        need("exist", "exist", ids["item"]),
        need("hidden", "hidden", ids["item"], ids["item"]),
        need("seated", "seated", ids["npc"], ids["seat"]),
        need("companion", "companion", ids["npc"], ids["npc"]),
        need("axis", "axis", ids["npc"], axis="consciousness", pole="awake"),
    ]

    results = check_needs(contract(("1A", needs)), package, rules=RULES)

    assert all(result.outcome == "ok" for result in results)
    assert result_for(results, "know").q2 == "yes"


def test_worldkeeper_ticket_for_unrepresentable_relation(package) -> None:
    ids = ids_for(package)

    result = check_needs(contract(("1A", [need("bad-hold", "hold", ids["npc"], ids["item"])])), package, rules=RULES)[0]

    assert result.outcome == "worldkeeper_ticket"
    assert result.q1 == "no"
    assert "hold needs a thing subject" in result.reasons


def test_unknown_kind_and_undeclared_fact_are_story_holes(package) -> None:
    ids = ids_for(package)
    results = check_needs(
        contract(
            (
                "1A",
                [
                    need("unknown-kind", "exist", ids["item"], subject_kind="not_declared"),
                    need("unknown-fact", "know", ids["npc"], "missing_fact"),
                ],
            )
        ),
        package,
        rules=RULES,
    )

    assert result_for(results, "unknown-kind").outcome == "story_hole"
    assert any(reason.startswith("unknown kind") for reason in result_for(results, "unknown-kind").reasons)
    assert result_for(results, "unknown-fact").outcome == "story_hole"
    assert "fact is not declared" in result_for(results, "unknown-fact").reasons


def test_q2_package_producer_and_earlier_contract_creator(package) -> None:
    ids = ids_for(package)
    local_fact = "local_fact"
    results = check_needs(
        contract(
            (
                "1A",
                [
                    need("from-package", "know", ids["npc"], ids["fact_with_producer"]),
                    need("create", "know", ids["npc"], local_fact, role="creates"),
                ],
            ),
            ("2C", [need("from-earlier", "know", ids["npc"], local_fact)]),
        ),
        package,
        rules=RULES,
    )

    assert result_for(results, "from-package").q2 == "yes"
    assert result_for(results, "from-earlier").q2 == "yes"


def test_q2_no_and_q3_support_from_package_or_later_contract(package) -> None:
    ids = ids_for(package)
    later_fact = "later_fact"
    results = check_needs(
        contract(
            (
                "1A",
                [
                    need("q2-no", "know", ids["npc"], ids["fact_without_producer"]),
                    need("q3-package", "know", ids["npc"], ids["fact_with_consumer"], role="creates"),
                    need("q3-later-create", "know", ids["npc"], later_fact, role="creates"),
                ],
            ),
            ("2C", [need("q3-later-read", "know", ids["npc"], later_fact)]),
        ),
        package,
        rules=RULES,
    )

    assert result_for(results, "q2-no").q2 == "no"
    assert result_for(results, "q2-no").outcome == "story_hole"
    assert result_for(results, "q3-package").q3 == "yes"
    assert result_for(results, "q3-later-create").q3 == "yes"


def test_q3_no_role_default_and_supplied_kinds(package) -> None:
    ids = ids_for(package)
    results = check_needs(
        contract(
            (
                "1A",
                [
                    need("q3-no", "know", ids["npc"], ids["fact_without_producer"], role="creates"),
                    need("default-role", "know", ids["npc"], ids["fact_with_producer"]),
                    need(
                        "undeclared-entity",
                        "hold",
                        "ghost",
                        "ghost-target",
                        subject_kind="thing",
                        object_kind="character",
                    ),
                ],
            )
        ),
        package,
        rules=RULES,
    )

    assert result_for(results, "q3-no").q3 == "no"
    assert result_for(results, "default-role").q2 == "yes"
    assert result_for(results, "undeclared-entity").outcome == "ok"


def test_malformed_need_and_ticket_precedence(package) -> None:
    ids = ids_for(package)
    results = check_needs(
        contract(
            (
                "1A",
                [
                    {"id": "malformed", "relation": "know", "subject": ids["npc"]},
                    need("ticket-and-hole", "know", ids["item"], ids["fact_without_producer"]),
                ],
            )
        ),
        package,
        rules=RULES,
    )

    malformed = result_for(results, "malformed")
    assert malformed.outcome == "story_hole"
    assert malformed.reasons == ("malformed need",)
    assert result_for(results, "ticket-and-hole").outcome == "worldkeeper_ticket"
    assert "nothing earlier produces it" in result_for(results, "ticket-and-hole").reasons


def test_tickets_for_has_one_record_per_problem(package) -> None:
    ids = ids_for(package)
    results = check_needs(
        contract(("1A", [need("bad", "hold", ids["npc"], ids["item"]), need("good", "exist", ids["item"])])),
        package,
        rules=RULES,
    )

    tickets = tickets_for(results)

    assert len(tickets) == 1
    assert tickets[0]["kind"] == "worldkeeper_ticket"
    assert tickets[0]["need_id"] == "bad"
    assert tickets[0]["summary"].endswith(".")


def test_cli_success_failure_json_and_invalid_contract(tmp_path: Path, package, capsys, monkeypatch) -> None:
    ids = ids_for(package)
    story_root = tmp_path / "story"
    monkeypatch.setattr("factory.checks.world_need.load_story_package", lambda _root: package)
    good_path = tmp_path / "good.json"
    good_path.write_text(json.dumps(contract(("1A", [need("good", "exist", ids["item"])]))), encoding="utf-8")
    output_path = tmp_path / "results.json"

    assert main([str(good_path), "--story", str(story_root), "--json", str(output_path)]) == 0
    assert capsys.readouterr().out.strip() == "ok"
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["results"][0]["outcome"] == "ok"
    assert payload["tickets"] == []

    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps(contract(("1A", [need("bad", "hold", ids["npc"], ids["item"])]))), encoding="utf-8")
    assert main([str(bad_path), "--story", str(story_root)]) == 1
    assert "worldkeeper_ticket 1A bad:" in capsys.readouterr().out

    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("not json", encoding="utf-8")
    assert main([str(invalid_path), "--story", str(story_root)]) == 2
    assert "error:" in capsys.readouterr().out
