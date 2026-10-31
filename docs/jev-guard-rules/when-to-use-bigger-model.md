# When to use the bigger model

Part of [the Jev guard rules](../jev-guard-rules.md).

## Jobs to pass to the bigger model

1. **The answer depends on what happened earlier.** "Did this contradict something from three turns ago?" "Is she already in this room?" Jev has to rebuild the whole story in its head, and it slips. On these questions it trailed the bigger model by about 4 to 5 points.
2. **Your rules have special exceptions.** For example, "looking at something counts as done even if she also picks it up," or "trying counts." Jev takes words at face value. Writing the exceptions into the prompt did not help.
3. **You need it to find things you did not ask about.** "Did the narrator make anything up?" Jev can only answer the questions you give it. It cannot list surprises.
4. **You would train a small model on Jev's answers from one set of data.** We tried this. It looked 3 points better on our old data. Then it broke badly on new data. Hand-written rules held up. The trained version did not.
