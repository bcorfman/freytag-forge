from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from storygame.engine.interfaces import load_policy_bundle
from storygame.plot.curves import normalize_session_length, select_curve_template
from storygame.story_canon import DEFAULT_MYSTERY_DETECTIVE_NAME

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
    "sci-fi": ("dock_hub", "market_arcade", "archive_node", "lab_ring", "tower_array", "command_core"),
    "mystery": ("front_steps", "foyer", "market_lane", "records_office", "safehouse", "watch_tower", "old_chapel"),
    "romance": ("courtyard", "cafe_row", "garden_path", "gallery_hall", "river_walk", "lantern_square"),
    "adventure": ("camp", "trailhead", "cliff_pass", "ruin_gate", "inner_chamber", "return_camp"),
    "action": ("safe_flat", "alley_junction", "control_room", "warehouse", "checkpoint", "extraction_point"),
    "suspense": ("apartment", "backstreet", "records_room", "subway_platform", "abandoned_site", "panic_room"),
    "drama": ("family_home", "main_street", "clinic", "school_hall", "community_center", "lake_house"),
    "fantasy": ("village_gate", "market_square", "scribe_hall", "enchanted_wood", "citadel_steps", "sanctum"),
    "horror": ("old_house", "fog_road", "chapel_ruins", "cellar", "woods_edge", "ritual_room"),
    "thriller": ("transit_hub", "newsroom", "intel_vault", "industrial_yard", "embassy_corridor", "final_site"),
}

_ITEM_TEMPLATES: dict[str, tuple[str, ...]] = {
    "sci-fi": ("data_key", "signal_lens", "power_cell"),
    "mystery": ("case_file", "ledger_page", "route_key"),
    "romance": ("letter", "locket", "keepsake"),
    "adventure": ("map_fragment", "rope_kit", "artifact_shard"),
    "action": ("badge", "breach_charge", "comm_scrambler"),
    "suspense": ("burner_phone", "security_card", "flash_drive"),
    "drama": ("old_photo", "medical_note", "voice_message"),
    "fantasy": ("rune_token", "moon_blade", "warded_scroll"),
    "horror": ("salt_pouch", "candle_bundle", "sigil_stone"),
    "thriller": ("cipher_sheet", "surveillance_tape", "access_chip"),
}

_DEFAULT_SETUP_OBJECTIVES: dict[str, str] = {
    "mystery": "Review the case file, question your first contact, and identify the strongest lead.",
    "thriller": "Get oriented, verify your intel, and secure the first trustworthy contact.",
    "horror": "Get oriented, survey the immediate threat, and establish a safe next move.",
}

_DEFAULT_PRIMARY_OBJECTIVES: dict[str, str] = {
    "mystery": "Uncover who is behind the case and why the truth was buried.",
    "thriller": "Expose the operation driving the crisis and stop it before escalation.",
    "horror": "Understand what is haunting the situation and break its hold before it spreads.",
}


class WorldPackageValidationError(ValueError):
    """Raised when external story data cannot form a coherent package."""


@lru_cache(maxsize=1)
def load_story_package_templates(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load declarative Phase 1 templates without exposing YAML to runtime code."""
    package_path = Path(__file__).resolve().parents[2] / "data" / "story_packages.yaml" if path is None else path
    payload = yaml.safe_load(package_path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != 1 or not isinstance(payload.get("packages"), dict):
        raise WorldPackageValidationError("story_packages.yaml has an unsupported schema.")
    default = payload.get("default", {})
    templates: dict[str, dict[str, Any]] = {"default": dict(default)}
    for genre, raw in payload["packages"].items():
        if not isinstance(raw, dict):
            raise WorldPackageValidationError(f"package template '{genre}' must be a mapping.")
        templates[str(genre)] = deepcopy(dict(raw))
    return templates


def _validate_ids(values: list[str], label: str) -> set[str]:
    if not values or len(values) != len(set(values)) or any(not value.strip() for value in values):
        raise WorldPackageValidationError(f"{label} require unique non-empty ids.")
    return set(values)


def validate_world_package(package: dict[str, Any]) -> dict[str, Any]:
    """Validate Phase 1 package sections and cross-section references."""
    if not isinstance(package, dict):
        raise WorldPackageValidationError("world package must be a mapping")
    required = ("map", "characters", "items", "opening_setup", "intent_aliases", "effect_templates")
    missing = [section for section in required if section not in package]
    if missing:
        raise WorldPackageValidationError(f"missing package sections: {', '.join(missing)}")
    map_data = package["map"]
    if (
        not isinstance(map_data, dict)
        or not isinstance(package["characters"], list)
        or not isinstance(package["items"], list)
    ):
        raise WorldPackageValidationError("map, characters, and items have invalid shapes")
    room_ids = _validate_ids([str(room) for room in map_data.get("rooms", [])], "map rooms")
    paths = map_data.get("paths", [])
    for path in paths:
        if path.get("from") not in room_ids or path.get("to") not in room_ids:
            raise WorldPackageValidationError("unknown map room in path")
        if not str(path.get("direction", "")).strip():
            raise WorldPackageValidationError("map paths require directions")
    _validate_ids([str(item.get("id", "")) for item in package["items"] if isinstance(item, dict)], "items")
    character_ids = _validate_ids(
        [str(character.get("id", "")) for character in package["characters"] if isinstance(character, dict)],
        "characters",
    )
    for character in package["characters"]:
        if not isinstance(character, dict) or character.get("location") not in room_ids:
            raise WorldPackageValidationError("unknown character location")
        for field in ("role", "scene_purpose"):
            if not str(character.get(field, "")).strip():
                raise WorldPackageValidationError(f"characters require {field}")
    seen_custody: set[str] = set()
    for item in package["items"]:
        if not isinstance(item, dict):
            raise WorldPackageValidationError("items must contain mappings")
        custody = item.get("initial_custody")
        if custody:
            custody_key = str(item["id"])
            if custody_key in seen_custody:
                raise WorldPackageValidationError(f"duplicate custody for item '{custody_key}'")
            seen_custody.add(custody_key)
            if custody.get("kind") == "npc" and custody.get("id") not in character_ids:
                raise WorldPackageValidationError("unknown custody reference")
            if custody.get("kind") == "room" and custody.get("id") not in room_ids:
                raise WorldPackageValidationError("unknown custody reference")
    opening = package["opening_setup"]
    if not isinstance(opening, dict):
        raise WorldPackageValidationError("opening_setup must be a mapping")
    public = set(map(str, opening.get("public_briefing", [])))
    protected = set(map(str, opening.get("protected_knowledge", [])))
    if public & protected:
        raise WorldPackageValidationError("protected knowledge is exposed as public briefing")
    if not isinstance(package["intent_aliases"], dict) or not isinstance(package["effect_templates"], dict):
        raise WorldPackageValidationError("intent aliases and effect templates must be mappings")
    package["map"]["room_presentation"] = {
        str(room): dict(package["map"].get("room_presentation", {}).get(str(room), {}))
        for room in room_ids
    }
    return package


@lru_cache(maxsize=1)
def _opening_setup_profiles() -> dict[str, dict[str, Any]]:
    path = Path(__file__).resolve().parents[2] / "data" / "opening_setup.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("opening_setup.yaml must contain genre-keyed mappings.")
    return {str(genre): dict(profile) for genre, profile in payload.items() if isinstance(profile, dict)}


def _clean_outline_sentence(outline_text: str) -> str:
    text = outline_text.strip()
    if text.lower().startswith("premise:"):
        text = text[len("premise:") :].strip()
    sentence = text.split(".")[0].strip()
    return sentence


def _trim_goal_fragment(text: str, max_len: int = 120) -> str:
    normalized = re.sub(r"\s+", " ", text).strip(" .,:;-")
    if len(normalized) <= max_len:
        return normalized
    shortened = normalized[:max_len].rsplit(" ", 1)[0].strip()
    return shortened if shortened else normalized[:max_len]


def _outline_fragments(outline_text: str) -> list[str]:
    fragments: list[str] = []
    for raw_line in outline_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        for prefix in ("premise:", "outline:", "scene:", "characters:"):
            if lowered.startswith(prefix):
                line = line[len(prefix) :].strip()
                break
        if not line:
            continue
        parts = re.split(r"[.!?]\s+", line)
        for part in parts:
            cleaned = _trim_goal_fragment(part, max_len=140)
            if len(cleaned) < 20:
                continue
            if cleaned not in fragments:
                fragments.append(cleaned)
            if len(fragments) >= 6:
                return fragments
    return fragments


def _build_outline_goals(genre: str, outline_text: str, beat_candidates: list[str]) -> dict[str, Any]:
    fragments = _outline_fragments(outline_text)
    setup = _DEFAULT_SETUP_OBJECTIVES.get(
        genre,
        "Survey the situation, confirm your first lead, and choose a concrete next action.",
    )
    primary = _DEFAULT_PRIMARY_OBJECTIVES.get(
        genre,
        f"Define and confront the core conflict in this {genre} scenario.",
    )

    secondary: list[str] = []
    for fragment in fragments[:2]:
        secondary.append(f"Pursue this emerging thread: {fragment}.")
    for moment in beat_candidates:
        if len(secondary) >= 3:
            break
        secondary.append(f"Reach beat: {moment}")

    return {"setup": setup, "primary": primary, "secondary": secondary[:3]}


def _split_setup_and_future_threads(outline_text: str) -> tuple[str, tuple[str, ...]]:
    normalized = _trim_goal_fragment(_clean_outline_sentence(outline_text), max_len=420)
    if not normalized:
        return "", ()

    spoiler_markers = (
        " that leads ",
        " which leads ",
        " leading to ",
        " and a choice ",
        " and must choose ",
        " where they must choose ",
    )
    lowered = normalized.lower()
    split_index = -1
    for marker in spoiler_markers:
        idx = lowered.find(marker)
        if idx >= 0 and (split_index < 0 or idx < split_index):
            split_index = idx

    if split_index < 0:
        return normalized, ()

    public_setup = normalized[:split_index].strip(" ,;")
    hidden_text = _trim_goal_fragment(normalized[split_index:].strip(" ,;"), max_len=420)
    return public_setup, (hidden_text,) if hidden_text else ()

def _build_story_plan(outline_text: str, goals: dict[str, Any]) -> dict[str, Any]:
    _public_setup, hidden_threads = _split_setup_and_future_threads(outline_text)
    setup_paragraphs = (
        "The situation is still taking shape, and the facts in front of you are incomplete.",
        f"You are {DEFAULT_MYSTERY_DETECTIVE_NAME}.",
        f"Your first objective is clear: {goals['setup']}",
    )
    reveal_schedule = tuple(
        {
            "thread_index": index,
            "min_progress": round(0.55 + (0.2 * index), 2),
        }
        for index in range(len(hidden_threads))
    )

    return {
        "protagonist_name": DEFAULT_MYSTERY_DETECTIVE_NAME,
        "setup_paragraphs": setup_paragraphs,
        "hidden_threads": hidden_threads,
        "reveal_schedule": reveal_schedule,
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
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    payload = yaml.load(Path(path_key).read_text(encoding="utf-8"), Loader=loader)
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
    ignored_labels = {
        "premise",
        "settings",
        "characters",
        "outline",
        "scene",
        "situation",
    }
    for line in outline_text.splitlines():
        match = re.match(r"^([A-Z][A-Za-z .'-]{1,60}):\s", line.strip())
        if match:
            candidate = match.group(1).strip()
            if candidate.lower() in ignored_labels:
                continue
            if candidate not in names:
                names.append(candidate)
        if len(names) >= 8:
            break
    if not names:
        return ["Guide", "Rival", "Witness"]
    return names


def _normalize_character_names_for_genre(genre: str, names: list[str]) -> list[str]:
    if genre != "mystery":
        return names

    normalized: list[str] = ["Daria Stone"]
    for name in names:
        if name.strip().lower() == "daria stone":
            continue
        normalized.append(name)
    return normalized


def select_story_outline(
    genre: str,
    seed: int,
    tone: str | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    normalized_genre = _normalize_genre(genre)
    # Validate executable predicate/rule data before realizing any package.
    load_policy_bundle(normalized_genre)
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
    template = load_story_package_templates().get(genre, load_story_package_templates()["default"])
    room_ids = tuple(template.get("map", {}).get("rooms", _ROOM_TEMPLATES[genre]))
    if template.get("map", {}).get("paths"):
        return {"rooms": list(room_ids), "paths": deepcopy(template["map"]["paths"]), "room_presentation": {}}
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
    character_names = _normalize_character_names_for_genre(
        normalized_genre,
        _extract_character_names(outline["outline"]),
    )
    map_section = _build_map_for_genre(normalized_genre)
    template = load_story_package_templates().get(normalized_genre, load_story_package_templates()["default"])
    item_ids = list(template.get("items", _ITEM_TEMPLATES[normalized_genre]))
    beat_candidates = list(curve["obligatory_moments"])
    goals = _build_outline_goals(normalized_genre, str(outline["outline"]), beat_candidates)
    story_plan = _build_story_plan(str(outline["outline"]), goals)
    opening_setup = deepcopy(_opening_setup_profiles().get(normalized_genre, {}))
    opening_setup.update(deepcopy(template.get("opening_setup", {})))
    characters = []
    character_template = template.get("characters", {})
    for index, name in enumerate(character_names):
        characters.append(
            {
                "id": re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "character",
                "name": name,
                "location": map_section["rooms"][min(index, len(map_section["rooms"]) - 1)],
                "available": True,
                "traits": list(character_template.get("traits", [])),
                "appearance": str(character_template.get("appearance", "")),
                "role": str(character_template.get("role", "contact")),
                "relationship": str(character_template.get("relationship", "")),
                "scene_purpose": str(character_template.get("scene_purpose", "")),
                "initial_knowledge": list(character_template.get("initial_knowledge", [])),
                "protected_knowledge": list(character_template.get("protected_knowledge", [])),
            }
        )
    items = [
        {
            "id": item_id,
            "affordances": list(template.get("items", {}).get("affordances", ["examine", "take"]))
            if isinstance(template.get("items"), dict) else ["examine", "take"],
                "initial_state": "available",
                "initial_custody": None,
        }
        for item_id in item_ids
    ]

    trigger_seeds = [
        {"name": moment, "trigger": f"beat:{moment}", "effect": "advance_tension"}
        for moment in curve["obligatory_moments"]
    ]
    item_graph_edges = [
        {"from": item_ids[0], "to": beat_candidates[0]},
        {"from": item_ids[1], "to": beat_candidates[min(1, len(beat_candidates) - 1)]},
        {"from": item_ids[2], "to": beat_candidates[-1]},
    ]

    package = {
        "schema_version": 1,
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
        "characters": characters,
        "items": items,
        "goals": goals,
        "story_plan": story_plan,
        "opening_setup": opening_setup,
        "beat_candidates": beat_candidates,
        "item_graph": {
            "items": item_ids,
            "edges": item_graph_edges,
        },
        "trigger_seeds": trigger_seeds,
        "intent_aliases": deepcopy(template.get("intent_aliases", {})),
        "effect_templates": deepcopy(template.get("effect_templates", {})),
    }
    package["map"]["room_presentation"] = {
        room_id: {
            "name": re.sub(r"\s+", " ", room_id.replace("_", " ").replace("-", " ")).strip().title(),
            "description": f"The {room_id.replace('_', ' ')} awaits close inspection.",
        }
        for room_id in package["map"]["rooms"]
    }
    return validate_world_package(package)
