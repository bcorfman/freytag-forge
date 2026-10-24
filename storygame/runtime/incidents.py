"""Pure helpers for package-declared incident outcomes."""

from __future__ import annotations

from storygame.story_package.models import Incident, IncidentOutcome


def resolved_incident_outcome(incident: Incident, facts) -> IncidentOutcome | None:
    """Return the first outcome whose advantages are all asserted as story truths."""

    true_facts = {
        fact.predicate for fact in facts.asserted if fact.subject == "story" and str(fact.value).lower() == "true"
    }
    return next((outcome for outcome in incident.outcomes if set(outcome.advantages) <= true_facts), None)
