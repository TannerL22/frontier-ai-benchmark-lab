"""Generate free local tasks, run an oracle demonstration, or grade submitted JSON artifacts."""
import argparse
import json
from pathlib import Path
from frontierlab.pilot import prepare, grade


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "oracle-demo", "grade"])
    parser.add_argument("--workspace", type=Path, default=Path("pilot_runs/demo"))
    parser.add_argument("--responses", type=Path)
    parser.add_argument("--systems", type=Path)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args()
    if args.action == "prepare":
        tasks, answers = prepare(args.workspace)
        print(f"Prepared {len(tasks)} public synthetic tasks; no model calls.")
        return
    if args.action == "oracle-demo":
        if not args.workspace.exists():
            prepare(args.workspace)
        tasks = [json.loads(line) for line in (args.workspace / "tasks.jsonl").read_text().splitlines()]
        answers = json.loads((args.workspace / "oracle_answers.json").read_text())
        systems = [{"system_id": "oracle_fixture", "model_snapshot": "not_applicable", "endpoint": "local_fixture",
                    "reasoning_effort": "not_applicable", "harness": "oracle_demo", "fallback_policy": "none",
                    "resource_budget": "zero_paid_model_calls", "evaluation_date": "not_a_model_run",
                    "data_class": "oracle_demonstration_not_model_performance"}]
        responses = [{"system_id": "oracle_fixture", "task_id": t["task_id"], "task_sha256": t["task_sha256"],
                      "attempt": attempt, "artifact": answers[t["task_id"]], "elapsed_seconds": None, "cost_usd": 0}
                     for t in tasks for attempt in range(1, args.attempts + 1)]
    else:
        if args.responses is None or args.systems is None:
            parser.error("grade requires --responses and --systems")
        responses = [json.loads(line) for line in args.responses.read_text().splitlines() if line.strip()]
        systems = json.loads(args.systems.read_text())["systems"]
    result = grade(args.workspace, responses, systems, args.attempts)
    output = args.workspace / ("oracle_demo_report.json" if args.action == "oracle-demo" else "report.json")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {output}; no model calls.")


if __name__ == "__main__":
    main()
