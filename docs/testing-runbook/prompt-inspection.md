# Prompt inspection

Part of [the testing runbook](../testing-runbook.md).

## 3. Prompt inspection (free)

**Purpose:** See exactly what the narrator receives, without a model call.

```bash
uv run python .plans/world-model-s1/prompt_capture.py /tmp/payload-before.json
# After the package edit:
uv run python .plans/world-model-s1/prompt_capture.py /tmp/payload-after.json
diff -u /tmp/payload-before.json /tmp/payload-after.json
uv run python -m bench prompt --scene 1A --text
uv run python -m bench prompt --scene 1A --beat 1A.2 --text --player-input "Search under the drawer in her workstation."
uv run python -m bench describe --variation bench/variations/authored-handoff-phase1.json --json
```

The capture script stubs the network and records 1A opening/turn payloads with
and without card custody. Unrelated scene edits should leave those captures
identical; inspect the affected scene separately. Delete the `/tmp/payload-*.json`
files after reviewing the diff.

For an existing live failure, inspect saved artifacts before making another
model call. For example:

```bash
uv run python -m json.tool bench/results/environment-narration/t9h/smoke/e/rows/summary.json
```

Read each turn's complete prompts and provider responses beside its narration,
errors, observation request and call timings. JSON parsing only verifies the
artifact shape. A flat parent map cannot verify relation changes or full
rollback; compare runtime snapshots and parent/relation/hidden/axis facts in a
network-free reconstruction when those fields were not recorded. Scene-start
helpers may use scripted journey checkpoints, which do not prove parity with a
live prefix. Keep diagnostic results in the active plan. Artifact inspection
is read-only, costs nothing and needs no cleanup; a live replay is billed and
follows [section 4](live-narration-bench.md#4-live-narration-bench-billed).

**Pass:** the prompt contains only material the scene has made available.
For an authored-handoff turn, private candidate metadata stays out of the
narrator request. The selected delivery sentence may be shown as the text the
game will append. Check the complete player text after runtime composition,
including delivery and cues.

**Notes:** Player inputs in scripts and examples are imperative commands
("Search the kitchen."), never first person. See the [player-input guide](../player-input-guide.md).
