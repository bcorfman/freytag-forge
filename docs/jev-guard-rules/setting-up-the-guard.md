# Setting up the guard

Part of [the Jev guard rules](../jev-guard-rules.md).

## How to set up the guard

- **Send up one question at a time, not the whole job.** A task made of 12 small answers almost always has one unsure answer. If any unsure answer sends the whole job up, you save very little. In our test, 2 out of 3 jobs would have gone to the bigger model. Send up only the answers that are unsure.
- **Treat the two kinds of mistakes differently.** Say a false alarm is cheap but a miss is costly. Then trust Jev's sure "no" answers, and have the bigger model check every "yes." Flip that if the costs flip.
- **Try one sentence that says what the job is.** We added "You are a continuity editor for an interactive story..." Jev's score went up by about 5 points, and the gain held up on new data. Example sets and long rule lists added nothing.
- **Give each question only what it needs.** Extra text did not help. A small input also makes a wrong answer easier to trace.
- **Measure the noise before you trust a gain.** Running the same test twice moved the score by about 3 answers in 100. Any gain smaller than that is not real.
- **Write down the model version every time.** The model's name can point to a newer version without warning. When the version changes, re-run a fixed set of checked answers.
