# Preregistration: Stage 7 2B Details-subtraction transition screen

Written 2026-10-18, before any billed run of this screen. Source of the change:
`.plans/astra-hardware-pull.md` (ChatGPT answer to `.plans/chatgpt-2b-hardware-pull-prompt.md`),
adapted by Brandon's choice because the story loader requires 3 to 7 Details items.
Harness: experiment `details` in `scripts/ringer/stage7/door_probe.py`, built on the
`transition` experiment (`.plans/astra-2a-grounded-transition-prereg.md`, which still
governs the player, the 20-command cap, the timer, clarification forwarding, the
disabled semantic fallback and the measures).

## Question

Does removing the 2B.1 elaboration targets (and adding one already-declared item)
raise the share of full 2B continuations that leave the scene by an earned transition?

## Change under test (one line, `plot.md`, Scene 2B.1)

- **baseline:** `**Details:** restricted records archive; unfamiliar system files; government data; financial data; Michelle’s research`
- **details:** `**Details:** restricted records archive; Michelle’s research; the Initiative’s selection files`

Removes three broad elaboration targets; adds "the Initiative’s selection files",
which the 2B entry text and `k_sl_2b_a_r1`'s wording already use. This is two
changes in one line (subtract three, add one declared item); a positive result
cannot say which did the work. Offline payload diff (`payload_2b.py`) shows the SCENE
bullets are the only difference in the 2B turn-1 user prompt.

## Arms (frozen)

- **baseline:** `bench/frozen/continuity-pre-details/` (byte copy of HEAD `1c08389d`
  before the edit; every file verified equal to `git show HEAD:`), via
  `bench/variations/stage7-details-control.json`.
- **details:** the current package, via `bench/variations/stage7-door-grounded.json`.
- Both arms use the SAME 2A prompt (recorded turn-7 prompt plus the derived panel
  additions; hashes identical across arms, checked in the dry run), the same
  authored bridge and 2B entry, the same raw player, and fresh 2B state. Arms
  interleave rep by rep.

## Sample, caps and spend

N = 12 per arm (24 rows), once, no extension. Hard caps unchanged from the
transition screen: 480 Cloudflare, 408 player requests. That screen used 319 and 297.
Cloudflare ceiling about $0.96 at $0.0020 per request (priced high on purpose);
player calls carry a request cap only. One Ringer task, one attempt; a cap, quota
or malformed-output error stops the run and is recorded; no replacement samples.
No smoke is repeated for this change: the harness is the already-smoked
`transition` harness, and the dry run plus payload diff cover the only new parts.

## Counted measures (deterministic)

`earned_exit`, `timer_exit`, `no_exit` per arm, from the runtime's `transition_cause`.
Reported as explanation, not acceptance: first-reveal turn, whether command 1
targets hardware or the terminals, hardware-chase length (commands before the
first command naming terminals, files, records, Michelle or Brandon), rows with a
clarification.

## Keep rule

The `details` arm is kept only if **earned_exit >= 10/12**. Because the baseline is
also sampled, the report also states `details - baseline` earned exits; a change of
less than 3 rows is called "not distinguishable at this n". With N=12 a true 80% rate
passes the bar about 56% of the time, so 9/12 is "borderline", not a failure. Do not
extend N after seeing results.

## Known limits

Same as the transition prereg: replayed 2A, fresh 2B state, semantic fallback
disabled, one raw-player prompt, one story. The change tests a source edit to
narrator input, not the player's choice of first command: 22 of 24 earlier first
commands were hardware, chosen from the 2A text, which this edit does not touch. If
first-command targets do not move, a positive result is unlikely and the lead is
the generated 2A unfinished task, or the semantic fallback (measure separately).
The 2B.1 Details edit is also one of several elaboration sources; the 2B
cue and the entry text are unchanged.

## Stop rules

Stop and report on malformed output, quota or outage, a cap error, a row that cannot
record `transition_cause`, or a dry run whose 2A prompt hashes differ across arms.
Record aborted attempts; no pooling with earlier screens.
