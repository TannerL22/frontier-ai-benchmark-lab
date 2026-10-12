# Frontier AI Benchmark Lab — v5.0 / first working milestone

A reproducible Python research project migrated from the frontier-AI Excel series. **This is a working local prototype**, not yet a hosted production website. It preserves the original source observations and reproduces v4.2's published six-model index and v4.4 historical cross-validation. The newly released Meta Muse models are staged separately and **not yet assigned a spurious Super-Aggregate score**.

## Start here

Requires Python 3.10+.

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e '.[app,dev]'
pytest -q
python scripts/reproduce.py
streamlit run app.py
```

For the slower, leakage-aware **nested Brier probability-calibration** reconstruction:

```bash
python scripts/reproduce.py --calibration
```

View `outputs/results.json` and `outputs/cross_validation_predictions.csv`. The dashboard offers a leaderboard, shared-test model comparisons, a clickable evidence table, a cross-validation page and a new-model intake page.

## Source of truth

| Location | What it contains |
| --- | --- |
| `data/benchmarks.csv` | 57 benchmark rows, original evaluator, family, units, version/conditions, floor, URL and provenance |
| `data/scores.csv` | 284 original model-by-benchmark observations, no imputed missing values |
| `data/models.csv` | Six frozen baseline models plus separate Muse Wonder and Muse Wonder Full candidates |
| `data/candidate_scores.csv` | Select independently reported AA task results for Muse; **held, not in ranking** |
| `data/external_indices.csv` | Rounded Artificial Analysis index comparisons, **never input to model scoring** |
| `data/config.json` | Model roster, domain weights and index display convention |
| `src/frontierlab/core.py` | Single Python calculation engine; sparse-pair graph estimator and weight variants |
| `src/frontierlab/validation.py` | Nested family-excluded probability calibration |
| `snapshots/` | Frozen v4.2 and v4.4 reference outputs and source manifest |
| `tests/` | Regression and data-integrity tests |
| `app.py` | Local interactive Streamlit interface |

### Baseline method

Three predeclared methods are implemented:

1. **Equal benchmark families** (preferred transparent baseline after v4.4).
2. **Equal capability domains**.
3. **Super-Aggregate v4.2** (experimental, evaluator/coverage-weighted joint estimator).

The model solves one common graph of observed pair differences within each benchmark. Scores are normalized by the max of a predefined scale floor and observed population standard deviation, differences are clipped to ±2, and sparse missing pairs receive no vote. All methods are fit on the same observations. The displayed index is **100 + 20 × (model latent estimate − Opus latent estimate)**, a relative convention, not an intelligence percentage. The default methodology in the dashboard is the simple equal-family baseline; v4.2 is available for comparison.

### Historical validation

Each benchmark-family, evaluator and domain is held out entirely before refitting all three methods. Pairwise directional success is averaged within holdout groups. Historical v4.4 results on this fixed dataset: equal families 61.0%, equal domains 56.1%, advanced v4.2 57.3% for leave-one-family-out. **This does not show that the advanced index is better than equal weighting.** Nested Brier calibration is optional and slower.

**Not a prospective test:** historical weights and model choices were partly informed by the broader benchmark landscape. Model-level outcomes on a benchmark and 15 within-benchmark model pairs are not independent tasks. Scenario sensitivity is not a calibrated probability of model superiority. Some historical source URLs describe reports with non-identical configurations; this migration does not turn their reported scores into equal-compute measurements.

## Muse Wonder and Muse Wonder Full — October 12, 2026

Meta launched both variants on October 12. Independent Artificial Analysis **Intelligence Index v4.3**: Wonder Full **56**, Wonder **52**, current Opus **58**. AA Coding Agents Index: Full **68**, Wonder **63**, Opus **66**. Sources:
- https://research.meta.ai/blog/muse-wonder
- https://artificialanalysis.ai/articles/muse-wonder
- https://artificialanalysis.ai/models/muse-wonder-full
- https://artificialanalysis.ai/models/muse-wonder/

`data/candidate_scores.csv` contains a *limited set* of AA individual task values reported in the launch analysis, with model identities, units and source links, but these do not enter the index until original run/benchmark version and settings are reconciled with the existing historical snapshots. Meta's own scorecard also mixes independently evaluated and provider-reported results; **do not automatically ingest its published composite or all vendor scores**. Full is available via Muse Code rather than a public model API at launch.

## Governance / next milestones

- **M1 (included):** canonical data, audited provenance, testable scoring code, historical validation reproduction, local dashboard, model intake.
- **M2:** verify Muse's entire underlying AA 10-test score vectors under the matching current test versions. Version the baseline and handle updated existing-model observations together; add an explicit model-promotion review with overlap checks.
- **M3:** source monitoring that proposes new observations rather than silently publishing them; immutable observation history and provenance verification queue.
- **M4:** prospective holdout registration, live independent benchmark ingestion by reviewed release batch, report export, optional public deployment.

**Do not add a new model to `baseline_models` without sufficient matched observations and a versioned rebuild.** The current engine requires all baseline models to form a connected comparison graph; this is a deliberate quality gate.

## Sharing

GitHub Actions runs tests and regenerates the results on pushes. No actual remote repository, API credentials, subscriptions, hosting or automation was created. Data/code can be committed as a new GitHub repo once reviewed. Export Excel as a presentation layer only, never an authoritative second calculation engine.

---

## v5.1 / Eight-model release batch (12 October 2026)

**Use v5.1 for new eight-model research; retain v4.2/v4.4 as the frozen historical validation.** The application defaults to the eight-model release but permits switching between snapshots. No historical method or cross-validation result is overwritten.

```bash
pip install -e '.[app,dev]'
pytest -q -m 'not slow'
python scripts/reproduce_v51.py
streamlit run app.py
```

### Data and safeguards

- `data/v5_1/` contains the full **57 original benchmark rows** and **304 model scores** (the six-model 284-score baseline + 20 new independently published score cells).
- Muse Wonder Full and Muse Wonder are **separate model IDs**, each with ten original Artificial Analysis Intelligence Index v4.3.2 constituents. No composite-score inputs. Original links and settings in `data/v5_1/source_audit.csv`.
- `data/` and `snapshots/v4_2_reference.json` remain frozen, making the 6-model rankings and v4.4 cross-validation exactly reproducible.
- `python scripts/reproduce_v51.py` regenerates `outputs/v5_1_preview_results.json` and `outputs/v5_1_rankings.csv` using the **joint eight-model pairwise estimator**.
- The score anchor of 100 is purely a convenient baseline. **Do not compare the numerical eight-model values directly to the earlier 6-model values.** All eight-model estimates are refitted; the new models have only 10/57 benchmark coverage, all from AA, whereas previous models have 34–57 rows from multiple evaluators. AA's own composite is an external cross-check only.
- The original scores are best-available-system scores, not equal-budget and not equal-harness comparisons; some Claude experiments use fallback. SciCode and CritPt remain labelled *under review* by AA.
- `pytest` checks exact new AA vectors, original task families, no double-counting, frozen baseline reproduction and connected joint estimation.

### Matched original AA sources

- [AA Muse Wonder comparison with Opus](https://artificialanalysis.ai/models/comparisons/muse-wonder-vs-claude-opus-5-5) contains Wonder's ten scores.
- [AA model comparison (three-way including Wonder Full)](https://artificialanalysis.ai/es/models/comparisons) and [AA launch methodology discussion](https://artificialanalysis.ai/articles/muse-wonder) corroborate Wonder Full's ten scores.
- [AA current model benchmark definitions](https://artificialanalysis.ai/models/comparisons) confirm the same 10 benchmark identifiers and publication.

### GitHub publication

This folder is a complete repository-ready source tree. The GitHub connector allows writing to repositories **already created and authorised**, but currently does not expose a *create repository* action. Create a new **private, empty** repository (suggested name `frontier-ai-benchmark-lab`) at https://github.com/new, then connect/authorise it for ChatGPT's GitHub app. The project can then be published using the connector, without touching any of your unrelated existing repositories. Alternatively, download the ZIP and push with `git` after creating a repository:

```bash
git init
git add .
git commit -m "Initialize Frontier AI Benchmark Lab v5.1"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/frontier-ai-benchmark-lab.git
git push -u origin main
```
