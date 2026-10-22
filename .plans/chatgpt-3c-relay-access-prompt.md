# Prompt for ChatGPT Desktop: relay audibility, return route after the flood, and Brandon's fate (scene 3C), plus one 2B cue line

Paste everything below the line into a fresh ChatGPT Desktop chat. It is self-contained.

---

You are helping finish the last scene (3C) of an interactive story. You cannot see the repository, so everything you need is here. Answer each question with a recommendation and exact text. Do not rewrite anything beyond what is asked.

## Where we are

An earlier round gave us a text that is now shipped. When the evacuation finishes, the game shows this once, after the facts commit:

> The captives have emerged into Los Angeles. News drones, civilians, and local responders begin arriving. Over the relay, Brandon tells you, "Reports from other detention sites are reaching the broadcast chamber. Families of the missing are calling there for news." The maintenance network still leads back to Rebecca's executive office. The broadcast chamber inside remains reachable.

Three things in it are not yet backed by the story. Part A asks you to settle them. Part B is one small unrelated cue line in scene 2B.

## Facts you must work inside (checked against the story files)

**Plot (3C.3 and 3C.4, verbatim):**
- "Michelle leads the prisoners through the maintenance tunnel while Kristin keeps the pumps and barrier working."
- "From Rebecca's office, Michelle uses the senior official's expiring authorization to release the emergency surface gates once. Brandon remains at the relay so the broadcast stays live. His fate is initially uncertain."
- "Thousands of captives emerge into Los Angeles as news drones, civilians, and local responders begin arriving."
- "Reports from other detention sites reach the broadcast chamber as families of the missing call for news."
- "Kristin's personal goal is fulfilled when she and Michelle are reunited, but neither can return to their former life."
- Charles's deluge is running. Kristin "cannot keep every route open." Water "closes the facility around them." The facility is lost.

**Places (the world model is a tree; every place has one parent):**
- The facility contains these areas: the **command levels**, which contain the **maintenance network** (the drainage pump controls sit here and the captives start here); the **executive office** (Rebecca's), which contains the **broadcast chamber**; the **Broadcast relay**, a separate area where Brandon is placed; and the **Los Angeles surface**, where the emergency surface gates are.
- Kristin starts scene 3C in the broadcast chamber. The scene's own location is the Los Angeles surface.
- The engine does not check that areas are connected. "Go to the broadcast chamber" works as a destination if the chamber exists and the model proposes the move. Nothing in the story declares a passage between the maintenance network and the executive office, and nothing declares a radio, speaker, intercom or earpiece for scene 3C.
- A new place, person or thing must be declared in the story files, and we avoid new names. Any noun your text uses as a place or a physical thing must already exist, or you must say exactly which noun needs declaring and where it sits in the tree.

**Mechanics:**
- The sentence about reports and the sentence about families are two optional "cues" that stay in the narration until the player acts on them. The player earns the reports moment by checking or reading the reports, and the families moment by calling or answering the families.
- The engine has no location rule for either one. Kristin does not have to be in the chamber for the game to accept them. Only the narration has to make sense.
- The reports and families facts are already true when the escape text shows, so the text may say they are happening now.
- Brandon is the only person placed at the relay. Michelle's position in the story is not fixed by the story files beyond the plot lines above.

**Evidence of the problem:** in the one recorded full playthrough, the player stayed in the tunnel and at the surface with Michelle and the captives after the gates opened, asking to lead them through the gates again for eight turns. The cues appeared but nobody was at the chamber.

## Part A: three decisions

1. **Can Kristin hear Brandon?** She may be at the pumps, in the maintenance network, at the surface gates, or in the chamber when the escape text shows. Pick one of these and say why the others fail: (a) state, in the shipped line, that the relay carries over the facility's own emergency speakers, naming only things the story can resolve; (b) show the relay line only if Kristin is in the chamber, and give her another line elsewhere; (c) drop the audio idea and use a carrier that needs no equipment. Give the exact new sentence. If it names a thing, say which noun needs declaring and its parent.

2. **Is the way back still open?** The shipped line says the maintenance network "still leads back to Rebecca's executive office." That conflicts with "water closes the facility around them" and with "the facility is lost." Decide one: the route stays open (and say what keeps it open, tied to Kristin's barrier); or Kristin returns by a different way you name from the places above; or the reports and calls move somewhere that is reachable after the flood. Check your choice against the Kristin and Michelle reunion in 3C.4. Give the exact player-visible sentence.

3. **Brandon's fate.** The plot says his fate is "initially uncertain." The shipped line has him speaking calmly at the moment of the escape, which settles that he is alive then. Rewrite his part so his fate is still uncertain after it, for example as a last transmission that ends in silence, or explain why the shipped wording already fits. Keep the two facts he must carry: reports from other detention sites reach the chamber, and families of the missing are calling there.

Then give the **final text of the whole escape delivery** with your three changes in it, no longer than the shipped one by more than about 25 words.

## Part B: one cue line in scene 2B

A delivery for the fact "Charles expected Kristin to seek Brandon" has this fallback (shown at a deadline if the player never learns it):

> Charles expected Kristin to seek Brandon. He left Michelle's evidence where she could find it and expose Brandon's hidden network. Corrupted files flicker on the medical terminal.

Its cue (the line shown while the player has not learned it) is currently the last sentence only: "Corrupted files flicker on the medical terminal." So the cue repeats the fallback's last sentence. Write a different cue of one short sentence that points the player to the medical terminal without telling them the answer. It must not say Charles expected anything or that the evidence was left for her.

## Rules for your text

Plain words, 12th grade reading level, one idea per sentence, no new names, short. After your answers, give a short contradiction check: any plot line your text breaks, and any sentence that puts a person in two places or in a place they cannot reach.
