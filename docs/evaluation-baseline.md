# Evaluation baseline

Phase 0 freezes a repeatable, deterministic starting point for later engine
changes. The fixture input is [evaluation_fixtures.yaml](../data/evaluation_fixtures.yaml).
It fixes the model identifier, prompt version, temperature, token limit, and
seed for each evaluation run.

## Fixture slices

| Fixture | Genre | What it covers | Seed |
| --- | --- | --- | --- |
| Mystery investigation | mystery | investigation and evidence | 101 |
| Fantasy journey | fantasy | travel and adventure | 202 |
| Sci-fi technical crisis | sci-fi | technical pressure | 303 |
| Relationship social scene | romance | social and relationship play | 404 |

Each slice initializes a package, saves and loads it, and replays its scripted
commands twice with the same result. Evaluation failures are derived from
structured artifacts, with categories for contradiction, impossible action,
hidden-information leak, role drift, causal omission, uncommitted narration,
repetitive scene pressure, and blocked player agency.

## Recorded baseline

Recorded 2026-08-06 on the repository test environment:

| Measure | Result |
| --- | --- |
| Full test suite | 557 passed in 55.59s, no warnings |
| Branch coverage | 90.14% |
| Local web ordinary turn | 10 stub-model calls; 268.9 ms |
| Hosted-demo ordinary turn | 10 stub-model calls; 11.7 ms |

The surface timings use FastAPI's in-process test client and the frozen
`phase0-deterministic-stub-v1` response. They measure orchestration rather
than network/model service latency. The call counts are the useful baseline:
later phases should reduce them while retaining fact validation and fail-closed
surface behavior.
