# V2 staged and production acceptance matrix

This is the manual acceptance checklist for each frozen genre fixture in
staging (`/dev/`) and production (`/`). Record the deployed SHA, channel,
fixture, timestamp, and request/response evidence. The current workflow
automates deployment identity, hosted E2E, and its named V2 test slice; it does
not emit this complete matrix. Production evidence is valid only for a SHA that
first passed staging.

| Fixture | Opening | Freeform turn | Malformed model | Save/load | Protected revelation | Session isolation |
| --- | --- | --- | --- | --- | --- | --- |
| Mystery investigation | Required | Required | Required | Required | Required | Required |
| Fantasy journey | Required | Required | Required | Required | Required | Required |
| Sci-fi technical crisis | Required | Required | Required | Required | Required | Required |
| Relationship social scene | Required | Required | Required | Required | Required | Required |

| Check | Passing evidence |
| --- | --- |
| Opening | New session returns public opening prose and initial state. |
| Freeform turn | An unconstrained move succeeds and commits only valid state. |
| Malformed model | Typed fail-closed error leaves state and persistence unchanged. |
| Save/load | Loading restores the saved V2 snapshot. |
| Protected revelation | Protected content is absent from output and rejected from updates. |
| Session isolation | Sessions and deployment channels cannot observe or mutate one another. |

[`deployment/channel-contract.json`](../deployment/channel-contract.json) and
its tests enforce root/`/dev/` channel isolation before deployment claims.
