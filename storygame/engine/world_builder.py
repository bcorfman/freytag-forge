from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from storygame.plot.curves import normalize_session_length, select_curve_template

_ALLOWED_GENRES = (
    "sci-fi",
    "mystery",
    "romance",
    "adventure",
    "action",
    "suspense",
    "drama",
    "fantasy",
    "horror",
    "thriller",
)

_TONE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "dark": ("grim", "bleak", "death", "murder", "haunted", "dystopian", "tragic", "corrupt"),
    "light": ("comedic", "hopeful", "whimsical", "warm", "uplifting", "playful"),
    "romantic": ("love", "romance", "relationship", "heart", "reunion"),
    "tense": ("chase", "deadline", "threat", "hostage", "conspiracy", "danger"),
    "mysterious": ("mystery", "clue", "secret", "suspect", "disappearance", "unknown"),
    "epic": ("kingdom", "prophecy", "realm", "legend", "odyssey", "quest"),
    "neutral": (),
}

_ROOM_TEMPLATES: dict[str, tuple[str, ...]] = {
    "sci-fi": ("dock_hub", "market_arcade", "archive_node", "lab_ring", "tower_array", "sanctuary_core"),
    "mystery": ("front_steps", "market_lane", "records_office", "safehouse", "watch_tower", "old_chapel"),
    "romance": ("courtyard", "cafe_row", "garden_path", "gallery_hall", "river_walk", "lantern_square"),
    "adventure": ("camp", "trailhead", "cliff_pass", "ruin_gate", "inner_chamber", "return_harbor"),
    "action": ("safe_flat", "alley_junction", "control_room", "warehouse", "checkpoint", "extraction_point"),
    "suspense": ("apartment", "backstreet", "records_room", "subway_platform", "abandoned_site", "panic_room"),
    "drama": ("family_home", "main_street", "clinic", "school_hall", "community_center", "lake_house"),
    "fantasy": ("village_gate", "market_square", "scribe_hall", "enchanted_wood", "citadel_steps", "sanctum"),
    "horror": ("old_house", "fog_road", "chapel_ruins", "cellar", "woods_edge", "ritual_room"),
    "thriller": ("transit_hub", "newsroom", "intel_vault", "industrial_yard", "embassy_corridor", "final_site"),
}

_ITEM_TEMPLATES: dict[str, tuple[str, ...]] = {
    "sci-fi": ("data_key", "signal_lens", "power_cell"),
    "mystery": ("case_file", "ledger_page", "bronze_key"),
    "romance": ("letter", "locket", "keepsake"),
    "adventure": ("map_fragment", "rope_kit", "artifact_shard"),
    "action": ("badge", "breach_charge", "comm_scrambler"),
    "suspense": ("burner_phone", "security_card", "flash_drive"),
    "drama": ("old_photo", "medical_note", "voice_message"),
    "fantasy": ("rune_token", "moon_blade", "warded_scroll"),
    "horror": ("salt_pouch", "candle_bundle", "sigil_stone"),
    "thriller": ("cipher_sheet", "surveillance_tape", "access_chip"),
}


def _story_outlines_path() -> Path:
    data_dir = Path(__file__).resolve().parents[2] / "data"
    preferred = data_dir / "story_outlines.yaml"
    fallback = data_dir / "story_outline.yaml"
    if preferred.exists():
        return preferred
    if fallback.exists():
        return fallback
    return preferred


def _normalize_genre(genre: str) -> str:
    normalized = genre.strip().lower()
    if normalized not in _ALLOWED_GENRES:
        raise ValueError(f"Unknown genre '{genre}'.")
    return normalized


def _normalize_tone(tone: str | None) -> str:
    if tone is None:
        return "neutral"
    normalized = tone.strip().lower()
    if not normalized:
        return "neutral"
    if normalized in _TONE_KEYWORDS:
        return normalized
    return "neutral"


@lru_cache(maxsize=2)
def _load_story_outlines(path_key: str) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path_key).read_text(encoding="utf-8"))
    stories = payload["stories"]
    if not stories:
        raise ValueError("story_outlines.yaml contains no stories.")
    return payload


def load_story_outlines(path: Path | None = None) -> dict[str, Any]:
    resolved_path = _story_outlines_path() if path is None else path
    return _load_story_outlines(str(resolved_path.resolve()))


def _tone_score(text: str, tone: str) -> int:
    if tone == "neutral":
        return 0
    score = 0
    for keyword in _TONE_KEYWORDS[tone]:
        if keyword in text:
            score += 1
    return score


def _stable_hash(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def _extract_character_names(outline_text: str) -> list[str]:
    names: list[str] = []
    for line in outline_text.splitlines():
        match = re.match(r"^([A-Z][A-Za-z .'-]{1,60}):\\s", line.strip())
        if match:
            candidate = match.group(1).strip()
            if candidate not in names:
                names.append(candidate)
        if len(names) >= 8:
            break
    if not names:
        return ["Guide", "Rival", "Witness"]
    return names


def select_story_outline(
    genre: str,
    seed: int,
    tone: str | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    normalized_genre = _normalize_genre(genre)
    normalized_tone = _normalize_tone(tone)
    stories = load_story_outlines(path)["stories"]
    candidates = [story for story in stories if story["genre"] == normalized_genre]
    if not candidates:
        raise ValueError(f"No outlines found for genre '{genre}'.")

    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for story in candidates:
        text = str(story["outline"]).lower()
        tone_rank = _tone_score(text, normalized_tone)
        tie_break = _stable_hash(f"{story['id']}|{seed}")
        ranked.append((tone_rank, tie_break, story))
    ranked.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
    selected = dict(ranked[0][2])
    selected["tone"] = normalized_tone
    return selected


def _build_map_for_genre(genre: str) -> dict[str, Any]:
    room_ids = _ROOM_TEMPLATES[genre]
    paths: list[dict[str, str]] = []
    directions = ("north", "east", "north", "east", "north")
    for index, direction in enumerate(directions):
        paths.append({"direction": direction, "from": room_ids[index], "to": room_ids[index + 1]})
        reverse = {"north": "south", "south": "north", "east": "west", "west": "east"}[direction]
        paths.append({"direction": reverse, "from": room_ids[index + 1], "to": room_ids[index]})
    return {"rooms": list(room_ids), "paths": paths}


def build_world_package(
    genre: str,
    session_length: int | str,
    seed: int,
    tone: str | None = None,
    outlines_path: Path | None = None,
) -> dict[str, Any]:
    normalized_genre = _normalize_genre(genre)
    normalized_length = normalize_session_length(session_length)
    outline = select_story_outline(
        genre=normalized_genre,
        seed=seed,
        tone=tone,
        path=outlines_path,
    )
    curve = select_curve_template(
        genre=normalized_genre,
        session_length=normalized_length,
        seed=seed,
    )
    character_names = _extract_character_names(outline["outline"])
    map_section = _build_map_for_genre(normalized_genre)
    item_ids = list(_ITEM_TEMPLATES[normalized_genre])
    primary_goal = str(outline["outline"]).split(".")[0].strip()
    if not primary_goal:
        primary_goal = f"Resolve the central conflict in this {normalized_genre} scenario."

    beat_candidates = list(curve["obligatory_moments"])
    trigger_seeds = [
        {"name": moment, "trigger": f"beat:{moment}", "effect": "advance_tension"}
        for moment in curve["obligatory_moments"]
    ]
    item_graph_edges = [
        {"from": item_ids[0], "to": beat_candidates[0]},
        {"from": item_ids[1], "to": beat_candidates[min(1, len(beat_candidates) - 1)]},
        {"from": item_ids[2], "to": beat_candidates[-1]},
    ]

    return {
        "genre": normalized_genre,
        "tone": outline["tone"],
        "session_length": normalized_length,
        "curve_id": curve["curve_id"],
        "curve_points": list(curve["points"]),
        "outline": {
            "id": str(outline["id"]),
            "source_text": outline["outline"],
        },
        "entities": {
            "npcs": character_names,
            "factions": [f"{normalized_genre}_faction"],
        },
        "map": map_section,
        "goals": {
            "primary": primary_goal,
            "secondary": [f"Reach beat: {moment}" for moment in beat_candidates[:3]],
        },
        "beat_candidates": beat_candidates,
        "item_graph": {
            "items": item_ids,
            "edges": item_graph_edges,
        },
        "trigger_seeds": trigger_seeds,
    }
