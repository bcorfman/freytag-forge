from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

LengthBucket = str


def _plot_curves_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "plot_curves.yaml"


def _normalize_genre(genre: str) -> str:
    normalized = genre.strip().lower()
    if not normalized:
        raise ValueError("genre must be a non-empty string.")
    return normalized


def normalize_session_length(session_length: int | str) -> LengthBucket:
    if isinstance(session_length, str):
        normalized = session_length.strip().lower()
        if normalized in {"short", "medium", "long"}:
            return normalized
        raise ValueError("session_length string must be one of: short, medium, long.")

    if session_length < 1:
        raise ValueError("session_length int must be >= 1.")
    if session_length <= 12:
        return "short"
    if session_length <= 25:
        return "medium"
    return "long"


@lru_cache(maxsize=4)
def _load_plot_curves_cached(path_key: str) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path_key).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("plot_curves.yaml must parse to a mapping.")

    curve_library = payload.get("curve_library")
    if not isinstance(curve_library, dict):
        raise ValueError("plot_curves.yaml is missing a valid curve_library mapping.")
    return payload


def load_plot_curves(path: Path | None = None) -> dict[str, Any]:
    resolved_path = _plot_curves_path() if path is None else path
    return _load_plot_curves_cached(str(resolved_path.resolve()))


def _stable_index(genre: str, length_bucket: LengthBucket, seed: int, count: int) -> int:
    digest = hashlib.sha256(f"{genre}|{length_bucket}|{seed}".encode()).digest()
    value = int.from_bytes(digest[:8], byteorder="big", signed=False)
    return value % count


def _genre_curves(genre: str, path: Path | None = None) -> list[dict[str, Any]]:
    payload = load_plot_curves(path)
    library = payload["curve_library"]
    normalized_genre = _normalize_genre(genre)
    if normalized_genre not in library:
        raise ValueError(f"Unknown genre '{genre}'.")

    curves = library[normalized_genre]
    if not isinstance(curves, list) or not curves:
        raise ValueError(f"Genre '{genre}' has no curve templates.")
    return curves


def select_curve_template(
    genre: str,
    session_length: int | str,
    seed: int,
    path: Path | None = None,
) -> dict[str, Any]:
    length_bucket = normalize_session_length(session_length)
    curves = _genre_curves(genre=genre, path=path)
    index = _stable_index(_normalize_genre(genre), length_bucket, seed, len(curves))
    selected = curves[index]
    if not isinstance(selected, dict):
        raise ValueError(f"Invalid curve template entry for genre '{genre}'.")
    return selected


def select_curve_id(
    genre: str,
    session_length: int | str,
    seed: int,
    path: Path | None = None,
) -> str:
    template = select_curve_template(
        genre=genre,
        session_length=session_length,
        seed=seed,
        path=path,
    )
    curve_id = template.get("curve_id")
    if not isinstance(curve_id, str) or not curve_id:
        raise ValueError(f"Selected curve for genre '{genre}' is missing a valid curve_id.")
    return curve_id
