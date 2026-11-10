"""Read-only probe: does handing the card to Reyes change reveal or exit eligibility?"""
from pathlib import Path
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_world_effects, world_for
from storygame.runtime.reveal_eligibility import explain_reveal
from storygame.runtime.validation import ProgressionValidator, unavailable_entity_ids
from storygame.story_package.loader import load_story_package

P = load_story_package(Path("data/stories/continuity-initiative"))
s = RuntimeState.bootstrap(P)
for f in ("patrol_on_scene", "patrol_in_house", "memory_card_recovered", "card_challenged",
          "kristin_marked_by_patrol", "officer_demanded_card", "patrol_return_pressure"):
    s.facts.assert_fact(Fact(predicate=f, subject="story", value="true"))
apply_world_effects(P, s.facts)
s.active_event_ids = set(getattr(s, "active_event_ids", set())) | {"SL-1A-B"}

def snapshot(label):
    w = world_for(P, s.facts)
    claim = next(k for k in P.knowledge.knowledge if k.id == "k_sl_1a_b_r1")
    el = explain_reveal(s, "player", claim)
    t = next(t for t in P.pacing.transitions if t.id == "t_1a_1b")
    v = ProgressionValidator(P)
    print(f"[{label}] card parent={w.parent('memory_card')!r}; read-card claim eligible={el.eligible} ({el.reason}); "
          f"deps_available={v.transition_dependencies_available(t, s.facts)}; "
          f"memory_card unavailable={'memory_card' in unavailable_entity_ids(P, s.facts)}; "
          f"lead_actionable asserted={Fact(predicate='michelle_lead_actionable', subject='story', value='true') in s.facts.asserted}")

snapshot("kept")
world = world_for(P, s.facts)
world.move("memory_card", "patrol_officer")
snapshot("handed to Reyes")
