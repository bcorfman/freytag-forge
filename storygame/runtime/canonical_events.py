"""Apply package-authored canonical events after a validated turn."""

from __future__ import annotations

from storygame.runtime.contracts import FactOperation, NarrationSegment
from storygame.runtime.facts import Fact


class CanonicalEventMixin:
    """Keep route-event application separate from turn orchestration."""

    def _apply_canonical_route_events(self) -> None:
        """Commit route-authored bridge/resolution facts once their conditions hold."""

        routes = self.state.package.storylet_routes
        events = (*routes.bridge_events, *routes.resolution_events)
        resolution_ids = {event.id for event in routes.resolution_events}
        while True:
            for event in events:
                if event.scene_id != self.state.current_scene_id or event.id in self.state.fired_event_ids:
                    continue
                if not event.activation.is_satisfied(self._true_facts(self.state.facts)):
                    continue
                if event.id in resolution_ids and not all(
                    storylet_id in self.state.fired_event_ids for storylet_id in event.realization_storylets
                ):
                    continue
                self._commit_canonical_event(event)
                break
            else:
                return

    def _commit_canonical_event(self, event) -> None:
        operations = tuple(
            FactOperation(
                operation=operation.op,
                fact=Fact(predicate=operation.fact_id, subject="story", value=str(operation.value).lower()),
            )
            for operation in event.operations
        )
        for operation in operations:
            self.state._apply_operation(self.state.facts, operation)
        self.state.fired_event_ids.add(event.id)

    def _apply_resolution_deadline_backstop(self) -> tuple[NarrationSegment, ...]:
        """Show and commit ready resolution events when their scene reaches its Deadline."""

        routes = self.state.package.storylet_routes
        events = tuple(event for event in routes.resolution_events if event.scene_id == self.state.current_scene_id)
        if not events:
            return ()
        window = next(
            window for window in self.state.package.pacing.scenes if window.scene_id == self.state.current_scene_id
        )
        turns_since_entry = self.state.turn_index - self.state.scene_entered_at_turn
        if turns_since_entry < window.handoff_after_turns:
            return ()

        segments: list[NarrationSegment] = []
        while True:
            for event in events:
                if event.id in self.state.fired_event_ids:
                    continue
                if not event.activation.is_satisfied(self._true_facts(self.state.facts)):
                    continue
                self._commit_canonical_event(event)
                self.state.fired_event_ids.update(event.realization_storylets)
                self.state.active_event_ids.difference_update(event.realization_storylets)
                segments.append(NarrationSegment(kind="narration", text=event.fallback_text or ""))
                break
            else:
                return tuple(segments)

    @staticmethod
    def _true_facts(facts) -> frozenset[str]:
        return frozenset(fact.predicate for fact in facts.asserted if str(fact.value).lower() == "true")
