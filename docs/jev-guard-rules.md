# Jev as a Guard Model

When can a cheap yes/no model check the work first? And when should you pass
the job to a bigger, smarter model?

- **What Jev is:** a fast model that answers yes/no questions about a piece of
  text. It also gives a number for how sure it is.
- **Cost:** $0.042 per million tokens it reads. That is about 1/15 of the cost
  of the model we compared it to.
- **Our test:** about 800 hand-checked answers from one interactive story.

We used Jev to check a story game. Each turn, the player types a command and a
narrator writes what happens. We asked two kinds of questions:

- **Fact questions** check one object at a time: "Did the phone move?"
- **Story-sense questions** check the whole turn: "Did the narrator start the
  scene over?"

Jev did well on the first kind and worse on the second. These rules come from
that test. They are a starting point, not proven law.

## Jobs Jev does well

1. **The answer is right there in a short piece of text.** "Does this
   paragraph show the phone moving?" Asked one object at a time, Jev matched
   the bigger model.
2. **Code can do the counting and comparing.** Let your code compare lists,
   count things and combine answers. Ask Jev only the part that needs reading.
   Our fact checks worked because code compared the "before" and "after"
   lists.
3. **The job splits into small yes/no questions** that each make sense alone.
   Make "yes" always mean the thing you are looking for.
4. **You plan to act on how sure it is.** When Jev was sure (its number was far
   from 0.5), it was right about 95% of the time. When it was unsure, it was
   right only about 76% of the time. Its "sure" number means something. Use it.
5. **You need the same answer every time.** Asking the exact same question
   twice changed fewer than 1 answer in 100.

## Jobs to pass to the bigger model

1. **The answer depends on what happened earlier.** "Did this contradict
   something from three turns ago?" "Is she already in this room?" Jev has to
   rebuild the whole story in its head, and it slips. On these questions it
   trailed the bigger model by about 4 to 5 points.
2. **Your rules have special exceptions.** For example, "looking at something
   counts as done even if she also picks it up," or "trying counts." Jev takes
   words at face value. Writing the exceptions into the prompt did not help.
3. **You need it to find things you did not ask about.** "Did the narrator
   make anything up?" Jev can only answer the questions you give it. It cannot
   list surprises.
4. **You would train a small model on Jev's answers from one set of data.** We
   tried this. It looked 3 points better on our old data. Then it broke badly
   on new data. Hand-written rules held up. The trained version did not.

## How to set up the guard

- **Send up one question at a time, not the whole job.** A task made of 12
  small answers almost always has one unsure answer. If any unsure answer
  sends the whole job up, you save very little. In our test, 2 out of 3 jobs
  would have gone to the bigger model. Send up only the answers that are
  unsure.
- **Treat the two kinds of mistakes differently.** Say a false alarm is cheap
  but a miss is costly. Then trust Jev's sure "no" answers, and have the
  bigger model check every "yes." Flip that if the costs flip.
- **Try one sentence that says what the job is.** We added "You are a
  continuity editor for an interactive story..." Jev's score went up by about
  5 points, and the gain held up on new data. Example sets and long rule lists
  added nothing.
- **Give each question only what it needs.** Extra text did not help. A small
  input also makes a wrong answer easier to trace.
- **Measure the noise before you trust a gain.** Running the same test twice
  moved the score by about 3 answers in 100. Any gain smaller than that is not
  real.
- **Write down the model version every time.** The model's name can point to
  a newer version without warning. When the version changes, re-run a fixed
  set of checked answers.

## The short version

Jev is a strong, cheap first check for "Is this thing actually in the text?"
It is a weak check for "Does this make sense, given everything that came
before?"

## Where the numbers come from

Each score is the share of answers that matched a person's hand check. "New
data" means story turns that no setting was ever tuned on.

| Question type | Jev | Bigger model (GPT-5.6 Luna) |
|---|---|---|
| Fact questions, earlier rounds | 93% | 93% |
| Fact questions, new data | 95% | 97% |
| Story-sense questions, earlier rounds | 91% | 96% |
| Story-sense questions, new data | 93% | 97% |

These results used Jev version `jev-1.13.0`, reached through Cloudflare
Workers AI as `typesafe/jev`. Claude checked the new-data answers using the
author's written rules. The author did not check them directly. All results
come from one story, so test on your own data before you rely on them.
