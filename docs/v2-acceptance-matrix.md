# V2 staged and production acceptance matrix

This acceptance matrix defines the same six checks for each frozen genre fixture
in both isolated channels. A production result is valid only for a SHA that
first passed the complete staging matrix and human review.

| Fixture | Opening | Freeform turn | Malformed-model failure | Persistence round-trip | Protected revelation | Session isolation |
| --- | --- | --- | --- | --- | --- | --- |
| Mystery investigation | Required | Required | Required | Required | Required | Required |
| Fantasy journey | Required | Required | Required | Required | Required | Required |
| Sci-fi technical crisis | Required | Required | Required | Required | Required | Required |
| Relationship social scene | Required | Required | Required | Required | Required | Required |

For every cell, run the check independently against `/dev/` + the staging API and `/` + the production API. A passing check records the deployed SHA, channel, fixture ID, request/response evidence, and timestamp. A production result is valid only for a SHA that first passed the complete staging matrix.

| Check | Passing evidence |
| --- | --- |
| Opening | A new session returns player-visible opening prose and initial state. |
| Freeform turn | An unconstrained player move returns a typed successful turn and commits only valid state. |
| Malformed-model failure | Invalid provider output returns the typed fail-closed error; state and persistence remain unchanged. |
| Persistence round-trip | Save, mutate, and load restores the saved V2 runtime snapshot. |
| Protected revelation | Protected content is absent from visible output and rejected from invalid updates. |
| Session isolation | Two sessions, and the two channels, cannot observe or mutate one another's state. |

The checked-in channel contract is [`deployment/channel-contract.json`](../deployment/channel-contract.json); its unit tests protect the root and `/dev/` isolation invariants before a workflow or deployment can claim compliance.
