"""Fail-closed Cloudflare Worker transport for typed scene proposals."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from os import getenv
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from storygame.runtime.contracts import (
    NarrationSegment,
    RuntimeContractError,
    TurnProposal,
    contract_error_summary,
    parse_turn_proposal,
)
from storygame.runtime.knowledge import KnowledgeProjector, TurnKnowledgeContext
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import derive_grounding, derive_statement_grounding, unconveyed_terms
from storygame.story_package.models import Scene, SceneBeat, SceneMetadata

logger = logging.getLogger(__name__)

MAX_TURN_SEGMENTS = 5

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
    story ID. ``hint`` is for the recovery prompt only, where the offending IDs
    are already part of the Worker's own context.
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
    ) -> None:
        self.worker_url = worker_url
        self.token = token
        self.state = state
        self.projector = projector or KnowledgeProjector()
        self.last_projection: TurnKnowledgeContext | None = None
        self.grounding_attributions: tuple[str, ...] = ()

    @classmethod
    def from_environment(cls, state: RuntimeState) -> CloudflareTurnProvider:
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
        )

    def __call__(self, player_input: str) -> object:
        self.last_projection = self.projector.project(self.state, "player", player_input)
        handoff_staged = bool(self.last_projection.handoff_deliveries)
        self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
            update={
                "hint_staged": bool(self.last_projection.hinted_deliveries),
                "handoff_staged": handoff_staged,
            }
        )
        speaker_contexts = self._speaker_contexts(player_input)
        scene_setting = self._scene_setting()
        return self._dispatch(
            self._turn_instruction(),
            {
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
            },
        )

    def _turn_instruction(self) -> str:
        """State the selection rule that actually applies to this turn.

        The two cases pull in opposite directions and both have cost a
        playthrough. With no candidates, "select at most one" invites the model
        to invent an ID and the player loses the turn. With candidates offered,
        permissive wording leaves the model free to select nothing, the earned
        reveal never commits, and the story stalls in the scene instead. So the
        rule is stated as a duty when a reveal is on offer, and as a
        prohibition when none is.
        """

        candidates = self.last_projection.candidates if self.last_projection else ()
        selection_rules = [
            "Select at most one candidate ID in selected_knowledge_ids.",
            "A selected candidate must be conveyed by one readable segment, and that segment must carry its ID "
            "in grounding_ids.",
            "A candidate with neither a statement nor a must_convey group cannot be selected.",
            "Leave selected_knowledge_ids empty when no candidate fits what just happened.",
            "Narrating a reveal without selecting it stalls the story.",
        ]
        if not candidates:
            selection_rules.append("This turn offers no candidates, so selected_knowledge_ids must be empty.")
        hinted = self.last_projection.hinted_deliveries if self.last_projection else ()
        handoffs = self.last_projection.handoff_deliveries if self.last_projection else ()
        if handoffs:
            handoff_rule = (
                "Write every declared handoff intervention, convey every required concept, answer the player's input, "
                "and do not claim that the player took an action they did not take."
            )
        elif hinted:
            handoff_rule = (
                "Surface the hinted evidence as an actionable NPC remark, noticed detail, or radio call without "
                "establishing or committing a fact."
            )
        else:
            handoff_rule = ""
        rules = [
            "Narrate the concrete immediate consequence of the player's action.",
            "Ground narration in the scene and knowledge context.",
            "Use the authored place, texture, and physical detail.",
            "Answer what the player actually did.",
            "Never invent durable evidence, physical objects, items, or container contents.",
            "Treat the authored entry_text and beat details as already true.",
            "A grounding ID may name only committed knowledge or the selected candidate.",
            "Never ground on a candidate you did not select.",
            "Dialogue may use only its speaker's sayable knowledge.",
            *selection_rules,
            "Never write source IDs, events, operations, facts, or transitions as prose.",
            f"Return one paragraph per segment, roughly 30 to 55 words, with at most {MAX_TURN_SEGMENTS} segments.",
            "Never reuse a beat's sentences.",
            "Never contradict authored text.",
            "Never echo the request fields.",
        ]
        if handoff_rule:
            rules.append(handoff_rule)
        # The example is not the place to teach grounding. Showing a grounded
        # selection here made the model ground on IDs it had not selected, and a
        # live sample went from no failures in sixteen turns to six in eighteen -
        # five of them HTTP 409 for grounding on knowledge that was neither
        # committed nor selected. The engine attributes the delivering segment
        # itself, so the model never needs to be shown how.
        example = (
                '<output_example>{"segments":['
                '{"kind":"narration","text":"The drawer sticks, then gives. Inside, under a curl of packing tape, '
                "her fingers find the flat edge of something that was never meant to be seen from above, and the "
                'kitchen behind her goes very quiet."},'
                '{"kind":"narration","text":"She works it loose and turns it over in the light from the window. '
                "The plastic is scuffed at one corner, as though it had been pressed into place in a hurry, and "
                'the initials carved into the drawer front suddenly read less like affection than instruction."}],'
                '"selected_knowledge_ids":[]}</output_example>'
            )
        return "\n".join([*(f"<rule>{rule}</rule>" for rule in rules), example])

    def opening(self) -> object:
        """Continue the authored entry text, before any player input exists."""

        self.last_projection = self.projector.project(self.state, "player", "")
        entry = self._scene_entry()
        rules = [
            "The player has already read entry_text as the opening paragraph; write only what follows it in the "
            "same voice and tense.",
            "Dramatize only the opening beat and knowledge context as the protagonist encounters them.",
            "Do not repeat or paraphrase entry_text, invent evidence, characters, or events, resolve the objective, "
            "act for the protagonist, or offer choices.",
            f"Return one paragraph per segment, roughly 30 to 55 words, with at most {MAX_TURN_SEGMENTS} segments.",
            "Keep selected_knowledge_ids empty.",
            "Do not contradict authored entry_text or beat details.",
            "Do not invent physical objects, items, or contents the authored context does not describe.",
            "Never write source IDs, events, operations, facts, or transitions as prose.",
        ]
        return self._dispatch(
            "\n".join(
                [
                    *(f"<rule>{rule}</rule>" for rule in rules),
                    '<output_example>{"segments":['
                    '{"kind":"narration","text":"The gate stands open on a driveway that has not been swept in '
                    "days, and the house beyond it keeps the particular stillness of a place someone left in the "
                    'middle of doing something ordinary."},'
                    '{"kind":"narration","text":"She goes up the steps slowly, listening for the sounds a lived-in '
                    "house makes and hearing none of them, and the front door gives under her hand without her "
                    'having to reach for a key."}],'
                    '"selected_knowledge_ids":[]}</output_example>',
                ]
            ),
            {"scene_entry": entry, "knowledge_context": {"player": self.last_projection.model_dump(mode="json")}},
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
                    "details": list(beat.details),
                    "your_job": (
                        "Dramatize this world state only as far as the player's action reaches; "
                        "never reproduce its wording."
                    ),
                }
                for beat in beats
            ]
        return setting

    def _serialized_player_context(self, scene_setting: dict[str, object]) -> dict[str, object]:
        """Serialize candidate context without repeating facts already carried by beats."""

        if self.last_projection is None:
            return {}
        context = self.last_projection.model_dump(mode="json", exclude={"sayable_knowledge"})
        # Every candidate statement remains an explicit item in the tagged prompt;
        # the beat is additional dramatic context, not a replacement for the claim.
        context["candidates"] = list(context["candidates"])
        return context

    def _beat_covered_candidate_ids(self, beat_anchors: set[object]) -> set[str]:
        """Find offered facts whose authored storylet beat is already serialized."""

        package = self.state.package
        storylets = {storylet.id: storylet for storylet in package.storylets}
        covered: set[str] = set()
        for candidate in self.last_projection.candidates if self.last_projection else ():
            knowledge = package.knowledge_indexes.by_id[candidate.id]
            source = knowledge.source
            storylet = storylets.get(source.storylet_id) if source.storylet_id else None
            if source.kind == "storylet_realization" and storylet and beat_anchors & set(storylet.source_links):
                covered.add(candidate.id)
        return covered

    def _candidate_beats(self) -> tuple[SceneBeat, ...]:
        """Return only the beats belonging to storylets offered this turn."""

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
            "user": self._tagged_user_prompt(user),
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
                    return self._cap_accepted_response(salvaged, proposal)
                return self._recover_malformed_response(payload, getattr(error, "hint", ""))
            return self._cap_accepted_response(response, proposal)

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
        correction = f" {hint}" if hint else ""
        recovery_payload = {
            **payload,
            "system": (
                f"{payload['system']} Your previous response was invalid.{correction} Return only a complete JSON "
                "TurnProposal with non-empty segments and optional selected_knowledge_ids; include no markdown, no "
                "explanation, and none of the request's own fields echoed back. If you are unsure whether an ID is "
                "groundable, omit grounding_ids entirely."
            ),
        }
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
            return self._cap_accepted_response(
                narration_only, proposal.model_copy(update={"selected_knowledge_ids": ()})
            )
        except RuntimeContractError as error:
            if self.last_projection and self.last_projection.handoff_deliveries:
                return self._fallback_handoff()
            summary = contract_error_summary(error) or "invalid proposal"
            raise NarrationProviderError(
                f"narration service returned an invalid proposal ({summary})",
                502,
                "INVALID_PROPOSAL",
            ) from error
        return self._cap_accepted_response(response, proposal)

    @staticmethod
    def _tagged_user_prompt(user: dict[str, object]) -> str:
        """Render model context as distinct, whole tagged items."""

        lines: list[str] = []

        def add(name: str, value: object, **attrs: object) -> None:
            attributes = "".join(f' {key}="{value}"' for key, value in attrs.items())
            lines.append(f"<{name}{attributes}>{value}</{name}>")

        scene_entry = user.get("scene_entry")
        if isinstance(scene_entry, dict):
            add("protagonist", scene_entry["protagonist"])
            add("location", scene_entry["location"])
            add("phase", scene_entry["phase"])
            add("objective", scene_entry["objective"])
            add("entry_text", _plain(scene_entry["entry_text"]))
            beat = scene_entry["opening_beat"]
            add("beat_title", beat["title"])
            for detail in beat.get("details", []):
                add("beat_detail", _plain(detail))
            add(
                "beat_job",
                "Dramatize this world state only as far as the protagonist's arrival reaches; never reproduce its "
                "wording.",
            )

        context = user.get("knowledge_context", {})
        player = context.get("player", {}) if isinstance(context, dict) else {}
        if isinstance(player, dict):
            add("scene_id", player["scene_id"])
            add("phase", player["phase"])
            add("situation", _plain(player["scene_frame"]))
            add("pressure", player["pressure"])
            scene_setting = user.get("scene_setting")
            if isinstance(scene_setting, dict):
                add("entry_text", _plain(scene_setting["entry_text"]))
                for beat in scene_setting.get("beats", []):
                    if isinstance(beat, dict):
                        add("beat_title", beat["title"])
                        for detail in beat.get("details", []):
                            add("beat_detail", _plain(detail))
                        add("beat_job", beat["your_job"])
            for item in player.get("committed_knowledge", []):
                add("known", item["statement"], id=item["id"])
            for candidate in player.get("candidates", []):
                add("candidate", candidate["statement"], id=candidate["id"])
                for group in candidate.get("must_convey", []):
                    if group:
                        add("must_convey", group[0], candidate=candidate["id"])
        if isinstance(context, dict):
            speakers = context.get("speakers", {})
            if isinstance(speakers, dict):
                for speaker_id, speaker in speakers.items():
                    for item in speaker.get("sayable_knowledge", []):
                        add("speaker", item["statement"], id=speaker_id)
        if "player_input" in user:
            add("player_input", user["player_input"])
        return "\n".join(lines)

    def _cap_accepted_response(self, response: object, proposal: TurnProposal) -> object:
        """Bound accepted narration while retaining an out-of-band reveal segment."""

        if len(proposal.segments) <= MAX_TURN_SEGMENTS and not self.grounding_attributions:
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
        proposal = parse_turn_proposal(response)
        if self.last_projection is None:
            raise RuntimeContractError("knowledge projection is unavailable")
        # This pre-check must mirror every provider-facing rule in SelectedRevealResolver.resolve;
        # a rule missing here becomes a hard turn failure in the browser instead of one recovery.
        if len(proposal.selected_knowledge_ids) > 1:
            raise _EligibilityError(
                "at most one knowledge selection is allowed per turn",
                f"You selected {', '.join(sorted(proposal.selected_knowledge_ids))}. Resend the same narration with "
                "selected_knowledge_ids holding at most one of those IDs, or an empty list to reveal nothing.",
            )
        candidate_ids = {candidate.id for candidate in self.last_projection.candidates}
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
            raise _EligibilityError(
                "segment grounding is not committed or selected knowledge",
                f"You grounded a segment on {', '.join(ungroundable)}, which is neither committed knowledge nor a "
                "candidate you selected. Resend the same narration with an empty grounding_ids list; only if that ID "
                "is one of this turn's candidates may you instead place it in selected_knowledge_ids.",
            )
        candidates = {candidate.id: candidate for candidate in self.last_projection.candidates}
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
        try:
            body = json.loads(error.read())
        except (OSError, ValueError, json.JSONDecodeError):
            code = ""
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
