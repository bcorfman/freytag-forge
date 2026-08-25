from __future__ import annotations

import json
from pathlib import Path

import pytest

import storygame.authoring.sources as source_module
from storygame.authoring.cli import build_parser, select_source
from storygame.authoring.compiler import CompilationError
from storygame.authoring.sources import StorySourceLoader
from storygame.runtime.state import bootstrap_runtime_state


def _profiles(root: Path) -> None:
    root.mkdir()
    (root / "mystery.yaml").write_text("genre: mystery\n", encoding="utf-8")
    (root / "fantasy.yaml").write_text("genre: fantasy\n", encoding="utf-8")


def _inventory(path: Path) -> None:
    path.write_text(
        "stories:\n"
        "  - id: ordinary\n"
        "    genre: fantasy\n"
        "    tone: hopeful\n"
        "    variant: quest\n"
        "    outline: A courier crosses a broken kingdom.\n"
        "  - id: vale_mansion_rebuild\n"
        "    genre: mystery\n"
        "    authoring_only: true\n"
        "    outline: A winter death at a mansion needs a fair solution.\n",
        encoding="utf-8",
    )


def _brief(path: Path, *, expanded: bool = False) -> None:
    payload: dict[str, object] = {
        "schema_version": "freytag-story-brief-v1",
        "id": "moonlit_signal",
        "genre": "mystery",
        "profile": "mystery",
        "premise": "A signal interrupts a lighthouse vigil.",
        "opening_public_boundary": "The lighthouse is dark and the keeper is missing.",
    }
    if expanded:
        payload.update(
            {
                "hard_truths": ["The keeper staged the outage."],
                "protections": ["The keeper's location remains earned knowledge."],
                "ending_constraints": ["The rescue remains viable."],
                "world_notes": ["Storm-lashed island."],
                "cast_notes": ["The keeper trusts no one."],
                "dramatic_beats": ["A false alarm raises the stakes."],
                "possibility_library": ["A damaged radio may help."],
                "author_notes": ["Keep the weather vivid."],
                "extensions": {"author.palette": {"weather": "indigo"}},
            }
        )
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_inventory_sources_have_deterministic_provenance_and_authoring_only_selection(tmp_path: Path):
    inventory = tmp_path / "outlines.yaml"
    profiles = tmp_path / "profiles"
    _inventory(inventory)
    _profiles(profiles)
    loader = StorySourceLoader(inventory, profiles)

    ordinary = loader.select_outline("ordinary")
    vale = loader.select_outline("vale_mansion_rebuild")

    assert ordinary.source_format == "story-outline-inventory-v1"
    assert ordinary.creative_direction == {"tone": ("hopeful",), "variant": ("quest",)}
    assert ordinary.source_hash == loader.select_outline("ordinary").source_hash
    assert vale.authoring_only is True
    assert vale.provenance() == {
        "source_format": "story-outline-inventory-v1",
        "source_id": "vale_mansion_rebuild",
        "source_path": "outlines.yaml#vale_mansion_rebuild",
        "source_schema_version": "story-outline-inventory-v1",
        "source_hash": vale.source_hash,
    }


def test_outline_normalizes_typed_opening_orientation_fields(tmp_path: Path):
    inventory = tmp_path / "outlines.yaml"
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "fantasy.yaml").write_text("genre: fantasy\n", encoding="utf-8")
    inventory.write_text(
        "stories:\n"
        "  - id: courier\n"
        "    genre: fantasy\n"
        "    outline: A courier crosses a broken kingdom.\n"
        "    protagonist_context: You are a courier carrying an urgent seal.\n"
        "    opening_companions:\n"
        "      - id: guide\n"
        "        role: guide\n"
        "    public_briefing: [The western bridge has fallen.]\n"
        "    arrival_context: You reached the gate at dawn.\n"
        "    scene_purpose: Establish the crossing and its stakes.\n"
        "    first_available_actions: [Question the guide, Inspect the bridge]\n",
        encoding="utf-8",
    )

    source = StorySourceLoader(inventory, profiles).select_outline("courier")

    assert source.opening_setup["protagonist_context"].startswith("You are a courier")
    assert source.opening_setup["public_briefing"] == ("The western bridge has fallen.",)
    assert source.opening_setup["first_available_actions"] == ("Question the guide", "Inspect the bridge")


def test_inventory_normalization_is_shared_across_loaders_for_unchanged_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    inventory = tmp_path / "outlines.yaml"
    profiles = tmp_path / "profiles"
    _inventory(inventory)
    _profiles(profiles)
    inventory.write_text(inventory.read_text(encoding="utf-8") + "\n# cache-key test\n", encoding="utf-8")
    original_safe_load = source_module.yaml.safe_load
    calls = 0

    def counting_safe_load(value: object) -> object:
        nonlocal calls
        calls += 1
        return original_safe_load(value)

    monkeypatch.setattr(source_module.yaml, "safe_load", counting_safe_load)
    StorySourceLoader(inventory, profiles).list_outlines()
    StorySourceLoader(inventory, profiles).list_outlines()

    assert calls == 1


def test_checked_in_outline_inventory_is_complete_and_vale_is_offline_only():
    sources = StorySourceLoader(Path("data/story_outlines.yaml"), Path("data/genre_profiles")).list_outlines()

    assert len(sources) > 1
    assert len({source.source_id for source in sources}) == len(sources)
    vale = next(source for source in sources if source.source_id == "vale_mansion_rebuild")
    assert vale.authoring_only is True
    assert any("Beatrice Harrow" in constraint for constraint in vale.hard_constraints["terminal_constraints"])
    assert any("west gallery" in constraint for constraint in vale.hard_constraints["terminal_constraints"])
    assert any("diegetic" in constraint for constraint in vale.hard_constraints["terminal_constraints"])
    assert any(
        "within Vale Mansion and its estate" in constraint
        for constraint in vale.hard_constraints["terminal_constraints"]
    )


def test_checked_in_vale_source_declares_causal_spatial_playability() -> None:
    sources = StorySourceLoader(Path("data/story_outlines.yaml"), Path("data/genre_profiles")).list_outlines()
    vale = next(source for source in sources if source.source_id == "vale_mansion_rebuild")

    projection = vale.extensions["author.causal_spatial_projection"]
    assert projection["foyer_ensemble"] == [
        "beatrice_harrow",
        "thomas_pike",
        "julian_vale",
        "clara_mere",
        "lydia_fenn",
    ]
    assert projection["scene_subjects"][0]["id"] == "emma_vale_remains"
    assert len(projection["performance_profiles"]) >= 2
    assert any(frame["initiation"] == "npc_initiated" for frame in projection["interaction_frames"])
    assert any(frame["refusal_path"] for frame in projection["interaction_frames"])
    assert all(
        realization["kind"] in {"scene_evidence", "document", "testimony", "item"}
        for realization in projection["evidence_realizations"]
    )
    assert all(
        frame["agency_modes"] == ["engage", "refuse", "redirect", "interrupt", "depart"]
        for frame in projection["interaction_frames"]
    )
    clara_opening = next(frame for frame in projection["interaction_frames"] if frame["id"] == "clara_foyer_opening")
    assert set(clara_opening["location_ids"]) == {"grand_foyer", "west_gallery"}
    assert clara_opening["movement_intent_id"] == "clara_to_west_gallery"
    thomas_follow_up = next(
        frame for frame in projection["interaction_frames"] if frame["id"] == "thomas_boiler_log_follow_up"
    )
    assert set(thomas_follow_up["location_ids"]) == {"grand_foyer", "boiler_house"}
    assert thomas_follow_up["movement_intent_id"] == "thomas_to_boiler_house"
    suggestions = vale.opening_setup["first_action_suggestions"]
    assert {suggestion["text"] for suggestion in suggestions} == set(vale.opening_setup["first_available_actions"])
    assert {suggestion["target_kind"] for suggestion in suggestions} == {
        "group_encounter",
        "participant",
        "scene_subject",
    }


def test_minimal_and_expanded_briefs_keep_constraints_separate_from_creative_direction(tmp_path: Path):
    profiles = tmp_path / "profiles"
    _profiles(profiles)
    minimal_path = tmp_path / "minimal.yaml"
    expanded_path = tmp_path / "expanded.yaml"
    _brief(minimal_path)
    _brief(expanded_path, expanded=True)
    loader = StorySourceLoader(tmp_path / "unused.yaml", profiles)

    minimal = loader.load_brief(minimal_path)
    expanded = loader.load_brief(expanded_path)

    assert minimal.hard_constraints == {"hard_truths": (), "protections": (), "ending_constraints": ()}
    assert expanded.hard_constraints["hard_truths"] == ("The keeper staged the outage.",)
    assert expanded.creative_direction["world_notes"] == ("Storm-lashed island.",)
    assert expanded.extensions == {"author.palette": {"weather": "indigo"}}


@pytest.mark.parametrize(
    "payload, code",
    [
        ({"schema_version": "freytag-story-brief-v1"}, "SOURCE_INVALID"),
        (
            {
                "schema_version": "freytag-story-brief-v1",
                "id": "brief",
                "genre": "mystery",
                "profile": "mystery",
                "premise": "A premise.",
                "opening_public_boundary": "An opening.",
                "untyped_truth": "not allowed",
            },
            "SOURCE_INVALID",
        ),
    ],
)
def test_brief_loader_rejects_missing_identity_and_unknown_top_level_fields(
    tmp_path: Path, payload: dict[str, object], code: str
):
    profiles = tmp_path / "profiles"
    _profiles(profiles)
    path = tmp_path / "invalid.yaml"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CompilationError, match=code):
        StorySourceLoader(tmp_path / "unused.yaml", profiles).load_brief(path)


def test_source_loader_rejects_malformed_yaml_missing_path_profile_mismatch_and_changed_hash(tmp_path: Path):
    profiles = tmp_path / "profiles"
    _profiles(profiles)
    loader = StorySourceLoader(tmp_path / "missing.yaml", profiles)
    with pytest.raises(CompilationError, match="SOURCE_NOT_FOUND"):
        loader.select_outline("missing")
    with pytest.raises(CompilationError, match="SOURCE_NOT_FOUND"):
        loader.load_brief(tmp_path / "missing-brief.yaml")

    malformed = tmp_path / "malformed.yaml"
    malformed.write_text("schema_version: [", encoding="utf-8")
    with pytest.raises(CompilationError, match="SOURCE_INVALID"):
        loader.load_brief(malformed)

    brief = tmp_path / "brief.yaml"
    _brief(brief)
    first_hash = loader.load_brief(brief).source_hash
    _brief(brief, expanded=True)
    assert loader.load_brief(brief).source_hash != first_hash

    mismatch = tmp_path / "mismatch.yaml"
    _brief(mismatch)
    mismatch.write_text(
        mismatch.read_text(encoding="utf-8").replace('"profile": "mystery"', '"profile": "fantasy"'),
        encoding="utf-8",
    )
    with pytest.raises(CompilationError, match="PROFILE_MISMATCH"):
        loader.load_brief(mismatch)


def test_inventory_loader_rejects_unnamespaced_extensions(tmp_path: Path):
    inventory = tmp_path / "invalid.yaml"
    inventory.write_text(
        "stories:\n"
        "  - id: invalid\n"
        "    genre: mystery\n"
        "    outline: A constrained story.\n"
        "    extensions: {projection: {}}\n",
        encoding="utf-8",
    )

    with pytest.raises(CompilationError, match="SOURCE_INVALID"):
        StorySourceLoader(inventory, tmp_path / "profiles").list_outlines()


@pytest.mark.parametrize(
    "content",
    [
        "not: a list",
        "stories:\n  - id: duplicate\n    genre: fantasy\n    outline: one\n"
        "  - id: duplicate\n    genre: fantasy\n    outline: two\n",
        "stories:\n  - id: [invalid]\n    genre: fantasy\n    outline: invalid\n",
    ],
)
def test_inventory_loader_rejects_invalid_cached_payloads(tmp_path: Path, content: str):
    inventory = tmp_path / "invalid.yaml"
    inventory.write_text(content, encoding="utf-8")

    with pytest.raises(CompilationError, match="SOURCE_INVALID"):
        StorySourceLoader(inventory, tmp_path / "profiles").list_outlines()


def test_cli_requires_exactly_one_source_selector_and_never_bootstraps_raw_source(tmp_path: Path):
    inventory = tmp_path / "outlines.yaml"
    profiles = tmp_path / "profiles"
    brief = tmp_path / "brief.yaml"
    _inventory(inventory)
    _profiles(profiles)
    _brief(brief)
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])
    with pytest.raises(SystemExit):
        parser.parse_args(["--outline-id", "ordinary", "--story", str(brief)])

    source = select_source(
        parser.parse_args(["--story", str(brief), "--inventory", str(inventory), "--profile-root", str(profiles)])
    )
    assert source["source_id"] == "moonlit_signal"
    with pytest.raises(TypeError, match="reviewed CompiledStory"):
        bootstrap_runtime_state(source)  # type: ignore[arg-type]
