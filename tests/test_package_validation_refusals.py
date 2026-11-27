from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from storygame.story_package.default_root import default_package_root
from storygame.story_package.loader import (
    StoryPackageError,
    _read_ownership,
    _validate,
    _validate_incidents,
    _validate_knowledge,
    load_story_package,
)
from storygame.story_source.l1_root import _validate_acts, _validate_fact_fields


@pytest.fixture(scope="module")
def package():
    return load_story_package(default_package_root())


def _replace(items: tuple, index: int, **updates: object) -> tuple:
    return items[:index] + (items[index].model_copy(update=updates),) + items[index + 1 :]


def _index_of(items: tuple, predicate, description: str) -> int:
    for index, item in enumerate(items):
        if predicate(item):
            return index
    pytest.fail(f"no record found for {description}")


def _scene(package, scene_id: str):
    return next(scene for scene in package.scenes if scene.metadata.scene_id == scene_id)


def _scene_index(package, scene_id: str) -> int:
    return _index_of(package.scenes, lambda scene: scene.metadata.scene_id == scene_id, f"scene {scene_id}")


def _route(package, route_id: str):
    return next(route for route in package.storylet_routes.storylets if route.id == route_id)


def _incident(package, incident_id: str):
    return next(incident for incident in package.incidents if incident.id == incident_id)


def _incident_index(package, predicate, description: str) -> int:
    return _index_of(package.incidents, predicate, description)


def _target_incident_index(package) -> int:
    return _incident_index(
        package, lambda incident: incident.id == "i_1c_freight_transfer", "incident i_1c_freight_transfer"
    )


def _target_incident(package):
    return package.incidents[_target_incident_index(package)]


def _incidents_with_shared_target_scene(package) -> tuple:
    target = _target_incident(package)
    other = next(incident for incident in package.incidents if incident.scene_id != target.scene_id)
    rest = tuple(incident for incident in package.incidents if incident.id not in {target.id, other.id})
    return (target, other.model_copy(update={"scene_id": target.scene_id}), *rest)


def _knowledge(package, predicate, description: str):
    return package.knowledge.knowledge[_index_of(package.knowledge.knowledge, predicate, description)]


def _knowledge_index(package, predicate, description: str) -> int:
    return _index_of(package.knowledge.knowledge, predicate, description)


def _realization_knowledge_index(package) -> int:
    return _knowledge_index(
        package,
        lambda knowledge: knowledge.source.kind == "storylet_realization",
        "knowledge sourced from a realization",
    )


def _realization_knowledge(package):
    return package.knowledge.knowledge[_realization_knowledge_index(package)]


def _different_effects_knowledge_index(package) -> int:
    return _knowledge_index(
        package,
        lambda knowledge: knowledge.id == "k_supervisor_escorting" and knowledge.source.kind == "storylet_realization",
        "realization knowledge for supervisor escorting",
    )


def _scene_entry_index(package, scene_id: str) -> int:
    return _knowledge_index(
        package,
        lambda knowledge: (
            knowledge.source.kind == "scene_entry" and knowledge.id == f"k_scene_{scene_id.lower()}_entry"
        ),
        f"{scene_id} scene-entry knowledge",
    )


def _scene_entry(package, scene_id: str):
    return package.knowledge.knowledge[_scene_entry_index(package, scene_id)]


def _package_with(package, **updates: object):
    return package.model_copy(update=updates)


@pytest.mark.parametrize(
    ("case", "mutate", "message"),
    [
        (
            "duplicate-entity",
            lambda p: _package_with(
                p, world=p.world.model_copy(update={"locations": p.world.locations + (p.world.locations[0],)})
            ),
            "entity IDs must be unique",
        ),
        (
            "unknown-fallback",
            lambda p: _package_with(
                p,
                world=p.world.model_copy(
                    update={"locations": _replace(p.world.locations, 0, fallback_ids=("missing",))}
                ),
            ),
            "entity 'mcgehee_home' has an unknown fallback",
        ),
        ("protagonist-not-npc", lambda p: _package_with(p, protagonist_id="home"), "protagonist_id must name an NPC"),
        (
            "placement-not-listed",
            lambda p: _package_with(
                p,
                scenes=_replace(
                    p.scenes,
                    _scene_index(p, "1A"),
                    metadata=_scene(p, "1A").metadata.model_copy(update={"item_placements": {"missing": "here"}}),
                ),
            ),
            r"scene 1A item_placements reference items not listed in item_ids",
        ),
        (
            "placement-unknown-guard",
            lambda p: _package_with(
                p,
                scenes=_replace(
                    p.scenes,
                    0,
                    metadata=_scene(p, "1A").metadata.model_copy(
                        update={
                            "item_placements": {
                                p.scenes[0].metadata.item_ids[0]: p.scenes[0]
                                .metadata.item_placements[p.scenes[0].metadata.item_ids[0]]
                                .model_copy(update={"while_fact_true": "missing"})
                            }
                        }
                    ),
                ),
            ),
            r"item placement names unknown guard fact 'missing'",
        ),
        (
            "scene-unknown-entity",
            lambda p: _package_with(
                p,
                scenes=_replace(
                    p.scenes, 0, metadata=_scene(p, "1A").metadata.model_copy(update={"participant_ids": ("missing",)})
                ),
            ),
            r"scene 1A references unknown entities",
        ),
        (
            "duplicate-transition",
            lambda p: _package_with(
                p, pacing=p.pacing.model_copy(update={"transitions": p.pacing.transitions + (p.pacing.transitions[0],)})
            ),
            r"duplicate transition ID 't_1a_1b'",
        ),
        (
            "transition-unknown-scene",
            lambda p: _package_with(
                p,
                pacing=p.pacing.model_copy(
                    update={"transitions": _replace(p.pacing.transitions, 0, target_scene_id="missing")}
                ),
            ),
            r"transition 't_1a_1b' references an unknown scene",
        ),
        (
            "transition-unknown-trigger",
            lambda p: _package_with(
                p,
                pacing=p.pacing.model_copy(
                    update={
                        "transitions": _replace(
                            p.pacing.transitions,
                            0,
                            triggers=(p.pacing.transitions[0].triggers[0].model_copy(update={"fact_id": "missing"}),),
                        )
                    }
                ),
            ),
            r"transition 't_1a_1b' has an unknown trigger predicate",
        ),
        (
            "transition-unknown-dependency",
            lambda p: _package_with(
                p,
                pacing=p.pacing.model_copy(
                    update={"transitions": _replace(p.pacing.transitions, 0, required_dependencies=("missing",))}
                ),
            ),
            r"transition 't_1a_1b' has unknown dependency",
        ),
        (
            "scene-unknown-transition",
            lambda p: _package_with(
                p,
                scenes=_replace(
                    p.scenes, 0, metadata=_scene(p, "1A").metadata.model_copy(update={"transition_ids": ("missing",)})
                ),
            ),
            r"scene 1A references an unknown transition",
        ),
        (
            "duplicate-pacing-event",
            lambda p: _package_with(
                p, pacing=p.pacing.model_copy(update={"events": p.pacing.events + (p.pacing.events[0],)})
            ),
            r"duplicate pacing event ID 'kristin_steadies_1a'",
        ),
        (
            "event-unknown-scene",
            lambda p: _package_with(
                p, pacing=p.pacing.model_copy(update={"events": _replace(p.pacing.events, 0, scene_id="missing")})
            ),
            r"pacing event 'kristin_steadies_1a' references an unknown scene",
        ),
        (
            "event-unknown-transition",
            lambda p: _package_with(
                p, pacing=p.pacing.model_copy(update={"events": _replace(p.pacing.events, 0, transition_id="missing")})
            ),
            r"pacing event 'kristin_steadies_1a' references an unknown transition",
        ),
        (
            "event-unknown-effect",
            lambda p: _package_with(
                p,
                pacing=p.pacing.model_copy(
                    update={
                        "events": _replace(
                            p.pacing.events,
                            0,
                            effects=(p.pacing.events[0].effects[0].model_copy(update={"fact_id": "missing"}),),
                        )
                    }
                ),
            ),
            r"pacing event 'kristin_steadies_1a' has an unknown effect predicate",
        ),
        (
            "event-unknown-guard",
            lambda p: _package_with(
                p,
                pacing=p.pacing.model_copy(
                    update={
                        "events": _replace(
                            p.pacing.events,
                            0,
                            when=(p.pacing.events[0].when[0].model_copy(update={"fact_id": "missing"}),),
                        )
                    }
                ),
            ),
            r"pacing event 'kristin_steadies_1a' has an unknown event guard predicate",
        ),
        (
            "storylet-unknown-scene",
            lambda p: _package_with(p, storylets=_replace(p.storylets, 0, scene_id="missing")),
            r"storylet 'SL-1A-A' references unknown scene",
        ),
        (
            "route-unknown-activation",
            lambda p: _package_with(
                p,
                storylet_routes=p.storylet_routes.model_copy(
                    update={
                        "storylets": _replace(
                            p.storylet_routes.storylets,
                            0,
                            activation_conditions=(
                                p.storylet_routes.storylets[0]
                                .activation_conditions[0]
                                .model_copy(update={"fact_id": "missing"}),
                            ),
                        )
                    }
                ),
            ),
            r"storylet route 'SL-1A-A' has an unknown activation fact",
        ),
        (
            "storylet-unknown-operation",
            lambda p: _package_with(
                p,
                storylet_routes=p.storylet_routes.model_copy(
                    update={
                        "storylets": _replace(
                            p.storylet_routes.storylets,
                            0,
                            realizations=(
                                p.storylet_routes.storylets[0]
                                .realizations[0]
                                .model_copy(
                                    update={
                                        "operations": (
                                            p.storylet_routes.storylets[0]
                                            .realizations[0]
                                            .operations[0]
                                            .model_copy(update={"fact_id": "missing"}),
                                        )
                                    }
                                ),
                            ),
                        )
                    }
                ),
            ),
            r"storylet route 'SL-1A-A' has an unknown operation fact",
        ),
        (
            "canonical-event-unknown-scene",
            lambda p: _package_with(
                p,
                storylet_routes=p.storylet_routes.model_copy(
                    update={"bridge_events": _replace(p.storylet_routes.bridge_events, 0, scene_id="missing")}
                ),
            ),
            r"canonical route event 'bridge_1a_actionable_lead' references an unknown scene",
        ),
        (
            "cycle",
            lambda p: _package_with(
                p,
                pacing=p.pacing.model_copy(
                    update={
                        "transitions": p.pacing.transitions
                        + (
                            p.pacing.transitions[-1].model_copy(
                                update={"id": "cycle", "source_scene_id": "3C", "target_scene_id": "1A"}
                            ),
                        )
                    }
                ),
            ),
            "scene transition graph contains a dependency cycle",
        ),
        (
            "sole-ending-scene",
            lambda p: _package_with(
                p, storylet_routes=p.storylet_routes.model_copy(update={"sole_ending_scene_id": "1A"})
            ),
            "storylet-routes sole ending must be the final plot scene",
        ),
        (
            "protected-boundary",
            lambda p: _package_with(
                p,
                storylet_routes=p.storylet_routes.model_copy(
                    update={
                        "storylets": _replace(
                            p.storylet_routes.storylets,
                            0,
                            realizations=_replace(
                                p.storylet_routes.storylets[0].realizations,
                                0,
                                protected_knowledge_boundaries=("missing",),
                            ),
                        )
                    }
                ),
            ),
            "storylet route 'SL-1A-A' has an unknown protected boundary",
        ),
        (
            "vacuous-canonical-activation",
            lambda p: _package_with(
                p,
                storylet_routes=p.storylet_routes.model_copy(
                    update={
                        "bridge_events": _replace(
                            p.storylet_routes.bridge_events,
                            0,
                            activation=p.storylet_routes.bridge_events[0].activation.model_copy(
                                update={"all_facts_true": ()}
                            ),
                        )
                    }
                ),
            ),
            "canonical route event 'bridge_1a_actionable_lead' has a vacuous activation rule",
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_validate_refuses_broken_package(package, case, mutate, message):
    _validate(package)
    with pytest.raises(StoryPackageError, match=re.escape(message)):
        _validate(mutate(package))


@pytest.mark.parametrize(
    ("case", "mutate", "message"),
    [
        (
            "duplicate-id",
            lambda p: _package_with(
                p,
                incidents=p.incidents + (_target_incident(p),),
            ),
            "incident 'i_1c_freight_transfer' has a duplicate incident id",
        ),
        (
            "unknown-scene",
            lambda p: _package_with(
                p,
                incidents=_replace(
                    p.incidents,
                    _target_incident_index(p),
                    scene_id="missing",
                ),
            ),
            "incident 'i_1c_freight_transfer' references unknown scene 'missing'",
        ),
        (
            "shared-scene",
            lambda p: _package_with(
                p,
                incidents=_incidents_with_shared_target_scene(p),
            ),
            "shares scene '1C' with another incident",
        ),
        (
            "unknown-event",
            lambda p: _package_with(
                p,
                incidents=_replace(
                    p.incidents,
                    _target_incident_index(p),
                    missed_window_event_id="missing",
                ),
            ),
            "references unknown pacing event 'missing'",
        ),
        (
            "event-wrong-scene",
            lambda p: _package_with(
                p,
                incidents=_replace(
                    p.incidents, _target_incident_index(p), missed_window_event_id="inspection_window_2a"
                ),
            ),
            "event 'inspection_window_2a' belongs to scene '2A', not '1C'",
        ),
        (
            "unknown-transition",
            lambda p: _package_with(
                p, incidents=_replace(p.incidents, _target_incident_index(p), successor_transition_id="missing")
            ),
            "references unknown transition 'missing'",
        ),
        (
            "transition-wrong-scene",
            lambda p: _package_with(
                p, incidents=_replace(p.incidents, _target_incident_index(p), successor_transition_id="t_2a_2b")
            ),
            "transition 't_2a_2b' starts in '2A', not '1C'",
        ),
        (
            "event-uses-successor-transition",
            lambda p: _package_with(
                p,
                pacing=p.pacing.model_copy(
                    update={
                        "events": _replace(
                            p.pacing.events,
                            next(i for i, event in enumerate(p.pacing.events) if event.id == "transfer_window_1c"),
                            transition_id="t_1c_2a",
                        )
                    }
                ),
            ),
            "cannot use successor transition 't_1c_2a'",
        ),
        (
            "duplicate-outcome",
            lambda p: _package_with(
                p,
                incidents=_replace(
                    p.incidents,
                    _target_incident_index(p),
                    outcomes=_target_incident(p).outcomes + (_target_incident(p).outcomes[0],),
                ),
            ),
            "has duplicate outcome id",
        ),
        (
            "outcomes-different-storylets",
            lambda p: _package_with(
                p,
                incidents=_replace(
                    p.incidents,
                    _target_incident_index(p),
                    outcomes=(
                        _target_incident(p).outcomes[0],
                        _target_incident(p).outcomes[1].model_copy(update={"storylet_id": "SL-1C-G"}),
                    ),
                ),
            ),
            "is not shared by every outcome",
        ),
        (
            "outcome-storylet-wrong-scene",
            lambda p: _package_with(
                p,
                incidents=_replace(
                    p.incidents,
                    _target_incident_index(p),
                    outcomes=tuple(
                        outcome.model_copy(update={"storylet_id": "SL-2A-C"})
                        for outcome in _target_incident(p).outcomes
                    ),
                ),
            ),
            "outcome references storylet 'SL-2A-C' outside scene '1C'",
        ),
        (
            "unknown-recovery",
            lambda p: _package_with(
                p, incidents=_replace(p.incidents, _target_incident_index(p), recovery_storylet_id="missing")
            ),
            "recovery storylet 'missing' is unknown",
        ),
        (
            "recovery-same-as-outcome",
            lambda p: _package_with(
                p,
                incidents=_replace(
                    p.incidents,
                    _target_incident_index(p),
                    recovery_storylet_id=_target_incident(p).outcomes[0].storylet_id,
                ),
            ),
            "must differ from the outcomes' shared storylet",
        ),
        (
            "unknown-outcome-fact",
            lambda p: _package_with(
                p,
                incidents=_replace(
                    p.incidents,
                    _target_incident_index(p),
                    outcomes=_replace(_target_incident(p).outcomes, 0, advantages=("missing",)),
                ),
            ),
            "references unknown fact 'missing'",
        ),
        (
            "duplicate-realization",
            lambda p: _package_with(
                p,
                incidents=_replace(
                    p.incidents,
                    _target_incident_index(p),
                    outcomes=(
                        _target_incident(p).outcomes[0],
                        _target_incident(p)
                        .outcomes[1]
                        .model_copy(update={"realization_id": _target_incident(p).outcomes[0].realization_id}),
                    ),
                ),
            ),
            "has duplicate realization id",
        ),
        (
            "unknown-realization",
            lambda p: _package_with(
                p,
                incidents=_replace(
                    p.incidents,
                    _target_incident_index(p),
                    outcomes=_replace(_target_incident(p).outcomes, 0, realization_id="missing"),
                ),
            ),
            "references unknown realization 'missing'",
        ),
        (
            "outcome-overlap",
            lambda p: _package_with(
                p,
                incidents=_replace(
                    p.incidents,
                    _target_incident_index(p),
                    outcomes=_replace(
                        _target_incident(p).outcomes, 0, costs=_target_incident(p).outcomes[0].advantages
                    ),
                ),
            ),
            "overlaps advantage and cost fact",
        ),
        (
            "unknown-knowledge",
            lambda p: _package_with(
                p, incidents=_replace(p.incidents, _target_incident_index(p), observation_knowledge_ids=("missing",))
            ),
            "references unknown knowledge 'missing'",
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_validate_incidents_refuses_broken_package(package, case, mutate, message):
    _validate_incidents(package)
    with pytest.raises(StoryPackageError, match=re.escape(message)):
        _validate_incidents(mutate(package))


@pytest.mark.parametrize(
    ("case", "mutate", "message"),
    [
        (
            "fact-set",
            lambda p: _package_with(p, knowledge=p.knowledge.model_copy(update={"facts": p.knowledge.facts[:-1]})),
            "knowledge facts must define every world fact exactly once",
        ),
        (
            "frame-set",
            lambda p: _package_with(
                p, knowledge=p.knowledge.model_copy(update={"scene_frames": p.knowledge.scene_frames[:-1]})
            ),
            "knowledge must declare exactly one safe scene frame per scene",
        ),
        (
            "duplicate-id",
            lambda p: _package_with(
                p,
                knowledge=p.knowledge.model_copy(
                    update={"knowledge": p.knowledge.knowledge + (p.knowledge.knowledge[0],)}
                ),
            ),
            "duplicate knowledge ID",
        ),
        (
            "unknown-entity",
            lambda p: _package_with(
                p,
                knowledge=p.knowledge.model_copy(
                    update={"knowledge": _replace(p.knowledge.knowledge, 0, entity_ids=("missing",))}
                ),
            ),
            "references unknown entities",
        ),
        (
            "unknown-reach",
            lambda p: _package_with(
                p,
                knowledge=p.knowledge.model_copy(
                    update={"knowledge": _replace(p.knowledge.knowledge, 0, reach_entity_ids=("missing",))}
                ),
            ),
            "references unknown reach entity 'missing'",
        ),
        (
            "unknown-speaker",
            lambda p: _package_with(
                p,
                knowledge=p.knowledge.model_copy(
                    update={"knowledge": _replace(p.knowledge.knowledge, 0, speaker_text={"missing": "x"})}
                ),
            ),
            "references unknown speaker 'missing'",
        ),
        (
            "unknown-scene",
            lambda p: _package_with(
                p,
                knowledge=p.knowledge.model_copy(
                    update={"knowledge": _replace(p.knowledge.knowledge, 0, available_in_scenes=("missing",))}
                ),
            ),
            "references an unknown scene",
        ),
        (
            "unknown-fact",
            lambda p: _package_with(
                p,
                knowledge=p.knowledge.model_copy(
                    update={
                        "knowledge": _replace(
                            p.knowledge.knowledge,
                            0,
                            establishes=(
                                p.knowledge.knowledge[0].establishes[0].model_copy(update={"fact_id": "missing"}),
                            ),
                        )
                    }
                ),
            ),
            "references an unknown fact",
        ),
        (
            "duplicate-variant",
            lambda p: _package_with(
                p,
                knowledge=p.knowledge.model_copy(
                    update={
                        "knowledge": _replace(
                            p.knowledge.knowledge,
                            next(i for i, k in enumerate(p.knowledge.knowledge) if k.delivery_variants),
                            delivery_variants=(
                                next(k for k in p.knowledge.knowledge if k.delivery_variants).delivery_variants[0],
                                next(k for k in p.knowledge.knowledge if k.delivery_variants).delivery_variants[0],
                            ),
                        )
                    }
                ),
            ),
            "has duplicate delivery variant requires sets",
        ),
        (
            "unknown-audience",
            lambda p: _package_with(
                p,
                knowledge=p.knowledge.model_copy(
                    update={
                        "knowledge": _replace(
                            p.knowledge.knowledge,
                            next(i for i, k in enumerate(p.knowledge.knowledge) if k.audience.kind == "characters"),
                            audience=next(
                                k for k in p.knowledge.knowledge if k.audience.kind == "characters"
                            ).audience.model_copy(update={"character_ids": ("missing",)}),
                        )
                    }
                ),
            ),
            "references an unknown audience character",
        ),
        (
            "source-scene",
            lambda p: _package_with(
                p,
                knowledge=p.knowledge.model_copy(
                    update={
                        "knowledge": _replace(
                            p.knowledge.knowledge, _realization_knowledge_index(p), available_in_scenes=("2A",)
                        )
                    }
                ),
            ),
            "has a source unavailable in its scene",
        ),
        (
            "unknown-realization",
            lambda p: _package_with(
                p,
                knowledge=p.knowledge.model_copy(
                    update={
                        "knowledge": _replace(
                            p.knowledge.knowledge,
                            _realization_knowledge_index(p),
                            source=_realization_knowledge(p).source.model_copy(update={"realization_id": "missing"}),
                        )
                    }
                ),
            ),
            "references an unknown realization",
        ),
        (
            "effects-differ-from-realization",
            lambda p: _package_with(
                p,
                knowledge=p.knowledge.model_copy(
                    update={
                        "knowledge": _replace(
                            p.knowledge.knowledge,
                            _different_effects_knowledge_index(p),
                            establishes=_realization_knowledge(p).establishes,
                        )
                    }
                ),
            ),
            "effects differ from its realization",
        ),
        (
            "scene-entry-effects-differ",
            lambda p: _package_with(
                p,
                knowledge=p.knowledge.model_copy(
                    update={
                        "knowledge": _replace(
                            p.knowledge.knowledge,
                            _scene_entry_index(p, "1A"),
                            establishes=_scene_entry(p, "1B").establishes,
                        )
                    }
                ),
            ),
            "scene entry effects differ from its entry fact",
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_validate_knowledge_refuses_broken_package(package, case, mutate, message):
    _validate_knowledge(package)
    with pytest.raises(StoryPackageError, match=re.escape(message)):
        _validate_knowledge(mutate(package))


@pytest.mark.parametrize(
    ("case", "value", "message"),
    [
        ("bad-yaml", "[", "ownership.yaml"),
        ("not-a-map", [], "ownership.yaml"),
        ("bad-schema", {"schema": 2, "catalog": "compiled", "scenes": {}}, "offending entries: schema"),
        (
            "unknown-key",
            {"schema": 1, "catalog": "compiled", "scenes": {}, "extra": True},
            "offending entries: ownership.yaml.extra, schema",
        ),
        ("bad-catalog", {"schema": 1, "catalog": "other", "scenes": {}}, "offending entries: catalog, schema"),
        (
            "bad-scene",
            {"schema": 1, "catalog": "compiled", "scenes": {"bad": "compiled"}},
            "offending entries: scenes.bad, schema",
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_read_ownership_refuses_broken_manifest(tmp_path: Path, case, value, message):
    (tmp_path / "ownership.yaml").write_text(
        value if isinstance(value, str) else yaml.safe_dump(value), encoding="utf-8"
    )
    with pytest.raises(StoryPackageError, match=re.escape(message)):
        _read_ownership(tmp_path)


@pytest.mark.parametrize(
    ("case", "value", "expected"),
    [
        (
            "unknown-key",
            [{"title": "Act", "intro": "Intro", "scenes": [], "extra": 1}],
            ("L1.unknown_key", "acts[0]", "unknown key 'extra'"),
        ),
        (
            "missing-field",
            [{"title": "Act", "intro": "Intro"}],
            ("L1.missing_key", "acts[0]", "missing required key 'scenes'"),
        ),
        ("bad-title", [{"title": 1, "intro": "Intro", "scenes": []}], ("L1.type", "acts[0]", "title must be str")),
        (
            "bad-scene-list",
            [{"title": "Act", "intro": "Intro", "scenes": "1A"}],
            ("L1.type", "acts[0]", "scenes must be list"),
        ),
        (
            "bad-scene-id",
            [{"title": "Act", "intro": "Intro", "scenes": ["bad"]}],
            ("L1.id_pattern", "acts[0]", "scene id 'bad' is invalid"),
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_validate_acts_reports_specific_diagnostic(case, value, expected):
    diagnostics = []
    _validate_acts("story.yaml", value, diagnostics)
    assert (diagnostics[0].name, diagnostics[0].address, diagnostics[0].message) == expected


@pytest.mark.parametrize(
    ("case", "record", "expected"),
    [
        ("bad-purpose", {"purpose": 1}, ("L1.type", "catalog.f", "purpose must be str")),
        ("bad-on-assert", {"on_assert": "yes"}, ("L1.type", "catalog.f", "on_assert must be list")),
        (
            "unknown-delivery-key",
            {"delivery": {"source_kind": "message", "fallback_text": "x", "extra": 1}},
            ("L1.unknown_key", "catalog.f", "unknown key 'extra'"),
        ),
        (
            "missing-delivery",
            {"delivery": {"source_kind": "message"}},
            ("L1.missing_key", "catalog.f", "missing required key 'fallback_text'"),
        ),
        (
            "bad-source-kind",
            {"delivery": {"source_kind": "other", "fallback_text": "x"}},
            ("L1.enum", "catalog.f", "source_kind must be one of"),
        ),
        (
            "bad-scene",
            {"delivery": {"source_kind": "message", "fallback_text": "x", "scene": "bad"}},
            ("L1.id_pattern", "catalog.f", "scene does not match"),
        ),
        (
            "bad-text",
            {"delivery": {"source_kind": "message", "fallback_text": 1}},
            ("L1.type", "catalog.f", "fallback_text must be str"),
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_validate_fact_fields_reports_specific_diagnostic(case, record, expected):
    diagnostics = []
    _validate_fact_fields("story.yaml", "catalog.f", record, diagnostics)
    assert diagnostics
    assert diagnostics[0].name == expected[0]
    assert diagnostics[0].address == expected[1]
    assert expected[2] in diagnostics[0].message
