# Jev as a Guard Model

When can a cheap yes/no model check the work first? And when should you pass the job to a bigger, smarter model?

These rules come from that test. They are a starting point, not proven law.

- **What Jev is:** a fast model that answers yes/no questions about a piece of text. It also gives a number for how sure it is.
- **Cost:** $0.042 per million tokens it reads. That is about 1/15 of the cost of the model we compared it to.
- **Our test:** about 800 hand-checked answers from one interactive story.
- Jev is a strong, cheap first check for "Is this thing actually in the text?" It is a weak check for "Does this make sense, given everything that came before?"
- These results used Jev version `jev-1.13.0`, reached through Cloudflare Workers AI as `typesafe/jev`. Claude checked the new-data answers using the author's written rules. The author did not check them directly. All results come from one story, so test on your own data before you rely on them.

Read the detail file that matches the task:

- [When Jev works well](jev-guard-rules/when-jev-works-well.md): read this when deciding whether a proposed yes/no check is a good fit for Jev.
- [When to use the bigger model](jev-guard-rules/when-to-use-bigger-model.md): read this when deciding whether a question should be passed to the bigger model.
- [Setting up the guard](jev-guard-rules/setting-up-the-guard.md): read this when designing prompts, routing, confidence handling, or model-version tracking.
- [Test context and question types](jev-guard-rules/test-context-and-question-types.md): read this when you need the story-game setup or definitions of fact and story-sense questions.
- [Numbers and test limits](jev-guard-rules/numbers-and-test-limits.md): read this when checking benchmark scores, noise, provenance, or limitations.
