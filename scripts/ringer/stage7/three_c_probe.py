"""Bounded, auditable raw-player probe for the fresh 3C scene."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from door_transport import RawRequestError, SpendBudget, counted_provider  # noqa: E402
from three_c_prefix import (  # noqa: E402
    UNCLOCKED_JOURNEY,
    _committed_reveals,
    _prefix_count,
    _ScriptedProvider,
    _transition_texts,
)
from three_c_prefix import (  # noqa: E402
    _run as run_canon_prefix,
)
from three_c_prefix import (  # noqa: E402
    _turn as run_scripted_turn,
)

from bench.core import load_variation, package_and_state, provider_for  # noqa: E402
from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff  # noqa: E402
from storygame.runtime.cloudflare import NarrationProviderError  # noqa: E402
from storygame.runtime.engine import RuntimeEngine  # noqa: E402
from storygame.runtime.facts import Fact  # noqa: E402
from storygame.runtime.world_model import world_for  # noqa: E402
from storygame.story_package.loader import load_story_package  # noqa: E402

CAPS = {1: {"cloudflare": 80, "raw_player": 40}, 12: {"cloudflare": 960, "raw_player": 480}}
POSTC_CAPS = {1: {"cloudflare": 80, "raw_player": 40}, 12: {"cloudflare": 480, "raw_player": 240}}
COMMAND_TURNS = tuple(range(9, 15))
RECORDED_TURNS = tuple(range(1, 16))
ARMS = ("control", "pre667")
ALL_ARMS = ("control", "pre667", "surface", "entry", "escape", "custody", "pump", "families", "families-v2")
ARM_FILES = {
    "control": "stage7-3c-control.json",
    "pre667": "stage7-3c-pre667.json",
    "surface": "stage7-3c-surface-binding.json",
    "entry": "stage7-3c-entry-package.json",
    "escape": "stage7-3c-escape-result.json",
    "custody": "stage7-3c-custody-result.json",
    "pump": "stage7-3c-pump-need.json",
    "families": "stage7-3c-families.json",
    "families-v2": "stage7-3c-families-v2.json",
}
STARTS = ("entry", "posta", "post8", "postc", "carried")
POSTA_ATTEMPT_CAP = 20
POST8_ATTEMPT_CAP = 10
POSTC_ATTEMPT_CAP = 10
TRANSCRIPT_CHAR_CAP = 12000
POST8_LABEL = "synthetic post-turn-8: A-R1,B-R1,C-R1,C-R2,D-R2 committed by scripted reveals; not a historical replay"
REPLACEMENT_OLD = ", broadcasting the reports, broadcasting reports, relay the reports, relaying the reports]"
ESCAPE_REPLACEMENT_OLD = (
    "statement: 'Kristin restores power to drainage pumps and holds one watertight barrier while Michelle leads "
    "captives through the maintenance tunnel.'"
)
ESCAPE_REPLACEMENT_NEW = "statement: 'The drainage pumps have power. The evacuation route is open.'"
REMOVED_PHRASES = ("broadcasting the reports", "broadcasting reports", "relay the reports", "relaying the reports")
ENTRY_TEXT_OLD = (
    "entry_text: \"The broadcast chamber lights steadied as Brandon's relay held open. "
    "Outside, Charles's emergency deluge was filling the outer access level and forcing water toward the "
    'maintenance routes; inside, the evidence was ready to leave for good.\\n\\n"'
)
CUSTODY_DELIVERY_OLD = (
    'delivery_text: "Kristin stops Rebecca from fleeing with the data case. Michelle sends its prisoner locations '
    'to independent networks. Water rises around the drainage pump controls."'
)
CUSTODY_DELIVERY_NEW = (
    'delivery_text: "Kristin takes the Portable data case from Rebecca. Michelle sends its prisoner locations '
    'to independent networks. Water rises around the drainage pump controls."'
)
PUMP_DELIVERY_NEW = (
    'delivery_text: "Kristin takes the Portable data case from Rebecca. Michelle sends its prisoner locations '
    'to independent networks. The drainage pumps need power. Water rises around the drainage pump controls."'
)
REQUIRED = {
    "k_sl_3c_a_r1",
    "k_sl_3c_b_r1",
    "k_sl_3c_c_r1",
    "k_sl_3c_c_r2",
    "k_sl_3c_d_r1",
    "k_sl_3c_d_r2",
}
CHAIN = {"k_sl_3c_a_r1", "k_sl_3c_b_r1", "k_sl_3c_c_r1", "k_sl_3c_c_r2"}
DE_R1 = "k_sl_3c_d_r1"
E_IDS = {"k_sl_3c_e_r1", "k_sl_3c_e_r2"}
POST8_REVEALS = (
    ("k_sl_3c_a_r1", "Send the evidence package."),
    ("k_sl_3c_b_r1", "Take the Portable data case from Rebecca."),
    ("k_sl_3c_c_r1", "Restore the drainage pumps."),
    ("k_sl_3c_c_r2", "Open the surface gates."),
    ("k_sl_3c_d_r2", "Call the families of the missing."),
)
POSTC_REVEALS = POST8_REVEALS[:4]
POSTA_REVEALS = (("k_sl_3c_a_r1", "Send the evidence package."),)
POSTC_LABEL = "synthetic post-turn-7: A-R1,B-R1,C-R1,C-R2 committed by scripted reveals; not a historical replay"
CARRIED_LABEL = (
    "carried 3B state: scripted canon journey 1A-3B replayed per arm on the real engine, then real 3B->3C "
    "transition; transcript is authored text, one shared history; not a live save"
)
CARRIED_ENTRY_STATE = "carried: real 3B prefix replayed and real 3B->3C transition rendered"
CARRIED_ATTEMPT_CAP = 20
POSTA_LABEL = "synthetic post-turn-1: A-R1 committed by scripted reveal; not a historical replay"
ENTRY_FACTS = ("broadcast_started", "brandon_confession_available", "detention_locations_secured")
ENTRY_STATE = "synthetic: 3C entry facts asserted, no replay of earlier scenes"
OPENING_REVEALS = {"k_sl_3c_a_r1", "k_sl_3c_a_r2"}
POSTA_REVEALS_EXPECTED = ["k_sl_3c_b_r1", "k_sl_3c_b_r2"]
ACQUISITION_COMMAND_RE = re.compile(
    r"(?:\b(?:take|grab|retrieve|wrest|snatch|get)\b.*\b(?:case|archive)\b|"
    r"\b(?:case|archive)\b.*\b(?:take|grab|retrieve|wrest|snatch|get)\b)",
    re.IGNORECASE,
)
CASE_ENTITY_ID = "portable_archive"


class ProbeRunFailure(RuntimeError):
    """A non-recoverable row failure with enough context for the run ledger."""

    def __init__(self, error: BaseException, attempt: int, row_id: str | None = None) -> None:
        self.error = error
        self.attempt = attempt
        self.row_id = row_id
        super().__init__(failure_message(self))


def _http_details(error: BaseException) -> tuple[int | None, str | None]:
    current: BaseException | None = error
    while current is not None:
        if isinstance(current, HTTPError):
            return current.code, current.reason
        current = current.__cause__
    return None, None


def failure_message(failure: ProbeRunFailure | BaseException) -> str:
    if isinstance(failure, ProbeRunFailure):
        error = failure.error
        row_id = failure.row_id or "unknown"
        attempt = failure.attempt
    else:
        error = failure
        row_id = "unknown"
        attempt = "unknown"
    status = getattr(error, "status_code", None)
    reason = None
    cause_status, cause_reason = _http_details(error)
    if status is None:
        status = cause_status
    if cause_reason is not None:
        reason = cause_reason
    detail = getattr(error, "message", None) or str(error)
    parts = [
        f"row_id={row_id}",
        f"attempt={attempt}",
        f"exception={type(error).__name__}",
        f"detail={detail}",
    ]
    if status is not None:
        parts.append(f"http_status={status}")
    if reason is not None:
        parts.append(f"http_reason={reason}")
    return " ".join(parts)


def _entry_replacement() -> tuple[str, str]:
    variation = load_variation(ROOT / "bench/variations/stage7-3c-entry-package.json")
    replacement = variation["overrides"]["plot.md"]["replacements"][0]
    return replacement["old"], replacement["new"]


def atomic_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def variation_paths(arms: tuple[str, ...] = ARMS) -> dict[str, Path]:
    return {arm: ROOT / "bench/variations" / ARM_FILES[arm] for arm in arms}


def source_proof(arms: tuple[str, ...] = ARMS) -> dict[str, Any]:
    source = ROOT / "data/stories/continuity-initiative"
    knowledge_path = source / "knowledge.yaml"
    plot_path = source / "plot.md"
    raw = knowledge_path.read_text(encoding="utf-8")
    count = raw.count(REPLACEMENT_OLD)
    if count != 1:
        raise RuntimeError(f"replacement text did not match exactly once (found {count})")
    escape_count = raw.count(ESCAPE_REPLACEMENT_OLD)
    if escape_count != 1:
        raise RuntimeError(f"escape replacement text did not match exactly once (found {escape_count})")
    custody_count = raw.count(CUSTODY_DELIVERY_OLD)
    if custody_count != 1:
        raise RuntimeError(f"custody B-R1 replacement did not match exactly once (found {custody_count})")
    pump_count = raw.count(PUMP_DELIVERY_NEW)
    if pump_count != 0:
        raise RuntimeError(f"pump B-R1 replacement is already present in knowledge.yaml (found {pump_count})")
    loaded: dict[str, Any] = {}
    for arm, path in variation_paths(arms).items():
        variation = load_variation(path)
        package, _ = package_and_state(variation, "3C")
        entry = package.knowledge_indexes.by_id[DE_R1]
        c_r1 = package.knowledge_indexes.by_id["k_sl_3c_c_r1"]
        phrases = {phrase for group in entry.action_evidence for phrase in group}
        loaded[arm] = {
            "variation": path.name,
            "package_hash": variation["_package_hash"],
            "d_r1_action_evidence": [list(group) for group in entry.action_evidence],
            "has_removed_phrases": any(phrase in phrases for phrase in REMOVED_PHRASES),
            "c_r1_statement": c_r1.statement,
            "b_r1_delivery": package.knowledge_indexes.by_id["k_sl_3c_b_r1"].delivery_text,
        }
    entry_old, entry_new = _entry_replacement()
    entry_raw = plot_path.read_text(encoding="utf-8")
    entry_count = entry_raw.count(entry_old)
    if entry_count != 1:
        raise RuntimeError(f"plot.md entry_text replacement did not match exactly once (found {entry_count})")
    entry_variation = load_variation(ROOT / "bench/variations/stage7-3c-entry-package.json")
    entry_package, _ = package_and_state(entry_variation, "3C")
    entry_scene = next(item for item in entry_package.scenes if item.metadata.scene_id == "3C")
    old_entry_text = entry_old.removeprefix('entry_text: "').removesuffix('"').replace("\\n", "\n")
    new_entry_text = entry_new.removeprefix('entry_text: "').removesuffix('"').replace("\\n", "\n")
    if entry_scene.metadata.entry_text != new_entry_text:
        raise RuntimeError("entry variation did not produce the recorded new entry_text")
    removed = REMOVED_PHRASES
    if "control" in loaded:
        control_phrases = {phrase for group in loaded["control"]["d_r1_action_evidence"] for phrase in group}
        if not all(phrase in control_phrases for phrase in removed):
            raise RuntimeError("control d_r1 action evidence is missing one of the four PR 667 phrases")
    if "pre667" in loaded:
        pre_phrases = {phrase for group in loaded["pre667"]["d_r1_action_evidence"] for phrase in group}
        if any(phrase in pre_phrases for phrase in removed):
            raise RuntimeError("pre667 d_r1 action evidence still contains a PR 667 phrase")
    if "escape" in loaded and loaded["escape"]["c_r1_statement"] != ESCAPE_REPLACEMENT_NEW.removeprefix(
        "statement: '"
    ).removesuffix("'"):
        raise RuntimeError("escape variation did not produce the recorded new C-R1 statement")
    if "control" in loaded and loaded["control"]["c_r1_statement"] != ESCAPE_REPLACEMENT_OLD.removeprefix(
        "statement: '"
    ).removesuffix("'"):
        raise RuntimeError("control package did not retain the recorded old C-R1 statement")
    if "pump" in loaded:
        if loaded["pump"]["b_r1_delivery"] != PUMP_DELIVERY_NEW.removeprefix('delivery_text: "').removesuffix('"'):
            raise RuntimeError("pump variation did not produce the recorded new B-R1 delivery")
        if loaded["pump"]["b_r1_delivery"].count("The drainage pumps need power. ") != 1:
            raise RuntimeError("pump B-R1 delivery does not contain the new sentence exactly once")
    return {
        "player_screen": (
            "entry text + running transcript of command lines (prefixed with a greater-than sign) "
            "and replies, as the page #transcript"
        ),
        "transcript_note": (
            "Only accepted turns append to the transcript; rejected turns show no rejection notice "
            "in the player screen."
        ),
        "variation_files": {
            arm: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for arm, path in variation_paths(arms).items()
        },
        "knowledge_yaml": {
            "path": str(knowledge_path),
            "sha256": hashlib.sha256(knowledge_path.read_bytes()).hexdigest(),
            "replacement": {"old": REPLACEMENT_OLD, "new": "]", "matches": count},
            "custody_b_r1_replacement": {
                "old": CUSTODY_DELIVERY_OLD,
                "new": CUSTODY_DELIVERY_NEW,
                "matches": custody_count,
            },
            "pump_b_r1_replacement": {
                "old": CUSTODY_DELIVERY_NEW,
                "new": PUMP_DELIVERY_NEW,
                "matches": 1
                if "pump" in loaded
                and loaded["pump"]["b_r1_delivery"]
                == PUMP_DELIVERY_NEW.removeprefix('delivery_text: "').removesuffix('"')
                else 0,
            },
            "escape_replacement": {
                "old": ESCAPE_REPLACEMENT_OLD,
                "new": ESCAPE_REPLACEMENT_NEW,
                "matches": escape_count,
            },
            "loaded_arms": loaded,
        },
        "plot_md": {
            "replacement": {
                "old_entry_text": old_entry_text,
                "new_entry_text": new_entry_text,
                "matches": entry_count,
            }
        },
    }


def recorded_commands() -> list[dict[str, Any]]:
    """Load all explicitly labelled raw-language replay commands at runtime."""

    table = ROOT / "bench/results/stage7-3c-matcher-table/table.json"
    rows = json.loads(table.read_text(encoding="utf-8"))["rows"]
    selected = [row for row in rows if row["turn"] in RECORDED_TURNS]
    if [row["turn"] for row in selected] != list(RECORDED_TURNS):
        raise RuntimeError("matcher table does not contain exactly the recorded turns 1 through 15")
    return [{"turn_label": row["turn"], "command": row["commands"]["raw"]} for row in selected]


def command_probe_commands() -> list[dict[str, Any]]:
    """Return the bounded six-turn command-mode subset used by the live probe."""

    return [item for item in recorded_commands() if item["turn_label"] in COMMAND_TURNS]


def classify_outcome(
    story_complete: bool,
    player_reveals: set[str],
    all_reveals: set[str] | None = None,
    deadline_ids: list[str] | tuple[str, ...] = (),
    given_reveals: set[str] | None = None,
) -> str:
    if not story_complete:
        return "no_complete"
    all_reveals = player_reveals if all_reveals is None else all_reveals
    given_reveals = set() if given_reveals is None else given_reveals
    effective_reveals = player_reveals | given_reveals
    provenance_known = player_reveals == all_reveals or bool(given_reveals)
    earned = (
        provenance_known
        and REQUIRED.issubset(effective_reveals)
        and DE_R1 in player_reveals
        and bool(E_IDS & player_reveals)
        and not deadline_ids
    )
    if earned:
        return "earned_complete"
    return "deadline_complete"


def should_stop(
    attempts: int,
    accepted_turns: int,
    story_complete: bool,
    extra_after_14: bool,
    max_attempts: int = 20,
) -> bool:
    """Apply the row bounds after a turn has been recorded."""

    return story_complete or attempts >= max_attempts or (accepted_turns >= 14 and extra_after_14)


def _ask_player(screen: str, budget: SpendBudget) -> str:
    budget.reserve("raw_player")
    result = subprocess.run(
        ["node", str(ROOT / "scripts/ringer/stage7/door_ask_player.mjs")],
        input=json.dumps({"transcript": screen, "status": ""}),
        text=True,
        capture_output=True,
        cwd=ROOT,
        env=os.environ.copy(),
        check=False,
    )
    if result.returncode:
        budget.acknowledge("raw_player", False, result.stderr.strip() or "child failed")
        raise RawRequestError("player", RuntimeError(result.stderr.strip() or "player child failed"))
    try:
        command = json.loads(result.stdout)["command"]
    except (ValueError, KeyError, TypeError) as error:
        budget.acknowledge("raw_player", False, "malformed child JSON")
        raise RawRequestError("player-parse", error, result.stdout) from error
    if not isinstance(command, str) or not command.strip():
        budget.acknowledge("raw_player", False, "empty command")
        raise RawRequestError("player-parse", ValueError("player returned an empty command"))
    budget.acknowledge("raw_player", True)
    return command


def _status(response: Any) -> str:
    if hasattr(response, "clarification"):
        return "clarification"
    if getattr(response, "game_break", None) is not None:
        return "rejected"
    return "accepted"


def _response_text(response: Any) -> str:
    if hasattr(response, "clarification"):
        clarification = response.clarification
        return str(getattr(clarification, "text", clarification))
    return str(getattr(response, "narration", response))


def _rejection_text(response: Any) -> str | None:
    if getattr(response, "game_break", None) is not None:
        return str(getattr(response.game_break, "reason", response.game_break))
    return None


def _fact_keys(state: Any) -> set[str]:
    return {"|".join(str(part) for part in fact.key) for fact in state.facts.asserted}


def _staged_cue(state: Any) -> dict[str, Any] | None:
    fact_id = state.last_turn_delivery.cue_fact_id
    if fact_id is None:
        return None
    delivery = next((item for item in state.package.deliveries if item.fact_id == fact_id), None)
    return {
        "fact_id": fact_id,
        "stage": state.staged_cue_stage,
        "text": delivery.cue_text if delivery is not None else None,
    }


def _parent_snapshot(package: Any, state: Any) -> tuple[str | None, str | None, str | None]:
    world = world_for(package, state.facts)
    return world.parent("captives"), world.parent("kristin"), world.parent(CASE_ENTITY_ID)


def assert_3c_entry_facts(state: Any) -> Any:
    for fact_id in ENTRY_FACTS:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    return state


def _scripted_provider(package: Any, knowledge_id: str) -> Callable[[str], dict[str, Any]]:
    knowledge = package.knowledge_indexes.by_id[knowledge_id]
    text = knowledge.delivery_text or knowledge.statement
    return lambda _command: {
        "segments": [{"kind": "narration", "text": text, "grounding_ids": [knowledge_id]}],
        "selected_knowledge_ids": [knowledge_id],
    }


def carried_replay(package: Any, variation: dict[str, Any]) -> dict[str, Any]:
    """Replay the shared canon prefix and cross into 3C on this arm's package."""

    prefix_record = json.loads((ROOT / "bench/results/stage7-3c-prefix/prefix.json").read_text(encoding="utf-8"))
    expected_count = prefix_record["turn_index"]
    if expected_count != _prefix_count(package):
        raise RuntimeError(f"carried prefix turn count changed: expected {expected_count}")
    if variation.get("_package_hash") == prefix_record["package_content_hash"]:
        raise RuntimeError("carried arm package hash matches the checkpoint package")
    state, transcript = run_canon_prefix(package, expected_count)
    if state.current_scene_id != "3B" or state.has_pending_break:
        raise RuntimeError("carried canon prefix did not end cleanly in 3B")
    committed = _committed_reveals(state)
    if committed != prefix_record["committed_reveal_ids"]:
        raise RuntimeError("carried 3B committed reveal ids differ from prefix.json")
    prefix_hash = hashlib.sha256(
        json.dumps(committed, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    provider = _ScriptedProvider(package)
    engine = RuntimeEngine(state, provider)
    selection, expected_scene = UNCLOCKED_JOURNEY[expected_count]
    transition_result = run_scripted_turn(engine, provider, selection)
    if state.current_scene_id != "3C" or expected_scene != "3C" or state.has_pending_break:
        raise RuntimeError("carried scripted crossing did not end cleanly in 3C")
    entry_text, bridge_text = _transition_texts(state, transition_result)
    if not any(fact.predicate == "relay_open" and str(fact.value).lower() == "true" for fact in state.facts.asserted):
        raise RuntimeError("carried 3C entry did not commit relay_open")
    chain_ids = {item for item in _committed_reveals(state) if item.startswith("k_sl_3c_")}
    if chain_ids:
        raise RuntimeError(f"carried crossing committed 3C chain reveals: {sorted(chain_ids)}")
    return {
        "state": state,
        "transcript": transcript,
        "prefix": {
            "turn_index": expected_count,
            "committed_reveal_ids": committed,
            "committed_reveal_ids_hash": prefix_hash,
        },
        "entry_text": entry_text,
        "bridge_text": bridge_text,
        "crossing_response": _response_text(transition_result),
    }


def _player_screen(entry_text: str, transcript: list[tuple[str, str]]) -> tuple[str, int]:
    """Render the player-visible page transcript, retaining whole oldest turns."""

    rendered = [f"> {command}\n{reply}" for command, reply in transcript]
    transcript_text = "\n\n".join(rendered)
    while len(transcript_text) > TRANSCRIPT_CHAR_CAP and len(rendered) > 1:
        rendered.pop(0)
        transcript_text = "\n\n".join(rendered)
    if len(transcript_text) > TRANSCRIPT_CHAR_CAP:
        transcript_text = transcript_text[-TRANSCRIPT_CHAR_CAP:]
    screen = entry_text.rstrip()
    if transcript_text:
        screen = f"{screen}\n\n{transcript_text}"
    return screen, len(transcript_text)


def apply_post8_prefix(package: Any, state: Any) -> dict[str, Any]:
    """Build the labelled post-turn-8 state without invoking a live provider."""

    engine = RuntimeEngine(state, None)
    commits: list[dict[str, Any]] = []
    for knowledge_id, command in POST8_REVEALS:
        engine.provider = _scripted_provider(package, knowledge_id)
        before = {record.id for record in state.turn_records}
        response = engine.turn(command)
        new_records = [record for record in state.turn_records if record.id not in before]
        committed = [item for record in new_records for item in record.reveal_ids]
        if committed != [knowledge_id]:
            raise RuntimeError(f"post8 scripted reveal {knowledge_id} committed {committed or 'nothing'}")
        commits.append(
            {
                "knowledge_id": knowledge_id,
                "command": command,
                "response": _response_text(response),
            }
        )
        engine._activate_pacing()  # noqa: SLF001 - mirror the cue-chain test helper.
    state.turn_index = 8
    last_knowledge = package.knowledge_indexes.by_id[POST8_REVEALS[-1][0]]
    return {
        "committed_reveal_ids": [item[0] for item in POST8_REVEALS],
        "turn_index": state.turn_index,
        "turns": commits,
        "latest_narration": last_knowledge.delivery_text or last_knowledge.statement,
    }


def apply_postc_prefix(package: Any, state: Any) -> dict[str, Any]:
    """Build the labelled post-turn-7 state with only the completed C chain."""

    engine = RuntimeEngine(state, None)
    commits: list[dict[str, Any]] = []
    for knowledge_id, command in POSTC_REVEALS:
        engine.provider = _scripted_provider(package, knowledge_id)
        before = {record.id for record in state.turn_records}
        response = engine.turn(command)
        new_records = [record for record in state.turn_records if record.id not in before]
        committed = [item for record in new_records for item in record.reveal_ids]
        if committed != [knowledge_id]:
            raise RuntimeError(f"postc scripted reveal {knowledge_id} committed {committed or 'nothing'}")
        commits.append({"knowledge_id": knowledge_id, "command": command, "response": _response_text(response)})
        engine._activate_pacing()  # noqa: SLF001
    state.turn_index = 7
    last_knowledge = package.knowledge_indexes.by_id[POSTC_REVEALS[-1][0]]
    return {
        "committed_reveal_ids": [item[0] for item in POSTC_REVEALS],
        "turn_index": state.turn_index,
        "turns": commits,
        "latest_narration": last_knowledge.delivery_text or last_knowledge.statement,
    }


def apply_posta_prefix(package: Any, state: Any) -> dict[str, Any]:
    """Build the labelled post-turn-1 state after committing A-R1."""

    engine = RuntimeEngine(state, _scripted_provider(package, POSTA_REVEALS[0][0]))
    knowledge_id, command = POSTA_REVEALS[0]
    before = {record.id for record in state.turn_records}
    response = engine.turn(command)
    new_records = [record for record in state.turn_records if record.id not in before]
    committed = [item for record in new_records for item in record.reveal_ids]
    if committed != [knowledge_id]:
        raise RuntimeError(f"posta scripted reveal {knowledge_id} committed {committed or 'nothing'}")
    engine._activate_pacing()  # noqa: SLF001
    state.turn_index = 1
    knowledge = package.knowledge_indexes.by_id[knowledge_id]
    return {
        "committed_reveal_ids": [knowledge_id],
        "turn_index": state.turn_index,
        "turns": [{"knowledge_id": knowledge_id, "command": command, "response": _response_text(response)}],
        "latest_narration": knowledge.delivery_text or knowledge.statement,
    }


def apply_start_prefix(package: Any, state: Any, start: str) -> dict[str, Any] | None:
    if start == "posta":
        return apply_posta_prefix(package, state)
    if start == "post8":
        return apply_post8_prefix(package, state)
    if start == "postc":
        return apply_postc_prefix(package, state)
    return None


def preflight_reveal_universe(engine: RuntimeEngine, state: Any, start: str = "entry") -> list[str]:
    engine._activate_pacing()  # noqa: SLF001 - initialize the row's real opening storylets.
    projection = engine.projector.project(state, "player", "Send the evidence package.")
    universe_ids = sorted(candidate.id for candidate in projection.reveal_universe)
    if start == "posta":
        if universe_ids != POSTA_REVEALS_EXPECTED:
            raise RuntimeError(
                f"3C posta preflight failed: expected reveal universe "
                f"{POSTA_REVEALS_EXPECTED}, got {universe_ids}; no player or narrator call was made"
            )
        return universe_ids
    if start in {"post8", "postc"}:
        expected = [DE_R1] if start == "post8" else ["k_sl_3c_d_r1", "k_sl_3c_d_r2"]
        if universe_ids != expected:
            raise RuntimeError(
                f"3C {start} preflight failed: expected reveal universe "
                f"{expected}, got {universe_ids}; no player or narrator call was made"
            )
        return universe_ids
    if start == "carried":
        committed = set(_committed_reveals(state))
        chain = sorted(committed & CHAIN)
        if chain:
            raise RuntimeError(f"3C carried preflight failed: 3C chain reveals are already committed: {chain}")
        if not any(
            fact.predicate == "relay_open" and str(fact.value).lower() == "true" for fact in state.facts.asserted
        ):
            raise RuntimeError("3C carried preflight failed: relay_open is not committed")
    missing = sorted(OPENING_REVEALS - set(universe_ids))
    if missing:
        raise RuntimeError(
            "3C entry preflight failed: reveal universe is missing opening reveals "
            f"{', '.join(missing)}; no player or narrator call was made"
        )
    return universe_ids


def _commit_scene_turn(row: dict[str, Any], reveal_id: str) -> int | None:
    """Find the accepted scene turn where a reveal was committed, including prefixes."""

    for turn in row.get("turns", []):
        if reveal_id in turn.get("committed_reveals", []):
            return turn.get("scene_turn")
    for turn in row.get("scripted_prefix", {}).get("turns", []):
        if reveal_id == turn.get("knowledge_id"):
            return row.get("scripted_prefix", {}).get("turn_index")
    return None


def both_c_by_turn_10(row: dict[str, Any]) -> bool:
    """Return whether both C parts committed by accepted scene turn 10."""

    c_r1 = row.get("c_r1_commit_scene_turn", _commit_scene_turn(row, "k_sl_3c_c_r1"))
    c_r2 = row.get("c_r2_commit_scene_turn", _commit_scene_turn(row, "k_sl_3c_c_r2"))
    return c_r1 is not None and c_r2 is not None and c_r1 <= 10 and c_r2 <= 10


def _surface_fact_true(row: dict[str, Any]) -> bool:
    if row.get("captives_reaching_surface") is True or row.get("surface_fact") is True:
        return True
    return any(
        any("captives_reaching_surface" in fact for fact in turn.get("story_fact_delta", {}).get("added", []))
        for turn in row.get("turns", [])
    )


def gate_only_escape(row: dict[str, Any]) -> bool:
    """Return true for a surface-fact escape with C-R2 but never C-R1."""

    c_r1 = row.get("c_r1_commit_scene_turn", _commit_scene_turn(row, "k_sl_3c_c_r1"))
    c_r2 = row.get("c_r2_commit_scene_turn", _commit_scene_turn(row, "k_sl_3c_c_r2"))
    return c_r2 is not None and c_r1 is None and _surface_fact_true(row)


def run_row(
    arm: str,
    variation_path: Path,
    budget: SpendBudget,
    ask: Callable[[str, SpendBudget], str] = _ask_player,
    semantic: str = "off",
    provider_factory: Callable[[Any, dict[str, Any]], Any] | None = None,
    start: str = "entry",
    first_command: str | None = None,
) -> dict[str, Any]:
    variation = load_variation(variation_path)
    carried = None
    if start == "carried":
        package = load_story_package(Path(variation["_package_path"]))
        carried = carried_replay(package, variation)
        state = carried["state"]
        prefix = carried["prefix"] | {"turns": []}
    else:
        package, state = package_and_state(variation, "3C")
        assert_3c_entry_facts(state)
        prefix = apply_start_prefix(package, state, start)
    preflight_engine = RuntimeEngine(state, None)
    opening_universe = preflight_reveal_universe(preflight_engine, state, start)
    provider = provider_factory(state, variation) if provider_factory is not None else provider_for(state, variation)
    if semantic == "off" and hasattr(provider, "semantic_ask"):
        provider.semantic_ask = None
    engine = RuntimeEngine(state, provider)
    scene = next(item for item in package.scenes if item.metadata.scene_id == "3C")
    transcript: list[tuple[str, str]] = (
        ([("canon prefix", response) for response in carried["transcript"]] if carried is not None else [])
        if prefix is not None and carried is not None
        else ([(turn["command"], turn["response"]) for turn in prefix["turns"]] if prefix is not None else [])
    )
    entry_text = carried["entry_text"] if carried is not None else scene.metadata.entry_text
    if carried is not None:
        transcript.append(("3B → 3C transition", f"{carried['bridge_text']}\n\n{carried['crossing_response']}"))
    turns: list[dict[str, Any]] = []
    accepted = state.turn_index if start in {"posta", "post8", "postc"} else 0
    rejections = clarifications = attempts = 0
    extra_after_14 = False
    max_attempts = (
        POSTC_ATTEMPT_CAP if start == "postc" else POST8_ATTEMPT_CAP if start == "post8" else POSTA_ATTEMPT_CAP
    )
    first_command_response: str | None = None
    b_commit_attempt: int | None = None
    acquisition_commands = 0
    provider_context = counted_provider(provider, budget) if hasattr(provider, "_request") else nullcontext(provider)
    with provider_context:
        while not should_stop(attempts, accepted, state.story_complete, extra_after_14, max_attempts):
            screen, transcript_chars = _player_screen(entry_text, transcript)
            scripted_first = attempts == 0 and first_command is not None
            command = first_command if scripted_first else ask(screen, budget)
            attempts += 1
            before_facts = _fact_keys(state)
            before = state.snapshot()
            if accepted >= 14:
                extra_after_14 = True
            b_committed_before_turn = b_commit_attempt is not None
            acquisition_command = b_committed_before_turn and bool(ACQUISITION_COMMAND_RE.search(command))
            try:
                response = engine.turn(command)
            except NarrationProviderError as error:
                raise ProbeRunFailure(error, attempts) from error
            except Exception as error:
                if isinstance(error, RuntimeError) and any(
                    term in str(error).casefold() for term in ("cap", "quota", "malformed", "budget")
                ):
                    raise ProbeRunFailure(error, attempts) from error
                state.restore_snapshot(before)
                rejections += 1
                if acquisition_command:
                    acquisition_commands += 1
                turns.append(
                    {
                        "attempt": attempts,
                        "command": command,
                        "status": "rejected",
                        "error": str(error),
                        "committed_reveals": [],
                        "story_fact_delta": {"added": [], "removed": []},
                        "cue_text_staged": None,
                        "response": str(error),
                        "transcript_chars": transcript_chars,
                        "deadline_event_ids": [],
                        "scene_turn": accepted,
                        "scripted_first": scripted_first,
                        "captives_parent": _parent_snapshot(package, state)[0],
                        "kristin_parent": _parent_snapshot(package, state)[1],
                        "case_parent": _parent_snapshot(package, state)[2],
                        "acquisition_command": acquisition_command,
                    }
                )
                continue
            after_facts = _fact_keys(state)
            # TurnRecord ids are only unique within the bounded continuity window:
            # RuntimeEngine trims the list to 24 records and then reuses
            # ``turn_{len(turn_records) + 1}``.  The last record is the record
            # created by this successful turn, even when its id was already in
            # the pre-turn window; use its durable deadline field directly.
            record = state.turn_records[-1] if state.turn_records else None
            committed = list(record.reveal_ids) if record is not None else []
            status = _status(response)
            if acquisition_command:
                acquisition_commands += 1
            if b_commit_attempt is None and "k_sl_3c_b_r1" in committed:
                b_commit_attempt = attempts
            if status == "accepted":
                accepted += 1
            elif status == "clarification":
                clarifications += 1
            else:
                rejections += 1
            response_text = _response_text(response)
            if scripted_first:
                first_command_response = response_text
            if status == "accepted":
                transcript.append((command, response_text))
            turns.append(
                {
                    "attempt": attempts,
                    "scene_turn": accepted,
                    "command": command,
                    "status": status,
                    "committed_reveals": committed,
                    "story_fact_delta": {
                        "added": sorted(after_facts - before_facts),
                        "removed": sorted(before_facts - after_facts),
                    },
                    "cue_text_staged": _staged_cue(state),
                    "response": response_text,
                    "transcript_chars": transcript_chars,
                    "deadline_event_ids": list(record.deadline_event_ids) if record else [],
                    "scripted_first": scripted_first,
                    "captives_parent": _parent_snapshot(package, state)[0],
                    "kristin_parent": _parent_snapshot(package, state)[1],
                    "case_parent": _parent_snapshot(package, state)[2],
                    "acquisition_command": acquisition_command,
                }
            )
    all_reveals = {item for turn in turns for item in turn.get("committed_reveals", [])}
    player_reveals = all_reveals
    deadline_ids = [item for turn in turns for item in turn.get("deadline_event_ids", [])]
    given_reveals = set(prefix["committed_reveal_ids"]) if prefix is not None and start != "carried" else set()
    outcome = classify_outcome(state.story_complete, player_reveals, all_reveals, deadline_ids, given_reveals)
    c_r1_commit_scene_turn = _commit_scene_turn({"turns": turns}, "k_sl_3c_c_r1")
    c_r2_commit_scene_turn = _commit_scene_turn({"turns": turns}, "k_sl_3c_c_r2")
    derived = {
        "c_r1_commit_scene_turn": c_r1_commit_scene_turn,
        "c_r2_commit_scene_turn": c_r2_commit_scene_turn,
    }
    derived["both_c_by_turn_10"] = both_c_by_turn_10({"turns": turns, **derived})
    derived["gate_only_escape"] = gate_only_escape({"turns": turns, **derived})
    for turn in turns:
        turn.update(derived)
    return {
        "arm": arm,
        "semantic": semantic,
        "outcome": outcome,
        "accepted_turns": accepted,
        "attempts": attempts,
        "rejections": rejections,
        "clarifications": clarifications,
        "committed_reveal_ids": list(
            dict.fromkeys(item for turn in turns for item in turn.get("committed_reveals", []))
        ),
        "d_r1_committed": DE_R1 in player_reveals,
        "d_r1_commit_scene_turn": next(
            (turn["scene_turn"] for turn in turns if DE_R1 in turn.get("committed_reveals", [])), None
        ),
        "d_r2_commit_scene_turn": next(
            (turn["scene_turn"] for turn in turns if "k_sl_3c_d_r2" in turn.get("committed_reveals", [])), None
        ),
        "e_commit_scene_turn": next(
            (
                turn["scene_turn"]
                for turn in turns
                if {"k_sl_3c_e_r1", "k_sl_3c_e_r2"} & set(turn.get("committed_reveals", []))
            ),
            None,
        ),
        "first_d_commit_scene_turn": next(
            (
                turn["scene_turn"]
                for turn in turns
                if {"k_sl_3c_d_r1", "k_sl_3c_d_r2"} & set(turn.get("committed_reveals", []))
            ),
            None,
        ),
        "d_r1_commit_attempt": next(
            (turn["attempt"] for turn in turns if DE_R1 in turn.get("committed_reveals", [])), None
        ),
        "story_complete": state.story_complete,
        "turns": turns,
        "entry_state": CARRIED_ENTRY_STATE if carried is not None else ENTRY_STATE,
        "opening_reveal_universe": opening_universe,
        "start": start,
        "scripted_prefix": prefix,
        "first_command": first_command,
        "first_command_response": first_command_response,
        "b_commit_on_first": bool(turns and "k_sl_3c_b_r1" in turns[0].get("committed_reveals", [])),
        "b_commit_attempt": b_commit_attempt,
        "first_attempt_a": next(
            (
                turn["attempt"]
                for turn in turns
                if {"k_sl_3c_a_r1", "k_sl_3c_a_r2"} & set(turn.get("committed_reveals", []))
            ),
            None,
        ),
        "b_reach": b_commit_attempt is not None,
        "repeated_acquisition_commands": acquisition_commands,
        "deadline_event_ids": deadline_ids,
        "acquisition_commands": acquisition_commands,
        "entry_text_shown": entry_text,
        "bridge_text_shown": carried["bridge_text"] if carried is not None else None,
        "prefix_turn_index": prefix["turn_index"] if carried is not None else None,
        "prefix_committed_reveal_ids_hash": prefix["committed_reveal_ids_hash"] if carried is not None else None,
        "a_commit_attempt": next(
            (
                turn["attempt"]
                for turn in turns
                if {"k_sl_3c_a_r1", "k_sl_3c_a_r2"} & set(turn.get("committed_reveals", []))
            ),
            None,
        ),
        "a_commit_scene_turn": next(
            (
                turn["scene_turn"]
                for turn in turns
                if {"k_sl_3c_a_r1", "k_sl_3c_a_r2"} & set(turn.get("committed_reveals", []))
            ),
            None,
        ),
        "pre_a_commands": [
            turn["command"]
            for turn in turns[
                : next(
                    (
                        index
                        for index, turn in enumerate(turns)
                        if {"k_sl_3c_a_r1", "k_sl_3c_a_r2"} & set(turn.get("committed_reveals", []))
                    ),
                    len(turns),
                )
            ]
        ],
        **derived,
    }


def run_command_probe(
    arm: str,
    rep: int,
    turn_label: int,
    command: str,
    variation_path: Path,
    budget: SpendBudget,
    semantic: str = "off",
    provider_factory: Callable[[Any, dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    """Run one recorded command against one fresh synthetic post8 state."""

    variation = load_variation(variation_path)
    package, state = package_and_state(variation, "3C")
    assert_3c_entry_facts(state)
    prefix = apply_post8_prefix(package, state)
    provider = provider_factory(state, variation) if provider_factory is not None else provider_for(state, variation)
    if semantic == "off" and hasattr(provider, "semantic_ask"):
        provider.semantic_ask = None
    engine = RuntimeEngine(state, provider)
    universe = preflight_reveal_universe(engine, state, "post8")
    projection = engine.projector.project(state, "player", command)
    handoff = uniquely_matched_authored_handoff(command, projection.candidates)
    before_facts = _fact_keys(state)
    before_record_ids = {record.id for record in state.turn_records}
    before_requests = budget.cloudflare_requests
    try:
        provider_context = (
            counted_provider(provider, budget) if hasattr(provider, "_request") else nullcontext(provider)
        )
        with provider_context:
            response = engine.turn(command)
    except NarrationProviderError:
        raise
    except RuntimeError as error:
        if any(term in str(error).casefold() for term in ("cap", "quota", "malformed", "budget")):
            raise
        after_facts = _fact_keys(state)
        return {
            "row_id": f"stage7-3c-{rep:02d}-{arm}-turn{turn_label}",
            "arm": arm,
            "rep": rep,
            "turn_label": turn_label,
            "command": command,
            "status": "rejected",
            "committed_reveals": [],
            "d_r1_committed": False,
            "rejection_text": str(error),
            "response_text": str(error),
            "story_fact_delta": {
                "added": sorted(after_facts - before_facts),
                "removed": sorted(before_facts - after_facts),
            },
            "request_count": budget.cloudflare_requests - before_requests,
            "opening_reveal_universe": universe,
            "matched_authored_handoff": handoff.candidate.id if handoff is not None else None,
            "scripted_prefix": prefix,
            "semantic": semantic,
            "entry_state": ENTRY_STATE,
        }
    except Exception as error:
        after_facts = _fact_keys(state)
        return {
            "row_id": f"stage7-3c-{rep:02d}-{arm}-turn{turn_label}",
            "arm": arm,
            "rep": rep,
            "turn_label": turn_label,
            "command": command,
            "status": "rejected",
            "committed_reveals": [],
            "d_r1_committed": False,
            "rejection_text": str(error),
            "response_text": str(error),
            "story_fact_delta": {
                "added": sorted(after_facts - before_facts),
                "removed": sorted(before_facts - after_facts),
            },
            "request_count": budget.cloudflare_requests - before_requests,
            "opening_reveal_universe": universe,
            "matched_authored_handoff": handoff.candidate.id if handoff is not None else None,
            "scripted_prefix": prefix,
            "semantic": semantic,
            "entry_state": ENTRY_STATE,
        }
    after_facts = _fact_keys(state)
    new_records = [record for record in state.turn_records if record.id not in before_record_ids]
    committed = [item for record in new_records for item in record.reveal_ids]
    status = _status(response)
    return {
        "row_id": f"stage7-3c-{rep:02d}-{arm}-turn{turn_label}",
        "arm": arm,
        "rep": rep,
        "turn_label": turn_label,
        "command": command,
        "status": status,
        "committed_reveals": committed,
        "d_r1_committed": DE_R1 in committed,
        "rejection_text": _rejection_text(response),
        "response_text": _response_text(response),
        "story_fact_delta": {
            "added": sorted(after_facts - before_facts),
            "removed": sorted(before_facts - after_facts),
        },
        "request_count": budget.cloudflare_requests - before_requests,
        "opening_reveal_universe": universe,
        "matched_authored_handoff": handoff.candidate.id if handoff is not None else None,
        "scripted_prefix": prefix,
        "semantic": semantic,
        "entry_state": ENTRY_STATE,
    }


def plan_for(
    out: Path,
    n: int,
    mode: str,
    start: str,
    semantic: str = "off",
    probe_mode: str = "play",
    arms: tuple[str, ...] = ARMS,
    first_command: str | None = None,
) -> None:
    universe_ids: dict[str, list[str]] = {}
    carried_records: dict[str, dict[str, Any]] = {}
    for arm, path in variation_paths(arms).items():
        variation = load_variation(path)
        if start == "carried":
            package = load_story_package(Path(variation["_package_path"]))
            replay = carried_replay(package, variation)
            state = replay["state"]
            carried_records[arm] = {
                "turn_index": replay["prefix"]["turn_index"],
                "committed_reveal_ids": replay["prefix"]["committed_reveal_ids"],
                "committed_reveal_ids_hash": replay["prefix"]["committed_reveal_ids_hash"],
                "entry_text": replay["entry_text"],
            }
        else:
            package, state = package_and_state(variation, "3C")
            assert_3c_entry_facts(state)
            apply_start_prefix(package, state, start)
        universe_ids[arm] = preflight_reveal_universe(RuntimeEngine(state, None), state, start)
    if probe_mode == "commands":
        for _rep in range(1, n + 1):
            for arm in ARMS:
                variation = load_variation(variation_paths()[arm])
                package, state = package_and_state(variation, "3C")
                assert_3c_entry_facts(state)
                apply_post8_prefix(package, state)
                preflight_reveal_universe(RuntimeEngine(state, None), state, "post8")
    if probe_mode == "commands":
        order = [
            {"row": i, "rep": rep, "arm": arm, "turn_label": turn_label}
            for i, (rep, arm, turn_label) in enumerate(
                ((rep, arm, turn) for rep in range(1, n + 1) for arm in ARMS for turn in COMMAND_TURNS), 1
            )
        ]
    else:
        order = [{"row": rep, "arm": arm} for rep in range(1, n + 1) for arm in arms]
    caps = (
        {"cloudflare": 3 * len(order), "raw_player": 0}
        if probe_mode == "commands"
        else POSTC_CAPS[n]
        if start == "postc"
        else CAPS[n]
    )
    atomic_json(
        out / "plan.json",
        {
            "mode": probe_mode,
            "execution": mode,
            "n": n,
            "semantic": semantic,
            "order": order,
            "caps": caps,
            "entry_state": CARRIED_ENTRY_STATE if start == "carried" else ENTRY_STATE,
            "start": start,
            "start_label": (
                POSTA_LABEL
                if start == "posta"
                else POSTC_LABEL
                if start == "postc"
                else POST8_LABEL
                if start == "post8"
                else CARRIED_LABEL
                if start == "carried"
                else None
            ),
            "arms": list(arms),
            "first_command": first_command,
            "scripted_prefix": (
                {
                    "committed_reveal_ids": [
                        item[0]
                        for item in (
                            POSTA_REVEALS if start == "posta" else POSTC_REVEALS if start == "postc" else POST8_REVEALS
                        )
                    ],
                    "turn_index": 1 if start == "posta" else 7 if start == "postc" else 8,
                }
                if start in {"posta", "post8", "postc"}
                else carried_records
                if start == "carried"
                else None
            ),
            "rendered_entry_text": (
                {arm: record["entry_text"] for arm, record in carried_records.items()} if start == "carried" else None
            ),
            "reveal_universe_ids": universe_ids,
        },
    )


def carried_metadata(arms: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for arm, path in variation_paths(arms).items():
        variation = load_variation(path)
        package = load_story_package(Path(variation["_package_path"]))
        replay = carried_replay(package, variation)
        records[arm] = {
            "turn_index": replay["prefix"]["turn_index"],
            "committed_reveal_ids": replay["prefix"]["committed_reveal_ids"],
            "committed_reveal_ids_hash": replay["prefix"]["committed_reveal_ids_hash"],
            "entry_text": replay["entry_text"],
        }
    return records


def dry_run(out: Path, n: int, start: str, semantic: str, arms: tuple[str, ...], first_command: str | None) -> None:
    source = source_proof(arms)
    source["semantic"] = semantic
    source["mode"] = "play"
    source["entry_state"] = CARRIED_ENTRY_STATE if start == "carried" else ENTRY_STATE
    source["start"] = start
    source["start_label"] = (
        POSTA_LABEL
        if start == "posta"
        else POSTC_LABEL
        if start == "postc"
        else POST8_LABEL
        if start == "post8"
        else CARRIED_LABEL
        if start == "carried"
        else None
    )
    source["arms"] = list(arms)
    source["first_command"] = first_command
    if start == "carried":
        source["scripted_prefix"] = carried_metadata(arms)
        source["rendered_entry_text"] = {arm: data["entry_text"] for arm, data in source["scripted_prefix"].items()}
    else:
        source["scripted_prefix"] = (
            {
                "committed_reveal_ids": [
                    item[0]
                    for item in (
                        POSTA_REVEALS if start == "posta" else POSTC_REVEALS if start == "postc" else POST8_REVEALS
                    )
                ],
                "turn_index": 1 if start == "posta" else 7 if start == "postc" else 8,
            }
            if start in {"posta", "post8", "postc"}
            else None
        )
    atomic_json(out / "source.json", source)
    plan_for(out, n, "dry", start, semantic, "play", arms, first_command)


def commands_source(semantic: str, start: str) -> dict[str, Any]:
    source = source_proof()
    source.update(
        {
            "semantic": semantic,
            "mode": "commands",
            "raw_commands_note": "These are an explicitly labelled raw-language check, not new player input.",
            "recorded_commands": recorded_commands(),
            "entry_state": ENTRY_STATE,
            "start": start,
            "start_label": POST8_LABEL,
            "scripted_prefix": {"committed_reveal_ids": [item[0] for item in POST8_REVEALS], "turn_index": 8},
        }
    )
    return source


def commands_dry_run(out: Path, n: int, semantic: str, start: str) -> None:
    atomic_json(out / "source.json", commands_source(semantic, start))
    plan_for(out, n, "dry", start, semantic, "commands")


def live_run(out: Path, n: int, semantic: str, start: str, arms: tuple[str, ...], first_command: str | None) -> None:
    source = source_proof(arms)
    carried_source = carried_metadata(arms) if start == "carried" else None
    atomic_json(
        out / "source.json",
        {
            **source,
            "semantic": semantic,
            "entry_state": CARRIED_ENTRY_STATE if start == "carried" else ENTRY_STATE,
            "start": start,
            "start_label": POSTA_LABEL
            if start == "posta"
            else POSTC_LABEL
            if start == "postc"
            else POST8_LABEL
            if start == "post8"
            else CARRIED_LABEL
            if start == "carried"
            else None,
            "arms": list(arms),
            "first_command": first_command,
            "scripted_prefix": carried_source
            if carried_source is not None
            else {
                "committed_reveal_ids": [
                    item[0]
                    for item in (
                        POSTA_REVEALS if start == "posta" else POSTC_REVEALS if start == "postc" else POST8_REVEALS
                    )
                ],
                "turn_index": 1 if start == "posta" else 7 if start == "postc" else 8,
            }
            if start in {"posta", "post8", "postc"}
            else None,
            "rendered_entry_text": (
                {arm: data["entry_text"] for arm, data in carried_source.items()}
                if carried_source is not None
                else None
            ),
        },
    )
    plan_for(out, n, "live", start, semantic, "play", arms, first_command)
    caps = POSTC_CAPS[n] if start == "postc" else CAPS[n]
    budget = SpendBudget(caps["cloudflare"], cloudflare_limit=caps["cloudflare"], player_limit=caps["raw_player"])
    rows: list[dict[str, Any]] = []
    try:
        for rep in range(1, n + 1):
            for arm in arms:
                row_id = f"stage7-3c-{rep:02d}-{arm}"
                try:
                    row = run_row(
                        arm,
                        variation_paths(arms)[arm],
                        budget,
                        semantic=semantic,
                        start=start,
                        first_command=first_command,
                    )
                except ProbeRunFailure as error:
                    error.row_id = row_id
                    error.args = (failure_message(error),)
                    raise
                except Exception as error:
                    raise ProbeRunFailure(error, 0, row_id) from error
                row.update(
                    {
                        "row_id": row_id,
                        "rep": rep,
                        "semantic": semantic,
                        "entry_state": CARRIED_ENTRY_STATE if start == "carried" else ENTRY_STATE,
                        "start_label": CARRIED_LABEL
                        if start == "carried"
                        else POSTA_LABEL
                        if start == "posta"
                        else POSTC_LABEL
                        if start == "postc"
                        else POST8_LABEL
                        if start == "post8"
                        else None,
                    }
                )
                rows.append(row)
                atomic_json(out / "rows.json", rows)
    except Exception:
        atomic_json(out / "rows.json", rows)
        atomic_json(out / "spend.json", {"caps": caps, "events": budget.events})
        raise
    atomic_json(out / "spend.json", {"caps": caps, "events": budget.events})
    summary: dict[str, Any] = {"n": n, "arms": {}}
    for arm in arms:
        arm_rows = [row for row in rows if row["arm"] == arm]
        summary["arms"][arm] = {
            "outcomes": {
                outcome: sum(row["outcome"] == outcome for row in arm_rows)
                for outcome in ("earned_complete", "deadline_complete", "no_complete")
            },
            "mean_accepted_turns": sum(row["accepted_turns"] for row in arm_rows) / len(arm_rows),
            "d_r1_commit_rate": sum(row["d_r1_committed"] for row in arm_rows) / len(arm_rows),
            "both_c_by_turn_10": sum(row["both_c_by_turn_10"] for row in arm_rows),
            "c_r1_rows": sum(row["c_r1_commit_scene_turn"] is not None for row in arm_rows),
            "c_r2_rows": sum(row["c_r2_commit_scene_turn"] is not None for row in arm_rows),
            "gate_only_escape": sum(row["gate_only_escape"] for row in arm_rows),
            "rejections": sum(row["rejections"] for row in arm_rows),
            "clarifications": sum(row["clarifications"] for row in arm_rows),
        }
    atomic_json(out / "summary.json", summary)


def commands_live_run(out: Path, n: int, semantic: str, start: str) -> None:
    atomic_json(out / "source.json", commands_source(semantic, start))
    probe_count = n * len(ARMS) * len(COMMAND_TURNS)
    plan_for(out, n, "live", start, semantic, "commands")
    budget = SpendBudget(3 * probe_count, cloudflare_limit=3 * probe_count, player_limit=0)
    rows: list[dict[str, Any]] = []
    try:
        for rep in range(1, n + 1):
            for arm in ARMS:
                for recorded in command_probe_commands():
                    row_id = f"stage7-3c-{rep:02d}-{arm}-turn{recorded['turn_label']}"
                    try:
                        row = run_command_probe(
                            arm,
                            rep,
                            recorded["turn_label"],
                            recorded["command"],
                            variation_paths()[arm],
                            budget,
                            semantic,
                        )
                    except ProbeRunFailure as error:
                        error.row_id = row_id
                        error.args = (failure_message(error),)
                        raise
                    except Exception as error:
                        raise ProbeRunFailure(error, recorded["turn_label"], row_id) from error
                    rows.append(row)
                    atomic_json(out / "rows.json", rows)
    except Exception:
        atomic_json(out / "rows.json", rows)
        atomic_json(
            out / "spend.json",
            {"caps": {"cloudflare": 3 * probe_count, "raw_player": 0}, "events": budget.events},
        )
        raise
    atomic_json(
        out / "spend.json",
        {"caps": {"cloudflare": 3 * probe_count, "raw_player": 0}, "events": budget.events},
    )
    summary: dict[str, Any] = {"n": n, "mode": "commands", "arms": {}}
    for arm in ARMS:
        arm_rows = [row for row in rows if row["arm"] == arm]
        summary["arms"][arm] = {"turns": {}}
        for turn_label in COMMAND_TURNS:
            selected = [row for row in arm_rows if row["turn_label"] == turn_label]
            summary["arms"][arm]["turns"][str(turn_label)] = {
                "d_r1_committed": sum(row["d_r1_committed"] for row in selected),
                "accepted": sum(row["status"] == "accepted" for row in selected),
                "rejected": sum(row["status"] == "rejected" for row in selected),
                "clarification": sum(row["status"] == "clarification" for row in selected),
            }
        summary["arms"][arm]["totals"] = {
            "d_r1_committed": sum(row["d_r1_committed"] for row in arm_rows),
            "accepted": sum(row["status"] == "accepted" for row in arm_rows),
            "rejected": sum(row["status"] == "rejected" for row in arm_rows),
            "clarification": sum(row["status"] == "clarification" for row in arm_rows),
        }
    atomic_json(out / "summary.json", summary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True, choices=(1, 12))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--semantic", choices=("on", "off"), default="off")
    parser.add_argument("--start", choices=STARTS, default="entry")
    parser.add_argument("--arms", default="control,pre667")
    parser.add_argument("--first-command")
    parser.add_argument("--mode", choices=("play", "commands"), default="play")
    args = parser.parse_args(argv)
    arms = tuple(item.strip() for item in args.arms.split(",") if item.strip())
    if not arms or any(arm not in ALL_ARMS for arm in arms) or len(set(arms)) != len(arms):
        raise SystemExit(f"--arms must be a comma-separated selection from {','.join(ALL_ARMS)}")
    if not {"control", "entry", "custody", "pump"} & set(arms):
        raise SystemExit("--arms must include control, entry, custody, or pump as the baseline")
    out = args.out if args.out.is_absolute() else ROOT / args.out
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"output directory must be absent or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    try:
        if args.mode == "commands" and args.start != "post8":
            raise SystemExit("commands mode requires --start post8")
        if args.dry_run:
            if args.mode == "commands":
                commands_dry_run(out, args.n, args.semantic, args.start)
            else:
                dry_run(out, args.n, args.start, args.semantic, arms, args.first_command)
            return 0
        if not args.confirm:
            raise SystemExit("--confirm is mandatory for live execution")
        if args.mode == "commands":
            commands_live_run(out, args.n, args.semantic, args.start)
        else:
            live_run(out, args.n, args.semantic, args.start, arms, args.first_command)
    except Exception as error:
        (out / "run-failure.txt").write_text(failure_message(error), encoding="utf-8")
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
