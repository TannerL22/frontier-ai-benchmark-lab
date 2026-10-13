"""Validate all releases and canonical hashes. Manifest creation is explicit."""
import argparse
import json
from pathlib import Path
from frontierlab.core import Evidence
from frontierlab.integrity import digest, verify_manifest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "snapshots/canonical_integrity_manifest.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-manifest", action="store_true", help="Explicit maintainer action after reviewing input changes")
    args = parser.parse_args()
    counts = []
    for folder in ("data", "data/v5_1", "data/v5_2", "data/v5_3"):
        evidence = Evidence(ROOT / folder)
        counts.append({"release": folder, "models": len(evidence.models), "benchmarks": len(evidence.rows), "scores": len(evidence.score_records)})
    if args.write_manifest:
        files = [p for folder in ("data", "snapshots") for p in (ROOT / folder).rglob("*") if p.is_file() and p != MANIFEST]
        manifest = {"canonicalization": "UTF-8 without BOM, LF newlines; original legacy manifest retained separately",
                    "release_counts": counts, "sha256": {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(files)}}
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest = verify_manifest(ROOT, MANIFEST)
    if counts != manifest["release_counts"]:
        raise ValueError("Registered release counts changed")
    print(f"Verified {len(manifest['sha256'])} canonical input hashes and all {len(counts)} release contracts")


if __name__ == "__main__":
    main()
