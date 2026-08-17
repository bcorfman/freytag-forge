from __future__ import annotations

import json
from pathlib import Path

import pytest

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


def test_checked_in_outline_inventory_is_complete_and_vale_is_offline_only():
    sources = StorySourceLoader(Path("data/story_outlines.yaml"), Path("data/genre_profiles")).list_outlines()

    assert len(sources) > 1
    assert len({source.source_id for source in sources}) == len(sources)
    vale = next(source for source in sources if source.source_id == "vale_mansion_rebuild")
    assert vale.authoring_only is True


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
