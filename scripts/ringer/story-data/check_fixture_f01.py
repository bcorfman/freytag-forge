"""Independent check for fixture F01 (`tests/fixtures/story_source/mini_ok`).

Run from the repo (or a worktree of it): `python check_fixture_f01.py <repo_root>`.
Verifies shape only; no compiler exists yet. Four things, each printed on failure:

1. Every source file loads with a duplicate-key-rejecting YAML loader, starts with `schema: 1`,
   and has top-level keys that are known and in contract order (contract section 2).
2. The tree has the files and records F01 must contain (contract section 10, row F01).
3. Ids follow the contract patterns and are unique within their kind.
4. Passage fidelity: every authored passage is a substring of today's story files (whitespace
   collapsed) or is listed in `NEW_TEXT.txt` beside the fixture (one passage per line).
"""

from __future__ import annotations

import contextlib
import re
import sys
from pathlib import Path

import yaml

ORDER = {
    "story.yaml": [
        "schema",
        "story",
        "title",
        "genre",
        "protagonist",
        "budget_seconds",
        "scenes",
        "principal_characters",
        "acts",
        "front_matter",
        "retired_ids",
    ],
    "catalog.yaml": [
        "schema",
        "places",
        "characters",
        "groups",
        "items",
        "kinds",
        "props",
        "connections",
        "protected_knowledge",
        "disclosure_guards",
        "unplaced_facts",
    ],
    "scene": [
        "schema",
        "scene",
        "title",
        "location",
        "objective",
        "freytag_phase",
        "situation",
        "pressure",
        "turns",
        "scripted_opening",
        "companions",
        "participants",
        "items",
        "setting",
        "prop_pool",
        "entry",
        "entry_additions",
        "entry_claims",
        "brief",
        "outline",
        "facts",
        "placements",
        "beats",
        "reveals",
        "bridge",
        "incidents",
        "exit",
        "ending",
    ],
    "match": ["schema", "scene", "lexicon", "plural_twins", "shared", "claims", "deliveries"],
}
ID = re.compile(r"^[a-z][a-z0-9_]*$")
PLACEHOLDER = re.compile(r"(?<!\{)\{[a-z_][a-z0-9_]*\}(?!\})")


class DupKeyLoader(yaml.SafeLoader):
    pass


def _construct(loader: DupKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    seen: set = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(None, None, f"duplicate key {key!r}", key_node.start_mark)
        seen.add(key)
    return loader.construct_mapping(node, deep)


DupKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct)


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def main(repo: Path) -> int:
    errors: list[str] = []
    root = repo / "tests/fixtures/story_source/mini_ok"
    if not root.is_dir():
        print(f"missing fixture directory {root}")
        return 1
    docs: dict[str, dict] = {}
    for path in sorted(root.rglob("*.yaml")):
        rel = path.relative_to(root).as_posix()
        try:
            doc = yaml.load(path.read_text(encoding="utf-8"), Loader=DupKeyLoader)  # noqa: S506 - safe subclass
        except yaml.YAMLError as exc:
            errors.append(f"{rel}: not loadable: {exc}")
            continue
        if not isinstance(doc, dict) or list(doc)[:1] != ["schema"] or doc.get("schema") != 1:
            errors.append(f"{rel}: must be a mapping whose first key is `schema: 1`")
            continue
        kind = (
            rel
            if rel in ORDER
            else "match"
            if rel.endswith(".match.yaml")
            else "scene"
            if rel.startswith("scenes/")
            else None
        )
        if kind is None:
            errors.append(
                f"{rel}: unexpected file (allowed: story.yaml, catalog.yaml, scenes/<id>.yaml, scenes/<id>.match.yaml)"
            )
            continue
        order = ORDER[kind]
        unknown = [key for key in doc if key not in order]
        if unknown:
            errors.append(f"{rel}: unknown top-level keys {unknown}")
        positions = [order.index(key) for key in doc if key in order]
        if positions != sorted(positions):
            errors.append(f"{rel}: top-level keys out of contract order; expected order {order}")
        docs[rel] = doc

    for needed in ("story.yaml", "catalog.yaml"):
        if needed not in docs:
            errors.append(f"missing {needed}")
    story = docs.get("story.yaml", {})
    scenes = story.get("scenes")
    if scenes != ["1A", "2C"]:
        errors.append(f"story.yaml scenes must be [1A, 2C], got {scenes}")
    for sid in ("1A", "2C"):
        for rel in (f"scenes/{sid}.yaml", f"scenes/{sid}.match.yaml"):
            if rel not in docs:
                errors.append(f"missing {rel}")

    scene_1a = docs.get("scenes/1A.yaml", {})
    scene_2c = docs.get("scenes/2C.yaml", {})
    reveals = {r.get("id"): r for r in scene_1a.get("reveals", []) if isinstance(r, dict)}
    card = reveals.get("find_card")
    if not card:
        errors.append("1A must contain reveal `find_card`")
    else:
        variants = card.get("variants", {})
        if set(variants) != {"quiet", "witnessed"}:
            errors.append(f"find_card variants must be quiet and witnessed, got {sorted(variants)}")
        elif (
            variants["quiet"].get("claim_id") != "k_sl_1a_b_r0"
            or variants["witnessed"].get("claim_id") != "k_sl_1a_b_r0w"
        ):
            errors.append("find_card claim ids must be k_sl_1a_b_r0 (quiet) and k_sl_1a_b_r0w (witnessed)")
        if not card.get("parts"):
            errors.append("find_card must use `parts` (the {find_lead} pattern)")
    if not scene_1a.get("beats"):
        errors.append("1A must contain pacing beats (the patrol events)")
    if not any(e.get("id") == "t_1a_1b" or e.get("to") == "2C" for e in _as_list(scene_1a.get("exit"))):
        errors.append("1A exit must target 2C (F01 keeps the exit id t_1a_1b only if the target is changed to 2C)")
    if not scene_2c.get("incidents"):
        errors.append("2C must contain an incident with outcomes")
    else:
        incident = scene_2c["incidents"][0]
        if len(incident.get("outcomes", [])) < 2:
            errors.append("2C incident needs at least 2 outcomes")
    if not scene_2c.get("ending"):
        errors.append("2C is the last scene of F01, so it must contain `ending`")
    entry_claims = [c for sid in ("1A", "2C") for c in docs.get(f"scenes/{sid}.yaml", {}).get("entry_claims", [])]
    if len(entry_claims) < 2:
        errors.append(f"F01 needs at least two entry claims across its scenes, found {len(entry_claims)}")
    if not any(
        isinstance(d, dict) and "protected_knowledge" in d and d["protected_knowledge"]
        for d in [docs.get("catalog.yaml", {})]
    ):
        errors.append("catalog.yaml needs protected_knowledge (safety fixtures F26 and the safety tests use it)")
    if not any(
        isinstance(c, dict) and isinstance(c.get("audience"), dict) and c["audience"].get("kind") == "characters"
        for r in list(reveals.values()) + list({r.get("id"): r for r in scene_2c.get("reveals", [])}.values())
        for c in [*(r.get("variants", {}).values()), *entry_claims]
    ) and not any(isinstance(c.get("audience"), dict) for c in entry_claims):
        errors.append("F01 must include one claim with a non-public audience (audience scoping)")

    # ids: patterns and uniqueness within kind
    seen: dict[str, set[str]] = {}

    def claim_ids(scene: dict):
        for reveal in scene.get("reveals", []):
            for variant in reveal.get("variants", {}).values():
                if variant.get("claim_id"):
                    yield variant["claim_id"]
                for extra in variant.get("extra_claims", []):
                    yield extra["claim_id"]
        for claim in scene.get("entry_claims", []):
            yield claim["claim_id"]

    for rel, doc in docs.items():
        if rel.startswith("scenes/") and not rel.endswith(".match.yaml"):
            for fact in doc.get("facts", {}) or {}:
                if not ID.match(fact):
                    errors.append(f"{rel}: fact id {fact!r} breaks the id pattern")
                if fact in seen.setdefault("fact", set()):
                    errors.append(f"{rel}: fact {fact} declared twice")
                seen["fact"].add(fact)
            for cid in claim_ids(doc):
                if not ID.match(cid):
                    errors.append(f"{rel}: claim id {cid!r} breaks the id pattern")
                if cid in seen.setdefault("claim", set()):
                    errors.append(f"{rel}: claim {cid} defined twice")
                seen["claim"].add(cid)
    for sid in ("1A", "2C"):
        match = docs.get(f"scenes/{sid}.match.yaml", {})
        have = set(match.get("claims") or {})
        want = set(claim_ids(docs.get(f"scenes/{sid}.yaml", {})))
        if have != want:
            missing, extra = sorted(want - have), sorted(have - want)
            errors.append(f"{sid}.match.yaml claims differ from the scene's claims: missing {missing}, extra {extra}")

    # passage fidelity
    haystack_parts = []
    live = repo / "data/stories/continuity-initiative"
    for name in (
        "plot.md",
        "storylets.md",
        "knowledge.yaml",
        "world.yaml",
        "handoffs.yaml",
        "pacing.yaml",
        "storylet-routes.yaml",
        "incidents.yaml",
        "connections.yaml",
    ):
        text = (live / name).read_text(encoding="utf-8")
        haystack_parts.append(text)
        with contextlib.suppress(yaml.YAMLError):  # decoded scalars, so folded or block styles still match
            haystack_parts.extend(strings(yaml.safe_load(text)))
        for line in text.splitlines():  # plot.md keeps quoted YAML scalars such as `entry_text: "..."`
            if re.match(r"^[a-z_]+: \"", line):
                with contextlib.suppress(yaml.YAMLError):
                    haystack_parts.extend(strings(yaml.safe_load(line)))
    haystack = squash(" ".join(haystack_parts))
    new_text_path = root / "NEW_TEXT.txt"
    allowed = (
        {squash(line) for line in new_text_path.read_text(encoding="utf-8").splitlines() if line.strip()}
        if new_text_path.exists()
        else set()
    )
    used_allowed: set[str] = set()
    for rel, doc in docs.items():
        for text in strings(doc):
            if " " not in text.strip():
                continue  # an identifier or path, not a passage
            for piece in re.split(r"\n\s*\n|" + PLACEHOLDER.pattern, text.replace("{{", "").replace("}}", "")):
                piece = squash(piece)
                if len(piece) < 25 or piece in haystack:
                    continue
                if piece in allowed:
                    if piece in used_allowed:
                        continue
                    used_allowed.add(piece)
                    continue
                errors.append(
                    f"{rel}: passage not found in today's story files and not in NEW_TEXT.txt: {piece[:110]!r}"
                )

    for stale in sorted(allowed):
        if stale in haystack:
            errors.append(f"NEW_TEXT.txt lists text that exists live (delete it): {stale[:80]!r}")
    for name in ("README.md",):
        if not (root.parent / name).exists():
            errors.append(f"missing tests/fixtures/story_source/{name} (the API contract and fixture index)")
    if errors:
        print("\n".join(errors[:60]))
        if len(errors) > 60:
            print(f"... and {len(errors) - 60} more")
        return 1
    print(f"F01 shape ok: {len(docs)} files, {len(seen.get('claim', ()))} claims, {len(seen.get('fact', ()))} facts")
    return 0


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve()))
