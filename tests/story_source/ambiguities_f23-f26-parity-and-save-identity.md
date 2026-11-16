F23: the parity checker API and report mapping are unspecified; assumed `story_source.check_parity(legacy, compiled, reviews=...)` returns `differences` and `summary` mappings.
F24: the review-digest checker API is unspecified; assumed it is the same `story_source.check_parity` call and marks a stale compiled digest unreviewed.
F25: the save-identity checker API and manifest shape are unspecified; assumed `story_source.check_save_identity(package, manifest, retired_ids=...)` emits `UserWarning` for missing non-retired IDs.
F26: the compiler's narrator-input accessor is unspecified; assumed excluding the marker from the compiled package dump is the available isolation assertion.
