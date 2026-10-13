# Prepared artifact pilot

Preparation is free and local. There are no model results in this directory.

```bash
python scripts/artifact_pilot.py prepare --workspace pilot_runs/my_pilot
python scripts/artifact_pilot.py oracle-demo --workspace pilot_runs/my_pilot
```

Read `protocol.json`. Inspect the generated task prompts and inputs. Keep the oracle file outside the context given to a model. The tasks and oracle are public synthetic demonstration material, so separation alone does not make them private holdouts. Have an expert review task realism and scorer validity, and create a separately registered task set before scientific claims.

Copy `systems_template.json` to your run registry and declare actual system IDs, snapshots/endpoints, reasoning, harness/tools, fallback/retries, budgets and evaluation dates before running. No endpoint has been selected and this preparation performs no API call. Record three independent attempts for every task/system, including failures.

Responses are newline-delimited JSON records with `system_id`, `task_id`, `task_sha256`, `attempt` (1–3), and `artifact`. Time and actual cost may be finite nonnegative numbers or null. The protocol includes an example; use the hash from the corresponding task. Submit parsed JSON artifacts, not Markdown fences.

```bash
python scripts/artifact_pilot.py grade --workspace pilot_runs/my_pilot --responses responses.jsonl --systems systems.json
```

The report retains missing attempts, exact correctness, category outcomes and paired task/attempt results. Incorrect field names, extra fields, float cents, booleans as integers and unsorted duplicate lists fail strict grading. Duplicate attempt identities, altered task hashes and invalid budgets reject the report. Oracle reports are labelled `oracle_demonstration_not_model_performance`. Do not mix them into a model comparison or claim expert-reviewed task validity from a passing fixture.
