# Review instructions

Review for the ways this engine fails. Style is Ruff's job.

## Checklist

For each item the diff can affect, say what you checked. The boundaries are
described in [runtime and authoring boundaries](docs/contributor-guide/runtime-and-authoring-boundaries.md)
and [gameplay, model, and interaction safety](docs/contributor-guide/gameplay-model-and-interaction-safety.md).

1. **Rejected turns change nothing.** After a rejected turn, facts are as they
   were before it, in memory and after a save and load.
2. **Narrator inputs stay bounded.** No protected knowledge the player has not
   earned, no future effects, and no transcript memory reaches a model payload.
3. **Providers only propose.** Every provider proposal passes validation before
   any fact is committed. A failed or malformed reply fails closed. Facts do not
   change after rendering.
4. **World logic lives in `World`.** A rule that reads or changes only world
   state is a `World` method in `packages/worldkeeper`, with its tests there.
5. **Shared runtime stays story-agnostic.** No story, character, premise or genre
   behavior outside validated package data.
6. **Story changes carry their snapshots.** Source edits came from the story CLI
   and the scene-entry snapshots were regenerated.
7. **Safety tests did not get weaker.** Look at every removed or loosened
   assertion, deleted test, and new skip or xfail, and say why it is right.

Story declarations and narrator prompts are behavior changes, even when the
diff is only YAML, Markdown or prompt text.

## Findings

Every finding gives:

- **Location:** `path:line`.
- **Failure scenario:** the concrete input or state, and the wrong result.

A concern with no failure scenario is a question, not a finding. Label it so.
If nothing survives, say so and list what you checked and what you could not.

## Risk tiers

[`.github/review-policy.yml`](.github/review-policy.yml) defines low, ordinary
and high. The "review risk" workflow writes a PR's tier to its job summary. To
compute it locally:

```bash
uv run python scripts/review_risk.py --base origin/main --head HEAD
```

The tier is advisory. It sets how much evidence a review needs and does not
approve or block a merge. A high-tier change needs evidence for each checklist
item it touches (a test or command and its result), and a fresh-session review.

## Fresh-session review

Required for high-tier changes; useful for any other.

1. Record the commit under review:
   `sha=$(gh pr view <number> --json headRefOid --jq .headRefOid)`.
2. Start a new session that did not write the change. Give it only this file,
   the diff (`gh pr diff <number>`) and the feature plan the PR links.
3. The review begins with `Reviewed commit: <full 40-character SHA>`. Post it as
   a PR comment.
4. Confirm the PR head is still `$sha`, then attach the result to that commit:

```bash
gh api --method POST "repos/{owner}/{repo}/statuses/$sha" \
  -f state=success -f context=fresh-review -f description="Fresh-session review: no open findings"
```

Use `state=failure` while findings are open. A commit status belongs to one SHA,
so a later push starts with no `fresh-review` status and needs a new review.

Nothing enforces this status. See
[ownership](docs/agent-workflow-guide.md#ownership) for who may merge.
