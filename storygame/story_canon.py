from __future__ import annotations

DEFAULT_MYSTERY_DETECTIVE_NAME = "Detective Elias Wren"
_GENERIC_DETECTIVE_LABELS = {
    "",
    "detective",
    "the detective",
}


def canonical_detective_name(genre: str, protagonist_name: str) -> str:
    normalized_genre = genre.strip().lower()
    cleaned_name = " ".join(protagonist_name.split()).strip()
    if normalized_genre != "mystery":
        return cleaned_name
    if cleaned_name.lower() in _GENERIC_DETECTIVE_LABELS:
        return DEFAULT_MYSTERY_DETECTIVE_NAME
    return cleaned_name
