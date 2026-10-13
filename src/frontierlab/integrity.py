"""Portable LF/UTF-8 hashes for release files; no platform newline ambiguity."""
from pathlib import Path
import hashlib
import json


def canonical_bytes(path):
    return Path(path).read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode("utf-8")


def digest(path):
    return hashlib.sha256(canonical_bytes(path)).hexdigest()


def verify_manifest(root, manifest_path):
    root = Path(root).resolve()
    manifest = manifest_path if isinstance(manifest_path, dict) else json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    errors = []
    for relative, expected in manifest["sha256"].items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Manifest path escapes repository")
        if not path.is_file() or digest(path) != expected:
            errors.append(relative)
    if errors:
        raise ValueError("Release integrity mismatch: " + ", ".join(errors))
    return manifest
