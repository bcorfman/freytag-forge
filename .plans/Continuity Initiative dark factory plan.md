# Continuity Initiative: dark factory plan

Nov 15, 2026 · @Brandon Corfman

## Bottom line

Build the factory in three steps, in this order, because each one removes a reason you are still in the loop.

1. **One story source, wording written once.** Finish the D1 compiler first, with matcher lists written out and parity on every scene. That alone gives one owner per fact, effects stated once, tests that look wording up by record ID, and a beat change that is one edit by record ID. Then add a name lexicon as a second pass, only where the measurements show phrases repeat (the noun-phrase scenes, 1A to 2C). It is not the foundation of step 1, and it does not help the large synonym lists in 3A to 3C.
2. **World model inside the loop.** Before any prose is written for a scene, a free check lists the state the scene depends on and compares it with what Worldkeeper can represent. Gaps become Worldkeeper tickets first. This replaces the unplanned fork you have hit three times.
3. **A deterministic line with no LLM orchestrator session.** A small Python state machine drives Ringer. Models are called only at fixed stations with small packets: Opus for planning and replanning under a hard call cap, Sonnet for specs, prose and triage, Luna for wiring and code, Jev for judging. Free checks always run before billed ones.

Your work ends before the factory starts. Pre-flight is setting the budget and the spend caps; there is no manual planning session. After start you write and check nothing until the game is delivered. The only interruption is a circuit breaker: a factory error or a spend loop.

One change to your tiering: canon prose is written by the expensive model, not Luna. The whole authored text is small, and every player reads it. Wiring, tests and code stay cheap.

This plan is based on reading `main` at `eac9d666` (PR #766, 2026-11-14). I did not run the suite or play the game.

## What the repo shows today

Worker capacity is not the bottleneck. Four things in the repo are, and each maps to one step of this plan.

| What the repo shows | Evidence | Fixed by |
| --- | --- | --- |
| Story facts and wording have several owners | 121 facts defined in both routes and knowledge, all 176 listed again in `world.yaml`, 24 already drifted; 96 of 112 sourced claims restate their route's effects and 16 are subsets (recounted 2026-11-16 in `story-data-schema-contract.md`; the redesign plan's earlier "87 of 99" is stale) | Step 1 |
| Tests are tied to wording | 67 authored sentences copied into 36 test files; 43 test files patch source strings; a rename fails four tests | Step 1 |
| World-model gaps surface late, in play | Stage 7 blind run: 84 turns, 30 stuck, 2B forced after the narrator invented an undeclared door; the Reyes card custody gap; 2C costs set and never read | Step 2 |
| Every fix is a bespoke experiment that waits on you | 57 run folders and about 1,600 files under `scripts/ringer/`, about 130 plan files, a hand-written preregistration per probe, and status lines such as "waiting for Brandon's two edits" | Step 3 |

Much of the factory already exists as loose parts. The scripted provider, stall-exit audit, gap rules, branch report, impact report, `bench prompt`, the blind player and the Jev judge are all built. What is missing is a fixed order, pass rules a machine can apply, and a loop that does not need a chat session to hold its state.

The D1 decision is the right base. Scene blocks compile to the existing `StoryPackage`, so the engine, loader checks and most tests keep working. The 1A draft still repeats one noun phrase across `purpose`, `intent`, `says`, `text`, `aliases`, `leak_terms`, `must_convey` and `action_evidence`. Step 1 goes after that.

## Step 1: one story source, wording written once

Step 1 has two passes, and they have separate gates.

**Pass 1: the D1 compiler with explicit lists.** Matcher lists (`action_evidence`, `must_convey`, `leak_terms`, `aliases`) are written out in the scene file as they are today. Fact ownership, claim effects, test lookup by record ID and the story CLI all work without any derivation. The gate is an empty parity diff per scene. This pass does not depend on the lexicon, so a lexicon problem cannot hold up the migration.

**Pass 2: a name lexicon, scoped to where it pays.** Every entity and concept declares its names once, and the compiler expands them wherever today's files repeat them. The sample in "Where the lexicon pays" below says where that is. In the 1A draft, the card's names appear in the placement, nine `leak_terms`, two `must_convey` groups, two `action_evidence` groups, `aliases`, and three sentences that say the same thing. With a lexicon the reveal shrinks to roughly this:

```yaml
entities:
  memory_card:
    names: [memory card, card, "Michelle's card"]
    hidden_names: [hidden card, hidden memory card]   # guarded until revealed
  michelle_drawer:
    names: [drawer, KMS drawer, workstation drawer]

reveals:
  - id: find_card
    earned_by: [look_closely, under, michelle_drawer]   # slots, not word lists
    conveys: [memory_card, taped, {under: michelle_drawer}, {owner: michelle}]
    variants:
      quiet:
        when: {patrol_in_house: false}
        commits: {memory_card_recovered: true}
        text: "{find_lead} Her laptop is still out in her truck."
```

Pass 2 derivation rules, all explicit and all overridable with `add:` and `drop:`. The lexicon has three sections: **entities** (names and aliases), **concepts** (named phrases that are not world things, such as `dead drop`, `damaged recording`), and **verb classes** added by the story to the engine's own. An entity-only lexicon would leave half of 1A's matcher words typed by hand.

- `action_evidence` comes from the slots: a verb class the matcher already has, a position class, and the entity's names.
- `must_convey` comes from `conveys`, expanded through the lexicon.
- `leak_terms` come from the hidden names of every entity the reveal uncovers, plus the committed fact's key phrase.
- ~~`purpose`, `intent` and `says` collapse into one sentence per variant.~~ **Removed 2026-11-16 (Brandon).** `intent` equals `says` in only 10 of 100 claims; they are different sentences by design (a writer's note and what the player now knows), so deriving one from the other changes 90 compiled strings. A merge, if wanted, is a reviewed prose edit per scene later.
- `examples` stay, but as a separate test file per scene, so the scene file stays readable.

**Gates.** Pass 1 uses the parity gate you already planned: the compiled package must equal the legacy-loaded one, shown as a semantic diff, with an empty diff the exit. Pass 2 runs one scene at a time, after that scene has parity. A derived list either reproduces the explicit list exactly, or the difference is listed and reviewed as an override, a representation change, or a real bug in today's data. A field where more than a third of entries need `add:` or `drop:` stays explicit. Where a derivation shortens a list on purpose (for example, dropping verbs the engine's synonym class already admits), the compiler expands it back to the full list, so the compiled package does not change and matching behavior stays what was tuned in live play.

### Where the lexicon pays

Measured 2026-11-16 on the loaded package (`.plans/story-data-phase0/lexicon_derivable.py` and the sample table in the status note below). The matcher data is two different kinds of thing:

- **Noun-phrase scenes, 1A to 2C (and partly 3A).** Short lists that name things and concepts. 46% to 68% of phrase occurrences repeat across claims or fields, so a lexicon removes real repetition. 1A is the most repetitive scene, so its saving is the best case, not the average.
- **Broad-action scenes, 3A to 3C.** 3B has 563 `action_evidence` words across 11 claims and no `must_convey` or `leak_terms`; 3C has 502 across 17. Each claim lists dozens of ways to do one thing. Sibling claims share almost nothing (3B mean pairwise overlap 0.01), and only 16% to 22% of occurrences repeat. A lexicon does not help here. The one mechanical saving is plural twins: about 13% of all `action_evidence` entries (24% in 3B) are the plural or singular of another entry in the same group, which the matcher does not fold for phrases. Whether to derive those is a pass-2 choice with the same expand-back rule.

So pass 2 starts on 1A to 2C. 3A to 3C stay explicit unless the plural-twin derivation is taken, and it needs its own parity check.

### How this becomes factory work

- **Conversion is mechanical, so it is a swarm job.** After 1A passes parity, the other eight scenes convert in parallel, one Luna worker per scene, check equals parity diff empty.
- **Decouple the tests the same way.** One worker per test file replaces copied prose with a lookup by record ID. The check is the suite plus the existing `copied_prose.py` audit reporting zero.
- **Give workers a story CLI instead of grep.** `story show <id>`, `story set <id>.<field>`, `story rename <id>`, `story impact <id>` (the impact report already exists). A worker edits one record by ID and never loads a 176 KB file. For story data this replaces the knowledge graph. Keep Serena for engine and Worldkeeper code.
- **Generate the reading view.** The situation trace you accepted becomes the per-scene script: prose in order, with wiring folded away. You read that, not YAML.

No time box and no fallback format. The nine files are not coming back. If 1A parity stalls, the ordinary escalation applies (Sonnet rewrite, Opus refresh of the schema decision, set aside and return with the accumulated evidence); the parity diff stays the gate and the work continues until it is empty.

## Step 2: world model inside the factory loop

The world model gets its own station ahead of writing, and its own lane in triage, so a gap costs a ticket and not a fork in the road.

### Before a scene is written: the world-need check

The planner's scene contract lists every piece of state the scene relies on, in the four relations your plan already names: **hold, know, reach, exist**, plus hidden, seated, companion and any state axis. A free script then answers three questions per item:

1. Can Worldkeeper represent it today (kind, relation, axis)?
2. Does something earlier in the story produce it (the `no_producer` lookup)?
3. Does something later read it (the `unread_effect` lookup, narrowed to incident costs and advantages as your plan recommends)?

A "no" on question 1 opens a Worldkeeper ticket. It is built first, as a `World` method with its test in `packages/worldkeeper/tests/`, per your existing boundary rule. A "no" on 2 or 3 goes back to the planner as a story hole. No prose is written until the list is clean. This generalizes the one bookmark in `world-model.md`: declare an axis only when a story depends on it.

### After a scene is written: free continuity gates

All of these exist or nearly exist, cost nothing to run, and run on every change:

- **Gap rules as a delta gate.** Custody, co-location, no-strand, no-producer. Your D3 says rule results never block a build, and CI stays that way. The factory adds one rule for itself: a factory change may not add a new rule result against the baseline.
- **Carry matrix.** For each scene transition, enumerate the entry states (ledger facts times custody) and run the scripted stall and journey prefixes. You did this by hand for 2A to 3B and it found the 2B stuck state.
- **Branch report on every incident,** with one mechanical test: the next scene's entry variant must be selected by a fact the branch sets. That is the 2C-to-3A finding turned into a check.
- **Scene-versus-guard lint.** Fail if any leak term appears in narrator-visible text of the same scene before it is earned. The 2A "cooling fault" defect took five live rounds to find and is a string comparison.
- **Undeclared-noun lint.** Every multi-word noun in authored prose resolves in the lexicon or is listed as an incidental prop. The invented 2B door is the case this protects.

### In live play: triage routes to the right layer

Each failed playtest turn is classified into one of four classes: story data, world model, narrator prompt, engine. Jev answers the per-object fact questions it is good at (did the phone move, who holds the card), and code compares before and after lists. World-model failures open a Worldkeeper ticket with a failing test, never a story patch.

One escalation rule replaces the forks: **three failures of the same class in one scene stop story work on that scene and send one packet to the planner.** The engine change is then planned once, not discovered across weeks.

## Step 3: the factory line

The orchestrator is a Python state machine, not a model session. It reads a ticket queue from disk, generates Ringer manifests from templates, applies pass rules, and calls a model only at the stations below.

&#91;embedded content: factory line · 8 stations, 1 decision, 1 loop\]

A failed playtest loops back through triage to the writing station; nothing reaches a billed playtest without passing the free gates.

| Station | Who | Input packet | Passes when |
| --- | --- | --- | --- |
| 0. Act contracts, at start | Opus at medium effort, headless through Claude Code | Outline, scene rules, character list and contract template | Contract lint passes: every scene has beats, clock, delay costs, bond beats and world needs |
| 1. Contract refresh, only on escalation | Opus at medium effort, capped | One scene's contract and the failing evidence | Contract lint passes |
| 2. World-need check | Script, then Luna for Worldkeeper tickets | Contract's state list | Every item representable, produced and read |
| 3. Prose | Sonnet; Opus trialled on the tentpole passages, five candidates each | One scene's contract and character cards | Two or three candidates per passage; pairwise pick by the judge |
| 4. Wiring | Luna through the story CLI | Scene file, contract | Compiles; shape and integrity checks pass |
| 5. Free gates | Scripts | Compiled package | Gap-rule delta empty, no stuck state in the carry matrix, lints clean, quick suite and Ruff green |
| 6. Prompt snapshot | `bench prompt` | Changed scene | Payload diff limited to intended lines |
| 7. Live playtest | Blind player, Cloudflare narrator, Jev | Scene with a scripted prefix | Holdout scenarios met, zero stuck turns |
| 8. Triage | Script, Sonnet only for unclear cases | Failing turns only | Routed to a class; the escalation ladder below takes it from there |
| 9. Deliver | CI, staging, hosted E2E | Merged SHA | Green, every target met; the staged build is the delivery |

What makes it dark:

- **Holdout scenarios.** The contract's acceptance scenarios live outside every worker's `ownership` list. Workers never see them, so they cannot write to the test. This extends your rule that player actions are not generated from the matcher vocabulary they test.
- **Checks from a library, not written per run.** A dozen parameterized checks replace the hand-written check scripts. Use Ringer's `--baseline` so a broken check is caught before tokens are spent, and its lint for checks that cannot fail.
- **Preregistration as data.** Arms, sample size, keep rule and stop rule go in a small JSON file the state machine enforces. The discipline stays; the 100 KB plan files stop.
- **State on disk.** `factory/state.json` and the ticket queue replace "Resume here" sections. Any model call starts cold with only its packet.
- **Loop caps.** Three attempts per ticket, a token budget per ticket, a daily spend cap. A ticket that hits its cap climbs the escalation ladder below; it does not wait for you.

On review: Ringer's own README says a green check is not proof of semantic correctness and recommends [keeping orchestrator patch review mandatory](https://github.com/NateBJones-Projects/ringer). For story data the parity and scenario gates stand in for review. For engine and Worldkeeper code, add a fresh-context reviewer that sees only the diff and the ticket, and keep the 90 percent coverage gate.

### Keeping the graders honest

A loop that retries until its checks pass will optimize against the checks. These rules come from the loop-engineering and eval-integrity chapters of the [AI System Design Guide](https://github.com/ombharatiya/ai-system-design-guide), applied to this factory.

- **Verdicts, not reasons.** Test failures, exit codes and compile errors go back to the worker in full. A judge's reasoning and the text of a holdout scenario never do; the worker gets pass or fail plus the failing transcript. The guide cites a study where detailed rejections roughly doubled evaluator evasion.
- **Holdouts live outside the repository.** A worker with git can read history. Scenarios and judge prompts sit in a separate repository that only the playtest runner can read, and failure reports carry hashes.
- **Producer and grader come from different model families.** Luna fixes, so Luna does not write the scenarios. Claude writes prose, so a non-Claude model judges it.
- **Canary tickets.** A few tickets with no valid solution run through the line. A pass on one is a harness bug and trips a breaker.
- **The harness is frozen.** Gates, lints, judge prompts, caps, the allowlist and the protected-character list are outside every worker's ownership. A diff that touches one stops the factory.
- **Evidence from the executor.** Pass and fail come from Ringer's check exit codes and engine state, never from a worker's own report.
- **Noise-corrected gates.** Rate-based gates use the judge's measured error rates on the labelled set and pass on the lower bound, not the raw score. Stuck-turn detection is computed from engine state, with no judge involved.
- **Every replicate, not any replicate.** Delivery requires each holdout to pass in all runs of the final sample.
- **Budgets enforced outside the agents.** Caps live in the state machine and the Cloudflare gateway, with a rate-of-spend breaker beside the totals. Merge and deploy steps carry idempotency keys so a restart cannot repeat them.

### Which model does what

Sonnet is the right level for most judgment work here, and Opus is used in a few narrow places where a wrong early decision is expensive and the output is small. Both run headless through Claude Code on one subscription, so no step needs VS Code.

| Role | Model | Why |
| --- | --- | --- |
| Act contracts at start, scene-contract refresh, three-strikes replanning | Opus at medium | Few calls, small output, and everything downstream depends on them |
| Compiler and lexicon schema, during the build | Opus at medium | A schema mistake repeats across nine scenes |
| Slice specs, Ringer manifests, routine triage, holdout scenarios | Sonnet at high | Well-scoped work that is checked afterward; one independent index shows Sonnet falling off faster than Opus below high effort |
| Diff review on engine and Worldkeeper | Opus for those two, Sonnet elsewhere | High-risk changes get the deeper reviewer |
| Reunion, sacrifice and act-closing passages | Opus trialled against Sonnet | A handful of passages every player reads; the pairwise judge keeps whichever wins |
| Other canon prose and character cards | Sonnet | Volume is small and the judge picks among candidates |
| Pairwise prose judge | A mid-tier OpenAI model through Codex, if your plan includes one | A different family from the prose writer; a handful of calls |
| Wiring, test writing, scene conversion | Luna | Mechanical work with a hard check |
| Compiler core and Worldkeeper code | Luna first; step up one OpenAI tier if first-try pass rate is poor | The guide places Luna at routing, classification and extraction; retries on a weak model can cost more per task than one pass on a stronger one |
| Fact judging | Jev, binary questions only | Your 800-answer test supports it; the guide reports it weaker on graded scales and with irrelevant context |

Every station pins its model ID and effort level. Defaults move between versions, and a silent change to a judge or planner is a change to the factory.

Published comparisons put Opus 5.5 at [twice Sonnet 5.5's price on every line](https://claudefa.st/blog/models/claude-sonnet-vs-opus), ahead on repository-scale and long-context coding, and roughly level elsewhere. Anthropic's Claude Code guidance is to [plan with Opus and execute with Sonnet](https://support.claude.com/en/articles/14552983-models-usage-and-limits-in-claude-code), and it warns that routine work on Opus drains a subscription limit fastest. That is why Opus is capped by call count here.

The act contracts are the factory's first dark step. Opus gets the outline, the scene rules in this plan, the character list and a fixed contract template, and returns three act contracts with no prose, tests or code. A lint validates them.

Everything downstream of the contracts is cheaper models. Sonnet writes the character cards from the contracts as the first dark step. Sonnet expands each contract into holdout scenarios, stored in a separate repository no worker can read.

After start, planning is narrow and capped:

- **Replanning goes to Opus at medium effort through headless Claude Code,** one scene at a time, with a fixed number of calls per scene and per day.
- **A Luna critic checks each replanned contract against the contract checklist** before it is accepted.
- **No Fable and no other API-priced planner anywhere in the loop.** Every model call goes through a wrapper that refuses a model not on the allowlist.
- **Subscription rate limits are a wait, not a failure.** The affected lane sleeps until the limit clears (see sleep mode below).

### Running with nobody watching

Nothing parks for a human. A ticket that fails climbs this ladder:

1. Luna retries with the check output, up to three attempts.
2. Sonnet rewrites the scene's wiring from the contract, fresh context.
3. Opus refreshes the scene contract inside the act contract, then stations 2 to 7 rerun.
4. The scene is set aside, the factory works other scenes, and it returns later with a fresh context and the accumulated evidence.

A scene that still fails is never shipped around. Delivery needs all nine scenes green.

The factory stops and messages you only on a circuit breaker:

- The total budget set at pre-flight is spent before delivery.
- The same ticket fails the same check with the same output three times in a row.
- Tokens or calls per ticket run far above the running median, counted for every provider, including those with no dollar cost.
- A provider is still unavailable 24 hours after the reset time it reported. A spent weekly window is a normal sleep of up to a week, not a fault; the clock starts at the reported reset, or at the first limit when no reset was reported, and later probes do not move it. (Built in round 11c: the breaker counts from `limited_since`.)
- A subscription's weekly use passes the ceiling set at pre-flight (see "How spend is measured").
- Paid usage appears: the Codex credit balance drops, or Claude reports `isUsingOverage: true`. The factory runs on the plans' windows only.
- The state machine itself crashes.

### Sleep mode: limits are a wait, not a stop

A rate limit, a daily quota or a daily spend cap puts that provider's lane to sleep. It does not stop the factory or message you. State is on disk, so a sleeping lane costs nothing and resumes at the same station.

Limits come in three kinds, handled at two levels. The first two are retried inside `guarded_call`, so the ticket and the lane never see them unless every retry fails.

- **Rate limit** (a 429, short): retry the same call at least five times, about 45 seconds apart with jitter.
- **Overload** (the provider is busy): retry the same call with growing waits of 45, 90, 180 and 300 seconds, then treat it as a quota.
- **Quota or window** (a subscription window, a daily cap): the lane sleeps until the provider's own reset time. Both subscriptions report it on every call (see "How spend is measured"), so the factory sleeps to the exact time instead of guessing. Only when no reset time is known does it probe with one cheap call, waiting 5 minutes at first and growing to 15. The narrator's `AI_QUOTA_EXCEEDED` and `AI_DAILY_BUDGET_EXCEEDED` clear at 00:00 UTC, per your runbook.
- **Pace before the wall.** A lane also sleeps to its window's reset when the reported use passes its pre-flight ceiling, so the factory does not run a window to zero and lock you out of your own Claude Code or Codex.
- **Other lanes keep working.** Compiles, lints, gap rules and scripted journeys need no model.
- **A limit is never a failed attempt.** It does not count toward a ticket's three tries or the repeat-failure breaker. The lane keeps its reported reset time (or `first_limited_at` when none was reported) until a call succeeds, for the 24-hour breaker.
- **Both plans are subscription-only, with extra usage turned off (2026-11-19).** A spent window means a sleep, possibly for days. If you add credits or reset a limit yourself, `python -m factory wake <provider>` clears that lane's sleep so it resumes on its next step; a failed call after a wake just sleeps the lane again.

This follows how Archon's engine handles provider limits (`coleam00/Archon`, `docs/getting-started/operate.md` and `guides/loop-nodes.md`, read 2026-11-19): retry at the provider's reset time, retry rate limits in place with jitter, and never charge a limit to an attempt.

The honest consequence: with no human in the loop, the two possible end states are a delivered game or a stop at the budget with a report of what is still red.

## Fun and writing quality

A factory only delivers what it can measure, so fun and character are turned into contract fields, free checks and cheap judge questions. The targets are fixed at pre-flight, and the judges stand in for your taste until delivery.

### Pace: the thriller contract

Your `whole-story-pacing.md` already has the right five rules. The factory enforces them per scene. Most are checkable from story data with no model call:

| Rule | Free check |
| --- | --- |
| Room to explore, then pressure | The first pressure event lands on turn 3 or 4. It may land earlier only when the previous scene's exit already set the threat |
| One set piece done with the hands | The scene has an incident with at least two earned outcomes that are not "read" or "search" verbs |
| A person in the way | A talkable NPC is placed in the scene and named in the entry text |
| One choice per act that leaves a mark | Each ledger fact is read by a later entry variant or delivery variant |
| Release before the next blow | Pacing events alternate pressure and relief; no two reversals inside two turns |
| A visible clock | The scene states what is running out, and its bridge text ends on a hook |
| Delay costs you | Every missed window and recovery path carries a real cost (next section) |

### Delay costs you: a real price, never a free pass

A missed window or a wasted clock never opens the same exit for a token penalty. The contract must give each one a cost from this list:

- **A riskier storylet.** The player now has to do something more dangerous to get what they need.
- **Harm on stage to a valued NPC.** They are injured, shot, or must sacrifice themselves for the story to move. Michelle is protected and is never harmed.
- **Harm to the captives.** If information leaks early, prisoners are tortured or killed, and the player sees it.

Not allowed: a trust-only penalty, a substitute item that opens the same exit, or a neutral recovery bridge. Today's Act 2 has neutral ones (the 2C missed window, the 2A to 2C staller bridges), so those are rewritten as costed paths.

Free checks:

- Every recovery path either requires an extra earned storylet marked as higher risk, or sets a cost fact of the harm kinds above.
- Every cost fact has an authored passage shown when it lands, and at least one later scene reads it.
- No recovery asserts an exit trigger without a cost.
- No effect, cost or passage harms a character on the protected list. The list starts with Michelle.
- No-strand still holds: a cost never dead-ends the story.
- Each act contract carries a harm ladder, so costs escalate and do not spend a character canon needs later.

### Stuck turns: zero, as a hard gate

A stuck turn is one where the player is trying to progress and the story gives no way forward: a loop, a request for a task already done, a state with no authored path to the exit, or a forced handoff after a stall. Exploring is not stuck; a turn where the player looks around and the world answers is a good turn.

- **Structural proof, free.** The carry matrix and no-strand rule cover every reachable entry state and every recovery. Any state without an authored exit path blocks the change.
- **Live.** One stuck turn in any playtest opens a blocking ticket with the transcript. The scene cannot pass station 7.
- **Delivery.** Zero stuck turns across the final whole-game runs, or the factory does not deliver.

A sample cannot prove zero for all play. The structural proof carries that claim; the live runs catch what the model does with it.

Live playtest targets, fixed at pre-flight:

- Stuck turns: zero. The Stage 7 run had 30 of 84.
- Earned exits: every scene. A costed recovery counts only when its cost was shown.
- Scene length: 10 to 13 turns on average. Nine scenes make roughly 90 to 120 turns, so the 120-turn ceiling in `whole-story-pacing.md` has to rise; I would set 160.
- Quiet stretch: once the first pressure event has landed, no more than four turns without a reveal, a pressure event or an NPC move.
- Guard rejections and turn latency: tracked per scene, under your ten-second target.

### Character: one card each, used three ways

Write a card for Kristin, Michelle, Brandon, Charles, Rebecca, Reyes, the supervisor and the official. Each holds: what they want in this act, what they fear, what they hide, how they talk (three sample lines and two things they never say), and what they know scene by scene.

- The **prose station** writes from the cards, so Rebecca's survival instinct and Charles's ideology sound different.
- The **runtime** already builds NPC dialogue from the addressed NPC's permitted context. A short voice line from the card belongs there, written to your narrator guide.
- The **judge** asks yes or no questions against the card, one line at a time: does this line serve what she wants, does it give away what she hides, would a guard under orders say this. In-text questions suit Jev. Consistency with earlier scenes goes to Luna, per your own Jev findings.

### Feeling: bonds planted early, paid off with room

The player should feel the reunion and the sacrifice, and that is built scenes earlier. Each act contract carries an emotional line beside the plot line.

- **Bond beats.** Every valued NPC gets small shared moments with Kristin before anything happens to them: a favor, a joke, a confession, a habit. Brandon needs several across 1B to 3A for his goodbye to land. Michelle is present before 3A through her voice, her handwriting and the name only Kristin uses.
- **Setups and payoffs as data.** Each payoff passage lists the setup beats it depends on. A free check confirms every setup is deliverable before the payoff on every path, and the payoff has a variant for a player who missed one.
- **Room around the big beats.** No pressure event fires for two turns after the reunion or the sacrifice. The player gets a turn to answer, and the NPC answers back in voice.
- **Harm that matters.** The delay costs above fall on NPCs the player has bonded with, which is why the bond beats come first.
- **What the player should feel** is one line per scene in the contract: dread, relief, guilt, fury. The prose station writes to it, and the pairwise judge picks the candidate that best produces it.
- **The tentpoles get the largest prose budget** with Opus trialled against Sonnet: five candidates each, judged pairwise against the scene's feeling line. The winner is frozen so later passes cannot dull it.

### Prose: spend where players read

The narrator is a small model, so the ceiling on improvised prose is low. Put the quality in authored text: entries, verbatim beats, delivery text, NPC lines, bridges.

- The prose station writes two or three candidates per passage. A judge picks pairwise, which is cheaper and steadier than scoring.
- Use more verbatim beats for the punches: the officer's demand, Rebecca's offer, Brandon's goodbye.
- A style sheet of ten lines: short sentences under pressure, concrete nouns, one physical detail per beat, no summary of feelings.
- Cut reading-as-gameplay. Where a scene still makes the player a clerk, the contract fails rule two.

### Judging without you

There is no human sample during the run. Judge questions are frozen at pre-flight and checked against the labelled sets already in `bench/calibration/`. A second judge model re-scores a slice of every batch, and a disagreement rate above the noise you measured (about 3 in 100) pauses that judge's verdicts and falls back to the stricter one. At delivery you get the build, the full-run transcripts and the cost report.

## Token budget rules

The largest saving is removing the long-lived orchestrator session; the rest is ordering work so cheap evidence comes first.

1. **No model holds the loop.** Sonnet at high effort carrying a session's history is your largest avoidable cost. The state machine holds state; Sonnet sees only a triage packet.
2. **Free before billed, always.** Compile, lints, gap rules, carry matrix, quick suite and `bench prompt` run before any narrator or judge call. A change that fails a free gate never reaches a live run.
3. **Packets, not context.** Each call gets one scene file, its contract and the failing evidence. No plan history. Archive `.plans/` out of every agent's reach; several files there are 100 to 550 KB.
4. **Edit by ID.** The story CLI means a wiring worker reads one record, not a file.
5. **Jev first, one question at a time.** Per your guard rules: code does the counting, Jev answers in-text questions, and only unsure answers and story-sense questions go up to Luna.
6. **Sequential sampling.** Three replicates as a smoke. Stop on a clear fail. Go to twelve only for an adoption decision. Reach mid-story scenes with scripted prefixes, which are free.
7. **Opus plans, in few calls with small output.** Act contracts at start and replanning in flight both run under a per-scene and per-day call cap. A model allowlist blocks Fable and any other API-priced planner.
8. **Expensive prose, tiny volume.** Authored text for nine scenes is on the order of tens of thousands of tokens once. That is small next to one day of playtests.
9. **Route by scoreboard.** Ringer logs tokens and first-try pass rate per model. Start each task type on the cheapest model and move up only where the pass rate says so.
10. **Cost per merged ticket** is the factory's own metric. It feeds the circuit breakers during the run and the cost report at delivery.
11. **Unknown cost is unknown, never zero.** A ledger row's `usd` is a number only when real money was spent; otherwise it is empty and the row says why. Dollar breakers count only dollar rows, and a dollar total that includes an empty row is reported as a minimum, not the total.

### How spend is measured

Each provider declares in `factory.json` what its limit is, and the factory reads that limit from the provider itself. Checked 2026-11-19 with one tiny call each.

| Provider | Kind | What limits it | Where the factory reads it |
| --- | --- | --- | --- |
| Claude Code (Opus, Sonnet) | `subscription` | Five-hour and weekly windows | Headless `claude -p --output-format stream-json --verbose` emits a `rate_limit_event` per call: `unifiedWindows.five_hour` and `seven_day`, each with `utilization` (0.19 means 19%), `resetsAt` and `status` (`rejected` when the window is spent) |
| Codex (Luna) | `subscription` (ChatGPT Plus, through `codex login`; not API tokens) | Five-hour and weekly windows | `codex exec --json` gives tokens only. The run's session log (`~/.codex/sessions/YYYY/MM/DD/rollout-*-<thread_id>.jsonl`) carries `rate_limits`: `primary` (300 min) and `secondary` (10080 min), each with `used_percent` and `resets_at`, plus `credits.balance` |
| Cloudflare (narrator, Jev) | `reported` | Daily neuron allowance and gateway spend | The narrator's quota errors and the gateway's spend; unchanged from today |

- Claude's `total_cost_usd` is priced at list (`"costBasis": "list"`), not what you pay. The ledger keeps it as information and never counts it toward a budget.
- Every row records tokens and, for subscriptions, the window figures the call reported. The breakers read the latest figures, not a sum.
- The Codex plan has a paid credit balance beside its windows. The factory must not spend it: any drop in `credits.balance` across a call trips a breaker. Brandon turned off Codex's automatic credit use on 2026-11-19, so a spent window now stops Codex instead of drawing credits; the breaker stays as a tripwire in case that setting changes.

## Order of work

Build the line first on today's files so it pays back at once, then migrate the story through it. Sizes are my estimates from reading the repo, not measurements.

1. **Factory skeleton on today's package (small).** Ticket schema, state file, manifest templates, check library, model allowlist, spend caps and circuit breakers. Wire in the gates that already exist. Add the lints. Shake it down on one open defect, such as the 2C transmit branch leaving no trace in 3A.
2. **Compiler, 1A to parity (medium, the critical path).** Finish Phase 1 schema items with matcher lists written out and the lexicon left as an optional layer in the schema. Fixtures and tests first, as your plan says. Exit on an empty parity diff for 1A. The lexicon pass for 1A follows as its own ticket with its own gate, and does not block step 3.
3. **Swarm the migration (medium, parallel).** Eight scenes and the coupled tests, one worker each, parity gate per scene. Build the story CLI and the generated script view here.
4. **World-need check, contract lint and judge calibration (small, parallel with 2 and 3).** None depends on the new format.
5. **Pre-flight, then start.** First a watched rehearsal: one scene goes through the whole line, and each circuit breaker is tripped on purpose with an injected fault. Then you set the budget and caps and press start. Opus writes the three act contracts as the first dark step. The lint accepts the three act contracts. Pressing start is your last action.
6. **Content passes in story order (large, dark).** Per scene: world tickets, prose, wiring, free gates, playtests, triage. Every scene gets the new pacing, delay costs and bond beats, so 1A and 1B are no longer exempt. Act 2 and 3C get the most work, since that is where runs stalled.
7. **Whole-game runs and delivery (dark).** Blind-player full runs at the adoption sample size and hosted E2E on the staged SHA. Zero stuck turns and every target met, then the factory reports the delivered build.

**Status, 2026-11-16.** Step 1 is built: `factory/` has the ticket queue, state file, model allowlist and spend ledger, the eight circuit breakers, the manifest generator with check linting, the frozen-harness guard, the check library (`factory/checks/`, including the gap-rule baseline comparison and canary tickets), the breaker drill, and the `python -m factory` entry point with preflight. `python -m factory drill` trips all eight breakers on the real code. Preflight fails on purpose until the owner sets the budget and caps. Not yet built: the real model station handlers (stations 2 to 9), so the line runs only with injected handlers. The planned shakedown defect (the 2C transmit branch leaving no trace in 3A) was fixed by hand before the factory existed; the 1A laptop defect was fixed through Ringer as a stand-in, and canary tickets cover the "no valid solution" case. Next is step 2, the compiler and lexicon for 1A, with no time box and no fallback to the nine files (owner decision, 2026-11-16).

**Step 2 measurement, 2026-11-16** (`.plans/story-data-phase0/lexicon_derivable.py`, read-only, run on the loaded package). I sorted every entry in the 20 scene-1A claims' matcher lists by where a lexicon could get it. The categories are an entity name or alias, a word already in the engine's synonym classes, a word inside an entity name (`card`, `laptop`), and "bespoke" (none of those).

| List | Entries | Entity name or contained in one | Engine class word | Name token | Bespoke |
| --- | --- | --- | --- | --- | --- |
| `action_evidence` | 232 | 36 | 64 | 16 | 116 (50%) |
| `must_convey` | 174 | 74 | 0 | 23 | 77 (44%) |
| `leak_terms` | 34 | 17 | 0 | 0 | 17 (50%) |

What this means for the schema:

- **An entity-only lexicon fails the plan's own one-third rule** (a field with more than a third overridden drops back to explicit lists). Half of each list is bespoke.
- The bespoke entries are not random. They are story concepts that are not entities (`dead drop`, `damaged recording`, `reflective tape`, `federal patrol`) and verbs the engine has no class for (`call`, `listen`, `connect`, `insert`, `drive`, `head`). So the lexicon needs three sections: **entities** (names), **concepts** (named phrases that are not world things), and **verb classes** (story-level, added to the engine's). Re-measure against that lexicon before the schema is frozen.
- **There is little copying between claims in 1A.** 19 claims with `action_evidence` have 17 distinct lists, and 16 with `must_convey` have 15. The duplication this step removes is the same noun phrase repeated across fields of one claim (`leak_terms`, `must_convey`, `aliases`, `says`), not shared lists. The saving is real but smaller than "one edit by record ID" suggests for matcher words.
- The counts say what the lexicon *could* hold, not that derivation reproduces today's lists. That is still what the parity diff measures.

**Schema contract, 2026-11-16.** [story-data-schema-contract.md](story-data-schema-contract.md) is drafted (Opus, read-only on the live package) and Brandon accepted its five open questions: keep the 13 unplaced facts in `catalog.unplaced_facts`, drop the sentence-collapse rule, keep `storylets.md` sections as `notes`, keep the 11 bridge texts as `note`, leave `SL-3C-F-R1` claimless (review it with 3C's story work, step 6). Not built: no fixtures, validator or compiler yet. Next is Phase 1 item 6, the fixtures and schema tests, written before any compiler code and routed through Ringer.

**All-scene sample, same day** (`lexicon_repeat_by_scene.py`; every claim belongs to exactly one scene). "Repeated" is the share of phrase occurrences, counting `action_evidence`, `must_convey`, `leak_terms` and `aliases`, whose phrase appears in two or more claims or fields. "Bespoke" is the share that is not an entity name, a name token or an engine class word. Both are heuristics; the entity test is a substring match, so some "bespoke" words would be covered by a lexicon's short names.

| Scene | Claims | Occurrences | Distinct | Repeated | Bespoke |
| --- | --- | --- | --- | --- | --- |
| 1A | 20 | 471 | 255 | 68% | 47% |
| 1B | 14 | 178 | 117 | 56% | 37% |
| 1C | 11 | 124 | 84 | 53% | 32% |
| 2A | 12 | 165 | 107 | 58% | 56% |
| 2B | 12 | 208 | 122 | 64% | 49% |
| 2C | 10 | 149 | 112 | 46% | 53% |
| 3A | 15 | 371 | 233 | 61% | 54% |
| 3B | 11 | 581 | 525 | 16% | 79% |
| 3C | 17 | 540 | 471 | 22% | 77% |
| All | 122 | 2787 | 1693 | 55% | 60% |

1A does not represent the whole story. It is the most repetitive scene, and 3B and 3C are a different kind of data (long synonym enumerations, almost no sharing). `lexicon_plural_twins.py` counts `action_evidence` entries that are the plural or singular twin of another entry in the same group: 13% overall (2139 entries), 4% in 1A, 12% in 3A, 24% in 3B, 18% in 3C. Step 1 is rewritten around this: pass 1 compiles with explicit lists, pass 2 adds the lexicon per scene where it pays (see "Where the lexicon pays").

**Fixtures round 1, 2026-11-16.** Phase 1 item 6 has started, through Ringer (`scripts/ringer/story-data/fixtures-round1-manifest.json`, one Luna task, passed first try). Built: fixture F01 `mini_ok` under `tests/fixtures/story_source/` (1A `find_card` with both variants, the 2C incident, two entry claims, an ending), the patch helper `tests/story_source/helpers.py` that edits a copy by record ID and field, and the F01 tests (8 pass; the compiler test skips until `storygame.story_source` exists). The README there fixes the API the tests are written against: `check_source_tree`, `Diagnostic`, `compile_source_tree`, `story_text`, `story_value`. An independent check (`check_fixture_f01.py`) verifies key order, ids and that every passage is exact live text. I tightened it after the first pass, because the worker had parked live text in `NEW_TEXT.txt`; F01 needs no new text. Next: fixtures F02 to F31 (each F01 plus one change) in parallel workers, then the Layer 1 and 2 validator tests, then the compiler.

**Fixtures round 2, 2026-11-16.** Fixtures F02 to F31 are written, through Ringer (`scripts/ringer/story-data/fixtures-round2-manifest.json`, five Luna tasks by range, all passed first try, independent shape check `check_fixtures_round2.py`). Each is F01 plus one change, built by patching a copy; each test file has a test that runs today (the tree differs from F01 only where intended) and compiler assertions behind `importorskip`. Suite: 39 pass, 32 skip until `storygame.story_source` exists. The five `tests/story_source/ambiguities_*.md` files list every point the contract leaves open (API names for parity, lock, expand, examples and save identity; diagnostic address formats); the contract's new section 10.1 settles them (F27 now also calls the examples checker, with the examples file outside the source tree). Next: the Layer 1 and 2 validator tests, then the compiler.

**Validator round 3a, 2026-11-16.** The fixture tests F02 to F31 already hold the Layer 1 and 2 assertions, so no separate "validator tests" step is left; the next build is the validator itself. Round 3a (`scripts/ringer/story-data/build_validator_round3a_manifest.py`, one task) built the package skeleton `storygame/story_source/`: `Diagnostic` and `SourceError`, a strict YAML reader that reports `L1.duplicate_key` and `L1.syntax` with line numbers, and a check registry that discovers any `l1_*.py` or `l2_*.py` module, so later workers add checks in separate files. It also added `require_story_source()` to the test helpers, so a fixture test skips while a name it needs is unbuilt. The Ringer check failed twice on one fixture test (F31 starts a subprocess that needs the compiler and had no skip guard); the rest passed, so I applied the worker's output and added the one-line guard by hand. The branch `story-data-validator-skeleton` stays open and is not merged until the Layer 1 and 2 checks land, because F03 to F08 and others fail against an empty validator. Next: Layer 1 tasks (root and catalog files; scene files), then Layer 2 (facts and ids; claims and overrides), then the compiler.

**Validator round 3b, 2026-11-16.** Layer 1 shape checks are built through Ringer (`build_validator_round3b_manifest.py`, two parallel tasks, both passed first try): `l1_root.py` (ownership, story, catalog, match, lock and lexicon files; `L1.lexicon_off`, `L1.plural_off`, `L1.match_scene`) and `l1_scene.py` (scene files; condition values, passage lists, claim keys without a claim). I fixed one fixture, F19, which wrote a derived `leak_terms` as a one-item list; the contract shows a map. In `tests/story_source` 7 tests still fail, F04 to F08, F14 and F20, and each needs a Layer 2 diagnostic. Next: round 3c, the Layer 2 checks (facts and ids; claims, overrides and ownership).

**Validator round 3c, 2026-11-16.** Layer 2 checks are built through Ringer (`build_validator_round3c_manifest.py`, two parallel tasks, both passed first try): `l2_facts.py` (duplicate ids, dangling references, fact ownership and declaring scene, unplaced and undeclared facts) and `l2_claims.py` (claim authorization, add-only overrides, match coverage, incident observers, scene scope, ending scene, ownership manifest). `tests/story_source` now gives 87 passed, 24 skipped. F20 (`L2.lock_stale`) skips on purpose until the pass 2 expander exists; `L2.lock_stale`, `L2.drop_unused`, `L2.cycles` and `LOADER` are left to later rounds. The branch `story-data-validator-skeleton` holds rounds 3a to 3c, ready for a PR. Next: the pass 1 compiler to `StoryPackage` (Phase 1 item 7), then its parity gate against 1A.

Steps 1 to 4 build the factory, and you may still be steering there as you do today. The dark run is steps 6 and 7.

**Compiler round 4a, 2026-11-16.** The pass 1 compiler core is built through Ringer (`build_compiler_round4a_manifest.py`, one Codex task, passed on attempt 2): `compile_source_tree`, `source_digest`, `COMPILER_VERSION` in `storygame/story_source/` (`compiler.py`, `digest.py`, `c_*.py`). It runs every inherited loader check and wraps failures as `L2.cycles` or `LOADER`. `tests/story_source` gives 105 passed, 8 skipped. The worker also built a lexicon/plural expander (`c_lexicon.py`, 148 lines) that I had not asked for; it is pass 2 work and needs its own review before F19 to F22 are trusted. Applied on local branch `story-data-compiler-core`, not committed. Not built: parity (`check_parity`), save identity, examples, `story_cli`, lookup, and a converter that writes the real 1A source tree. Next: round 4b (those APIs), then the 1A converter and parity gate.

**Round 4b, 2026-11-16.** Parity, save identity, override ratio, examples and lookup are built (`build_round4b_manifest.py`, four parallel Codex tasks: `parity.py`, `identity.py` and `ratio.py`, `examples.py`, `lookup.py`). All four Ringer checks failed, but the cause was my lazy exports in `__init__.py`: a missing sibling module raised `ModuleNotFoundError`, which the test proxy does not skip, so each task's whole-suite step broke on the other three. Each worker's own gate tests passed. Workers also copied each other's modules and one edited `compiler.py` to hook the lookup; I took each task's own module and test from its own worktree and left `compiler.py` alone (F28 passes without the hook). `tests/story_source` gives 122 passed, 2 skipped (F19 needs `story_cli`, F20 needs the pass 2 expander). Not built: `storygame/story_cli.py`, `story expand`/`lock`, the pass 2 lock check, and the 1A converter with its parity gate. Next: round 4c (story CLI), then the 1A converter and parity gate. Lesson for the next manifest: make the lazy lookup turn `ModuleNotFoundError` into `AttributeError`, and keep `tests/shard_durations.json` in the orchestrator's hands.

**Round 4c, 2026-11-16.** The pass 2 lock layer and the story CLI are built through Ringer (`build_round4c_manifest.py`, two parallel Codex tasks, both passed first try): `lock.py` (`equivalent`, `lock_scene` with `--adopt`, `expand_scene`), `l2_lock.py` (`L2.lock_stale`, `L2.drop_unused`) and `storygame/story_cli.py` (`show`, `parity`, `lock`, `expand`; `set`, `rename`, `impact`, `new`, `fmt` are registered and exit 2 "not built yet"). I fixed three things by hand afterwards: the round 4b lookup found source trees by scanning `/tmp` for recent `story.yaml` files, so a neighbouring test's tree could win (it broke F28 once the new tests existed); the compiler now registers its source tree with the lookup instead. F19's helper called `dataclasses.asdict` on a pydantic package, so it now uses `model_dump`. F20's unconditional `pytest.skip` is removed. `tests/story_source`: 135 passed, 0 skipped. Not built: the 1A converter that writes the real source tree and the parity gate on it, and the remaining CLI commands. Next: round 5, the 1A converter and the parity gate.

**Round 5a to 5c, 2026-11-16.** The legacy-to-source converter is built and the converted default story compiles. Round 5a (`build_round5a_manifest.py`, four parallel Codex tasks, all passed) wrote the pieces: `convert_catalog.py`, `convert_facts.py`, `convert_reveals.py`, `convert_scene.py`. Round 5b (one task, failed its check by design of the blocker) wrote the assembler `convert.py` (`convert_package`, `write_source_tree`) and fixed the piece disagreements until `check_source_tree` returned nothing on the converted tree. The compile step then exposed three defects in my round 4a compiler that no fixture had touched: `build_connections` passed `id` twice (no fixture had connections), `must_convey` was dropped whenever a claim had `text_when` (the loader requires it on `k_sl_2c_d_r3`; F12 had been written to the wrong assumption and was corrected), and `compiler.py` dropped the resolution events. Round 5c fixed all three and `tests/story_source/test_convert_tree.py` now passes: the converted tree validates, compiles, keeps every scene, claim, storylet, realization, delivery, pacing event, incident and fact id of the legacy package, and is deterministic. `tests/story_source`: 150 passed, 0 skipped. Not done: the parity run. Compiling and keeping ids is not parity; whether every field of the compiled 1A equals the legacy 1A is untested. Next: round 5d, run `story parity 1A` on the converted tree, classify the differences, and fix the converter until unreviewed is 0.

**Round 5d and 5e, 2026-11-17.** The converted default story now has parity with the legacy package on the whole package, gated by `tests/story_source/test_parity_default.py` (zero unreviewed differences, reviews allowed only for `world.facts`). Round 5d (`build_round5d_manifest.py`, one Codex task) took the first parity run from 103 unreviewed differences to 2 by fixing the converter and compiler: storylet ids and `source_beats` now round trip, scene prose is carried verbatim, empty `fact_effects` stay empty lists, incident observation ids match, and the extra delivery-fallback asserts on `SL-1A-A-R1` are gone. Its Ringer check failed only because the last two differences needed contract decisions; I applied its patch. Round 5e (one Codex task) built the `parity.py` rule the contract implies but the checker lacked: a `knowledge_indexes` difference that is fully explained by provable `op_order` reorders does not count (the three reordered claims are `k_sl_1a_b_r1`, `k_sl_2b_b_r4`, `k_sl_2b_b_r5`); real index differences still fail and stay unreviewable (`test_parity_indexes.py`). The worker also refused to review `world.facts` because it found two inverted order pairs, not the one the contract names: `brandon_identified`/`relay_open` and `facility_perimeter_reached`/`rebecca_office_reached`. I checked the second: no route, bridge, pacing event or delivery ever asserts `facility_perimeter_reached`, so its effect is never pending beside the other, and I wrote the one `world.facts` review entry (`tests/fixtures/parity/continuity-initiative/world.reviewed.yaml`, class `dedupe`) with that reason. I had first removed the legacy duplicate from `world.yaml`, then reverted it: the contract lists it as a review entry and legacy data stays as it was. `tests/story_source`: 155 passed. Not done: the converted source tree is not yet committed under `data/` (the gate writes it to a temp directory), and `story parity <scene>` needs it there; pass 2 (the lexicon) and the story CLI commands `set`, `rename`, `impact`, `new`, `fmt` are still unbuilt. Next: round 6, commit the converted source tree as the story's source of truth and switch the loader to compile it, then convert the tests off copied prose (step 3).

**Round 6, 2026-11-17 (branch `story-data-round-6`, not merged).** The converted source tree is committed at `data/stories/continuity-initiative/source/` with a drift test (`test_source_tree_drift.py`: the committed tree must equal a fresh conversion of the legacy files). The loader now compiles `source/` when `ownership.yaml` marks the catalog and every scene `compiled`, raises on mixed ownership, and exposes `load_legacy_story_package`; the real story has no `ownership.yaml` yet, so it still loads from the legacy files. `compiled_story_copy` in `tests/story_source/helpers.py` gives tests a copy with no legacy files. 59 of the 66 continuity tests that touched legacy files are migrated through Ringer (pilot of 3, then four batches; 56 passed, 7 blocked). The conftest provider-opening fixture is migrated. Blocked, with the workers' notes kept in the Ringer worktrees (`story-data-round6c2-b0*/m-<key>/NOTES_*.txt`): `test_package_audit` (needs `storygame/audit.py` to read a compiled package), and `test_world_seats`, `test_seating`, `test_place_scoped_feed`, `test_markdown_story_package` (8 tests), `test_gap_rules` (2) and `test_3c_recall_live`, where the source route accepts something the legacy loader rejected (the item and NPC `unavailable` axis is not carried into the compiled world; blank place description; missing seat enter/leave text) or cannot express the legacy mutation at all (bridge text-key mismatch, duplicate delivery construction, ambiguous transition priority). Still unported non-test readers: `storygame/audit.py`, `bench/checks/penalty_rubric.py`, `scripts/generate_spine_expected_reveals.py`, and the file names in `impact_report.py`. Next: classify each blocked test as "add a source check" or "retire, since the source format cannot say it", port the readers, then flip (add `ownership.yaml`, delete the nine files, freeze the parity reference, drop the drift test).

**Round 6 findings and status, 2026-11-17 (branch `story-data-round-6`, not merged, stopped here at Brandon's request).** Read the scouts' reports before trusting the earlier "parity" line above: it was wrong.

- **The parity gate hid real differences.** `parity.py` `_compare_lists` returned after recording a key-order difference and never compared the items, so any reordered collection passed. Fixed in 6e-0 (`test_parity_order_hides_content.py`). The default story then showed 627 differences: 617 `storylets.md` section texts the converter never carried (the contract decided to keep them as reveal `notes`), 5 pacing events with effects the compiler invented, 3 storylet titles and `SL-3C-E` turn windows. Round 6e-1 fixed all of them: sections are carried as `notes` (7 derived-section overrides, 3 title overrides), the source tree is regenerated, and the gate is green again with only the one `world.facts` review.
- **The compiler's silent repair is gone.** `_supply_transition_sources` was documented for reduced fixtures but also ran on the real story, adding effects such as `memory_card_recovered` to `kristin_steadies_1a`. It is now a no-op kept only for a test that monkeypatches it, and a full story with an unproduced transition trigger fails. The mini fixture `mini_ok` now declares its producer explicitly. This also fixed the two `test_gap_rules` ports.
- **Source checks the legacy loader enforced and the source route did not** (found by six read-only scouts, `scripts/ringer/story-data/build_round6d_scout_manifest.py`): added in 6e-2 as new modules, `l2_story.py` (`L2.transition_source`, `L2.delivery_unseen`) and `l2_world.py` (`L2.axis_pole`, `L2.seat_lines`, `L2.blank_description`, `L2.scoped_alias_collision`), each with its own tests and a clean-default-tree test.
- **"The source format cannot say it" was checked, not assumed.** Five markdown tests (duplicate fact delivery, bridge text keys, same-scene transition priority, canonical-event and entry-claim sources, and the first half of the world-only delivery test) guard mistakes the new format cannot write, because the field is derived or keyed by id; the scouts tried two or more ways to write each one and got L1 rejections. They are not retired: each becomes a test that attempts the forbidden field and asserts the L1 rejection. Cost to remember: a scene has exactly one exit (contract 4.13), so a future story that needs two exits from one scene needs a contract change. Two scout verdicts were wrong: `test_3c_recall_live` was already skipped on `main` as stale (its skip is restored), and the ambiguous-knowledge-effect test is a port error (its faithful source mutation is rejected).
- **Open, in this order.** (1) Five ported tests (`test_world_seats` x2, `test_seating` x2, `test_place_scoped_feed` x1) still fail only because they catch `StoryPackageError` and the compiled route raises `SourceError`; the new checks do fire. Either widen those tests to accept `SourceError` (as the other ported tests do) or make `SourceError` a `StoryPackageError`. (2) Rewrite the 8 `test_markdown_story_package` tests blocked earlier: five as L1-shape rejections, the ambiguous-knowledge one as a corrected port, and the world-only delivery one against the new `L2.delivery_unseen`. (3) Port `storygame/audit.py` (`audit_package` reads raw legacy files; `test_package_audit` is still on them), `bench/checks/penalty_rubric.py`, `scripts/generate_spine_expected_reveals.py` and the file names in `impact_report.py`. (4) Go through the 15 tests in `tests/` that name a legacy file but use their own fixture stories (lighthouse); they stay on the legacy loader. (5) Flip: add `ownership.yaml`, delete the nine legacy files, freeze the parity reference and the converter input, drop the drift test, run the full suite once.
- **Lesson for the manifests.** My migration check forbade skips, so a worker un-skipped a stale test and it failed; checks must compare against the skips already on `main`, not forbid all of them.

**Round 6f to 6i, 2026-11-17 (branch `story-data-round-6`, not merged): the default story is flipped and the full suite is green (4765 passed, 25 skipped).** 6f restored `test_incidental_package` to its legacy form (lighthouse fixture tests stay on the legacy loader; the 6c-2 port had broken it and two importers) and fixed two tests for the new source checks. 6g rewrote the 8 blocked `test_markdown_story_package` tests as specific `L1`/`L2` rejections (one was a port error: `aliases`, not `scoped_aliases`). 6h ported the readers: `storygame/audit.py` (compiled roots rebuild the plot text from the package; legacy roots keep the legacy path), `penalty_rubric.py`, `generate_spine_expected_reveals.py` and `impact_report.py` (names real source files). The flip (`1ef50250`): the nine legacy files moved to `tests/fixtures/parity/continuity-initiative/legacy/` as the frozen parity reference and converter input, `ownership.yaml` added, drift test dropped, convert, parity and dispatch tests read the frozen copy through `load_legacy_story_package`. The flip broke about 30 tests that read legacy files by name; 6i fixed them: live-story variations (`bench/variations/stage7-3c-*.json`) now patch `source/` files, frozen experiments read the legacy copy, probes follow. Two of my own bugs surfaced: `audit_package` sent legacy roots down the compiled path (fixed: compiled path only when `plot.md` is absent), and a glob in my 6i ownership check rejected the probes task's correct work (taken from its worktree by hand).

- **Open: collection order.** The compiled package keeps within-scene claim order but orders `knowledge.knowledge`, `storylets`, `deliveries` and `pacing.events` by scene across the story, where legacy followed file order. The parity gate classes this `collection_order` and passes it. Per-claim content is equal except the three known `op_order` cases (`k_sl_1a_b_r1`, `k_sl_2b_b_r4`, `k_sl_2b_b_r5`). Three tests that pinned the legacy order (`test_voiceable_knowledge`, two 2B gating entries) now compare sets. Not checked: whether any runtime path (reveal candidate ties, prompt order) depends on cross-scene order. Decide: accept it, or make the compiler reproduce legacy order (the plan's "parity until the diff is empty").
- **Open: playtest.** Nothing here ran the game or a bench. The flip changes where the story loads from, so one cheap `bench prompt` snapshot of a scene against `main` should confirm the payload is unchanged before merging.
- **Still not built:** pass 2 (lexicon), `story set`, `rename`, `impact`, `new`, `fmt`, the examples file per scene, and step 3's test decoupling from copied prose.

**Prompt snapshot and collection order, 2026-11-18 (branch `story-data-round-6`, not merged).** I ran `bench prompt` (free) for all nine scenes on this branch and on a `main` worktree: the entry prompt plus every beat, 90 captures each. 89 are byte-identical. One differs: `1B` beat `1B.4` has one extra line on the branch, "The thermos carries a county emergency-water label." Cause, checked three ways: (a) the same branch code run on the frozen legacy files reproduces `main` exactly, so the compiler is the cause and not the loader or the prompt code; (b) the three knowledge claims named above are the only claims that differ in content, and none is the thermos claim; (c) **the compiler reorders storylets inside three scenes, 1A, 1B and 2C**, and not only across scenes (1B legacy: D, A, E, F, G, H, B, C; compiled: D, A, E, B, C, F, G, H). `bench.core.establish_prior_beats` fires storylets in `package.storylets` order, and an earlier firing can block a later one, so order changes which facts a beat's prompt treats as already known. The storylet routes are in the same order on both sides, which says the reorder happens when the compiler builds `package.storylets`, not in the source. **Decision on the open item: collection order is not harmless, so the compiler must reproduce legacy order** (the plan's "parity until the diff is empty"). The parity gate's `collection_order` class hid this, as `_compare_lists` once hid reorders; that class must stop auto-passing for `storylets`, `knowledge.knowledge`, `deliveries` and `pacing.events`. Whether other runtime paths read cross-scene order is still unchecked; the fix and a within-scene plus cross-scene order gate settle it. Capture scripts: scratchpad `snap.sh` (loop over scenes and beats); the diff method is `diff -r before after`. Side effect to remember: `uv run` inside a git worktree repoints the shared `.venv`'s editable installs at the worktree; run `uv sync --all-packages` after removing one (done).
- **Round 7 (2026-11-18), applied to the working tree, not committed.** Run `story-data-round7` (`build_round7_manifest.py`, one Codex task, passed on attempt 2). The investigation widened the scope: legacy keeps two different storylet orders (routes file vs `storylets.md`), and same-scene order also differs for deliveries (1B, 2A, 2B, 2C, 3B, 3C) and knowledge claims (1C, 2A, 2B, 2C, 3C), so the earlier line "the compiled package keeps within-scene claim order" was wrong for those scenes. The contract already said same-scene order must hold; `parity.py` was looser than the contract (any reorder auto-passed) and now follows it. The source format gains an optional last scene key `order` (`storylets`, `deliveries`, `knowledge`, `pacing_events`, each a list of that scene's ids); the converter writes it only where legacy order differs from the natural one (eight scene files changed); `L2.order_id` rejects stale or duplicate ids; the contract has a new subsection. Verified by me: all 90 `bench prompt` captures (entry plus every beat, nine scenes) are byte-identical to `main`; `tests/story_source` 179 passed; the independent check `scripts/ringer/story-data/check_order_parity.py` reports zero order or prompt differences. Known soft spot: `_collection_order_proof` still auto-passes a reorder for items that carry no scene id (as before), so the independent check is the real gate for order.
- **Full suite after round 7: 4 failures** (4768 passed). `tests/shard_durations.json` was missing two new test files (regenerated by hand, the orchestrator owns it). The other three fail because tests copy the source tree, delete a record, and the copy's `order` list still names it, so `L2.order_id` fires before the error the test is about (`test_branch_report` dead-end case; `test_incident_loader` cases `recovery has no extra fact` and `recovery awards both outcomes`). The strict check stays; the test helpers must prune deleted ids from `order`. Round 7b (`build_round7b_manifest.py`) does that. Consequence for the story CLI: `rename` and delete must update `order` lists as well.
- **Open after 7b:** commit round 7 and 7b, re-run the full suite once, decide whether to merge. Brandon asked (2026-11-18) how to find useless or redundant tests after the new format; plan: static scan of format-bound tests first (legacy filenames, legacy loader users, `copied_prose.py`, overlap between the rewritten markdown loader tests and the L1/L2 fixture tests), then per-test coverage contexts in the nightly job only, then mutation checks on the candidates; nothing deleted without that evidence.
- **Next (superseded):** the single Ringer task described earlier is done as round 7 above.

**Status, 2026-11-19.** Round 7 and 7b are merged (PR #780). The redundant-test scan is finished ([redundant-test-scan.md](redundant-test-scan.md)): 213 probe and experiment files retired (#781), 7 exact-duplicate tests removed (#782), five copied overprojection tests folded into one (#783), four duplicate parametrized 2C cases dropped (#784), and the 88 s golden-corpus test split into nine per-scene cases (#785). **Story CLI built (rounds 8a to 8b, branch `story-cli-writes`):** `story fmt [--check]`, `set` (`--add`, `--drop`, refuses generated and frozen fields), `rename` (frozen ids need `--retire`, cross-kind id collisions refused), `impact` and `new` (fact, beat, claim) all write through one round-trip YAML writer, `storygame/story_source/yamlio.py` (ruamel.yaml, width 10000, the committed tree round-trips byte for byte). Every write runs layers 1 and 2 plus a compile and restores the file bytes on failure. Commands are one module each in `storygame/story_cmds/`, discovered automatically. Not built yet: pass 2 (lexicon), the per-scene examples files, test decoupling from copied prose, factory station handlers 2 to 9. Full suite on merged `main` not re-run yet.

**Test decoupling, rounds 9a to 9b, 2026-11-19 (working tree, not committed).** Step 3's "decouple tests from copied prose" is done through Ringer (`build_round9a_manifest.py`, `build_round9a2_manifest.py`, `build_round9b_manifest.py`). The committed audit `scripts/audit_copied_prose.py` (with `tests/test_audit_copied_prose.py`) replaces the old `.plans/story-data-phase0/copied_prose.py`: it reads the compiled package, reports authored sentences of 45+ characters in test files, and joins neighbouring string constants in source order before matching. **The old audit was blind to wrapped literals:** its 36 files and 82 sentences were really 40 files and 133 sentences (the compiled-package address of a pacing beat is `beat:ID.say[i].text`, which the first audit version printed wrongly). Pilot workers also first got past the audit by splitting a copied sentence across string pieces, so the audit now sees joined constants and the spec forbids rebuilding a sentence from fragments. A rule travelled in every spec: no tautologies (never assert a record equals the lookup of the same record). Where a test only ever pinned the exact wording of the record it loads, the worker replaced the pin with the structural fact the test's name claims (a count, a key phrase from another record, an id) or marked it `RETIRE-CANDIDATE` in its notes. 39 test files were migrated (3 pilot, 36 in batches; 8 tasks needed a rerun after the beat-address fix and a check-tolerance fix). `tests/test_3c_recall_live.py` was done by hand: one copy now looks up its claim, and the other is text inside a frozen pre-adoption fixture that the helper must match byte for byte, so it stays (the audit reports that one file). Brandon then retired the five tests that had been reduced to weak wording checks (round 9c, 2026-11-19): four deleted whole (`test_1a_phone_thread` delivery texts, `test_1c_closeout` reunion, `test_1a_back_door_gap` new wording, `test_delivery_echo` badge delivery) and the wording assertions removed from `test_richer_1c`'s glimpse test, which keeps its metadata checks. Not done: pass 2 (lexicon), per-scene examples files, factory station handlers 2 to 9.

**Step 4, round 10a: contract schema and lint, 2026-11-19 (branch `factory-contracts`, not committed).** Brandon chose step 4 (the free gates) as the next build. Round 10a (`scripts/ringer/dark-factory/build_round10a_manifest.py`, one Codex task, passed first try, 104k tokens) built the act-contract format and its lint: `factory/contracts/lint.py` (also `python -m factory.contracts.lint FILE`, exit 0, 1, 2), `factory/config/contract_rules.json` (protected characters, cost kinds, beat kinds, relations, scene ids, first-pressure turns 3 or 4, minimum gap 2; frozen with the rest of `factory/config/**`), the blank planner template `factory/contracts/template.json`, a valid Act 1 fixture and 19 tests, one failing mutation per rule id (`contract.shape`, `placeholder`, `harm_ladder`, `beats`, `first_pressure`, `pacing`, `setpiece`, `npc`, `clock`, `delay_cost`, `protected`, `bond`, `world_need`, `feeling`). I applied the patch and re-ran the contract and frozen-harness tests: 32 pass. Not done: the world-need check (round 10b: it reads a contract's `world_needs`, asks Worldkeeper whether each relation is representable, and uses `producers` and `consumers` for the produced-earlier and read-later questions), judge calibration (round 10c), and the station handlers. Judgement calls the worker made are in its worktree notes, which Ringer deleted on pass; the rules in the spec are what the lint enforces.

**Step 4, round 10b: world-need check, 2026-11-19 (branch `factory-contracts`; 10a and 10b-1 committed locally, 10b-2 in the working tree).** Two Ringer runs, both passed first try. 10b-1 (`build_round10b1_manifest.py`, 26k tokens) added `WorldSchema.can_represent(relation, subject_kind, object_kind)` to `packages/worldkeeper` with its tests there, per the boundary rule: it answers question 1 from the kind tree alone (hold: thing held by a character; reach: character to area; hidden: thing under thing; seated: character in a container or supporter; companion; exist; axis; know needs a character subject). 10b-2 (`build_round10b2_manifest.py`, 156k tokens) added `factory/checks/world_need.py` (`python -m factory.checks.world_need CONTRACT [--story ROOT] [--json OUT]`, exit 0 only when every need is ok) and three optional need fields in the contract lint (`subject_kind`, `object_kind`, `role` = `relies_on` or `creates`); `factory/contracts/**` is now frozen. Outcomes: `ok`, `worldkeeper_ticket` (known kinds, relation unsupported), `story_hole` (unknown kind, undeclared fact, nothing earlier produces a fact the scene relies on, nothing later reads a fact the scene creates). Questions 2 and 3 apply to `know` needs only, using `producers` and `consumers` plus the other scenes of the same contract; hold, reach, hidden and seated custody stays with the gap rules after the scene is written. I probed it on the real story (177 facts, 99 with a producer and a reader, 13 with no producer): a produced and read fact is ok, an unproduced one and a created fact nobody reads are story holes. One small oddity: a `creates` need on a not-yet-declared fact also says "fact is not declared"; the spec limited that reason to `relies_on`. Tests: 186 pass across the contract, world-need, frozen-harness and worldkeeper suites. Not done: judge calibration (round 10c) and the station handlers.

**Step 4, round 10c: judge calibration, 2026-11-19 (branch `factory-contracts`).** One Ringer run, two parallel Codex tasks, both passed first try (`build_round10c_manifest.py`, 170k tokens). All of it is free and deterministic; no billed model was called. New package `factory/judges/` (already frozen): `stats.py` (Wilson interval; `corrected_lower_bound` and `gate_passes`, which correct an observed rate for the judge's sensitivity and specificity and pass only on the conservative lower bound), `calibration.py` (`python -m factory.judges.calibration --labels FILE`; measures saved judge output against the author's labels exactly as `check_calib.py` does, returns confusion counts per label, writes error rates as JSON, and never writes into `bench/`), `lock.py` (content-hash lock over the judge scripts, label files and `check_calib.py`: `write` and `check`, changed, missing and new files reported), and `agreement.py` (deterministic second-judge slice, disagreement above 3 in 100 pauses a judge, a paused judge stays paused until cleared, the stricter verdict applies while paused). Independent check by the task: the new `measure()` reproduces `check_calib.py`'s agree and total counts on the real round 9 corpus. Measured on that corpus (one story): continuity judge 137/142 agree (Wilson low 0.920), fact-tracking judge 248/251 (Wilson low 0.965); error rates for the corrected gate: continuity sensitivity 20/21 and specificity 117/121, fact-tracking sensitivity 40/41 and specificity 208/210. No lock file is committed; writing it is a pre-flight step. **Round 10 is complete:** contract lint, world-need check, `can_represent`, judge guards. Full suite on this branch: 4502 passed, 25 skipped. Still not built: factory station handlers 2 to 9, and the generated per-scene reading view.

**Step 5 prep, round 11a: free station handlers 2 and 5, 2026-11-19 (branch `factory-stations`).** Round 10 is merged (PR #789). Round 11a (`build_round11a_manifest.py`, one Codex task, 222k tokens over two attempts) built `factory/stations/`: `build_handlers()` returns handlers for station 2 and station 5, loadable with `python -m factory run --handlers factory.stations:build_handlers`. Neither handler calls a model. **Station 2** (`world_need.py`) reads the ticket payload's `contract` and optional `story_root`, runs `check_needs` for the ticket's scene and fails with one line per non-ok need; creating the Worldkeeper tickets (the Luna part) is not built, so the handler only lists them. **Station 5** (`free_gates.py`) runs cheapest first and stops at the first failure: source tree check and compile, gap-rule delta against `gap_baseline`, ruff on the changed `.py` files, then the listed tests. The carry-matrix gate (no stuck state) is not built, so it is not in the line yet. The first Ringer check failed through my own bug (`git add -A` staged the worker's notes file and the ownership guard rejected it), not the worker's output; I fixed the check and ran it in the surviving worktree: 51 tests pass, ruff clean, and a probe ran both real handlers on the real story. Not built: stations 0, 1, 3, 4, 6, 7, 8, 9, the carry-matrix gate, the generated per-scene reading view, pass 2 (lexicon), per-scene examples files. Next: station 6 (prompt snapshot, free) and the carry-matrix gate, then the billed stations behind a smoke test.

**Step 5 prep, round 11b: station 6, prompt snapshot, 2026-11-19 (branch `factory-stations`).** One Ringer task (`build_round11b_manifest.py`, 196k tokens over two attempts) built `factory/stations/prompt_snapshot.py`, free and with no model call. `python -m factory.stations.prompt_snapshot record --scene S --out DIR` saves the entry prompt and every beat prompt from `bench prompt`; the handler captures the ticket's scene again, diffs it against the payload's `baseline_dir`, and passes only when every added or removed line matches the payload's `allowed_changes` (a capture name, `entry`, a beat id or `*`, plus the substrings that are allowed; `new_capture: true` lets a capture appear or vanish). With no `allowed_changes`, nothing may change. Station 4 is meant to record the baseline before wiring starts. The failure again came from my probe (a `\n` inside an f-string became a real newline), not the worker; I fixed it and ran the check in the surviving worktree: 47 tests pass, ruff clean, and the probe recorded a real 1B baseline, passed it unchanged, failed it on one added line naming the capture, and passed it when that line was allowed. `build_handlers()` now returns stations 2, 5 and 6. A harmless `runpy` warning appears when the module runs as `-m` because the package `__init__` imports it. Not built: stations 0, 1, 3, 4, 7, 8, 9 and the carry-matrix gate.

**Round 11c: honest spend and limit waits, 2026-11-19 (merged as PR #791).** Three Ringer tasks run in order, all free with no model call (`build_round11c1_manifest.py` to `11c3`, run name `factory-honest-spend`, 389k tokens in total). 11c-1 and 11c-2 passed first try. 11c-3 failed both attempts on my own check: it grepped the drill output for `PASS ... paid_usage`, but the drill prints a table row, `paid_usage | PASS`. I fixed the grep and ran the whole check in the surviving worktree, and it passed.
- **11c-1, `factory/limits.py`** (now frozen): reads Claude's last `rate_limit_event` and Codex's last session-log `rate_limits` into one `LimitReport`. Both providers use the window names `five_hour` and `seven_day`, with use as a fraction. `window_sleep` sleeps when a window is rejected or at its ceiling, until the latest reset. `paid_usage` flags Claude overage or a drop in Codex credits. The fixtures are trimmed copies of the real 2026-11-19 samples.
- **11c-2, guard and ledger:** each ledger row has a `cost_kind`: `dollars`, `subscription` (`usd` empty, Claude's list price kept as `list_usd` for information) or `unknown` (a reported provider that returned no cost). Dollar caps and breakers sum dollar rows only. `factory.json` has `caps.providers`: `claude_code` and `codex` are subscriptions, and their ceilings ship at 0.0, which means "not set"; `cloudflare` is `reported`. Before each subscription call, the guard sleeps the lane to its reset if the last report is past a ceiling. 429s retry five times about 45 to 60 seconds apart, and overloads retry at 45, 90, 180 and 300 seconds. Neither retry writes a ledger row. A `ProviderLimit` that carries a report sleeps to the rejected window's reset. A credit drop or overage is stored on the row as `paid_usage`. Preflight now needs both window ceilings in (0, 1) for each subscription, and daily dollar caps only for reported providers.
- **11c-3, lanes and breakers:** `FactoryState.limited_since` keeps the reported reset, or the first limit when none was reported. Later probes never move it, and it is cleared on the next normal return from that lane. `provider_overdue` counts from it. The probe drove a real line, probing every 30 minutes past a six-day reset, and the breaker fired exactly at reset + 24 h. A new breaker, `paid_usage`, reads the ledger. The budget reason says "a minimum" when some rows have unknown cost. `python -m factory wake PROVIDER` clears the lane and wakes its sleeping tickets. It keeps `limited_since`, so the overdue clock survives a wake. `status` shows window use and limited lanes. The drill now trips nine breakers.
- **Lesson for the manifests:** before a run, test every grep in the check against real output from the command it reads.
- Known edge: a lane named only by `LimitSleep.provider` (the ticket has no provider) is slept, but a later success does not clear its `limited_since`, because the line only knows the ticket's provider. No station hits this today.
- Not built: stations 0, 1, 3, 4, 7, 8, 9, the carry-matrix gate (round 12 below, attempt 7 passed, applied on branch `factory-carry-matrix-attempt7`), the generated per-scene reading view, pass 2 (lexicon), and per-scene examples files. The station handlers must build `CallResult.limits` from the readers: the Claude stream for Opus and Sonnet, and `find_codex_session(thread_id)` for Luna.

**Round 12: carry-matrix gate, 2026-11-19 (attempt 5 merged as PR #792; attempt 7 passed and is applied, uncommitted, on branch `factory-carry-matrix-attempt7`).** Brandon chose the carry matrix as the next build, the last free check of station 5. One Ringer task (`build_round12_manifest.py`, run name `factory-carry-matrix`, Codex at high effort, no model call) builds `factory/checks/carry_matrix.py` and runs it from `free_gates.py` (on by default, `"carry_matrix": false` turns it off). It walks the scenes in order from the real start. It keeps every distinct entry state, keyed by the facts the package reads plus custody. From each state it runs a thorough player, one run preferring each player-visible realization, and a stall of the length of each pressure-event turn followed by the thorough player. A cell is stuck when the scene never changes, or a non-stall run leaves by a forced or timer exit, or a stall left enough turns for the default run and still left by force. A stall that ran out of time is reported as late, not stuck. The worker also measures today's story; that count is a finding for step 6, not a test. The first attempt was stopped: keyed on every fact the story reads anywhere, 2C reached 201 entry states (over the cap of 200) after 325 s. Relaunched with each entry state compared only on the facts that scene or a later scene reads, starting from the first attempt's files. That second attempt was also stopped: 1A had 1 entry state, 1B 8 (with 8 stuck cells, not yet read), and 2B again passed 200. A read-only diagnosis (`build_round12_diag_manifest.py`, report in `ringer-work/factory-carry-matrix/diag-2b-states/report.md`) walked 1A to 2A with no cap: entry states grow 1, 8, 27, 192, 908. Most of the splitting is bookkeeping: `knowledge_narrated` records for earlier-scene realizations (30 variants) and `story_elapsed_seconds` (19 values), neither read in 2B or later. Keyed on forward-read true flags only, 2B has 120 states; adding the custody, visibility and world-effect facts (`wk_parent`, `wk_relation`, `wk_place_text`, `wk_hidden`, `world_effects_applied`) gives 380. Even the good key leaves a product of choices across scenes, about 20 rollouts of about 3.5 s per state, so the full product is too slow for a per-change gate. Brandon chose (2026-11-19): **one branch at a time per change, pairwise nightly.** Per change (station 5, mode `one_branch`): each scene's entry states are the default path plus every state reached by one choice (one preferred realization or one stall) in an earlier scene, then default play. From the default entry every rollout runs. From the one-choice entries, only the default and the stalls run. Nightly (mode `pairwise`, its own workflow `carry-matrix-nightly.yml`, 330-minute limit, outside the coverage job): every pair of choices in two scenes is played and followed to the end. The key is forward-read true flags plus `wk_parent`, `wk_relation`, `wk_place_text`, `wk_hidden` and `world_effects_applied`. Random sampling was rejected because it would give different answers on the same story. Third launch built the one-branch and pairwise modes (files kept in `ringer-work/factory-carry-matrix/attempt3/`), but its tests were far too slow: a real-story test reaching 2B took 172 s, and one scene run takes about 3.5 s. Brandon stopped it: "These tests are WAY too slow", and the scripted runs repeat the same turns many times over. **Redesign (Brandon approved, 2026-11-20): a state map per scene.** A point is a distinct state inside the scene, and a step is one thing the player can do on a turn (pick one offered candidate, or wait). Each step from each point is played once; a step that lands on a known point joins it. A point is stuck when no sequence of steps from it reaches an earned exit. That is the plan's own definition, and it needs no scripted policy or stall rules. The map's distinct exits are the next scene's entry points. The existing realization journeys become a subset. Before building it: a profile of one run (`build_round12_profile_manifest.py`) and a map-size probe for 1A and 2B (`build_round12_map_manifest.py`). The rebuild will put time budgets in its check and run its logic tests on the fixture story. Result: the profile measured 105 to 150 ms per turn and 0.03 ms per snapshot restore, and 14 to 36% of turns in each scene from 1A to 2B were repeats. The map probe did not converge: after 14 minutes, 1A had 4,600 points with 3,299 waiting. Brandon stopped it and chose the fallback (2026-11-20), an **exit search**. From each entry state, a depth-first search stops at the first earned exit. From the default entry, every single-step deviation from that path is also searched. A memo shared within a scene means a point proved good is never searched again. The point identity keeps only the last two turn records in order (the full ordered list stopped the map from merging). The check enforces budgets: the whole-story gate under 240 s and the quick tests under 20 s, on a small story. The fourth launch passed on the real story (139 s, 0 stuck, quick tests 13.5 s) but failed its own check on a broken story: with 3A's exit made impossible, all 13 entry states into 3A spent their full 300-point search budget, taking 524 s, and station 5 ran it again, past the check's 1200 s limit (files in `ringer-work/factory-carry-matrix/attempt4/`). Fifth launch, from those files: the search budget is set from the measured largest earned search (three times that, at least 30), `one_branch` stops after the first stuck scene and lists the later scenes as not run, and the check requires a broken 3A to fail station 5 in under 240 s with 3B and 3C not run. **Result: the fifth launch passed on its first try (26 min).** A search run with a budget of 1000 found that the largest search reaching an earned exit used 13 new points, so the default budget is 39. The whole real story: 69 entry states (1A 1, 1B 2, 1C 2, 2A 6, 2B 8, 2C 11, 3A to 3C 13 each), 178 searches, 913 turns, 0 stuck, 139 s. A broken 3A failed station 5 in 123 s, with all 13 entry states into 3A stuck and 3B and 3C not run. Quick tests: 20 in 15.9 s on the two-scene fixture story. The 8 stuck 1B cells of the second attempt do not appear under the exit search, so they came from that design's scripted runs. The patch is applied on the branch, and `tests/shard_durations.json` lists the new test file. **Brandon rejected attempt 5 (2026-11-20):** "the tests should be correct AND fast, but you didn't offer a method to keep both test features intact." Attempt 5 bought its speed by giving up correctness in two ways. (a) A search that runs out of budget is reported as stuck, so with the budget at 39 a story edit that makes a scene's shortest exit longer than 39 points of search is a false failure. (b) Stopping after the first stuck scene hides stuck cells in later scenes when only some entry states are stuck. It saved nothing in the seeded test: with all 13 entry states into 3A stuck, 3B and 3C had no entry states anyway.

**Attempt 6 (launched 2026-11-20, `build_round12_attempt6_manifest.py`, stopped by Brandon).** Keep every check and stay fast both when the story is good and when it is broken:
1. *Static check first.* For each scene, take each earned exit's trigger facts. Ask whether each one is true at entry or has a producer that can fire in that scene, using `producers()` in `storygame/story_package/dependencies.py` (the gap gate already uses it). If no earned exit can have all its triggers met, the scene is stuck, proved in milliseconds with no turns played. A "maybe" answer goes to the search as now. This catches the seeded broken 3A at once.
2. *Three outcomes, never "ran out" as stuck.* A cell ends `earned`, `stuck` (proved by the static check or by a complete search) or `undecided` (budget spent). Raise the budget back to 300. Search an undecided cell again with no budget, and only that cell. On a healthy story no cell is undecided (the largest earned search measured needs 13 points), so the passing gate stays at about 139 s.
3. *No early stop.* Later scenes run from every entry state that did exit. A scene left with no entry states is reported `unreachable: every way in is stuck in <scene>`, not hidden and not listed as not run.
4. *Only if step 2's no-budget searches measure slow:* relevance pruning. A step whose effects touch none of the facts the scene's exits depend on (taken transitively through the conditions of the storylets and events that produce them) counts as a wait, and the point identity keeps only relevant facts plus turn and pacing fields. Fewer points to search makes complete searches cheap. This is sound only if the relevant set is a complete over-approximation, so time step 2 on a seeded deviation trap first.
Check for attempt 6: the seeded broken 3A is caught by the static check (well under a second on top of the walk of 1A to 2C); a seeded trap after one deviation is reported `stuck` by the search, not `undecided`; a seeded scene whose real exit needs more points than the budget passes through the no-budget search instead of failing; 3B and 3C are reported unreachable when all of 3A is stuck; the whole real story under 240 s; quick tests under 20 s on the fixture story.

**Attempt 6 result (stopped).** Steps 1 to 3 worked: the static check, three outcomes and unreachable scenes. Step 2's no-budget re-search started again from the entry, so every turn of the budgeted pass was played twice: at `--search-budget 3` the real story played 1,972 turns (913 at the default) and took 294 s, over 240 s. The first try reached for step 4's pruning to get under the budget; that dropped the deviations (69 entry states fell to 19) and the check failed it. Early in that try the static check also wrongly marked all 13 entry states of 3A stuck on the real story; the worker fixed that before the check ran. Brandon asked why the run kept rerunning tests and stopped it. Lesson: step 4 was the wrong fallback, because skipping steps trades correctness for speed again.

**Attempt 7 (2026-11-20, `build_round12_attempt7_manifest.py`, passed first try, 32 min, 197k tokens).** It starts from attempt 6's files (`ringer-work/factory-carry-matrix/attempt6/`), deletes relevance pruning and adds a step cache per worker and scene: (point identity, step) maps to the played result and the child snapshot, shared by the budgeted pass, the no-budget re-search and the deviations, so no turn is played twice. The cache uses the same identity the memo already uses to merge points, so it makes the same assumption as the memo and no weaker one. Results: the real story at the default budget 300 had 69 entry states, 913 turns, 0 stuck, 0 undecided, 127 s. At budget 3 it had the same 69 entry states, 913 turns, 92 undecided all earned unbounded, 642 cache hits, 128 s. A broken 3A failed station 5 once: all 13 entry states were proved stuck by the static check in 0.01 s, and 3B and 3C were reported unreachable. Quick tests: 23 in 14.3 s. Patch: `ringer-work/factory-carry-matrix/attempt6-out/carry-matrix-attempt7.patch`; notes in the same folder.

**Round 12 merged (PR #793, 2026-11-20).** First pairwise nightly on the new code (`carry-matrix-nightly.yml`, run 44758365713, started by hand): passed, 290 entry states, 3,546 searches, 18,536 turns, 0 stuck, 0 undecided, 55 min. 3A took 32 min of it.

**Nightly suite repair (2026-11-20, paused for Brandon; resume here).** `coverage nightly` (`coverage-nightly.yml`, all tests with `--run-nightly`) has failed every night since 2026-11-02; the last green run was on `1abb54b008` (2026-11-01). About 120 tests fail, the same ones each night.
- **Diagnosis done** (`scripts/ringer/build_nightly_journey_diag_manifest.py`, report in `ringer-work/nightly-journey-failures/report.md`). Commit `06b2ccb3` ("Rebuild 3C as a finite evacuation that ends the game", in PR #745) made `evacuation_complete` the ending, and the engine now sets `state.story_complete`. `_resolution_complete` in `storygame/personas.py` still looks only for the removed fact `resolution_complete`, so the scripted playthroughs never see the ending. I confirmed it: `test_the_default_policy_earns_the_whole_chain_without_a_deadline` passes at `06b2ccb3^` and fails at `06b2ccb3`. The verdict was stale tests, not a story defect. The diagnosis check itself failed on my own bug (`timeout` placed before the env assignments), not on the worker's answer.
- **Fix tried** (`scripts/ringer/build_nightly_journey_fix_manifest.py`, patches and notes saved in `ringer-work/nightly-journey-failures/fix/`: `personas-one-line.patch`, `journey-fix-full.patch`, `NOTES.txt`). The working part is one line: `return state.story_complete or _RESOLUTION_FACT in _true_facts(state)`. It takes `test_game_path_journeys.py` and `test_evidence_gap_journeys.py` from 101 failing to 87 passing and 14 failing, in about 125 s with `-n 16`. The check failed only on limits I guessed (at least 90 passing, at most 10 failing); all 14 are reported in `NOTES.txt`. The worker also added `OPTIONAL_FINAL_RESOLUTION_REALIZATIONS` to `tests/test_game_path_journeys.py`. Leave that out: the four cases it covers still fail, so it does nothing until the 3C decision below.
- **Next step 1 (recommended):** commit only the one-line `personas.py` fix and open a PR. That clears 87 of the 101. Nothing else changes.
- **Next step 2:** a read-only Ringer diagnosis of the ten earlier storylets that are never offered when a playthrough prefers them: `k_sl_1a_b_r1`, `k_sl_1a_f_r2`, `k_sl_1a_f_r3`, `k_sl_1a_j_r3`, `k_sl_1a_k_r1`, `k_sl_1b_g_r1`, `k_sl_2a_g_r1`, `k_sl_2a_h_r1`, `k_sl_2b_g_r1`, `k_sl_2c_g_r1`. They passed on `1abb54b008`, so find the commit that broke each one, and say whether the story or the playthrough script is wrong. Some may be real unreachable content. The carry matrix would not catch that, because it checks for stuck scenes, not for content that is never offered.
- **Decision for Brandon (step 3):** four optional 3C storylets look unplayable: `k_sl_3c_d_r1`, `k_sl_3c_d_r2`, `k_sl_3c_e_r1`, `k_sl_3c_e_r2`. They need `captives_reaching_surface`. The worker says only the escape sequence after the ending sets it (`source/scenes/3C.yaml` around 876-1151 and 1241-1256), and the game stops responding once the evacuation completes (`storygame/runtime/engine.py:469-474`). I have not traced this myself. If it holds, either drop them or move what they need before the ending.
- **Step 4, later:** the other nightly failures have separate causes (report, "Other failures").
  - Same 3C rebuild: the 3C probe expectations in `test_3c_item_facts_capture` and `test_3c_world_capture_wiring`.
  - Already failing before `06b2ccb3`, a stale saved 3B starting state: `test_3c_carried_start`, `test_3c_no_close_arm`, `test_3c_state_compare`.
  - Later regressions, each with its own cause and not yet narrowed to a commit: `test_environment_screen` (no place named `kitchen`), `test_drain_details_capture` (expects the old `plot.md`), `test_hidden_bench_1b2_capture` (old source format), `test_cue_escalation`, `test_recent_cue_unit`, `test_knowledge_leakage_matrix`, `test_bench_item_facts`.
- Side finding: `tests/test_persona_escalation.py::test_persona_cli_writes_json` spends 57 s in setup on unchanged main.
- Lesson for manifests (third time this round): run every check line against real output before launch, and set pass-count limits from a measured baseline, not a guess.

### Pre-flight: everything you do, all before start

- [ ] Confirm headless Claude Code runs Opus and Sonnet on your subscription, not on API billing
- [ ] Set the total dollar budget (Cloudflare) and its daily cap
- [ ] Set the weekly and five-hour use ceilings for Claude Code and for Codex, leaving room for your own use of both, and the Opus call caps
- [x] Turn off paid extra usage on Codex and Claude (done 2026-11-19); recheck that both are still off before start
- [ ] Give the factory a way to reach you for a circuit breaker
- [ ] Write the judge lock (`python -m factory.judges.lock write`) so the frozen judge questions are fixed
- [ ] Press start

After delivery: play the game, then promote it to production if you like it.

## Risks and open decisions

| Risk | Why it matters | Default the factory runs with |
| --- | --- | --- |
| The run ends at the budget, not at a delivered game | Full autonomy removes the person who would unstick it | Escalation ladder, set-aside and return, and a final report of what is red |
| Judges stand in for your taste | Emotional beats and fun are the hardest things to judge by model | Five candidates per tentpole; frozen questions; second-judge agreement check; pairwise picks |
| Zero stuck turns is proven structurally but only sampled live | A phrasing no playtest tried could still loop | Carry matrix on every state; blind-player personas with varied phrasing; any live stuck turn blocks |
| Harsher delay costs meet protected characters and canon | A cost could harm Michelle or spend a character needed later | Protected list lint; harm ladder in each act contract |
| Longer scenes raise playtest cost | 10 to 13 turns per scene roughly doubles narrator and judge calls per run | Scripted prefixes, three-replicate smokes, twelve only at adoption |
| Lexicon derivation may not reproduce today's matcher and guard lists | Parity fails, or overrides pile up. About half of 1A's matcher words are bespoke, and 3A to 3C have almost no repetition to remove | Pass 1 keeps explicit lists, so parity never depends on derivation. Pass 2 is per scene, starts on 1A to 2C, and a field with more than a third overridden stays explicit |
| New gap-rule results block factory changes | It amends the spirit of D3 | On for the factory; CI stays non-blocking |
| No human reads code diffs | Ringer's README advises against it | Fresh-context diff reviewer for engine and Worldkeeper; ownership lists; coverage gate |
| Opus, Sonnet and Luna call volume on subscriptions | A spent window stalls the factory and locks you out of your own tools; Codex credits could be drawn | Live window figures from each call, use ceilings below 100%, sleep to the reported reset, credit-drop breaker |
| Old saves | The migration changes package identity | Stale saves are rejected, as the loader does today |

### What I did not verify

- I read the README, PRD, guides, the redesign and reimagination plans, the 1A draft and the repo layout. I did not read all of `.plans/` or the engine modules line by line.
- I did not run tests, the bench or the game.
- Jev accuracy figures are yours, from one story.
- The Serena page lists YAML and Markdown among its languages but [does not say how deep symbol support goes](https://github.com/oraios/serena) for them, which is one more reason to prefer the story CLI for story edits.

### Sources

- [bcorfman/freytag-forge](https://github.com/bcorfman/freytag-forge) at `eac9d666`: `README.md`, `docs/PRD.md`, `docs/jev-guard-rules.md`, `docs/scene-fixing-guide.md`, `docs/story-gap-guide.md`, `.plans/story-data-redesign-plan.md`, `.plans/story-data-1a-draft.md`, `.plans/game-reimagination-plan.md`, `.plans/game-reimagination/whole-story-pacing.md`, `.plans/implementation_plan.md`
- [NateBJones-Projects/ringer](https://github.com/NateBJones-Projects/ringer)
- [oraios/serena](https://github.com/oraios/serena)

* [ombharatiya/ai-system-design-guide](https://github.com/ombharatiya/ai-system-design-guide) at `10bdeb25`: loop engineering, evaluating agentic systems, LLM evaluation, eval-gated CI/CD, model selection guide. Many of its figures are vendor-reported.
