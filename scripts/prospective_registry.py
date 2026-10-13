"""Verify a public registration or score the complete reviewed proposal ledger."""
import argparse
import json
from pathlib import Path
from frontierlab.prospective_ops import verify_publication, score_registered

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["verify", "score"])
    parser.add_argument("--publication", type=Path, default=ROOT / "studies/prospective_v1/publication.json")
    parser.add_argument("--proposals", type=Path, default=ROOT / "studies/prospective_v1/outcome_proposals.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/prospective_v1/status.json")
    args = parser.parse_args()
    publication = json.loads(args.publication.read_text())
    if args.action == "verify":
        result = verify_publication(ROOT, publication)
        print(f"Verified public registration and {result['forecast_count']} frozen forecasts")
    else:
        proposals = [json.loads(line) for line in args.proposals.read_text().splitlines() if line.strip()]
        result = score_registered(ROOT, publication, proposals)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(result["study_status"], "| proposals:", result["proposal_count"], "| accepted:", result["accepted_outcome_count"])


if __name__ == "__main__":
    main()
