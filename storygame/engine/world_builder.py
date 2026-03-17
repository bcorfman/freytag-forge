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
    "thriller": "Stabilize the situation, verify your intel, and secure the first trustworthy contact.",
    "horror": "Survey the immediate threat, gather protective tools, and establish a safe next move.",
}

_DEFAULT_PRIMARY_OBJECTIVES: dict[str, str] = {
    "mystery": "Uncover who is behind the case and why the truth was buried.",
    "thriller": "Expose the operation driving the crisis and stop it before escalation.",
    "horror": "Understand what is haunting the situation and break its hold before it spreads.",
}


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


def _sanitize_goal_anchor(anchor: str) -> str:
    cleaned = _trim_goal_fragment(anchor, max_len=140)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;-")
    cleaned = re.sub(r"\b(is|was|are|were)\s+tasked\s+with$", "", cleaned, flags=re.IGNORECASE).strip(" ,;:-")
    cleaned = re.sub(r"\b(tasked|assigned|ordered|forced)\s+to$", "", cleaned, flags=re.IGNORECASE).strip(" ,;:-")
    return cleaned


def _anchor_is_non_actionable(anchor: str) -> bool:
    lowered = anchor.lower().strip()
    if not lowered:
        return True
    if "is tasked with" in lowered or "are tasked with" in lowered:
        return True
    if lowered.startswith(("a detective", "an investigator", "you, a detective", "you are a detective")):
        return True
    if lowered.endswith(("tasked with", "assigned to", "ordered to", "forced to")):
        return True
    return False


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
    anchor = fragments[0] if fragments else _clean_outline_sentence(outline_text)
    anchor = _sanitize_goal_anchor(anchor)
    use_anchor = not _anchor_is_non_actionable(anchor)

    if use_anchor:
        setup = f"Get oriented and secure your first reliable lead: {anchor}."
        primary = f"Define and confront the core conflict: {anchor}."
    else:
        setup = _DEFAULT_SETUP_OBJECTIVES.get(
            genre,
            "Survey the situation, confirm your first lead, and choose a concrete next action.",
        )
        primary = _DEFAULT_PRIMARY_OBJECTIVES.get(
            genre,
            f"Define and confront the core conflict in this {genre} scenario.",
        )

    secondary: list[str] = []
    for fragment in fragments[1:3]:
        secondary.append(f"Pursue this emerging thread: {fragment}.")
    for moment in beat_candidates:
        if len(secondary) >= 3:
            break
        secondary.append(f"Reach beat: {moment}")

    return {"setup": setup, "primary": primary, "secondary": secondary[:3]}


def _select_protagonist_name(seed: int, genre: str) -> str:
    names = (
        "Rowan Vale",
        "Mara Quinn",
        "Elias Ward",
        "Sable Mercer",
        "Noah Kade",
        "Iris Holloway",
    )
    return names[_stable_hash(f"{genre}|{seed}|protagonist") % len(names)]


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


def _public_setting_line(genre: str) -> str:
    settings = {
        "mystery": "The estate stands at the edge of a rain-soaked district where every visitor brings a new rumor.",
        "thriller": "The residence overlooks a restless city perimeter where patrol lights never fully go dark.",
        "horror": "The house sits beyond a fog-bound road where the wind carries sounds that never resolve.",
        "fantasy": "The manor rises above old stone paths and watchfires that mark the border of a fragile realm.",
    }
    return settings.get(
        genre,
        "The residence is isolated from the nearest town, with only a narrow road and uncertain weather beyond it.",
    )


def _build_story_plan(genre: str, seed: int, outline_text: str, goals: dict[str, Any]) -> dict[str, Any]:
    protagonist_name = _select_protagonist_name(seed, genre)
    public_setup, hidden_threads = _split_setup_and_future_threads(outline_text)
    if not public_setup:
        public_setup = _trim_goal_fragment(
            str(goals["setup"]).replace("Get oriented and secure your first reliable lead: ", "")
        )

    setup_paragraphs = [
        (
            f"{protagonist_name} has kept a low profile for years, taking only the work that can be handled in silence. "
            f"{public_setup}."
        ),
        _public_setting_line(genre),
        f"The first practical objective is simple and immediate: {goals['setup']}",
        "What this case truly means is still hidden; the larger truths should surface only as the investigation advances.",
    ]

    reveal_schedule = tuple(
        {
            "thread_index": index,
            "min_progress": round(0.55 + (0.2 * index), 2),
        }
        for index in range(len(hidden_threads))
    )

    return {
        "protagonist_name": protagonist_name,
        "setup_paragraphs": tuple(setup_paragraphs),
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
    if genre == "mystery":
        return {
            "rooms": list(_ROOM_TEMPLATES[genre]),
            "paths": [
                {"direction": "north", "from": "front_steps", "to": "foyer"},
                {"direction": "south", "from": "foyer", "to": "front_steps"},
                {"direction": "east", "from": "foyer", "to": "market_lane"},
                {"direction": "west", "from": "market_lane", "to": "foyer"},
                {"direction": "north", "from": "market_lane", "to": "records_office"},
                {"direction": "south", "from": "records_office", "to": "market_lane"},
                {"direction": "east", "from": "records_office", "to": "safehouse"},
                {"direction": "west", "from": "safehouse", "to": "records_office"},
                {"direction": "north", "from": "safehouse", "to": "watch_tower"},
                {"direction": "south", "from": "watch_tower", "to": "safehouse"},
                {"direction": "east", "from": "watch_tower", "to": "old_chapel"},
                {"direction": "west", "from": "old_chapel", "to": "watch_tower"},
            ],
        }

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
    character_names = _normalize_character_names_for_genre(
        normalized_genre,
        _extract_character_names(outline["outline"]),
    )
    map_section = _build_map_for_genre(normalized_genre)
    item_ids = list(_ITEM_TEMPLATES[normalized_genre])
    beat_candidates = list(curve["obligatory_moments"])
    goals = _build_outline_goals(normalized_genre, str(outline["outline"]), beat_candidates)
    story_plan = _build_story_plan(normalized_genre, seed, str(outline["outline"]), goals)

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
        "goals": goals,
        "story_plan": story_plan,
        "beat_candidates": beat_candidates,
        "item_graph": {
            "items": item_ids,
            "edges": item_graph_edges,
        },
        "trigger_seeds": trigger_seeds,
    }
