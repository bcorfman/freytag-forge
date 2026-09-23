# Judge calibration corpus

This directory contains the author's labels for three saved judge runs. The
labels are an offline corpus for checking changes to the continuity and
fact-tracking judges.

`labels-round7.json` grades
`bench/results/item-facts-v8-two-scene-1a`. `labels-round8.json` grades
`bench/results/item-facts-v9-two-scene-1a`, using the author's comments in
`bench/results/round8.md` and its six explicit overrules. `labels-round9.json`
grades `bench/results/item-facts-v10-two-scene-1a`, using the author's
comments in `bench/results/round9.md`.

After producing `continuity-judgments.json` and
`fact-tracking-judgments.json`, score a run with:

```sh
uv run python bench/calibration/check_calib.py \
  --labels bench/calibration/labels-round8.json \
  --judgments path/to/judgments
```

The checker defaults to the label file's `results_dir` for both judgments
and `all-turn-records.json`, writes `calibration-report.md` beside the
judgments, and exits non-zero if either judge is below 90%. Use `--bar` to
change that threshold. `rejudge.py` can regenerate the two judgment files,
but it invokes paid model calls only when explicitly run.

These labels come from one story. Tuning a judge until it agrees with this
corpus does not show that it generalizes to another story.

An optional `superseded` block records labels that are kept for reference but skipped when scoring.
