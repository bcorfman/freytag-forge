# 3C families-v2 carried n12 preregistration (2026-10-20)

Arms: pump (baseline) vs families-v2 (pump + revised D-R2 recipient-qualified aliases, Step 7).
Start: carried (real 3B->3C crossing), semantic ON, deadline 14, 20 attempts/row, raw player unchanged.
n=12 per arm, interleaved. Caps: 960 Cloudflare / 480 player. Result dir: bench/results/stage7-3c-carried-v2-n12/.
Win: >=10/12 earned endings, no false reveals or new grounding failures. Differences under 3 rows are inconclusive; if both pass, prefer pump.
Measures: first-attempt A, B, both C by 10, D1/D2/E turns, rejections, deadline ids, fair movement.
If families-v2 earns 9/12: declare failure, inspect the failed rows, no pooling, no repeat samples, no more aliases from those sentences.
No retries or replacement rows; partial results preserved on failure. Nothing adopted into data/.
User authorized the billed run ("go ahead", 2026-10-20).

## RESULT (2026-10-20)
bench/results/stage7-3c-carried-v2-n12/, 12 rows/arm, 300/960 Cloudflare, 300/480 player, no run-failure file, checker OK.
Earned/deadline/none: pump 10/2/0, families-v2 9/3/0. Both C by 10: 12/12 each; rejections 0, clarifications 0.
pump meets the 10/12 bar; families-v2 misses it (9/12). The 1-row gap is not distinguishable, so prefer pump.
v2 earned-at-11 endings 7/12 vs pump 5/12 (earlier D2 at 8-9). v2 failures: rows 06 and 10 never earn D2; row 12 earns D2 at 12 and loses E at the 14 deadline (pump 07 same).
Decision rule: do not add aliases from these sentences, no pooling, no repeat samples. Next: inspect the three v2 failed rows. Step 6 (deadline 16) supported only if a failed row has both D earned by 14 and E reachable (row 12 is the candidate).
