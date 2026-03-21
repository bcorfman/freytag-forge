from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging

from storygame.engine.facts import active_story_goal, replace_fact_group, set_active_story_goal
from storygame.engine.state import Event, GameState
from storygame.llm.opening_coherence import cohere_opening_lines, item_labels_for_opening
from storygame.llm.output_editor import OutputEditor, build_output_editor
from storygame.llm.story_agents.agents import (
    DefaultStoryBootstrapAgent,
    DefaultStoryBootstrapCriticAgent,
    DefaultRoomPresentationAgent,
    DefaultStoryReplanAgent,
    RoomPresentationAgent,
    StoryBootstrapAgent,
    StoryBootstrapCriticAgent,
    StoryReplanAgent,
)
from storygame.story_canon import canonical_detective_name

_LOGGER = logging.getLogger(__name__)


class StoryDirector:
    def __init__(
        self,
        mode: str,
        output_editor: OutputEditor | None = None,
        story_bootstrap: StoryBootstrapAgent | None = None,
        story_bootstrap_critic: StoryBootstrapCriticAgent | None = None,
        story_architect=None,
        character_designer=None,
        plot_designer=None,
        narrator_opening=None,
        room_presentation: RoomPresentationAgent | None = None,
        story_replan: StoryReplanAgent | None = None,
    ) -> None:
        self._output_editor = build_output_editor(mode) if output_editor is None else output_editor
        self._story_bootstrap = DefaultStoryBootstrapAgent(mode) if story_bootstrap is None else story_bootstrap
        self._story_bootstrap_critic = (
            DefaultStoryBootstrapCriticAgent(mode) if story_bootstrap_critic is None else story_bootstrap_critic
        )
        self._room_presentation = (
            DefaultRoomPresentationAgent(mode) if room_presentation is None else room_presentation
        )
        self._story_replan = DefaultStoryReplanAgent(mode) if story_replan is None else story_replan
        self._ignored_legacy_components = any(
            component is not None for component in (story_architect, character_designer, plot_designer, narrator_opening)
        )

    def compose_opening(self, state: GameState) -> list[str]:
        return self._compose_opening_bootstrap(state)

    def _compose_opening_bootstrap(self, state: GameState) -> list[str]:
        bundle: dict[str, object] = {}
        bundle = self._story_bootstrap.run(state)
        critique = self._story_bootstrap_critic.run(state, bundle)
        bundle["bootstrap_critique"] = critique
        if str(critique.get("verdict", "")).strip().lower() != "accepted":
            raise RuntimeError(
                "Story bootstrap critique rejected plan: "
                + str(critique.get("continuity_summary", "")).strip()
            )
        self._apply_story_bundle(state, bundle)

        with ThreadPoolExecutor(max_workers=2) as executor:
            room_future = executor.submit(
                self._ensure_room_presentation_cache,
                state,
                bundle,
                {"contacts": list(bundle.get("contacts", []))},
                {
                    "assistant_name": str(bundle.get("assistant_name", "")),
                    "actionable_objective": str(bundle.get("actionable_objective", active_story_goal(state))),
                },
            )
            opening = [str(line).strip() for line in bundle.get("opening_paragraphs", ()) if str(line).strip()]
            if not opening:
                raise RuntimeError("Story bootstrap returned empty opening_paragraphs.")
            room_future.result()
        coherent_opening = cohere_opening_lines(
            opening,
            state.story_genre,
            str(bundle.get("protagonist_name", "")).strip(),
            str(bundle.get("assistant_name", "")).strip(),
            str(bundle.get("actionable_objective", active_story_goal(state))).strip(),
            item_labels_for_opening(tuple(state.world.items.keys())),
            tuple(str(contact.get("name", "")).strip() for contact in bundle.get("contacts", ()) if str(contact.get("name", "")).strip()),
        )
        return self._output_editor.review_opening(coherent_opening, active_story_goal(state))

    def _apply_story_bundle(self, state: GameState, bundle: dict[str, object]) -> None:
        contacts = list(bundle.get("contacts", []))
        protagonist_name = canonical_detective_name(state.story_genre, str(bundle.get("protagonist_name", "")).strip())
        opening_paragraphs = tuple(
            str(paragraph).strip() for paragraph in bundle.get("opening_paragraphs", ()) if str(paragraph).strip()
        )
        story_plan = {
            "protagonist_name": protagonist_name,
            "protagonist_background": str(bundle.get("protagonist_background", "")).strip(),
            "setup_paragraphs": opening_paragraphs,
            "expanded_outline": str(bundle.get("expanded_outline", "")).strip(),
            "story_beats": tuple(bundle.get("story_beats", ())),
            "villains": tuple(bundle.get("villains", ())),
            "timed_events": tuple(bundle.get("timed_events", ())),
            "clue_placements": tuple(bundle.get("clue_placements", ())),
            "hidden_threads": tuple(
                str(thread).strip() for thread in bundle.get("hidden_threads", ()) if str(thread).strip()
            ),
            "reveal_schedule": tuple(bundle.get("reveal_schedule", ())),
        }
        bundle["protagonist_name"] = protagonist_name
        goals = {
            "setup": str(bundle.get("actionable_objective", "")).strip(),
            "primary": str(bundle.get("primary_goal", "")).strip(),
            "secondary": tuple(
                str(goal).strip() for goal in bundle.get("secondary_goals", ()) if str(goal).strip()
            ),
        }
        state.world_package["llm_story_bundle"] = dict(bundle)
        state.world_package["story_plan"] = story_plan
        state.world_package["goals"] = goals
        state.world_package["story_cast"] = {"contacts": contacts}
        self._apply_story_bundle_facts(state, bundle, contacts, goals)
        self._apply_contacts_to_world(state, contacts, str(bundle.get("assistant_name", "")).strip())
        self._apply_clue_placements_to_world(state, list(bundle.get("clue_placements", ())))
        state.world_package["bootstrap_critique"] = dict(bundle.get("bootstrap_critique", {}))
        if goals["setup"]:
            state.active_goal = goals["setup"]
            set_active_story_goal(state, state.active_goal)

    def _apply_story_bundle_facts(
        self,
        state: GameState,
        bundle: dict[str, object],
        contacts: list[dict[str, object]],
        goals: dict[str, object],
    ) -> None:
        goal_facts: list[tuple[str, ...]] = []
        if str(goals.get("setup", "")).strip():
            goal_facts.append(("story_goal", "setup", str(goals["setup"]).strip()))
        if str(goals.get("primary", "")).strip():
            goal_facts.append(("story_goal", "primary", str(goals["primary"]).strip()))
        for goal in goals.get("secondary", ()):
            if str(goal).strip():
                goal_facts.append(("story_goal", "secondary", str(goal).strip()))
        replace_fact_group(state, "story_goal", tuple(goal_facts))

        profile_facts = []
        protagonist_name = str(bundle.get("protagonist_name", "")).strip()
        protagonist_background = str(bundle.get("protagonist_background", "")).strip()
        if protagonist_name:
            profile_facts.append(("player_name", protagonist_name))
        if protagonist_background:
            profile_facts.append(("player_background", protagonist_background))
        assistant_name = str(bundle.get("assistant_name", "")).strip()
        if assistant_name:
            profile_facts.append(("assistant_name", assistant_name))
        replace_fact_group(state, "player_name", tuple(fact for fact in profile_facts if fact[0] == "player_name"))
        replace_fact_group(
            state,
            "player_background",
            tuple(fact for fact in profile_facts if fact[0] == "player_background"),
        )
        replace_fact_group(state, "assistant_name", tuple(fact for fact in profile_facts if fact[0] == "assistant_name"))

        contact_role_facts: list[tuple[str, ...]] = []
        for contact in contacts:
            name = str(contact.get("name", "")).strip()
            role = str(contact.get("role", "")).strip()
            trait = str(contact.get("trait", "")).strip()
            if name and role:
                contact_role_facts.append(("npc_role", name, role))
                contact_role_facts.append(("npc_relationship", name, "player", role))
            if name and trait:
                contact_role_facts.append(("npc_contact_trait", name, trait))
        replace_fact_group(state, "npc_role", tuple(fact for fact in contact_role_facts if fact[0] == "npc_role"))
        replace_fact_group(
            state,
            "npc_relationship",
            tuple(fact for fact in contact_role_facts if fact[0] == "npc_relationship"),
        )
        replace_fact_group(
            state,
            "npc_contact_trait",
            tuple(fact for fact in contact_role_facts if fact[0] == "npc_contact_trait"),
        )

        villain_facts: list[tuple[str, ...]] = []
        for villain in bundle.get("villains", ()):
            if not isinstance(villain, dict):
                continue
            name = str(villain.get("name", "")).strip()
            if not name:
                continue
            villain_facts.extend(
                (
                    ("villain", name),
                    ("villain_motive", name, str(villain.get("motive", "")).strip()),
                    ("villain_means", name, str(villain.get("means", "")).strip()),
                    ("villain_opportunity", name, str(villain.get("opportunity", "")).strip()),
                )
            )
        replace_fact_group(state, "villain", tuple(fact for fact in villain_facts if fact[0] == "villain"))
        replace_fact_group(state, "villain_motive", tuple(fact for fact in villain_facts if fact[0] == "villain_motive"))
        replace_fact_group(state, "villain_means", tuple(fact for fact in villain_facts if fact[0] == "villain_means"))
        replace_fact_group(
            state,
            "villain_opportunity",
            tuple(fact for fact in villain_facts if fact[0] == "villain_opportunity"),
        )

        clue_facts: list[tuple[str, ...]] = []
        for entry in bundle.get("clue_placements", ()):
            if not isinstance(entry, dict):
                continue
            item_id = str(entry.get("item_id", "")).strip()
            room_id = str(entry.get("room_id", "")).strip()
            clue_text = str(entry.get("clue_text", "")).strip()
            hidden_reason = str(entry.get("hidden_reason", "")).strip()
            if item_id and clue_text:
                clue_facts.append(("clue_text", item_id, clue_text))
            if item_id and room_id:
                clue_facts.append(("clue_room", item_id, room_id))
            if item_id and hidden_reason:
                clue_facts.append(("clue_hidden_reason", item_id, hidden_reason))
        replace_fact_group(state, "clue_text", tuple(fact for fact in clue_facts if fact[0] == "clue_text"))
        replace_fact_group(state, "clue_room", tuple(fact for fact in clue_facts if fact[0] == "clue_room"))
        replace_fact_group(
            state,
            "clue_hidden_reason",
            tuple(fact for fact in clue_facts if fact[0] == "clue_hidden_reason"),
        )

        timed_event_facts: list[tuple[str, ...]] = []
        for event in bundle.get("timed_events", ()):
            if not isinstance(event, dict):
                continue
            event_id = str(event.get("event_id", "")).strip()
            summary = str(event.get("summary", "")).strip()
            min_turn = str(int(event.get("min_turn", 0)))
            location = str(event.get("location", "")).strip()
            if event_id and summary and location:
                timed_event_facts.append(("planned_event", event_id, summary, min_turn, location))
            for participant in event.get("participants", ()):
                if event_id and str(participant).strip():
                    timed_event_facts.append(("planned_event_participant", event_id, str(participant).strip()))
        replace_fact_group(state, "planned_event", tuple(fact for fact in timed_event_facts if fact[0] == "planned_event"))
        replace_fact_group(
            state,
            "planned_event_participant",
            tuple(fact for fact in timed_event_facts if fact[0] == "planned_event_participant"),
        )

        hidden_thread_facts = tuple(
            ("story_hidden_thread", str(thread).strip())
            for thread in bundle.get("hidden_threads", ())
            if str(thread).strip()
        )
        replace_fact_group(state, "story_hidden_thread", hidden_thread_facts)

        reveal_schedule_facts: list[tuple[str, ...]] = []
        for entry in bundle.get("reveal_schedule", ()):
            if not isinstance(entry, dict):
                continue
            thread_index = str(int(entry.get("thread_index", -1)))
            min_progress = str(float(entry.get("min_progress", 1.0)))
            if thread_index == "-1":
                continue
            reveal_schedule_facts.append(("story_reveal_schedule", thread_index, min_progress))
        replace_fact_group(state, "story_reveal_schedule", tuple(reveal_schedule_facts))

    def _apply_contacts_to_world(self, state: GameState, contacts: list[dict[str, object]], assistant_name: str) -> None:
        villains = {
            str(entry.get("name", "")).strip().lower(): dict(entry)
            for entry in state.world_package.get("story_plan", {}).get("villains", ())
            if isinstance(entry, dict)
        }
        contact_map = {
            str(contact.get("name", "")).strip().lower(): dict(contact)
            for contact in contacts
            if str(contact.get("name", "")).strip()
        }
        for npc in state.world.npcs.values():
            contact = contact_map.get(npc.name.strip().lower())
            villain = villains.get(npc.name.strip().lower())
            if contact:
                role = str(contact.get("role", "")).strip() or "contact"
                trait = str(contact.get("trait", "")).strip() or "measured"
                relation = "your assistant" if npc.name.strip().lower() == assistant_name.strip().lower() else role
                npc.identity = f"{relation}; {trait}"
                npc.description = f"{npc.name} serves as {relation} in the case and carries a {trait} demeanor."
                npc.dialogue = f"{npc.name} keeps the focus on {active_story_goal(state)}"
            if villain:
                motive = str(villain.get("motive", "")).strip()
                npc.identity = f"suspect with motive: {motive}" if motive else "suspect in the case"

    def _apply_clue_placements_to_world(self, state: GameState, placements: list[object]) -> None:
        valid_entries = [entry for entry in placements if isinstance(entry, dict)]
        if not valid_entries:
            return
        room_items = {room_id: list(room.item_ids) for room_id, room in state.world.rooms.items()}
        for entry in valid_entries:
            item_id = str(entry.get("item_id", "")).strip()
            room_id = str(entry.get("room_id", "")).strip()
            if item_id not in state.world.items or room_id not in state.world.rooms:
                continue
            for current_room_id, item_ids in room_items.items():
                if item_id in item_ids:
                    room_items[current_room_id] = [value for value in item_ids if value != item_id]
            room_items[room_id].append(item_id)
            item = state.world.items[item_id]
            item.clue_text = str(entry.get("clue_text", "")).strip() or item.clue_text
            hidden_reason = str(entry.get("hidden_reason", "")).strip()
            if hidden_reason:
                item.description = f"{item.description.rstrip('.')} Hidden because {hidden_reason.rstrip('.')}."
        for room_id, item_ids in room_items.items():
            deduped: list[str] = []
            for item_id in item_ids:
                if item_id not in deduped:
                    deduped.append(item_id)
            state.world.rooms[room_id].item_ids = tuple(deduped)

    def _ensure_room_presentation_cache(
        self,
        state: GameState,
        architect: dict[str, object],
        cast: dict[str, object],
        plan: dict[str, object],
    ) -> None:
        existing = state.world_package.get("room_presentation_cache", {})
        if all(room_id in existing for room_id in state.world.rooms):
            return
        try:
            generated = self._room_presentation.run(state, architect, cast, plan)
            state.world_package["room_presentation_cache"] = generated
        except RuntimeError:
            fallback = {
                room_id: {
                    "long": room.description,
                    "short": room.description.split(".")[0].strip() + ".",
                }
                for room_id, room in state.world.rooms.items()
            }
            state.world_package["room_presentation_cache"] = fallback

    def review_turn(self, state: GameState, lines: list[str], events: list[Event], debug: bool = False) -> list[str]:
        return self._output_editor.review_turn(list(lines), active_story_goal(state), state.turn_index, debug)

    def replan_if_needed(self, state: GameState) -> Event | None:
        if not state.player.flags.get("story_replan_required", False):
            return None
        disruption = dict(state.world_package.get("story_replan_context", {}))
        plan = self._story_replan.run(state, disruption)
        replan_scope = str(plan.get("replan_scope", disruption.get("replan_scope", "goal_change"))).strip().lower()
        new_goal = str(plan.get("new_active_goal", "")).strip()
        if replan_scope == "goal_change" and new_goal:
            state.active_goal = new_goal
            goals = dict(state.world_package.get("goals", {}))
            goals["primary"] = new_goal
            goals["setup"] = new_goal
            state.world_package["goals"] = goals
            set_active_story_goal(state, new_goal)
        state.world_package["story_replan_plan"] = dict(plan)
        state.player.flags["story_replan_required"] = False
        state.player.flags["story_replanned"] = True
        note = str(plan.get("note", "")).strip() or "The story shifts in response to your prior choice."
        return Event(
            type="story_replan",
            tags=("story", "replan"),
            message_key=note,
            turn_index=state.turn_index,
            metadata={
                "disruption": disruption,
                "plan": dict(plan),
            },
        )
