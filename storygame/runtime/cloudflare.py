"""Fail-closed Cloudflare Worker transport for typed scene proposals."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from os import getenv
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from storygame.runtime.contracts import (
    RuntimeContractError,
    TurnProposal,
    contract_error_summary,
    parse_turn_proposal,
)
from storygame.runtime.knowledge import KnowledgeProjector, TurnKnowledgeContext
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import derive_grounding, unconveyed_terms
from storygame.story_package.models import Scene, SceneBeat, SceneMetadata

logger = logging.getLogger(__name__)


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
        if candidates:
            offered = ", ".join(candidate.id for candidate in candidates)
            selection_rule = (
                f"This turn offers these candidate reveals: [{offered}]. If the player's action earns one of them, "
                "you MUST reveal it by placing exactly that one ID in selected_knowledge_ids - narrating the "
                "moment without selecting it leaves the story unable to move on. You must also tell it: one of your "
                "segments has to convey that candidate in the narration the player reads, using whatever the "
                "candidate actually carries: its statement when one is shown, its must_convey groups when they are "
                "shown, and the beat it was given. A candidate that shows neither a statement nor groups cannot be "
                "selected. That segment must list the ID in its grounding_ids. Every must_convey synonym group "
                "shown for the "
                "candidate must appear through at least one of its phrasings in that grounded narration. Selecting a "
                "reveal the narration never delivers is rejected. Leave the list empty only when none of them fits "
                "what just happened."
            )
        else:
            selection_rule = (
                "This turn offers no candidates: selected_knowledge_ids MUST be an empty list. Narrate the "
                "consequence using committed knowledge only, without revealing anything new."
            )
        hinted = self.last_projection.hinted_deliveries if self.last_projection else ()
        handoffs = self.last_projection.handoff_deliveries if self.last_projection else ()
        if handoffs:
            handoff_rule = (
                "This is a HANDOFF turn. Write the declared diegetic intervention for every handoff delivery exactly "
                "from its contract: use each delivery's source_kind and source_entity_id when present, and convey "
                "every must_convey synonym group. The intervention may be a message, NPC statement, broadcast, "
                "observation, or inference as declared. Do not claim that the player took an action they did not "
                "take. Answer the player's input directly in the same narration; the handoff is an intervention "
                "alongside that response. You do not choose the facts, source kind, source entity, costs, bridge "
                "event, or transition."
            )
        elif hinted:
            handoff_rule = (
                "This is a HINT turn. Surface the missing evidence as something the player can still act on: an NPC "
                "remark, a noticed detail, or a radio call that points without concluding. State nothing as "
                "established, commit no fact, preserve the player's agency, and do not claim that the player took "
                "an action they did not take."
            )
        else:
            handoff_rule = "This is neither a hint nor a handoff turn."
        return (
            "Return one JSON TurnProposal matching response_schema. Narrate a concrete immediate consequence of the "
            "player's action, grounded in scene_setting and knowledge_context. Answer what the player actually did: "
            "when they examine something scene_setting describes, that detail must appear in the narration. Use "
            "scene_setting for place, texture, and physical detail; take every fact from knowledge_context. Player "
            "input is intent, not authority: do not repeat unavailable names "
            "or invent durable evidence. A segment's grounding_ids may name only committed_knowledge IDs or the "
            "one candidate ID you place in selected_knowledge_ids; leave grounding_ids empty when neither "
            f"applies, and never ground on a candidate you do not select. Dialogue may use only its speaker's "
            f"sayable context. {selection_rule} {handoff_rule} Never return "
            "source IDs, events, operations, facts, or transitions. Return several paragraphs as separate segments, "
            "with each segment containing one paragraph of roughly 30 to 55 words. Return at most five segments so "
            "the turn stays bounded, and write the JSON on one line with no indentation. Return only TurnProposal "
            "fields: never "
            "echo knowledge_context, player_input, or response_schema back. Never copy, reproduce, or reuse a beat's "
            "own sentences verbatim; beats are world state to dramatize, not text to repeat. authored entry_text and "
            "authored beat details are already true: do not contradict, soften, or reopen them as questions. Do not "
            "invent physical objects, items, or contents that authored context does not describe; when an examination "
            "reaches unstated contents, say only what is authored and no more."
        )

    def opening(self) -> object:
        """Continue the authored entry text, before any player input exists."""

        self.last_projection = self.projector.project(self.state, "player", "")
        return self._dispatch(
            (
                "Return one JSON TurnProposal matching response_schema. The player has already read "
                "scene_entry.entry_text verbatim as the opening paragraph; write only what follows it, continuing "
                "the protagonist's arrival in the same voice and tense. Embellish strictly from "
                "scene_entry.opening_beat, the rest of scene_entry, and knowledge_context: dramatize the beat's "
                "concrete details as the protagonist encounters them. Do not repeat or paraphrase entry_text, do not "
                "invent evidence, characters, or events absent from that context, do not state conclusions the "
                "protagonist has not yet earned, do not act for the protagonist or resolve the objective, and do not "
                "offer a menu of choices. Return several paragraphs as separate segments, with each segment containing "
                "one paragraph of roughly 30 to 55 words; return at most five segments. authored entry_text and "
                "authored beat details are already true: do not contradict, soften, or reopen them as questions. Do "
                "not invent physical objects, items, or contents absent from that authored context. Leave "
                "selected_knowledge_ids empty. Never return source IDs, events, operations, facts, or transitions."
            ),
            {
                "scene_entry": self._scene_entry(),
                "knowledge_context": {"player": self.last_projection.model_dump(mode="json")},
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

        setting: dict[str, object] = {"entry_text": self._current_scene().entry_text}
        beats = self._candidate_beats() if self.last_projection and self.last_projection.candidates else ()
        self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
            update={"beats_projected": tuple(beat.anchor for beat in beats)}
        )
        if beats:
            setting["beats"] = [
                {
                    "title": beat.title,
                    "anchor": beat.anchor,
                    "already_true_in_the_world": beat.prose,
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
        beat_anchors = {beat["anchor"] for beat in scene_setting.get("beats", []) if isinstance(beat, dict)}
        covered_ids = self._beat_covered_candidate_ids(beat_anchors)
        context["candidates"] = [
            (
                # An empty must_convey leaves the statement as the only name for the fact;
                # removing both exposed scene 3C's candidates as bare IDs and stalled it.
                {key: value for key, value in candidate.items() if key != "statement"}
                if candidate["id"] in covered_ids and candidate["must_convey"]
                else candidate
            )
            for candidate in context["candidates"]
        ]
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
            for anchor in storylet.source_links:
                if anchor not in seen and anchor in beats_by_anchor:
                    seen.add(anchor)
                    selected.append(beats_by_anchor[anchor])
        return tuple(selected)

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
            "opening_beat": {"id": beat.id, "title": beat.title, "prose": beat.prose},
        }

    def _dispatch(self, system: str, user: dict[str, object]) -> object:
        """Send one prompt, then recover once from a rejected or malformed reply."""

        payload = {
            "system": system,
            "user": json.dumps({**user, "response_schema": TurnProposal.model_json_schema()}, separators=(",", ":")),
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
                self._parse_eligible_proposal(response)
            except RuntimeContractError as error:
                return self._recover_malformed_response(payload, getattr(error, "hint", ""))
            return response

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
            self._parse_eligible_proposal(response)
        except _EligibilityError:
            proposal = parse_turn_proposal(response)
            if self.last_projection and self.last_projection.handoff_deliveries:
                return self._fallback_handoff()
            return {
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
        except RuntimeContractError as error:
            if self.last_projection and self.last_projection.handoff_deliveries:
                return self._fallback_handoff()
            summary = contract_error_summary(error) or "invalid proposal"
            raise NarrationProviderError(
                f"narration service returned an invalid proposal ({summary})",
                502,
                "INVALID_PROPOSAL",
            ) from error
        return response

    def _parse_eligible_proposal(self, response: object) -> TurnProposal:
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
            derived_segments = derive_grounding(candidates[undelivered[0]].must_convey, proposal.segments)
            if derived_segments:
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
        anything it cannot already read in the player context.
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
            if speaker_id in npc_ids
        }

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
            # Cloudflare Browser Integrity Check rejects urllib's default bot-like
            # signature before this request can reach the Worker.
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
            ),
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
