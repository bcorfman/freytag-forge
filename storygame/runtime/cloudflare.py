"""Fail-closed Cloudflare Worker transport for typed scene proposals."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from os import getenv
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from storygame.runtime.candidate_matcher import (
    ActionEvidenceCandidate,
    AuthoredHandoff,
    uniquely_matched_authored_handoff,
    uniquely_matched_candidate,
)
from storygame.runtime.contracts import (
    NarrationSegment,
    RuntimeContractError,
    TurnProposal,
    contract_error_summary,
    parse_turn_proposal,
)
from storygame.runtime.knowledge import KnowledgeProjector, RevealCandidate, TurnKnowledgeContext
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import (
    derive_grounding,
    derive_statement_grounding,
    predicate_matches,
    unconveyed_terms,
)
from storygame.story_package.models import FactPredicate, ItemPlacement, Scene, SceneBeat, SceneMetadata

logger = logging.getLogger(__name__)

MAX_TURN_SEGMENTS = 5

DEFAULT_OUTPUT_EXAMPLE = (
    '{"segments":[{"kind":"narration","text":"The drawer sticks, then gives. Inside, under a curl of packing tape, '
    "her fingers find the flat edge of something that was never meant to be seen from above, and the "
    'kitchen behind her goes very quiet."},{"kind":"narration","text":"She works it loose and turns it over in the '
    "light from the window. "
    "The plastic is scuffed at one corner, as though it had been pressed into place in a hurry, and "
    'the initials carved into the drawer front suddenly read less like affection than instruction."}],'
    '"selected_knowledge_ids":[]}'
)

# Cloudflare's Browser Integrity Check rejects urllib's default bot-like signature
# before a request can reach the Worker at all, so every caller must send this.
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
)


_PROVIDER_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["narration", "dialogue", "action"]},
                    "text": {"type": "string"},
                    "speaker_id": {"type": ["string", "null"]},
                    "grounding_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["kind", "text"],
                "additionalProperties": False,
            },
        },
        "selected_knowledge_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["segments"],
    "additionalProperties": False,
}

_PRESENCE_ACTIONS = frozenset(
    [
        "act",
        "acts",
        "arrive",
        "arrives",
        "begins",
        "coordinate",
        "coordinates",
        "coordinating",
        "enters",
        "enter",
        "finds",
        "find",
        "follows",
        "follow",
        "reaches",
        "helps",
        "help",
        "leads",
        "lead",
        "notices",
        "notice",
        "explains",
        "explain",
        "says",
        "speaks",
        "speak",
        "speaking",
        "saves",
        "save",
        "stops",
        "stop",
        "triggers",
        "trigger",
        "organizes",
        "organized",
        "moves",
        "move",
        "fights",
        "fight",
        "escapes",
        "escape",
        "identifies",
        "identify",
        "reveals",
        "reveal",
        "works",
        "work",
    ]
)
_ABSENCE_OR_EVIDENCE = frozenset(
    [
        "absent",
        "missing",
        "taken",
        "captive",
        "recording",
        "recordings",
        "evidence",
        "files",
        "file",
        "photo",
        "photograph",
        "notes",
        "note",
        "phone",
        "research",
        "possession",
        "possessions",
        "through",
        "resembling",
        "resembles",
        "memory",
        "card",
        "contains",
        "fragments",
        "disappeared",
        "source",
        "hears",
    ]
)


@dataclass(frozen=True)
class NarrationProviderError(RuntimeError):
    message: str
    status_code: int = 503
    error_code: str = ""
    trace_id: str = ""
    worker_revision: str = ""


class _EligibilityError(RuntimeContractError):
    """A proposal that parsed cleanly but named knowledge this turn may not use.

    ``summary`` is safe to return to the client: it names the rule, never a
    story ID. ``hint`` is for the recovery prompt only.
    """

    def __init__(self, summary: str, hint: str) -> None:
        super().__init__(summary)
        self.summary = summary
        self.hint = hint


def _plain(text: str) -> str:
    """Render authored markdown as plain prose without breaking a sentence.

    plot.md is narrative ground truth and keeps its own formatting. The narrator
    is a small model that has been observed copying whatever shape it is shown,
    so bold markers, blockquote arrows and list bullets are stripped on the way
    out. Sentences and paragraph breaks survive untouched.
    """

    cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    cleaned = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", cleaned)
    lines = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        stripped = re.sub(r"^#{1,6}\s+", "", stripped)
        stripped = re.sub(r"^>\s?", "", stripped)
        stripped = re.sub(r"^[*+-]\s+", "", stripped)
        lines.append(stripped)
    return "\n".join(lines).strip()


class CloudflareTurnProvider:
    """Send only bounded, scene-safe context to the configured Worker."""

    def __init__(
        self,
        *,
        worker_url: str,
        token: str,
        state: RuntimeState,
        projector: KnowledgeProjector | None = None,
        prompt_variant: Mapping[str, object] | None = None,
    ) -> None:
        self.worker_url = worker_url
        self.token = token
        self.state = state
        self.projector = projector or KnowledgeProjector()
        self.last_projection: TurnKnowledgeContext | None = None
        self.last_prompt: dict[str, str] | None = None
        self.grounding_attributions: tuple[str, ...] = ()
        self.model_selected_knowledge_ids: tuple[str, ...] = ()
        self.model_grounding_ids: tuple[str, ...] = ()
        self.shadow_matched_candidate_id: str | None = None
        self.authored_handoff: AuthoredHandoff | None = None
        self.prompt_candidate_ids: tuple[str, ...] = ()
        self._example_player_input = ""
        self.prompt_variant = prompt_variant
        self.request_count = 0
        self.recovery_count = 0

    @classmethod
    def from_environment(
        cls, state: RuntimeState, prompt_variant: Mapping[str, object] | None = None
    ) -> CloudflareTurnProvider:
        worker_url = getenv("CLOUDFLARE_WORKER_URL", "").strip()
        if not worker_url:
            configuration_error = ValueError("CLOUDFLARE_WORKER_URL is not configured")
            try:
                raise configuration_error
            except ValueError as error:
                logger.warning(
                    "Narration service unavailable (worker host=unconfigured; "
                    "underlying exception type=%s; message=%s)",
                    type(error).__name__,
                    str(error),
                    exc_info=True,
                )
                raise NarrationProviderError("narration service is unavailable") from error
        return cls(
            worker_url=worker_url,
            token=getenv("CLOUDFLARE_WORKER_TOKEN", "").strip(),
            state=state,
            prompt_variant=prompt_variant,
        )

    def __call__(self, player_input: str) -> object:
        prompt = self.assemble_turn_prompt(player_input)
        return self._dispatch(prompt["system"], prompt["context"])

    def assemble_turn_prompt(self, player_input: str) -> dict[str, object]:
        """Build the exact turn prompt without contacting the narration worker."""

        self._example_player_input = player_input
        self.last_projection = self.projector.project(self.state, "player", player_input)
        self.authored_handoff = uniquely_matched_authored_handoff(player_input, self.last_projection.candidates)
        self.shadow_matched_candidate_id = self._shadow_matched_candidate_id(player_input)
        self.prompt_candidate_ids = tuple(candidate.id for candidate in self._model_candidates())
        self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
            update={
                "hint_staged": bool(self.last_projection.hinted_deliveries),
                "handoff_staged": bool(self.last_projection.handoff_deliveries),
            }
        )
        speaker_contexts = self._speaker_contexts(player_input)
        scene_setting = self._scene_setting()
        context = {
            "player_input": player_input,
            # The scene's own establishing material. Without it a turn carries one sentence
            # of frame and a few terse statements, so the narrator has nothing authored to
            # be concrete with and answers an apt search with "you find nothing". This is
            # the scene's first beat only, so it cannot narrate ahead of the player.
            "scene_setting": scene_setting,
            "knowledge_context": {
                # sayable_knowledge is the speakers' dialogue basis; repeating it for the
                # player doubled the largest field in every request for no reader.
                "player": self._serialized_player_context(scene_setting),
                "speakers": speaker_contexts,
            },
        }
        context["_rules"] = self._turn_rules()
        return {"system": self._system_prompt(), "context": context}

    def _shadow_matched_candidate_id(self, player_input: str) -> str | None:
        """Record a matcher result without changing the narrated turn.

        Action evidence stays out of the model context. This result is telemetry
        only: it neither changes candidates nor proposes, grounds, validates, or
        commits a reveal.
        """

        candidates = self.last_projection.candidates if self.last_projection else ()
        evidence_candidates = tuple(
            ActionEvidenceCandidate(id=candidate.id, required_groups=candidate.action_evidence)
            for candidate in candidates
            if candidate.action_evidence
        )
        matched = uniquely_matched_candidate(player_input, evidence_candidates)
        return matched.id if matched else None

    def _model_candidates(self) -> tuple[RevealCandidate, ...]:
        """Return candidates that the narrator may consider on this turn.

        Authored handoffs own their reveals in the runtime, so they never show
        up in the narrator's candidate list. The optional narrowing switch
        remains a prompt-only experiment for legacy turns.
        """

        if self._is_authored_handoff_turn():
            return ()
        candidates = self._legacy_projection_candidates()
        if not (
            self.prompt_variant
            and self.prompt_variant.get("narrow_to_shadow_match", False)
            and self.shadow_matched_candidate_id
        ):
            return candidates
        return tuple(candidate for candidate in candidates if candidate.id == self.shadow_matched_candidate_id)

    def _handoff_eligible_candidate_ids(self) -> set[str]:
        """Return projected candidates whose reveal belongs to the runtime."""

        return {
            candidate_id
            for candidate in (self.last_projection.candidates if self.last_projection else ())
            for candidate_id in (getattr(candidate, "id", None),)
            if candidate_id is not None
            and getattr(candidate, "action_evidence", ())
            and isinstance(getattr(candidate, "delivery_text", None), str)
            and candidate.delivery_text.strip()
        }

    def _legacy_projection_candidates(self) -> tuple[RevealCandidate, ...]:
        """Return projected candidates that the narrator is allowed to select."""

        handoff_ids = self._handoff_eligible_candidate_ids()
        return tuple(
            candidate
            for candidate in (self.last_projection.candidates if self.last_projection else ())
            if getattr(candidate, "id", None) not in handoff_ids
        )

    def _is_authored_handoff_turn(self) -> bool:
        """Return whether the runtime owns this turn's reveal delivery."""

        return getattr(self, "authored_handoff", None) is not None

    def _turn_rules(self) -> list[str]:
        """State the rules that apply to this turn.

        Authored handoffs need only ordinary scene narration. Legacy turns keep
        their candidate selection and grounding rules.
        """

        handoff_turn = self._is_authored_handoff_turn()
        candidates = self._model_candidates()
        model_grounding = not handoff_turn and not (
            self.prompt_variant is not None and self.prompt_variant.get("model_grounding", True) is False
        )
        if handoff_turn:
            selection_rules: list[str] = []
        else:
            selection_rules = [
                (
                    "When one or more offered candidates match the player's action, randomly pick one candidate "
                    "from that list and put its ID in selected_knowledge_ids."
                ),
            ]
        no_candidate_rule = "This turn has no candidates. Leave selected_knowledge_ids empty."
        if not handoff_turn and not candidates:
            selection_rules.append(no_candidate_rule)
        hinted = self.last_projection.hinted_deliveries if self.last_projection else ()
        handoffs = self.last_projection.handoff_deliveries if self.last_projection else ()
        if handoff_turn:
            handoff_rule = ""
        elif handoffs:
            handoff_rule = (
                "Write each handoff event. Cover each required idea. Answer the player. "
                "Do not say the player did something they did not do."
            )
        elif hinted:
            handoff_rule = (
                "Hint at the evidence with something a character says, notices, or hears on a radio. "
                "Do not make it a fact yet."
            )
        else:
            handoff_rule = ""
        default_rules = [
            "Show what happens right after the player acts.",
            "Use only what the SCENE section tells you.",
            "Use the places and details the story gives you.",
            "Keep each object where the scene puts it.",
            "Answer what the player did.",
            "Do not make up new objects, clues, or things inside containers.",
            "Everything in the SCENE section is already true.",
            *(
                (
                    "In grounding_ids, use only an ID you were given as known, or the one candidate you picked.",
                    "Do not put a candidate's ID in grounding_ids unless you picked it.",
                )
                if model_grounding
                else ()
            ),
            "A character may only say what you were told that character can say.",
            *selection_rules,
            "Never write IDs or story bookkeeping into the prose.",
            "Do not copy sentences from the SCENE section.",
            "Do not say anything that goes against the SCENE section.",
            "Do not repeat the request's labels back.",
        ]
        configured_rules = self.prompt_variant.get("rules") if self.prompt_variant else None
        rules = list(configured_rules) if not handoff_turn and isinstance(configured_rules, list) else default_rules
        if not all(isinstance(rule, str) and rule for rule in rules):
            raise ValueError("prompt variant rules must be a list of non-empty strings")
        # A variation that replaces the rules block still needs this turn-specific
        # rule, except on authored handoffs where selection is runtime-owned.
        if configured_rules and not candidates and not handoff_turn:
            rules.append(no_candidate_rule)
        if handoff_rule:
            rules.append(handoff_rule)
        rules.extend(self._owner_rules())
        rules.extend(self._placement_rules())
        rules.extend(self._setting_fact_rules())
        return rules

    def _owner_rules(self) -> list[str]:
        scene_items = {item.id: item for item in self.state.package.world.items}
        possessive_items = [
            scene_items[item_id].name
            for item_id in self._current_scene().item_ids
            if item_id in scene_items and re.fullmatch(r".+['’]s\s+.+", scene_items[item_id].name)
        ]
        if not possessive_items:
            return []
        return [f"Say who owns a thing the first time you name it: {', '.join(possessive_items)}."]

    def _placement_rules(self) -> list[str]:
        scene_items = {item.id: item for item in self.state.package.world.items}
        rules = []
        for item_id, placement in self._current_scene().item_placements.items():
            if item_id not in scene_items:
                continue
            if isinstance(placement, ItemPlacement) and placement.while_fact_false:
                guard = FactPredicate(fact_id=placement.while_fact_false, equals=True)
                if predicate_matches(guard, self.state.facts):
                    continue
            placement_text = placement if isinstance(placement, str) else placement.placement
            rules.append(f"{scene_items[item_id].name} is {placement_text}.")
        return rules

    def _setting_fact_rules(self) -> list[str]:
        return list(self._current_scene().setting_facts)

    def _output_example(self) -> str | None:
        """Resolve the response example, or None when this variation omits it."""

        if self.prompt_variant and not self.prompt_variant.get("include_output_example", True):
            return None
        if self._is_authored_handoff_turn():
            return DEFAULT_OUTPUT_EXAMPLE
        if self.prompt_variant and "output_example" in self.prompt_variant:
            example_text = self.prompt_variant["output_example"]
        else:
            candidates = self._model_candidates()
            example_candidate = (
                self._example_candidate(candidates)
                if self.prompt_variant and self.prompt_variant.get("positive_selection_example", False)
                else None
            )
            example_text = DEFAULT_OUTPUT_EXAMPLE
            if example_candidate:
                example_text = json.dumps(
                    {
                        "segments": [
                            {
                                "kind": "narration",
                                "text": example_candidate.statement,
                                "grounding_ids": [example_candidate.id],
                            }
                        ],
                        "selected_knowledge_ids": [example_candidate.id],
                    },
                    separators=(",", ":"),
                )
        if not isinstance(example_text, str):
            raise ValueError("prompt variant output_example must be a string")
        return example_text

    def _example_candidate(self, candidates: tuple[RevealCandidate, ...]) -> RevealCandidate | None:
        """Return a cue-matching candidate for a positive output example.

        This only chooses a prompt example.  It must never select a candidate,
        change facts, or replace the normal proposal validation path.  Requiring
        two meaningful cue words keeps an unrelated offered candidate out of an
        example for a different player action.
        """

        action_terms = self._content_terms(self._example_player_input)
        for candidate in candidates:
            if candidate.earn_when and len(action_terms & self._content_terms(candidate.earn_when)) >= 2:
                return candidate
        return None

    def _protagonist_name(self) -> str:
        """The short name the player is called by, not the full credited name."""

        package = self.state.package
        npc = next((entity for entity in package.world.npcs if entity.id == package.protagonist_id), None)
        if npc is None:
            return package.protagonist_id
        return min((*npc.aliases, npc.name), key=len)

    def _system_prompt(self) -> str:
        """The instructions that never vary: role, genre, player, and reply shape.

        Everything that changes with the scene or the beat lives in the user
        message, so this block is identical on every turn of every scene and
        carries nothing the model has to reconcile against the story.
        """

        package = self.state.package
        genre = f"{package.genre} " if package.genre else ""
        lines = [
            f"You are the narrator of an interactive {genre}roleplay. Follow the CHARACTERS, SCENE and CONSTRAINTS "
            "sections in the message that follows.",
            "Make the roleplay realistic, with realistic character behaviors, personalities and motivations.",
            f"The player is {self._protagonist_name()}.",
            "Describe each scene in 2-3 paragraphs of 2-3 short sentences, then stop immediately.",
        ]
        example = self._output_example()
        if example is not None:
            lines.append("Write each paragraph as one segment and return only JSON in this form:")
            lines.append(example)
        return "\n".join(lines)

    def opening(self) -> object:
        """Continue the authored entry text, before any player input exists."""

        self._example_player_input = ""
        self.last_projection = self.projector.project(self.state, "player", "")
        self.shadow_matched_candidate_id = None
        self.authored_handoff = None
        self.prompt_candidate_ids = tuple(candidate.id for candidate in self._model_candidates())
        entry = self._scene_entry()
        rules = [
            "The player already read the entry text. Write only what comes next. Keep the same voice and tense.",
            "Show only the opening beat and what the SCENE section tells you.",
            "Do not repeat or reword the entry text.",
            "Do not make up clues, characters, or events.",
            "Do not solve the goal for the player.",
            "Do not act for the player. Do not offer choices.",
            "Keep selected_knowledge_ids empty.",
            "Do not say anything that goes against the entry text or the beat details.",
            "Do not make up new objects, clues, or things inside containers.",
            "Never write IDs or story bookkeeping into the prose.",
            "Keep each object where the scene puts it.",
        ]
        rules.extend(self._owner_rules())
        rules.extend(self._placement_rules())
        rules.extend(self._setting_fact_rules())
        return self._dispatch(
            self._system_prompt(),
            {
                "scene_entry": entry,
                "knowledge_context": {"player": self._serialized_player_context({})},
                "_rules": rules,
            },
        )

    def _scene_setting(self) -> dict[str, object]:
        """The authored paragraph the player read on entering, safe to send every turn.

        Beat prose is added only for storylets whose reveals are candidates on
        this turn. The scene's beats describe what later reveals contain - Scene
        2B's first beat names JANUS outright - so sending all of them would hand
        the narrator knowledge the player has not earned. The projection already
        supplies place and objective; this adds only the authored material the
        player can earn now.
        """

        setting: dict[str, object] = {"entry_text": self._current_scene().entry_text.rstrip()}
        beats = self._candidate_beats() if self.last_projection and self.last_projection.candidates else ()
        self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
            update={"beats_projected": tuple(beat.anchor for beat in beats)}
        )
        if beats:
            setting["beats"] = [
                {
                    "title": beat.title,
                    "anchor": beat.anchor,
                    "prose": beat.prose,
                    "details": list(beat.details),
                    "your_job": (
                        "Show this world state only as far as the player's action reaches. Do not copy its words."
                    ),
                }
                for beat in beats
            ]
        return setting

    def _serialized_player_context(self, scene_setting: dict[str, object]) -> dict[str, object]:
        """Serialize only the player context the narrator may use."""

        if self.last_projection is None:
            return {}
        context = self.last_projection.model_dump(mode="json", exclude={"sayable_knowledge"})
        # Legacy candidate statements remain explicit constraint lines. Runtime-
        # owned handoffs stay in the projection for matching, not in this list.
        model_candidate_ids = {candidate.id for candidate in self._model_candidates()}
        context["candidates"] = [
            candidate for candidate in context["candidates"] if candidate["id"] in model_candidate_ids
        ]
        return context

    def _candidate_beats(self) -> tuple[SceneBeat, ...]:
        """Return the authored beats belonging to projected storylets."""

        package = self.state.package
        storylets = {storylet.id: storylet for storylet in package.storylets}
        beats_by_anchor = {anchor: beat for scene in package.scenes for anchor, beat in scene.beats.items()}
        seen: set[str] = set()
        selected: list[SceneBeat] = []
        for candidate in self.last_projection.candidates if self.last_projection else ():
            knowledge = package.knowledge_indexes.by_id[candidate.id]
            if knowledge.source.kind != "storylet_realization" or knowledge.source.storylet_id is None:
                continue
            storylet = storylets.get(knowledge.source.storylet_id)
            if storylet is None:
                continue
            candidate_terms = self._candidate_terms(candidate)
            for anchor in storylet.source_links:
                beat = beats_by_anchor.get(anchor)
                if (
                    anchor not in seen
                    and beat is not None
                    and len(candidate_terms & self._content_terms(beat.prose)) >= 2
                ):
                    seen.add(anchor)
                    selected.append(beat)
        return tuple(selected)

    @staticmethod
    def _content_terms(text: str) -> set[str]:
        """Return meaningful authored words for conservative statement/beat matching."""

        stopwords = {
            "a",
            "an",
            "and",
            "as",
            "at",
            "but",
            "by",
            "for",
            "from",
            "her",
            "his",
            "in",
            "is",
            "it",
            "of",
            "on",
            "or",
            "the",
            "their",
            "that",
            "to",
            "with",
        }
        return {word for word in re.findall(r"[a-z0-9]+", text.casefold()) if len(word) > 2 and word not in stopwords}

    def _candidate_terms(self, candidate: object) -> set[str]:
        values = [candidate.statement, *(term for group in candidate.must_convey for term in group)]
        entity_terms = {
            term
            for entity in (
                *self.state.package.world.npcs,
                *self.state.package.world.items,
                *self.state.package.world.locations,
            )
            for value in (entity.name, *entity.aliases)
            for term in self._content_terms(value)
        }
        return set().union(*(self._content_terms(value) for value in values)) - entity_terms

    def _scene_entry(self) -> dict[str, object]:
        """Expose the package-authored frame and first beat the opening must dramatize, never invent."""

        scene = self._current_scene()
        beat = self._current_beat()
        world = self.state.package.world
        location = next(item for item in world.locations if item.id == scene.location_id)
        protagonist = next((item.name for item in world.npcs if item.id == world.protagonist_id), world.protagonist_id)
        return {
            "protagonist": protagonist,
            "location": location.name,
            "phase": scene.freytag_phase,
            "objective": scene.objective,
            "entry_text": scene.entry_text,
            "opening_beat": {"id": beat.id, "title": beat.title, "details": list(beat.details)},
        }

    def _dispatch(self, system: str, user: dict[str, object]) -> object:
        """Send one prompt, then recover once from a rejected or malformed reply."""

        payload = {
            "system": system,
            "user": self._section_user_prompt(user),
            "max_tokens": 1024,
            "response_format": {"type": "json_object"},
        }
        try:
            response = self._request_allowing_one_transient_retry(payload)
        except HTTPError as error:
            worker_error_code = self._worker_error_code(error)
            self._log_typed_worker_error(error, worker_error_code)
            if worker_error_code != "AI_JSON_MODE_REJECTED":
                raise self._narration_error(error) from error
        except json.JSONDecodeError:
            return self._recover_malformed_response(payload)
        except (URLError, OSError, TimeoutError, ValueError) as error:
            self._log_unavailable(error)
            raise NarrationProviderError("narration service is unavailable") from error
        else:
            try:
                proposal = self._parse_eligible_proposal(response)
            except RuntimeContractError as error:
                salvaged = self._salvage_malformed_segments(response, error)
                if salvaged is not None:
                    try:
                        proposal = self._parse_eligible_proposal(salvaged)
                    except RuntimeContractError as salvage_error:
                        return self._recover_malformed_response(payload, getattr(salvage_error, "hint", ""))
                    return self._accept_proposal(salvaged, proposal)
                return self._recover_malformed_response(payload, getattr(error, "hint", ""))
            return self._accept_proposal(response, proposal)

        fallback_payload = {key: value for key, value in payload.items() if key != "response_format"}
        self._record_recovery()
        try:
            response = self._request_allowing_one_transient_retry(fallback_payload)
        except HTTPError as error:
            self._log_typed_worker_error(error, self._worker_error_code(error))
            raise self._narration_error(error) from error
        except (URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            self._log_unavailable(error)
            raise NarrationProviderError("narration service is unavailable") from error
        return self._eligible_or_narration_only(response)

    def _recover_malformed_response(self, payload: dict[str, object], hint: str = "") -> object:
        handoff_turn = self._is_authored_handoff_turn()
        correction = f" {hint}" if hint and not handoff_turn and not self._handoff_eligible_candidate_ids() else ""
        if handoff_turn:
            instruction = (
                "Your last answer was not valid. Send back only JSON. It must have segments with text in them. "
                "Do not select a fact. Do not add markdown. Do not explain. Do not repeat the request's labels."
            )
        else:
            instruction = (
                "Your last answer was not valid. Send back only JSON. It must have segments with text in them. "
                "selected_knowledge_ids must be a list. Leave it empty only when no offered candidate was earned. "
                "Do not add markdown. Do not explain. Do not repeat the request's labels. If you are not sure an ID "
                "belongs in grounding_ids, leave grounding_ids out."
            )
        recovery_payload = {**payload, "system": f"{payload['system']} {instruction}{correction}"}
        self._record_recovery()
        try:
            response = self._request_allowing_one_transient_retry(recovery_payload)
        except HTTPError as error:
            self._log_typed_worker_error(error, self._worker_error_code(error))
            raise self._narration_error(error) from error
        except (URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            self._log_unavailable(error)
            raise NarrationProviderError("narration service is unavailable") from error
        return self._eligible_or_narration_only(response)

    def _eligible_or_narration_only(self, response: object) -> object:
        """Accept the reply, or keep only its narration when it still names knowledge it may not use.

        A provider that will not correct its selection after one guided retry
        would otherwise cost the player the turn. Returning the narration with
        no selection and no grounding cannot commit an unearned fact: the
        runtime only ever commits through an eligible package route, and the
        projection never showed this provider the ineligible unit's statement.
        A reply that cannot be parsed at all is still refused.
        """

        try:
            proposal = self._parse_eligible_proposal(response)
        except _EligibilityError:
            proposal = parse_turn_proposal(response)
            if self.last_projection and self.last_projection.handoff_deliveries:
                return self._fallback_handoff()
            narration_only = {
                "segments": [
                    {
                        "kind": segment.kind,
                        "text": segment.text,
                        **({"speaker_id": segment.speaker_id} if segment.speaker_id else {}),
                    }
                    for segment in proposal.segments
                ],
                "selected_knowledge_ids": [],
            }
            return self._cap_accepted_response(narration_only, parse_turn_proposal(narration_only))
        except RuntimeContractError as error:
            if self.last_projection and self.last_projection.handoff_deliveries:
                return self._fallback_handoff()
            summary = contract_error_summary(error) or "invalid proposal"
            raise NarrationProviderError(
                f"narration service returned an invalid proposal ({summary})",
                502,
                "INVALID_PROPOSAL",
            ) from error
        return self._accept_proposal(response, proposal)

    def _accept_proposal(self, response: object, proposal: TurnProposal) -> object:
        """Compose an authored handoff before the engine's normal validation path."""

        if self.authored_handoff is not None:
            proposal = self._compose_authored_handoff(proposal)
            response = proposal.model_dump(mode="json")
        return self._cap_accepted_response(response, proposal)

    def _compose_authored_handoff(self, proposal: TurnProposal) -> TurnProposal:
        """Keep model prose ordinary, then append the package-owned delivery segment."""

        handoff = self.authored_handoff
        if handoff is None:
            return proposal
        committed_ids = (
            {item.id for item in self.last_projection.committed_knowledge}
            if self.last_projection is not None
            else set()
        )
        model_segments = tuple(
            segment.model_copy(
                update={
                    "grounding_ids": tuple(
                        grounding_id for grounding_id in segment.grounding_ids if grounding_id in committed_ids
                    )
                }
            )
            for segment in proposal.segments
        )
        delivery = NarrationSegment(
            kind="narration",
            text=handoff.delivery_text,
            grounding_ids=(handoff.candidate.id,),
        )
        composed = proposal.model_copy(
            update={
                "segments": (*model_segments, delivery),
                "selected_knowledge_ids": (handoff.candidate.id,),
            }
        )
        return self._auto_attribute_committed_knowledge(composed)

    def _character_lines(self) -> list[str]:
        """Introduce only the characters this scene actually involves.

        A package's cast is written for a reader who finishes the story, so
        sending all of it would hand the narrator later characters and their
        motives before the player has met them.
        """

        package = self.state.package
        scene = self._current_scene()
        involved = {package.protagonist_id, *scene.participant_ids}
        lines = []
        for character in package.characters:
            if character.id not in involved:
                continue
            bio = character.bio
            article = next((item for item in ("A ", "An ") if bio.startswith(item)), None)
            lines.append(
                f"{character.name} is {article.lower()}{bio[len(article) :]}" if article else f"{character.name}: {bio}"
            )
        return lines

    def _display_name(self, entity_id: str) -> str:
        """Name a speaker the way the story names them, never by runtime id."""

        npc = next((entity for entity in self.state.package.world.npcs if entity.id == entity_id), None)
        return npc.name if npc else entity_id

    def _section_user_prompt(self, user: dict[str, object]) -> str:
        """Render turn context as the authored roleplay sections.

        Each item is one whole line: an authored paragraph is never split
        across entries, and no section that has nothing to say is printed.
        """

        scene: list[str] = []
        constraints: list[str] = []
        player_lines: list[str] = []
        handoff_turn = self._is_authored_handoff_turn()

        def paragraphs(text: str) -> list[str]:
            """One entry per authored line, each kept whole."""

            return [line.strip() for line in _plain(text).splitlines() if line.strip()]

        scene_entry = user.get("scene_entry")
        if isinstance(scene_entry, dict):
            scene.append(f"The scene takes place at {scene_entry['location']}.")
            objective = str(scene_entry["objective"])
            scene.append(f"{scene_entry['protagonist']}'s objective is to {objective[0].lower()}{objective[1:]}.")
            scene.extend(paragraphs(scene_entry["entry_text"]))
            for detail in scene_entry["opening_beat"].get("details", []):
                scene.extend(paragraphs(detail))

        context = user.get("knowledge_context", {})
        player = context.get("player", {}) if isinstance(context, dict) else {}
        offered_ids = {candidate.id for candidate in self._model_candidates()}
        if isinstance(player, dict) and player:
            scene.extend(paragraphs(player["scene_frame"]))
            scene.append(f"What presses on {self._protagonist_name()} now: {player['pressure']}")
            scene_setting = user.get("scene_setting")
            if isinstance(scene_setting, dict):
                scene.extend(paragraphs(scene_setting["entry_text"]))
                for beat in scene_setting.get("beats", []):
                    if not isinstance(beat, dict):
                        continue
                    if (self.prompt_variant or {}).get("beat_delivery") == "prose":
                        scene.extend(paragraphs(beat["prose"]))
                    else:
                        for detail in beat.get("details", []):
                            scene.extend(paragraphs(detail))
            for item in player.get("committed_knowledge", []):
                scene.append(item["statement"])
            if not handoff_turn:
                for candidate in player.get("candidates", []):
                    if candidate.get("id") not in offered_ids:
                        continue
                    constraints.append(f"Candidate {candidate['id']}. The player does not know this yet.")
                    earn_when = candidate.get("earn_when")
                    if isinstance(earn_when, str) and earn_when:
                        constraints.append(f"Earn it when the player {earn_when}.")
                    constraints.append(f"What the player learns: {candidate['statement']}")
                    selection_instruction = (
                        f"If the player earns it, state what they learn. Put {candidate['id']} "
                        "in selected_knowledge_ids."
                    )
                    if (self.prompt_variant or {}).get("model_grounding", True):
                        selection_instruction = (
                            f"If the player earns it, state what they learn. Put {candidate['id']} "
                            "in selected_knowledge_ids "
                            f"and in the grounding_ids for that text."
                        )
                    constraints.append(selection_instruction)
                    for group in candidate.get("must_convey", []):
                        if group:
                            constraints.append(f"If you reveal {candidate['id']}, you must say this: {group[0]}")
        if isinstance(context, dict):
            speakers = context.get("speakers", {})
            if isinstance(speakers, dict):
                for speaker_id, speaker in speakers.items():
                    # The protagonist's sayable knowledge mirrors what SCENE already
                    # states, so listing it repeated every established statement
                    # verbatim and grew with every beat. The narrator writes the
                    # player character from the same SCENE material either way; what
                    # genuinely constrains a turn is which NPC may say what aloud.
                    if speaker_id == self.state.package.protagonist_id:
                        continue
                    for item in speaker.get("sayable_knowledge", []):
                        constraints.append(f"{self._display_name(speaker_id)} may say this aloud: {item['statement']}")
        rules = user.get("_rules", [])
        constraints.extend(rule for rule in rules if isinstance(rule, str))
        player_input = str(user.get("player_input", "")).strip()
        if player_input:
            player_lines.append(player_input)

        blocks = []
        for heading, items in (
            ("CHARACTERS", self._character_lines()),
            ("SCENE", scene),
            ("CONSTRAINTS", constraints),
            ("PLAYER", player_lines),
        ):
            if items:
                blocks.append("\n".join([f"{heading}:", *(f"- {item}" for item in items)]))
        return "\n\n".join(blocks)

    def _cap_accepted_response(self, response: object, proposal: TurnProposal) -> object:
        """Bound accepted narration while retaining an out-of-band reveal segment."""

        if (
            len(proposal.segments) <= MAX_TURN_SEGMENTS
            and not self.grounding_attributions
            and parse_turn_proposal(response) == proposal
        ):
            return response
        kept = list(proposal.segments[:MAX_TURN_SEGMENTS])
        if proposal.selected_knowledge_ids:
            selected_id = proposal.selected_knowledge_ids[0]
            delivering = next(
                (segment for segment in proposal.segments if selected_id in segment.grounding_ids),
                None,
            )
            if delivering is not None and delivering not in kept:
                kept.append(delivering)
        self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(update={"segments_truncated": True})
        return {
            "segments": [segment.model_dump(mode="json") for segment in kept],
            "selected_knowledge_ids": list(proposal.selected_knowledge_ids),
        }

    def _salvage_malformed_segments(self, response: object, error: RuntimeContractError) -> dict[str, object] | None:
        """Keep valid segment objects from a proposal with malformed array entries.

        This is deliberately limited to the first provider reply.  A selected
        reveal is only salvageable when its grounding survives in a valid
        segment; otherwise retaining the selection would commit knowledge the
        player never saw.
        """

        payload = response
        if isinstance(payload, dict) and "response" in payload:
            payload = payload["response"]
        if isinstance(payload, dict) and "content" in payload:
            payload = payload["content"]
        if not isinstance(payload, dict) or not isinstance(payload.get("segments"), list):
            return None

        raw_segments = payload["segments"]
        valid_segments: list[NarrationSegment] = []
        valid_raw_segments: list[dict[str, object]] = []
        dropped_shapes: list[str] = []
        for segment in raw_segments:
            try:
                parsed_segment = NarrationSegment.model_validate(segment)
            except Exception:  # noqa: BLE001 - provider values are untrusted
                dropped_shapes.append(self._segment_shape(segment))
            else:
                valid_segments.append(parsed_segment)
                valid_raw_segments.append(segment)
        if not dropped_shapes or not valid_segments:
            return None

        selected = payload.get("selected_knowledge_ids", [])
        if not isinstance(selected, list) or not all(isinstance(item, str) for item in selected):
            return None
        grounded = {item for segment in valid_segments for item in segment.grounding_ids}
        if any(knowledge_id not in grounded for knowledge_id in selected):
            return None

        self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
            update={"segments_dropped": len(dropped_shapes)}
        )
        self._log_segment_salvage(error, len(dropped_shapes), tuple(dropped_shapes))
        return {
            "segments": valid_raw_segments,
            "selected_knowledge_ids": selected,
        }

    @staticmethod
    def _segment_shape(value: object) -> str:
        if isinstance(value, dict):
            keys = ",".join(sorted(str(key) for key in value))
            return f"object(keys={keys})"
        return type(value).__name__

    def _log_segment_salvage(self, error: RuntimeContractError, count: int, shapes: tuple[str, ...]) -> None:
        cause = error.__cause__
        logger.warning(
            "Narration reply contained malformed segments; dropped %d segment(s) with shape(s)=%s "
            "(worker host=%s; underlying exception type=%s; message=%s)",
            count,
            ",".join(shapes),
            urlsplit(self.worker_url).hostname,
            type(cause).__name__ if cause is not None else type(error).__name__,
            contract_error_summary(error) or self._safe_error_message(error),
        )

    def _parse_eligible_proposal(self, response: object) -> TurnProposal:
        self.grounding_attributions = ()
        self.model_selected_knowledge_ids = ()
        self.model_grounding_ids = ()
        proposal = parse_turn_proposal(response)
        self.model_selected_knowledge_ids = tuple(proposal.selected_knowledge_ids)
        self.model_grounding_ids = tuple(
            sorted({grounding_id for segment in proposal.segments for grounding_id in segment.grounding_ids})
        )
        projection = self.last_projection
        if projection is None:
            raise RuntimeContractError("knowledge projection is unavailable")
        if self.authored_handoff is not None:
            return self._ordinary_handoff_proposal(proposal, projection)
        handoff_ids = self._handoff_eligible_candidate_ids()
        selected_handoff_ids = set(proposal.selected_knowledge_ids) & handoff_ids
        if selected_handoff_ids:
            raise _EligibilityError(
                "selected knowledge is owned by the runtime",
                "You selected a runtime-owned reveal that this turn did not offer. Resend the same narration "
                "with selected_knowledge_ids as an empty list and no grounding_ids, revealing nothing new.",
            )
        # This pre-check must mirror every provider-facing rule in SelectedRevealResolver.resolve;
        # a rule missing here becomes a hard turn failure in the browser instead of one recovery.
        if len(proposal.selected_knowledge_ids) > 1:
            raise _EligibilityError(
                "at most one knowledge selection is allowed per turn",
                f"You selected {', '.join(sorted(proposal.selected_knowledge_ids))}. Resend the same narration with "
                "selected_knowledge_ids holding at most one of those IDs, or an empty list to reveal nothing.",
            )
        proposal = self._auto_select_unambiguous_candidate(proposal)
        proposal = self._auto_attribute_committed_knowledge(proposal)
        candidate_ids = {candidate.id for candidate in self._legacy_projection_candidates()}
        ineligible = sorted(
            {knowledge_id for knowledge_id in proposal.selected_knowledge_ids if knowledge_id not in candidate_ids}
        )
        if ineligible:
            # Steer to the one response that is always valid. Offering a menu invites the model to
            # keep reaching for the reveal the player's intent implies, which fails the turn again.
            alternative = (
                f" Only if one of [{', '.join(sorted(candidate_ids))}] genuinely fits this moment may you select "
                "exactly one of those instead."
                if candidate_ids
                else " This turn offers no candidates at all."
            )
            raise _EligibilityError(
                "selected knowledge is not eligible for this turn",
                f"You selected {', '.join(ineligible)}, which this turn does not offer. Resend the same narration "
                "with selected_knowledge_ids as an empty list and no grounding_ids, revealing nothing new."
                + alternative,
            )
        # The runtime rejects a turn whose grounding is neither committed nor selected; catching it
        # here spends the transport's single recovery instead of failing the player's turn.
        groundable = {item.id for item in self.last_projection.committed_knowledge} | set(
            proposal.selected_knowledge_ids
        )
        ungroundable = sorted(
            {
                grounding_id
                for segment in proposal.segments
                for grounding_id in segment.grounding_ids
                if grounding_id not in groundable
            }
        )
        if ungroundable:
            if set(ungroundable) & handoff_ids:
                raise _EligibilityError(
                    "segment grounding names a runtime-owned reveal",
                    "You grounded a segment on a runtime-owned reveal that this turn did not offer. Resend the same "
                    "narration with an empty grounding_ids list.",
                )
            raise _EligibilityError(
                "segment grounding is not committed or selected knowledge",
                f"You grounded a segment on {', '.join(ungroundable)}, which is neither committed knowledge nor a "
                "candidate you selected. Resend the same narration with an empty grounding_ids list; only if that ID "
                "is one of this turn's candidates may you instead place it in selected_knowledge_ids.",
            )
        candidates = {candidate.id: candidate for candidate in self._legacy_projection_candidates()}
        # Selecting a reveal without telling it commits the fact silently: the scene's exit
        # unlocks and the player is moved somewhere the narration gave them no reason to go.
        # When the prose proves the reveal, derive the missing bookkeeping from that evidence.
        grounded = {grounding_id for segment in proposal.segments for grounding_id in segment.grounding_ids}
        undelivered = sorted(
            {knowledge_id for knowledge_id in proposal.selected_knowledge_ids if knowledge_id not in grounded}
        )
        if undelivered:
            candidate = candidates[undelivered[0]]
            derived_segments = (
                derive_grounding(candidate.must_convey, proposal.segments)
                if candidate.must_convey
                else derive_statement_grounding(candidate.statement, proposal.segments)
            )
            if derived_segments:
                self.grounding_attributions = tuple(undelivered)
                proposal = proposal.model_copy(
                    update={
                        "segments": tuple(
                            segment.model_copy(update={"grounding_ids": (*segment.grounding_ids, *undelivered)})
                            if any(segment is derived_segment for derived_segment in derived_segments)
                            else segment
                            for segment in proposal.segments
                        )
                    }
                )
            grounded = {grounding_id for segment in proposal.segments for grounding_id in segment.grounding_ids}
            undelivered = sorted(
                {knowledge_id for knowledge_id in proposal.selected_knowledge_ids if knowledge_id not in grounded}
            )
        if undelivered:
            raise _EligibilityError(
                "selected knowledge must be grounded in the segment that reveals it",
                f"You selected {', '.join(undelivered)} but no segment is grounded on it, so the player would never "
                "learn it. Resend with a segment whose text actually states what that reveal says, listing that ID "
                "in its grounding_ids - or, if the player has not earned it yet, with selected_knowledge_ids empty.",
            )
        for knowledge_id in proposal.selected_knowledge_ids:
            candidate = candidates[knowledge_id]
            grounded_text = " ".join(
                segment.text for segment in proposal.segments if knowledge_id in segment.grounding_ids
            )
            missing = unconveyed_terms(candidate.must_convey, grounded_text)
            if missing:
                self._record_misses((knowledge_id,))
                missing_text = ", ".join(missing)
                raise _EligibilityError(
                    f"selected knowledge does not convey: {missing_text}",
                    f"You selected {knowledge_id}, but its grounded narration is missing: {missing_text}. "
                    "Resend with a segment whose text conveys every must_convey group for that candidate and lists "
                    f"{knowledge_id} in its grounding_ids, or use an empty selected_knowledge_ids list.",
                )
        missing_handoff = self._missing_handoff_terms(proposal.narration)
        if missing_handoff:
            deliveries = self.last_projection.handoff_deliveries if self.last_projection else ()
            self._record_misses(
                tuple(
                    delivery.fact_id
                    for delivery in deliveries
                    if unconveyed_terms(delivery.must_convey, proposal.narration)
                )
            )
            missing_text = ", ".join(missing_handoff)
            raise _EligibilityError(
                f"handoff narration does not convey: {missing_text}",
                "This is a HANDOFF turn. Your narration must convey every missed handoff group: "
                f"{missing_text}. Keep the player's direct response and write the declared intervention; do not "
                "select facts or a transition.",
            )
        return proposal

    def _ordinary_handoff_proposal(self, proposal: TurnProposal, projection: TurnKnowledgeContext) -> TurnProposal:
        """Drop model selection work while retaining safe committed grounding."""

        committed_ids = {item.id for item in projection.committed_knowledge}
        filtered_segments = tuple(
            segment.model_copy(
                update={
                    "grounding_ids": tuple(
                        grounding_id for grounding_id in segment.grounding_ids if grounding_id in committed_ids
                    )
                }
            )
            for segment in proposal.segments
        )
        proposal = proposal.model_copy(update={"segments": filtered_segments})
        proposal = self._auto_attribute_committed_knowledge(proposal)
        return proposal.model_copy(update={"selected_knowledge_ids": ()})

    def _auto_select_unambiguous_candidate(self, proposal: TurnProposal) -> TurnProposal:
        """Select one reveal only when the narration itself proves exactly one candidate.

        This is a narrow harness repair for a small narrator that often describes
        an earned reveal but leaves its bookkeeping empty. It is safe only when:

        1. the candidate is in this turn's offered list;
        2. its non-empty ``must_convey`` groups are all present in the prose;
        3. exactly one offered candidate passes that test; and
        4. the normal selection, effect, and narration-safety checks still run.

        A variation can disable this rule for a controlled baseline comparison.
        """

        if (
            self.last_projection is None
            or proposal.selected_knowledge_ids
            or self.prompt_variant is not None
            and self.prompt_variant.get("auto_select_unambiguous_candidates", True) is False
        ):
            return proposal

        matches = []
        for candidate in self._legacy_projection_candidates():
            groups = tuple(group for group in candidate.must_convey if group)
            if not groups:
                continue
            matches.append((candidate, derive_grounding(groups, proposal.segments)))
        matches = [(candidate, segments) for candidate, segments in matches if segments]
        if len(matches) != 1:
            return proposal

        candidate, derived_segments = matches[0]
        segments = tuple(
            segment.model_copy(update={"grounding_ids": (*segment.grounding_ids, candidate.id)})
            if any(segment is derived_segment for derived_segment in derived_segments)
            and candidate.id not in segment.grounding_ids
            else segment
            for segment in proposal.segments
        )
        return proposal.model_copy(update={"segments": segments, "selected_knowledge_ids": (candidate.id,)})

    def _auto_attribute_committed_knowledge(self, proposal: TurnProposal) -> TurnProposal:
        """Repair omitted grounding for unambiguous, already-committed terms."""

        if self.last_projection is None:
            return proposal

        committed_ids = {item.id for item in self.last_projection.committed_knowledge}
        handoff_candidate_id = self.authored_handoff.candidate.id if self.authored_handoff is not None else None
        indexes = self.state.package.knowledge_indexes
        multi_word_terms = {term for term in indexes.term_to_knowledge if len(term.split()) > 1}
        changed = False
        segments: list[NarrationSegment] = []
        for segment in proposal.segments:
            normalized_text = " ".join(segment.text.casefold().split())
            new_ids: set[str] = set()
            for term in multi_word_terms:
                normalized_term = " ".join(term.casefold().split())
                if not re.search(rf"(?<!\w){re.escape(normalized_term)}(?!\w)", normalized_text):
                    continue
                owners = set(indexes.term_to_knowledge[term]) & committed_ids
                if (
                    not owners
                    and handoff_candidate_id is not None
                    and handoff_candidate_id in indexes.term_to_knowledge[term]
                ):
                    owners = {handoff_candidate_id}
                if len(owners) == 1:
                    owner = next(iter(owners))
                    if owner not in segment.grounding_ids:
                        new_ids.add(owner)
            if not new_ids:
                segments.append(segment)
                continue
            changed = True
            segments.append(segment.model_copy(update={"grounding_ids": (*segment.grounding_ids, *sorted(new_ids))}))

        return proposal.model_copy(update={"segments": tuple(segments)}) if changed else proposal

    def _missing_handoff_terms(self, narration: str) -> tuple[str, ...]:
        deliveries = self.last_projection.handoff_deliveries if self.last_projection else ()
        missing: list[str] = []
        for delivery in deliveries:
            missing.extend(unconveyed_terms(delivery.must_convey, narration))
        return tuple(missing)

    def _fallback_handoff(self) -> dict[str, object]:
        deliveries = self.last_projection.handoff_deliveries if self.last_projection else ()
        self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(update={"fallback_used": True})
        return {
            "segments": [{"kind": "narration", "text": delivery.fallback_text} for delivery in deliveries],
            "selected_knowledge_ids": [],
        }

    def _record_misses(self, ids: tuple[str, ...]) -> None:
        existing = self.state.last_turn_delivery.must_convey_misses
        additions = tuple(item for item in ids if item not in existing)
        if additions:
            self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
                update={"must_convey_misses": (*existing, *additions)}
            )

    def _record_recovery(self) -> None:
        self.recovery_count += 1
        self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(update={"recovery_used": True})

    def _speaker_contexts(self, player_input: str) -> dict[str, dict[str, object]]:
        """Send each speaker only what bounds their dialogue.

        A speaker context exists so an NPC says nothing it could not know. A
        second full projection per speaker - scene frame, candidates, entity
        lists and all - multiplies the request without telling the model
        anything it cannot already read in the player context. Participants
        are offered only when the authored scene beats portray them acting or
        speaking in person; mentions limited to absence, captivity, evidence,
        possessions, or recordings do not establish presence. The protagonist
        is always present. This derives presence from authored prose and
        package entity aliases, rather than a character-name allowlist.
        """

        scene = self._current_scene()
        npc_ids = {item.id for item in self.state.package.world.npcs}
        return {
            speaker_id: {
                "sayable_knowledge": [
                    {"id": item.id, "statement": item.statement}
                    for item in self.projector.project(self.state, speaker_id, player_input).sayable_knowledge
                ]
            }
            for speaker_id in scene.participant_ids
            if speaker_id in npc_ids and self._is_present(speaker_id)
        }

    def _is_present(self, speaker_id: str) -> bool:
        """Infer on-stage presence from authored beat prose and entity aliases."""

        if speaker_id == self.state.package.protagonist_id:
            return True
        entity = next(item for item in self.state.package.world.npcs if item.id == speaker_id)
        aliases = (entity.name, *entity.aliases)
        prose = " ".join(beat.prose for beat in self._scene().beats.values())
        for sentence in re.split(r"(?<=[.!?])\s+", prose):
            folded = sentence.casefold()
            if not any(re.search(rf"\b{re.escape(alias.casefold())}\b", folded) for alias in aliases):
                continue
            words = set(re.findall(r"[a-z]+", folded))
            if words & _ABSENCE_OR_EVIDENCE:
                continue
            action_pattern = "|".join(sorted(_PRESENCE_ACTIONS, key=len, reverse=True))
            if any(
                re.search(
                    rf"\b{re.escape(alias.casefold())}(?!['’]s)\b(?:\s+\w+){{0,2}}\s+(?:{action_pattern})\b",
                    folded,
                )
                for alias in aliases
            ):
                return True
        return False

    def _current_scene(self) -> SceneMetadata:
        return self._scene().metadata

    def _current_beat(self) -> SceneBeat:
        return self._scene().opening_beat

    def _scene(self) -> Scene:
        return next(item for item in self.state.package.scenes if item.metadata.scene_id == self.state.current_scene_id)

    def _request_allowing_one_transient_retry(self, payload: dict[str, object]) -> object:
        """Retry once when the connection itself fails, never on an answered request.

        A momentary connection failure is not the provider refusing the turn, but
        it reached the player as a lost turn all the same, and it ended a
        thirty-turn playthrough on its third turn. An answered request - any
        HTTPError, or a body that is not JSON - is left alone, because those are
        handled by the typed-error and recovery paths above.
        """

        try:
            return self._request(payload)
        except HTTPError:
            raise
        except (TimeoutError, URLError, OSError) as first_failure:
            try:
                return self._request(payload)
            except HTTPError:
                raise
            except (TimeoutError, URLError, OSError) as error:
                raise error from first_failure

    def _request(self, payload: dict[str, object]) -> object:
        self.request_count += 1
        self.last_prompt = {"system": payload["system"], "user": payload["user"]}
        headers = {
            "Content-Type": "application/json",
            "User-Agent": BROWSER_USER_AGENT,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(self.worker_url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urlopen(request, timeout=float(getenv("CLOUDFLARE_TIMEOUT", "15"))) as response:  # noqa: S310
            body = json.loads(response.read())
        if isinstance(body, dict) and body.get("status") == "error":
            raise NarrationProviderError(str(body.get("message", "narration service failed")), 502)
        if isinstance(body, dict) and isinstance(body.get("narration"), str):
            return self._decode_narration(body["narration"])
        return body

    def _decode_narration(self, narration: str) -> object:
        """Parse the reply, keeping its finished segments when the model was cut off mid-word.

        A reply that overruns max_tokens arrives as usable prose inside invalid
        JSON, and re-asking costs a second overrun as often as it buys a shorter
        one: that is how a turn became a 503 rather than a turn. The segments the
        model did finish are worth keeping, and keeping them commits nothing on
        its own - selection, grounding and must_convey are all still judged
        afterwards on whatever survives.
        """

        try:
            return json.loads(narration)
        except json.JSONDecodeError:
            salvaged = self._salvage_truncated_json(narration)
            if salvaged is None:
                raise
            logger.warning(
                "Narration reply was truncated; kept %d finished segment(s) (worker host=%s)",
                len(salvaged["segments"]),
                urlsplit(self.worker_url).hostname,
            )
            self._record_recovery()
            return salvaged

    @staticmethod
    def _salvage_truncated_json(narration: str) -> dict[str, object] | None:
        """Close the reply at its last finished segment, or give up.

        Truncation lands inside the segments array, so every candidate cut point
        is the end of an object. Walking those backwards finds the longest
        prefix that closes into a whole TurnProposal.
        """

        for end in reversed([index for index, char in enumerate(narration) if char == "}"]):
            for suffix in ("]}", "}]}"):
                try:
                    candidate = json.loads(narration[: end + 1] + suffix)
                except json.JSONDecodeError:
                    continue
                if isinstance(candidate, dict) and candidate.get("segments"):
                    return candidate
        return None

    def _log_unavailable(self, error: BaseException) -> None:
        logger.warning(
            "Narration service unavailable (worker host=%s; underlying exception type=%s; message=%s)",
            urlsplit(self.worker_url).hostname,
            type(error).__name__,
            self._safe_error_message(error),
            exc_info=True,
        )

    def _log_typed_worker_error(self, error: HTTPError, worker_error_code: str) -> None:
        logger.warning(
            "Narration worker returned a typed error (worker host=%s; underlying exception type=%s; message=%s; "
            "worker error code=%s)",
            urlsplit(self.worker_url).hostname,
            type(error).__name__,
            self._safe_error_message(error),
            worker_error_code or "UNKNOWN",
            exc_info=True,
        )

    @staticmethod
    def _safe_error_message(error: BaseException) -> str:
        if isinstance(error, (HTTPError, URLError)):
            return str(error.reason)
        return str(error)

    @staticmethod
    def _worker_error_code(error: HTTPError) -> str:
        cached_code = getattr(error, "_freytag_worker_error_code", None)
        if isinstance(cached_code, str):
            return cached_code
        header_code = CloudflareTurnProvider._error_header(error, "X-Narration-Error-Code")
        if header_code:
            error._freytag_worker_error_code = header_code
            return header_code
        try:
            body = json.loads(error.read())
        except (OSError, ValueError, json.JSONDecodeError):
            code = ""
        else:
            if isinstance(body, dict) and body.get("detail") == "rate limit exceeded":
                code = "RATE_LIMITED"
            else:
                code = str(body.get("code", "")) if isinstance(body, dict) else ""
        error._freytag_worker_error_code = code
        return code

    @classmethod
    def _narration_error(cls, error: HTTPError) -> NarrationProviderError:
        code = cls._worker_error_code(error) or "UNKNOWN"
        trace_id = cls._error_header(error, "X-Trace-ID")
        worker_revision = cls._error_header(error, "X-Worker-Revision")
        if code in {"AI_QUOTA_EXCEEDED", "AI_CAPACITY_EXCEEDED"}:
            return NarrationProviderError("narration service is at capacity", 429, code, trace_id, worker_revision)
        if code and 400 <= error.code < 500:
            return NarrationProviderError(
                "narration service rejected the turn", error.code, code, trace_id, worker_revision
            )
        return NarrationProviderError(
            "narration service rejected the turn", 429 if error.code == 429 else 502, code, trace_id, worker_revision
        )

    @staticmethod
    def _error_header(error: HTTPError, name: str) -> str:
        return str(error.headers.get(name, "")).strip() if error.headers else ""
