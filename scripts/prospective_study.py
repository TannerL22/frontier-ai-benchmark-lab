"""Prepare a sealed draft or score reviewed outcomes; never downloads outcomes."""
import argparse
import json
from pathlib import Path
from frontierlab.study import seal, verify, score_future

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["seal", "verify", "score"])
    parser.add_argument("--bundle", type=Path, default=ROOT / "studies/prospective_v1/registered")
    parser.add_argument("--outcomes", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "seal":
        result = seal(ROOT, args.bundle)
    elif args.action == "verify":
        result = verify(ROOT, args.bundle)
    else:
        if args.outcomes is None or args.output is None:
            parser.error("score requires --outcomes and --output")
        outcomes = [json.loads(line) for line in args.outcomes.read_text().splitlines() if line.strip()]
        result = score_future(ROOT, args.bundle, outcomes)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result.get("status", "study_verified"))


if __name__ == "__main__":
    main()
