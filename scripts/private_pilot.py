"""Prepare a private holdout, check review status, or grade actual approved artifacts."""
import argparse
import json
from pathlib import Path
from frontierlab.pilot_ops import prepare_holdout, verify_review, grade_controlled

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "verify-review", "grade"])
    parser.add_argument("--workspace", type=Path, default=ROOT / "private_pilot/artifact_private_v1")
    parser.add_argument("--responses", type=Path)
    parser.add_argument("--systems", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        result = prepare_holdout(args.workspace)
        public = {**result, "independent_human_review": "pending TannerL22 review", "execution_enabled": False,
                  "private_files": "Excluded from Git; review through the local pilot review app", "actual_model_runs": 0}
        (ROOT / "studies/artifact_pilot_v1/private_holdout_commitment.json").write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
        print("Prepared 24 private synthetic tasks; 24 independent SQL checks passed; zero paid/model runs")
    elif args.action == "verify-review":
        print(verify_review(args.workspace))
    else:
        if args.responses is None or args.systems is None:
            parser.error("grade requires --responses and --systems")
        execution = json.loads((ROOT / "studies/artifact_pilot_v1/execution_plan.json").read_text())
        responses = [json.loads(line) for line in args.responses.read_text().splitlines() if line.strip()]
        systems = json.loads(args.systems.read_text())["systems"]
        result = grade_controlled(args.workspace, responses, systems, execution)
        (args.workspace / "model_report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("Graded approved private tasks; model outcomes remain separate from oracle demonstrations")


if __name__ == "__main__":
    main()
