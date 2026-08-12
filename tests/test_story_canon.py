from storygame.story_canon import DEFAULT_MYSTERY_DETECTIVE_NAME, canonical_detective_name


def test_canonical_detective_name_uses_default_for_generic_mystery_label() -> None:
    assert canonical_detective_name("mystery", "detective") == DEFAULT_MYSTERY_DETECTIVE_NAME


def test_canonical_detective_name_keeps_non_mystery_name() -> None:
    assert canonical_detective_name("fantasy", "Captain Mira Vale") == "Captain Mira Vale"
