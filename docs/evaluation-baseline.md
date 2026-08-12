# V2 evaluation baseline

The V2 baseline is the SHA-bound `staging-evaluation.json` artifact produced by
the `V2 staging evaluation and promotion gate` workflow. It uses the immutable
compiled-story fixtures for mystery, fantasy, sci-fi, and relationship stories,
and exercises investigate, travel, social, avoidant, adversarial,
repeated-failure, and unexpected-action styles.

The artifact records deployment identity, model and prompt revision, one-call
and repair rates, latency, typed failures, revelation and continuity findings,
completion, and session failures. It is valid only when the API channel and SHA
match the Pages `/dev/deployment.json` metadata. See
[the staging-evaluation guide](phase-5-staging-evaluation.md) for the gate and
human review process.
