## Findings

`door_transport.raw_request` now unwraps responses like the runtime parser, removes only `item_facts` from the validation copy, and preserves the original normalized reply on `RawProposal`. The removed value is telemetry and is written on successful live rows; it is never applied to runtime state or verdicts. Other unknown fields still produce parse failures and retain failed-response evidence. Offline coverage includes populated and empty item-facts replies, strict unknown-key rejection, and one-request accounting.

## Verification

The focused suite passed 202 tests. Ruff check and format passed. The requested 12-repetition dry run and checker are the remaining verification commands.
