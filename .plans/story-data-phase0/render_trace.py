"""Read-only prototype: a situation-centered trace for the Reyes/card demand.

Generated from the CURRENT story sources only. Nothing here is a source of truth.

Gap rules (docs/story-gap-guide.md): a gap is a
common-sense contradiction between prose and engine behavior, computed and quoted by
file and line. Checks: (1) custody: using an item requires holding it; (2) co-location:
and being where the device the prose names is; (3) no strand: with 1 and 2 applied,
every response to a pressure keeps an authored path to the exit. Run from the repo root:

  PYTHONPATH=.:packages/worldkeeper/src .venv/bin/python \
    .plans/story-data-phase0/render_trace.py . > .plans/story-data-phase0/situation-trace-reyes-card.md
"""

import sys
from pathlib import Path

import yaml

from storygame.runtime.facts import Fact
from storygame.runtime.reveal_eligibility import explain_reveal
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProgressionValidator, predicate_matches, unavailable_entity_ids
from storygame.runtime.world_model import apply_world_effects, world_for
from storygame.story_package.loader import load_story_package

repo = Path(sys.argv[1]).resolve()
root = repo / "data/stories/continuity-initiative"
Y = lambda n: yaml.safe_load((root / n).read_text())
routes, know, pac, world, handoffs = Y("storylet-routes.yaml"), Y("knowledge.yaml"), Y("pacing.yaml"), Y("world.yaml"), Y("handoffs.yaml")
plot = (root / "plot.md").read_text()
P = load_story_package(root)

facts = {f["id"]: f["purpose"] for f in know["facts"]}
claims = know["knowledge"]
events = {e["id"]: e for e in pac["events"]}
transitions = {t["id"]: t for t in pac["transitions"]}
storylets = {s["id"]: s for s in routes["storylets"]}
entities = {e["id"]: e for e in (*world["items"], *world["npcs"])}
claim_ids = {c["id"] for c in claims}

TRIGGER_EVENT, TRIGGER_TRANSITION = "officer_presses_1a", "t_1a_1b"


def walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


def ft(cs):
    return " and ".join(f"{c['fact_id']} is {str(c['equals']).lower()}" for c in cs) or "always"


def producers(fact, value=True):
    out = []
    for e in pac["events"]:
        if any(x.get("fact_id") == fact and x.get("equals", True) == value for x in e.get("effects", [])):
            out.append(f"pacing event {e['id']} (turn {e.get('at_turn')})")
    for c in claims:
        if any(x.get("fact_id") == fact and x.get("value", True) == value for x in c.get("establishes", [])):
            src = c.get("source", {})
            out.append(f"claim {c['id']} from {src.get('realization_id') or src.get('storylet_id') or src.get('kind')}")
    for d in handoffs.get("deliveries", []):
        if any(x.get("fact_id") == fact and x.get("value", True) == value for x in d.get("costs", [])):
            out.append(f"fallback handoff for {d['fact_id']} (scene {d['scene_id']})")
    return out


def consumers(fact):
    """Return (kind, text) pairs. kind: wording | gate | world."""
    out = []
    for e in pac["events"]:
        if any(c.get("fact_id") == fact for c in e.get("when", [])):
            out.append(("gate", f"pacing event {e['id']} waits on it"))
        for r in e.get("realizations", []):
            if any(c.get("fact_id") == fact for c in r.get("when", [])):
                out.append(("wording", f"pacing event {e['id']} (scene {e['scene_id']}) picks a line of wording by it"))
    for t in pac["transitions"]:
        if any(c.get("fact_id") == fact for c in t["triggers"]):
            out.append(("gate", f"transition {t['id']} requires it"))
    for s in routes["storylets"]:
        if any(c.get("fact_id") == fact for c in s["activation"].get("conditions", [])):
            out.append(("gate", f"storylet {s['id']} activation depends on it"))
    for c in claims:
        if any(r.get("fact_id") == fact for r in c.get("requires", [])):
            out.append(("gate", f"claim {c['id']} requires it"))
    for d in walk(world):
        if d.get("unlock_fact") == fact:
            out.append(("world", f"guard {d.get('id')} unlocks on it"))
        if d.get("id") == fact and d.get("on_assert"):
            out.append(("world", "world effect runs when it is asserted"))
    return out


def sentence_with(text, needle):
    for line in text.splitlines():
        if needle in line:
            i = line.index(needle)
            start = max(line.rfind(". ", 0, i) + 2, 0)
            end = line.find(". ", i)
            return line[start : end + 1 if end != -1 else None].strip()
    return None


def simulate(*, handed_over, lead_read):
    s = RuntimeState.bootstrap(P)
    for f in ("patrol_on_scene", "patrol_in_house", "memory_card_recovered", "card_challenged",
              "kristin_marked_by_patrol", "officer_demanded_card", "patrol_return_pressure"):
        s.facts.assert_fact(Fact(predicate=f, subject="story", value="true"))
    if lead_read:
        for f in ("michelle_warning_known", "continuity_initiative_known", "michelle_abduction_suspicion", "michelle_lead_actionable"):
            s.facts.assert_fact(Fact(predicate=f, subject="story", value="true"))
    apply_world_effects(P, s.facts)
    s.active_event_ids = set(getattr(s, "active_event_ids", set())) | {"SL-1A-B"}
    if handed_over:
        world_for(P, s.facts).move("memory_card", "patrol_officer")
    w = world_for(P, s.facts)
    claim = next(k for k in P.knowledge.knowledge if k.id == "k_sl_1a_b_r1")
    t = next(x for x in P.pacing.transitions if x.id == TRIGGER_TRANSITION)
    triggers_ok = all(predicate_matches(x, s.facts) for x in t.triggers)
    deps_ok = ProgressionValidator(P).transition_dependencies_available(t, s.facts)
    return {
        "holder": w.parent("memory_card"),
        "read": explain_reveal(s, "player", claim).reason,
        "lead": Fact(predicate="michelle_lead_actionable", subject="story", value="true") in s.facts.asserted,
        "exit": triggers_ok and deps_ok,
    }


def yn(b):
    return "yes" if b else "no"


def cite(fname, needle):
    """Return 'file:line' for the first line of a story source containing needle. Raises if absent,
    so a quote in the gaps section can never be one the sources do not contain."""
    for n, line in enumerate((root / fname).read_text().splitlines(), 1):
        if needle in line:
            return f"{fname}:{n}"
    raise SystemExit(f"evidence not found in {fname}: {needle!r}")


def quote(fname, needle):
    return f"`{cite(fname, needle)}`: “{needle}”"


def after_departure(*, handed_over, lead_read):
    """Row A-D states, then the patrol leaves (patrol_departed) and its world effect runs."""
    s = RuntimeState.bootstrap(P)
    for f in ("patrol_on_scene", "patrol_in_house", "memory_card_recovered", "card_challenged",
              "kristin_marked_by_patrol", "officer_demanded_card"):
        s.facts.assert_fact(Fact(predicate=f, subject="story", value="true"))
    if lead_read:
        for f in ("michelle_warning_known", "continuity_initiative_known", "michelle_abduction_suspicion", "michelle_lead_actionable"):
            s.facts.assert_fact(Fact(predicate=f, subject="story", value="true"))
    apply_world_effects(P, s.facts)
    s.active_event_ids = set(getattr(s, "active_event_ids", set())) | {"SL-1A-B"}
    before = world_for(P, s.facts)
    kristin_at, laptop_at = before.parent("kristin"), before.parent("kristin_laptop")
    if handed_over:
        before.move("memory_card", "patrol_officer")
    for f, v in (("patrol_departed", "true"), ("patrol_in_house", "false"), ("patrol_on_scene", "false"),
                 ("patrol_return_pressure", "true")):
        s.facts.assert_fact(Fact(predicate=f, subject="story", value=v))
    apply_world_effects(P, s.facts)
    w = world_for(P, s.facts)
    t = next(x for x in P.pacing.transitions if x.id == TRIGGER_TRANSITION)
    claim = next(k for k in P.knowledge.knowledge if k.id == "k_sl_1a_b_r1")
    return {
        "kristin_at": kristin_at, "laptop_at": laptop_at,
        "card_holder": w.parent("memory_card"), "officer_at": w.parent("patrol_officer"),
        "read": explain_reveal(s, "player", claim).reason,
        "exit": all(predicate_matches(x, s.facts) for x in t.triggers) and ProgressionValidator(P).transition_dependencies_available(t, s.facts),
    }


ev = events[TRIGGER_EVENT]
L = []
L += [
    "# Situation trace: Reyes demands the recovered memory card (scene 1A)",
    "",
    "Generated from the current story files. Read-only; edit the sources, not this page.",
    "Each section answers one question: **what is happening, where does it lead, what does the next scene need, what can Kristin do, and where the story does not hold together.**",
    "Gaps (section 5) are places where the story contradicts itself or common sense; each is computed from the sources and quotes them with file and line.",
    "",
    "## 1. The situation",
    "",
    f"- Pacing event `{ev['id']}` fires at turn {ev['at_turn']} when: {ft(ev['when'])}.",
]
for c in ev["when"]:
    L.append(f"  - `{c['fact_id']}` ({facts.get(c['fact_id'], '?')}) comes from: " + "; ".join(producers(c["fact_id"], c["equals"])))
L += [
    f"- It sets: {ft(ev['effects'])}.",
    f"- Reyes's line: “{ev['realizations'][0]['text']}”",
    f"- Reyes in the story files: {entities['patrol_officer'].get('narrator_bio')}",
    "",
    "## 2. Where the demand leads",
    "",
]
dead_end = True
for e in ev["effects"]:
    cs = consumers(e["fact_id"])
    L.append(f"`{e['fact_id']}` is read by:")
    for kind, text in cs:
        L.append(f"- {text} [{kind}]")
        dead_end &= kind == "wording"
    if not cs:
        L.append("- nothing")
L += [
    "",
    "Nothing reads it except a line of wording." if dead_end else "It feeds more than wording.",
    "",
    "## 3. What Kristin needs to leave 1A",
    "",
    f"Transition `{TRIGGER_TRANSITION}` needs all of:",
    "",
    "| Needs | Meaning | Produced by |",
    "| --- | --- | --- |",
]
t = transitions[TRIGGER_TRANSITION]
for c in t["triggers"]:
    L.append(f"| `{c['fact_id']}` | {facts.get(c['fact_id'], '?')} | " + "; ".join(producers(c["fact_id"], c["equals"])) + " |")
card = entities["memory_card"]
card_can_fail = bool(card.get("unavailable") or card.get("axes"))
L += [
    "",
    f"It also lists `{t['required_dependencies'][0]}` as a required dependency.",
    "",
    "### What the story says, next to what the engine checks",
    "",
    "| The story says | The engine checks |",
    "| --- | --- |",
]
s1 = sentence_with(plot, "takes the card out to her truck")
s2 = storylets["SL-1A-D"]["pressure_role"].replace("\n", " ")
s3 = sentence_with(plot, "suspicion follows her out")
r1 = next(c for c in claims if c["id"] == "k_sl_1a_b_r1")
read_check = (
    f"Reading the files needs: {ft(r1.get('requires', []))}"
    + (f"; and being in the same area as {r1['reach_entity_ids']}" if r1.get("reach_entity_ids") else "; it names no thing she must be near")
    + ". It does not check who holds the card."
)
L += [
    f"| “{s1}” (plot 1A.2) | {read_check} |",
    f"| “… {s2[s2.find('let her read'):]}” (SL-1A-D) | Same check as above. |",
    f"| The exit lists `memory_card` as a dependency | Passes unless the card is destroyed or incapacitated" + (f" or on a declared unavailable pole; stand-in: {card.get('fallback_ids')}" if card_can_fail else f". The card has no unavailable state, so this can fail only if it is destroyed; stand-in: {card.get('fallback_ids')}") + ". It does not check who holds it. |",
    f"| “{s3}” (plot 1A.4) | The mark (`kristin_marked_by_patrol`) is set when the card is recovered in front of an officer, not by the demand or by any answer to it. |",
    "",
    "## 4. If Kristin answers the demand",
    "",
    "Responses below are **inference, not canon**. Rows A–D are run through the real engine; the rest have no authored mechanics.",
    "",
    "| Response | Who holds the card | Lead already read? | Can she still read the card's files? | Does she have the lead? | Can she leave 1A (once the patrol is due back)? |",
    "| --- | --- | --- | --- | --- | --- |",
]
rows = []
for label, ho, lr in (
    ("A. Keeps it (stalls, refuses, or walks out with it)", False, False),
    ("B. Keeps it", False, True),
    ("C. Hands it over", True, False),
    ("D. Hands it over", True, True),
):
    r = simulate(handed_over=ho, lead_read=lr)
    rows.append((label, ho, lr, r))
    L.append(f"| {label} | {r['holder']} | {yn(lr)} | {'yes' if r['read'] == 'eligible' else 'no: ' + r['read']} | {yn(r['lead'])} | {yn(r['exit'])} |")
L += [
    "| E. Runs | not simulated | | | | no authored mechanics |",
    "| F. Resists or escalates (taser, gunfire) | not simulated | | | | no authored mechanics; the story files never say Reyes is armed |",
    "",
    "Read rows C and D together. With the card in Reyes's hands she may still read its files (C), and once she has the lead the exit opens exactly as when she kept the card (D matches B). The engine cannot tell reading-then-surrendering from surrendering-then-reading.",
    "",
]
L += ["## 5. Story gaps", "",
      "Each gap below is **computed**: it appears only if its check fails against the current sources, and every quote is located by file and line. Fix the source and the gap disappears.", ""]
gaps = []

# Gap 1: custody continuity after surrender
kept, gave = after_departure(handed_over=False, lead_read=False), after_departure(handed_over=True, lead_read=False)
gave_lead = after_departure(handed_over=True, lead_read=True)
regain = [f"`{d['id']}` moves it to `{m['parent']}`" for d in walk(world) if d.get("id") for m in d.get("on_assert", []) if isinstance(m, dict) and m.get("move") == "memory_card"]
regain_fact_ids = [d["id"] for d in walk(world) if d.get("id") for m in d.get("on_assert", []) if isinstance(m, dict) and m.get("move") == "memory_card"]
regain_after_loss_exists = any(producers(f, False) for f in regain_fact_ids)
if gave["card_holder"] != "kristin" and gave["read"] == "eligible" and gave_lead["exit"]:
    gaps.append((
        "A surrendered card leaves with Reyes, but Kristin can still read it and leave.",
        "She can use the card only while she holds it. Losing it should either cost her something or send her after it; as written it does neither, so surrender is a dead end, not pressure.",
        [quote("world.yaml", "- {move: patrol_officer, parent: patrol_staging}"),
         quote("plot.md", "item_ids: [memory_card, transit_card"),
         "`t_1a_1b` lists `memory_card` as a required dependency (section 3)."],
        [f"After she hands it over and the patrol leaves: card is held by `{gave['card_holder']}`, who is in `{gave['officer_at']}`; Kristin is in `{gave['kristin_at']}`.",
         f"She can still read the files: `{gave['read']}` (kept-card case: `{kept['read']}`).",
         f"With the lead already read, `t_1a_1b` opens: {yn(gave_lead['exit'])}. Its `memory_card` dependency " + ("can fail only if the card is destroyed, not if someone else holds it." if not card_can_fail else "can also fail on a declared unavailable state, but not on who holds it."),
         f"Ways the card can return to Kristin: {len(regain)} authored effect(s) ({'; '.join(regain)}); `memory_card_recovered` is already true and nothing sets it false, so none can fire again."]))

# Gap 2: where she reads
r1_entities = set(r1.get("relevance", {}).get("entity_ids", [])) | set(r1.get("entity_ids", []))
if "kristin_laptop" in r1_entities and not r1.get("reach_entity_ids") and kept["read"] == "eligible" and kept["laptop_at"] != kept["kristin_at"]:
    gaps.append((
        "She reads the card in the kitchen with no laptop; the story sends her to the truck.",
        "She can read the card only where the laptop is: in the truck, or wherever she carries the laptop. Nothing in the model ties the reading to the laptop's place.",
        [quote("plot.md", "She takes the card out to her truck and opens it on her laptop."),
         quote("knowledge.yaml", "Her laptop is still out in her truck."),
         quote("plot.md", "on the passenger seat of Kristin's truck")],
        [f"Kristin is in `{kept['kristin_at']}`; the laptop is in `{kept['laptop_at']}`.",
         f"Claim `k_sl_1a_b_r1` lists `kristin_laptop` as relevant but sets no `reach_entity_ids` (needs: {ft(r1.get('requires', []))}).",
         f"Engine verdict on reading the card from the kitchen, with Reyes in the house and the demand outstanding: `{kept['read']}`."]))

# Gap 3: with G1 and G2 applied, the demand is a dead end. Pressure may cost; it may never strand the story.
lead_producers = producers("michelle_lead_actionable")
lead_fallbacks = [x for x in lead_producers if x.startswith("fallback")]
if gaps and not regain_after_loss_exists and not lead_fallbacks:
    # Hypothetical rule from G1/G2: she can read only while she holds the card. Re-run the four situations.
    hypo = []
    for label, ho, lr in (("Keeps the card, lead unread", False, False), ("Hands it over, lead unread", True, False),
                          ("Hands it over, lead already read", True, True)):
        r = after_departure(handed_over=ho, lead_read=lr)
        can_read = r["card_holder"] == "kristin"
        has_lead = lr or can_read
        hypo.append((label, can_read, has_lead))
    stranded = [h for h in hypo if not h[2]]
    challenged_by = "; ".join(producers("card_challenged"))
    gaps.append((
        "If she must hold the card to read it, Reyes taking the card strands the story.",
        "Story pressure can cost Kristin something, but it must never leave her with no way forward. Every pressure needs a plausible fallback.",
        [quote("plot.md", "If she takes it while he is watching, he challenges her"),
         quote("pacing.yaml", "Let's see it, ma'am. Right now."),
         quote("knowledge.yaml", "Her laptop is still out in her truck.")],
        [f"The challenge comes the moment she takes the card in front of him ({challenged_by}), so it comes before she can reach the laptop and read anything.",
         "Both producers of the lead are card-reading acts: " + "; ".join(lead_producers) + ".",
         "Fallbacks that produce the lead: " + (", ".join(lead_fallbacks) if lead_fallbacks else "none") + f" (the one handoff nearby only sets `memory_card_recovered`, which is already true).",
         "No authored effect returns the card to her once Reyes has it (G1).",
         "With the G1 and G2 rule applied, can she read, does she have the lead: " + "; ".join(f"{h[0]} → read {yn(h[1])}, lead {yn(h[2])}" for h in hypo) + ".",
         f"Stranded situations: {len(stranded)} ({', '.join(h[0] for h in stranded)}). From there `t_1a_1b` can never open.",
         "Today the engine hides this, because it lets her read a card she gave away. Fixing G1 and G2 without a fallback turns the demand into an unwinnable state."]))

if not gaps:
    L.append("No gaps found by the current checks.")
for i, (title, rule, story, engine) in enumerate(gaps, 1):
    L += [f"### G{i}. {title}", "", f"- **Common sense:** {rule}", "- **The story says:**"]
    L += [f"  - {x}" for x in story]
    L += ["- **The engine shows:**"]
    L += [f"  - {x}" for x in engine]
    L.append("")
print("\n".join(L))
