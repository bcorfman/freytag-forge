# ruff: noqa: E501
"""Generate .plans/game-path-completion-matrix.md from the package (read-only).

Run from the repo root: uv run python .plans/game-path-completion-matrix-gen.py
"""

import hashlib
import subprocess
from pathlib import Path

from storygame.story_package.loader import load_story_package
from storygame.story_package.obligations import required_storylet_ids

ROOT = Path("data/stories/continuity-initiative")
P = load_story_package(ROOT)
sr = P.storylet_routes
required = required_storylet_ids(P)
sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
pkg_hash = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(ROOT.iterdir()) if p.is_file())).hexdigest()[:16]
tests_text = {p.name: p.read_text() for p in Path("tests").glob("*.py")}


def mentions(token: str) -> int:
    return sum(1 for text in tests_text.values() if token in text)


def preds(items):
    return "; ".join(f"{p.fact_id}={str(p.equals).lower()}" for p in items) or "-"


def ops(items):
    return "; ".join(f"{o.op} {o.fact_id}" for o in items) or "-"


know_by_real = {}
for k in P.knowledge.knowledge:
    if k.source.realization_id:
        know_by_real.setdefault(k.source.realization_id, []).append(k)
bridge_facts = {}
for e in sr.bridge_events:
    bridge_facts.setdefault(e.scene_id, set()).update(e.activation.all_facts_true, e.activation.any_of)
deliveries = {d.fact_id: d for d in P.deliveries}
issues = []

out = []
w = out.append
w("# Game-path coverage ledger (step 1)\n")
w(
    f"Generated from baseline `{sha}`, package files hash `{pkg_hash}` (first 16 hex of sha256 over the seven source files)."
)
w(
    "Generator: `.plans/game-path-completion-matrix-gen.py`. The 'Test files' columns count test files that mention the ID text."
)
w(
    "They show where to look, not that a journey covers the row. Journey IDs and live evidence are filled in by later steps.\n"
)
w(
    "Classes: **required** = in `required_storylet_ids` (resolution/bridge closure); **alternative** = storylet with more than one realization;"
)
w(
    "**observer-only** = knowledge audience is not player-visible public. Scene-entry items and fallback text are listed in sections C and D.\n"
)

w("## A. Scene timing (accepted scene-local turns)\n")
w("| Scene | Min | Nudge | Handoff | Pressure events (turn, id, conditions) |\n|---|---|---|---|---|")
for s in P.pacing.scenes:
    ev = "; ".join(
        f"{e.at_turn} {e.id}" + (f" if {preds(e.when)}" if e.when else "")
        for e in P.pacing.events
        if e.scene_id == s.scene_id
    )
    w(f"| {s.scene_id} | {s.min_turns} | {s.nudge_after_turns} | {s.handoff_after_turns} | {ev or '-'} |")

w("\n## B. Storylets and realizations\n")
w(
    "| Scene | Storylet | Windows e/t/l | Class | Activation | Realization | Operations | Helps transitions | Knowledge item(s) | Test files |\n|---|---|---|---|---|---|---|---|---|---|"
)
for st in sr.storylets:
    cls = ["required" if st.id in required else "optional"]
    if len(st.realizations) > 1:
        cls.append("alternative")
    for r in st.realizations:
        ks = know_by_real.get(r.id, [])
        if not ks:
            issues.append(f"Realization {r.id} has no knowledge item whose source.realization_id matches it.")
        else:
            kfacts = {e.fact_id for k in ks for e in k.establishes}
            rfacts = {o.fact_id for o in r.operations}
            if kfacts != rfacts:
                issues.append(
                    f"{r.id}: realization operations {sorted(rfacts)} differ from knowledge establishes {sorted(kfacts)} ({', '.join(k.id for k in ks)})."
                )
        kids = ", ".join(k.id for k in ks) or "NONE"
        obs = [k.id for k in ks if k.audience.kind != "public" or not k.audience.player_visible]
        c = list(cls) + (["observer-only"] if obs else [])
        w(
            f"| {st.scene_id} | {st.id} {st.title} | {st.earliest_turn}/{st.target_turn}/{st.latest_turn} | {', '.join(c)} | {preds(st.activation_conditions)} | {r.id} | {ops(r.operations)} | {', '.join(r.helps_transition_triggers) or '-'} | {kids} | {sum(mentions(k.id) for k in ks) if ks else 0} |"
        )

w("\n## C. Knowledge items\n")
w("| Item | Source | Scenes | Audience | Requires | Establishes | Test files |\n|---|---|---|---|---|---|---|")
for k in P.knowledge.knowledge:
    src = k.source.realization_id or k.source.canonical_event_id or k.source.kind
    aud = k.audience.kind + ("" if k.audience.player_visible else " (not player-visible)")
    w(
        f"| {k.id} | {src} | {','.join(k.available_in_scenes)} | {aud} | {preds(k.requires)} | {ops(k.establishes)} | {mentions(k.id)} |"
    )
    if not k.source.realization_id and not k.source.canonical_event_id and k.source.kind != "scene_entry":
        issues.append(f"Knowledge {k.id} has source kind {k.source.kind} with no realization or event id.")

w("\n## D. Bridge and resolution events\n")
w(
    "| Kind | Event | Scene | Activation | Operations | Realization storylets | Fallback text | Test files |\n|---|---|---|---|---|---|---|---|"
)
for kind, evs in (("bridge", sr.bridge_events), ("resolution", sr.resolution_events)):
    for e in evs:
        act = ", ".join(e.activation.all_facts_true) + (
            f" any_of({', '.join(e.activation.any_of)}) at_least {e.activation.at_least}" if e.activation.any_of else ""
        )
        w(
            f"| {kind} | {e.id} | {e.scene_id} | {act} | {ops(e.operations)} | {', '.join(e.realization_storylets)} | {'yes' if e.fallback_text else 'no'} | {mentions(e.id)} |"
        )

w("\n## E. Transitions and ending\n")
w("| Transition | From -> to | Priority | Triggers | Required dependencies |\n|---|---|---|---|---|")
for t in P.pacing.transitions:
    w(
        f"| {t.id} | {t.source_scene_id} -> {t.target_scene_id} | {t.priority} | {preds(t.triggers)} | {', '.join(t.required_dependencies) or '-'} |"
    )
w(
    f"\nEnding: scene {P.pacing.ending.scene_id}, requires {preds(P.pacing.ending.when)}. Budget {P.pacing.budget_seconds}s (authored 120 accepted turns; see plan)."
)

w("\n## F. Custody and deliveries (step-2 extension targets)\n")
w(
    "Rows here are where an acquisition or custody obligation exists: a transition `required_dependencies` item (an availability check, see `ProgressionValidator.transition_dependencies_available`), a delivery cost, or a world `fact_effects` move/reveal.\n"
)
w("| Fact / dependency | Where declared | Effect | Staged cue text | Cue guard now applies |\n|---|---|---|---|---|")
for t in P.pacing.transitions:
    for dep in t.required_dependencies:
        w(
            f"| {dep} | {t.id} required_dependencies | entity must not be unavailable (for example destroyed) when the exit fires; not a possession check | - | - |"
        )
for fact_id, effects in P.world.fact_effects.items():
    desc = "; ".join(
        ("move " + e.move + " -> " + str(e.parent)) if e.move else ("reveal " + e.reveal) if e.reveal else str(e)
        for e in effects
    )
    d = deliveries.get(fact_id)
    cost_hit = d and any(c.op == "assert" for c in d.costs)
    w(
        f"| {fact_id} | world.yaml fact_effects | {desc} | {'yes' if d and d.cue_text else 'no'} | {'cost' if cost_hit else '-'} |"
    )
for d in P.deliveries:
    costs = [c for c in d.costs if c.op == "assert"]
    if costs:
        w(
            f"| {d.fact_id} (delivery, {d.scene_id}) | handoffs.yaml costs | asserts {', '.join(c.fact_id for c in costs)} | {'yes' if d.cue_text else 'no'} | applies to cue |"
        )

w("\n## G. Package issues found by the generator\n")
if issues:
    for i in dict.fromkeys(issues):
        w(f"- {i}")
else:
    w("None.")
w(
    "\nObservation (not a package defect): three deliveries carry an assert-cost that is a penalty (`evidence_gap_*`), not an earlier step."
)
w(
    "The cue guard added in step 2 retires a cue when any assert-cost fact is true. Those penalty facts are asserted only by their own delivery's fallback,"
)
w(
    "which also establishes the delivery fact, so the guard cannot misfire on them today. A future cost that is a penalty set by another path would retire its cue wrongly."
)
w("\n## H. Reachability and journeys (offline, scripted)\n")
w(
    "`tests/test_game_path_journeys.py` plays one whole-game journey per player-visible realization, withholding its sibling alternatives, and a default journey."
)
w(
    "Result at the baseline plus the step-2 cue fix: every player-visible realization is offered on a legal route and reaches the resolution with no deadline backstop event within 120 accepted turns."
)
w("Scripted histories prove reachability and downstream state, not free-text usability.\n")
w("| Id | Realization or branch | Result |\n|---|---|---|")
w(
    "| N-1 | SL-1C-C-R2 (architects strategy) | Earned through 1C-C, but the 1C exit is forced: `bridge_1c_infiltration_needed` needs `national_detention_network_known`, which only R1 sets. |"
)
w(
    "| N-2 | SL-2B-B-R3 (Kristin was bait) | The 2B exit is forced: `bridge_2b_archive_crisis` needs two of three Brandon/Michelle facts and R3 supplies none, leaving at most `michelle_resistance_known`. |"
)
w(
    "| J-1 | SL-1A-D-R1 (remaining files) | Reachable only after SL-1A-B-R2 (recording first); chained journey passes. The default policy never plays D. |"
)
w(
    "| O-1 | SL-2C-A-R1 and both SL-2A-C rebecca_observes rows | Observer-only (not player-visible); not journeyed. Withholding the player-visible sibling of an observer row makes a required storylet unfinishable, which is a test artifact. |"
)
w(
    "\nNot yet covered: the eight combinations of the three evidence-gap facts, E-R1 versus E-R2 composed text and ending (step 5), the 3C live loop, and live free-text evidence."
)
w(
    "N-1 and N-2 are authoring decisions: either the alternative should also establish the bridge fact, or the bridge should accept the alternative. Story meaning changes start in plot.md."
)
Path(".plans/game-path-completion-matrix.md").write_text("\n".join(out) + "\n")
print("rows:", len(out), "issues:", len(set(issues)))
