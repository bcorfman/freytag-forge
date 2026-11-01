from __future__ import annotations

import copy
import re
import shutil
from pathlib import Path

import pytest
import yaml

from storygame.story_package import StoryPackageError, load_story_package

PACKAGE = Path("data/stories/continuity-initiative")


def test_loader_documents_unproducible_positive_ledger_gate(tmp_path: Path) -> None:
    root = tmp_path / "package"
    shutil.copytree(PACKAGE, root)

    knowledge_source = root / "knowledge.yaml"
    catalog = yaml.safe_load(knowledge_source.read_text(encoding="utf-8"))
    original = next(item for item in catalog["knowledge"] if item["id"] == "k_sl_2c_c_r1")
    sibling = copy.deepcopy(original)
    sibling["id"] = "k_sl_2c_c_r2"
    sibling["requires"] = [*sibling["requires"], {"fact_id": "brandon_name_erased", "equals": True}]
    sibling["source"]["realization_id"] = "SL-2C-C-R2"
    catalog["knowledge"].append(sibling)
    knowledge_source.write_text(yaml.safe_dump(catalog, sort_keys=False, allow_unicode=True), encoding="utf-8")

    routes_source = root / "storylet-routes.yaml"
    routes = yaml.safe_load(routes_source.read_text(encoding="utf-8"))
    route = next(route for route in routes["storylets"] if route["id"] == "SL-2C-C")
    realization = copy.deepcopy(route["realization_options"][0])
    realization["id"] = "SL-2C-C-R2"
    route["realization_options"].append(realization)
    routes_source.write_text(yaml.safe_dump(routes, sort_keys=False, allow_unicode=True), encoding="utf-8")

    with pytest.raises(
        StoryPackageError,
        match=re.escape(
            "scene 2C reveal 'k_sl_2c_c_r2' requires 'brandon_name_erased', which scene entry does not guarantee "
            "and the scene cannot produce"
        ),
    ):
        load_story_package(root)
