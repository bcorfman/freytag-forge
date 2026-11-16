# Story-source fixtures

F01 `mini_ok` — a valid two-scene source tree covering the 1A card search and patrol pacing plus the 2C incident, claims, protected knowledge, audience scoping, and ending.

| # | Fixture | Property it exercises | Expected |
| --- | --- | --- | --- |
| F02 | `dup_key` | a repeated key in a variant | `L1.duplicate_key` |
| F03 | `unknown_key` | `done_when` on a reveal | `L1.unknown_key` |
| F04 | `fact_two_owners` | one fact in two scene files | `L2.fact_one_owner` |
| F05 | `fact_wrong_scene` | a fact declared in scene 2 but first set in 1A | `L2.fact_declaring_scene`, message names the block and target file |
| F06 | `claim_unauthorized` | `commits_subset` with a fact the variant does not commit | `L2.claim_authorized` |
| F07 | `leak_narrowed` | a claim replacing its shared `leak_terms` with a shorter list; and a variant `boundaries` key | `L2.override_add_only` twice |
| F08 | `dangling` | `{missing}` part, `use: nope`, unknown fact in `when`, exit to an unknown scene | four `L2.dangling_ref` |
| F09 | `cycles` | a two-scene transition cycle; a claim requiring its own fact | inherited loader errors |
| F10 | `outcome_not_committed` | an advantage the variant does not commit | inherited loader error |
| F11 | `observes_missing` | `observed_by` without an outcome claim | `L2.incident_observes_outcomes` |
| F12 | `passage_rules` | `say` with two matching entries; `text_when` with two holding; two entry additions | first `say` wins; `AMBIGUOUS`; both additions appended |
| F13 | `leak_null_vs_empty` | one claim without `leak_terms`, one with `[]` | `None` vs `()`; the leak index differs exactly by the alias forms |
| F14 | `two_owners_manifest` | scene marked `compiled` while legacy files define it | `L2.ownership` naming both sources |
| F15 | `manifest_absent` | sources present, no manifest | package equals the legacy one |
| F16 | `claim_order` | match file order differs from reveal order | claim order follows the match file |
| F17 | `lexicon_off_ignored` | malformed `lexicon.yaml`, every scene `lexicon: false` | compiles |
| F18 | `lexicon_ref_when_off` | a `$memory_card` reference without `lexicon: true` | `L1.lexicon_off` |
| F19 | `lexicon_roundtrip` | derived lists equivalent to the lock | package equals F01; `story expand` then compile with no lexicon gives the same canonical JSON |
| F20 | `lexicon_stale` | a lexicon name added, lock not regenerated | `L2.lock_stale` naming claim and field |
| F21 | `override_ratio` | a field with 2 of 5 entries added | ratio 0.4, status `over`, pass-2 gate fails, build passes |
| F22 | `plural_twins` | `saved file(s)` with the option on and off | two entries; `L1.plural_off` |
| F23 | `parity_classes` | legacy/compiled package pairs seeded with one difference of each class | each classified correctly; unreviewed ones fail |
| F24 | `review_digest` | a review entry whose compiled digest no longer matches | unreviewed, fail |
| F25 | `save_identity` | a frozen claim id removed; then listed in `retired_ids` | `UserWarning` naming the id; then silent |
| F26 | `review_isolation` | a beat `note` and a bridge `note` with unique marker text | the marker appears nowhere in the package dump or narrator inputs |
| F27 | `examples` | accept/reject lines for `k_sl_1a_b_r0`, one failing accept | the checker runs the real matcher, names the failing group and the smallest word to add |
| F28 | `lookup` | one address of every kind | each resolves; parts pasted in; `source=True` returns the template; unknown address raises `KeyError` |
| F29 | `typed_needs` | `exists`, `held`, `reach` and `not` needs on an exit | only `exists` and `held` reach `required_dependencies` |
| F30 | `claimless_variant` | a variant with no `claim_id` | a realization with no claim |
| F31 | `deterministic` | compile twice, in two processes | identical canonical JSON; the digest covers schema version, compiler version and every source file |

## Compiler and validator API these fixtures are written against

Package: `storygame.story_source`.

```python
check_source_tree(root: Path) -> list[Diagnostic]
```

Checks layers 1 and 2; an empty list means valid.

`Diagnostic` is a frozen dataclass with `name` (for example `"L2.fact_one_owner"`), `file` (path relative to root), `address` (the contract section 8.1 address or empty), `field`, and `message`.

```python
compile_source_tree(root: Path) -> StoryPackage
```

Raises `SourceError` carrying the diagnostics when the tree is invalid.

```python
story_text(address, *, package=None, source=False)
story_value(address, *, package=None)
```

These look up addresses as specified in contract section 8.2.

The remaining API names (`check_parity`, `check_save_identity`, `override_ratio`, `pass2_gate`, `check_examples`, `source_digest`, `storygame.story_cli.main`) are settled in contract section 10.1.

## Ambiguities found

# NOTE: F01 ends at 2C, so its ending keeps the live 3C base text and marker but does not copy the conditional 3C additions.
# NOTE: The 2C recovery reveal's two live extra claims are included so the scene claim set and match-file claim set remain complete.
