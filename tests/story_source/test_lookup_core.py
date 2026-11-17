"""Core behavior for the story address lookup API."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.story_source import compile_source_tree, story_text, story_value
from tests.story_source.helpers import copy_fixture


def _package(tmp_path: Path):
    """Compile the minimal source fixture for lookup tests."""

    return compile_source_tree(copy_fixture("mini_ok", tmp_path))


def test_unknown_kind_names_the_address(tmp_path: Path) -> None:
    """An unsupported address kind raises an address-named KeyError."""

    package = _package(tmp_path)

    with pytest.raises(KeyError, match="unknown:thing"):
        story_value("unknown:thing", package=package)


def test_unset_field_names_the_address(tmp_path: Path) -> None:
    """An explicitly unset package field is not returned as None."""

    package = _package(tmp_path)

    with pytest.raises(KeyError, match="delivery:continuity_initiative_known.cue_text"):
        story_text("delivery:continuity_initiative_known.cue_text", package=package)


def test_negative_one_selects_the_unguarded_pacing_realization(tmp_path: Path) -> None:
    """The beat shorthand selects the unguarded default realization."""

    package = _package(tmp_path)

    assert story_text("beat:patrol_leaves_1a.say[-1].text", package=package) == "The patrol pulls away from the curb."


def test_default_legacy_package_resolves_without_an_explicit_package() -> None:
    """The normal default loader supplies package-level lookup values."""

    assert story_text("scene:1A.entry")
