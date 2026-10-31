# Numbers and test limits

Part of [the Jev guard rules](../jev-guard-rules.md).

## Where the numbers come from

Each score is the share of answers that matched a person's hand check. "New data" means story turns that no setting was ever tuned on.

| Question type | Jev | Bigger model (GPT-5.6 Luna) |
|---|---|---|
| Fact questions, earlier rounds | 93% | 93% |
| Fact questions, new data | 95% | 97% |
| Story-sense questions, earlier rounds | 91% | 96% |
| Story-sense questions, new data | 93% | 97% |

These results used Jev version `jev-1.13.0`, reached through Cloudflare Workers AI as `typesafe/jev`. Claude checked the new-data answers using the author's written rules. The author did not check them directly. All results come from one story, so test on your own data before you rely on them.
