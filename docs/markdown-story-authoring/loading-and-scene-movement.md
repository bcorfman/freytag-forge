# Loading and scene movement

Part of [the Markdown story authoring guide](../markdown-story-authoring.md).

Load a package with `storygame.story_package.load_story_package(path)`. It is a
validated immutable authoring input; it does not interpret player text or add a
story-specific runtime branch.

The protagonist starts in the scene's location unless the scene gives the
protagonist a character placement. Things the protagonist carries therefore
move with the protagonist when the scene changes.
