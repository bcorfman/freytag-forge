"""Deterministic source-tree fingerprinting for compiler cache identity."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .compiler import COMPILER_VERSION


def source_digest(root: Path) -> str:
    """Hash schema version, compiler version, and every source file's bytes."""

    files = {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*.yaml"))
    }
    payload = {"schema_version": 1, "compiler_version": COMPILER_VERSION, "files": files}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
