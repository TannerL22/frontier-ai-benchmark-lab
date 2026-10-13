# Frontier AI Benchmark Lab

A small cross-source evidence observatory for reported AI systems and selected tasks. The primary workflow is to inspect coverage, compare raw task results, and trace each result to its configuration and source. Global aggregation is an optional research experiment.

## Evidence review v5.2

The proposed release contains **306 included results across 57 rows, eight model identities and nine evaluator labels**, plus one excluded alternative and 150 explicit missing cells. Two omitted FrontierCode 1.1 Main Scores are restored: Claude Fable 5.1 Medium / Claude Code, 50.9; GPT-6.1 Sol Medium / Codex, 50.2. Opus High 13.93 remains the frozen Agent Arena configuration; the published Max 17.29 alternative is documented separately because its observational session population differs.

The October 12 audit numerically corroborated 153 included values (including five reconstructions from rounded components); **153 were not individually rechecked**. Source records contain curated numeric transcriptions and their digests, or explicitly inherited links. They are not archives of original webpages. Exact endpoints, snapshots, run dates, budgets and some harness conditions remain unknown. Numeric corroboration does not certify equal compute or comparable runs.

Muse coverage is confined to ten AA rows; unobserved domains remain visible. SciCode and CritPt retain their publisher-under-review status and are excluded from primary comparison and aggregation views by default. Historical v4.2 and v5.1 input files remain unchanged and selectable.

## Run locally

Python 3.11+ is required. The complete dependency resolution was exercised on Windows / Python 3.14.2; CI checks Linux / Python 3.12.

```bash
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip check
python scripts/check_release.py
python -m pytest -q
python scripts/app_smoke.py
streamlit run app.py
```

For an editable development environment with the same direct package versions, use `python -m pip install -c constraints.txt -e '.[app,dev]'`. `requirements.txt` delegates to the complete lock for deployment. Reproduce all experiments:

```bash
python scripts/reproduce.py --calibration
python scripts/reproduce_v51.py
python scripts/reproduce_v52.py
```

The slow test and first command reconstruct the historical nested calibration. Outputs include conditional accuracy, attempted/predicted/abstained cases, model-level coverage, weight contributions, source/family deletion scenarios and an alternative genealogy scenario. Pair counts are correlated observations, not independent sample sizes. Deletion ranges are not confidence intervals.

## Free pilot and prepared study

No paid model runs or prospective outcomes have been collected.

```bash
python scripts/artifact_pilot.py prepare --workspace pilot_runs/my_pilot
python scripts/artifact_pilot.py oracle-demo --workspace pilot_runs/my_pilot
python scripts/prospective_study.py verify
```

The pilot generates 12 public synthetic artifact tasks in three categories, a configuration template and a hashed oracle file. The oracle demonstration exercises the evaluator; **it is not model performance**. To grade actual artifact submissions, fill a systems registry and use `artifact_pilot.py grade --workspace ... --responses responses.jsonl --systems systems.json`. Missing registered attempts are retained. Expert review, private/future tasks, real endpoints and fixed budgets are required before an original model study. See [pilot instructions](studies/artifact_pilot_v1/README.md).

The prospective protocol and locally sealed forecasts compare three global estimators, two pair votes, a random reference and an AA-only source baseline for the fixed roster. The seal records content hashes and time; independent public registration is still needed before collecting outcomes. It does not establish that a study has already run. See [study instructions](studies/prospective_v1/README.md).

## Source of truth

| Location | Purpose |
| --- | --- |
| `data/`, `data/v5_1/` | Frozen six-model and original eight-model inputs |
| `data/v5_2/` | Versioned correction, stable model/system IDs, observations, sources, missingness and decisions |
| `snapshots/source_corroboration_2026_10_12.csv` | Auditor's numeric ledger; no new remote fetch on rebuild |
| `snapshots/canonical_integrity_manifest.json` | Portable UTF-8/LF input hashes and release counts |
| `src/frontierlab/` | Validated loader, graph methods, analysis, integrity and research tools |
| `studies/` | Protocols and sealed forecast draft; no acquired outcomes |
| `outputs/v5_2/` | Reproducible coverage and sensitivity exports |
| `tests/` | Historical regression, malformed inputs, abstentions and research-tool integrity |

See [methodology](docs/METHODOLOGY.md), [data contract](docs/DATA_CONTRACT.md), [selection policy](docs/SELECTION_POLICY.md), [architecture](docs/ARCHITECTURE.md) and [deployment](docs/DEPLOYMENT.md). External publisher composites remain outside the fitting inputs; agreement with them is not independent validation when constituents overlap. The repository retains its existing absence of an open-source licence.
