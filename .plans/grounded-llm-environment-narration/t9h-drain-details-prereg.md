# T9h drain-details prose screen preregistration

Frozen before any output exists. Written 2026-10-30 for the P3 cheapest billed
check. The probe does not edit `plot.md`, the story package, or any runtime
enforcement code.

## Question

Does adding one grounded SCENE Details suffix about the existing storm-drain
opening reduce the unsupported drain-affordance prose produced for the ordinary
imperative request `inspect the storm drain`?

## Prompt provenance and edit

The billed control is the exact `system` and `user` text recorded in
`bench/results/environment-narration/t9h-hidden/smoke/rows/rows.json`, replicate
0, turn 5, whose input is `inspect the storm drain`, using the first prompt
whose system text starts with `You are the narrator`. The probe fails if the
rendered SCENE Details block is not found exactly once.

The candidate copies that request and makes one edit only: the rendered Details
material gains the suffix `; storm drain opening in the damaged grounds`.
Control and candidate must be identical everywhere else. The offline
`drain_details_capture.py:capture_arms()` control/candidate captures are also
checked for the same one-phrase material difference. The recorded prompt is the
billed control; agreement between it and the offline control prompt is reported,
not used to replace the recorded source.

## Design and caps

There are two arms, control and candidate, with 10 independent narration
samples per arm: 20 narration calls by default. The default command caps are
`--max-calls 20` and `--max-usd 0.03`; the historical estimate is approximately
$0.014. `--samples 15 --max-calls 30 --max-usd 0.04` is the separate later
15-per-arm confirmation design. The wrapper defaults to 10 samples and never
starts that confirmation.

Each request uses the project narration path and the recorded system/user
prompt unchanged apart from the candidate suffix, with the same request
parameters as `hidden_bench_prose_probe.py`. There are no negative command
restraints. The model is the project Worker's 70B narrator. The blind sheet is
shuffled with a fixed `SHUFFLE_SEED`; the labels file is frozen with a SHA-256
sidecar before report use.

## Labels and gate

The human reads every returned narration and labels each row independently with
these six booleans:

- `opens_or_enters_drain`
- `invents_ajar_or_cover_state`
- `asserts_definite_contents`
- `speculative_only`
- `wrong_place`
- `capture_prose_disagree`

The control reproduces the defect when at least one row has any of the first
three labels. The candidate passes the screen only when zero candidate rows
have any of those three labels. A complete run with both conditions is
`screen: PASS`; a complete run with control reproduction but candidate defects
is `screen: FAIL`; if control does not reproduce the defect, or the run is
partial, the result is `control did not reproduce the defect: INCONCLUSIVE` or
another explicit inconclusive status.

One passing screen is not an enforcement guarantee. The 15-per-arm confirmation
is a separate run and must be reviewed separately before any enforcement claim.

## Stop rules and authoring boundary

The probe refuses to send unless `--run --confirm` is present. It checks the
planned call count and USD ceiling before the first request, refuses an existing
rows file, never overwrites or reruns a row, and stops on the first quota, 429,
5xx, or authentication failure. A partial result is reported as incomplete and
inconclusive; no sample is substituted.

The proposed `plot.md` Details edit is conditional on this screen and the
separate 15-per-arm confirmation. It is not applied by this probe. A passing
screen alone does not authorize the plot edit, a runtime guard, or promotion of
the full enforced stage.

## Addendum (2026-10-30)

The screen stopped at 19 of 20 rows because the local Worker's own budget
guard returned HTTP 429 at $0.0223 spent of the $0.03 cap; the Worker reserves
headroom per call. The user raised the cap for the separate 15-per-arm
confirmation to $0.06 with a 30-call limit. The confirmation is a new run in
`bench/results/environment-narration/t9h-drain-details/confirm`; screen rows
are never rerun or edited, and the same refuse-if-rows-exist and port-in-use
guards apply.

The gate is unchanged: control must reproduce the defect with at least one
forbidden row, candidate must have zero forbidden rows, and the run must be
complete. The `plot.md` edit remains conditional on the confirmation passing;
the screen result alone does not authorize that edit.
