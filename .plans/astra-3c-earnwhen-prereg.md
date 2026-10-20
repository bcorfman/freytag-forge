# 3C D-R2 earn_when screen preregistration (2026-10-20)

Source cause (bench/results/stage7-3c-semantic-replay/): with semantic fallback ON, the judge refuses plain
messages to the families ("broadcast to the families that the captives are safe...", "send the families the
confirmed prisoner lists...", "give them word...") 15/15, because it compares them with D-R2's earn_when
"calls the families of the missing". Control (existing alias match) and "Broadcast music to the families." behave correctly.

One source change, k_sl_3c_d_r2 only, knowledge.yaml:
  old: `earn_when: calls the families of the missing`
  new: `earn_when: calls, messages, or broadcasts news to the families of the missing`
Technique: missing story material stated in the authored sentence the judge and narrator read (scene-fixing guide);
no alias, matcher, guard or runtime change. action_evidence and statement unchanged. earn_when also feeds the
narrator's "Earn it when the player ..." constraint (cloudflare.py ~1526) and the prompt-example picker (~1043); the
build task must report any payload change beyond the one sentence.

Arms: `pump` (baseline, unchanged) vs `earnwhen` (pump + that replacement). NOT stacked on families / families-v2.

Stage 1, free + capped replay (gate): rerun scripts/ringer/stage7/three_c_semantic_replay.py on the `earnwhen` arm,
cases 1-6 plus negatives (music, "Send the families into danger.", "Broadcast the reports to the families." with D1 open,
"Tell the journalists the captives are safe."), 3 runs each, cap 40 Cloudflare calls. Gate: cases 1-4 matched >=2/3,
all negatives refused 3/3, case 5 exact. If the gate fails, STOP: no n12, report.

Stage 2, billed: carried start, n=12 per arm interleaved, semantic ON, deadline 14, 20 attempts, unchanged raw player,
caps 960 Cloudflare / 480 player, fresh dir bench/results/stage7-3c-carried-ew-n12/. No retries, replacements or pooling.
Win: >=10/12 earned, no false reveals/new grounding failures. Report the usual A/B/C/D/E, rejection, deadline measures
and the semantic_match count. Baseline pump already earned 10/12 once (v2 run); a 1-2 row gap is inconclusive, prefer pump
unless earnwhen is >=3 rows better or fixes the D2-miss rows without new failures. Nothing is adopted into data/.

## STATUS (2026-10-20): NOT RUN. Brandon dropped the screen as too shaky: no past semantic-fallback data for messaging phrasings,
cases 3/4 likely still refused, and pump already earned 10/12. Replay finding stays as the recorded source cause. No arm, variation or billed call was created.
