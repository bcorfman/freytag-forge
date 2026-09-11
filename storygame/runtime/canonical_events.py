"""Apply package-authored canonical events after a validated turn."""

from __future__ import annotations

from storygame.runtime.contracts import FactOperation
from storygame.runtime.facts import Fact


class CanonicalEventMixin:
    """Keep route-event application separate from turn orchestration."""

    def _apply_canonical_route_events(self) -> None:
        """Commit route-authored bridge/resolution facts once their conditions hold."""

        routes = self.state.package.storylet_routes
        events = (*routes.bridge_events, *routes.resolution_events)
        for event in events:
            if event.scene_id != self.state.current_scene_id or event.id in self.state.fired_event_ids:
                continue
            true_facts = frozenset(
                fact.predicate for fact in self.state.facts.asserted if str(fact.value).lower() == "true"
            )
            if not event.activation.is_satisfied(true_facts):
                continue
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
