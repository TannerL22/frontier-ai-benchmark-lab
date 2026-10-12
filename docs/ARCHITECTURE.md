# System architecture

```text
Original evaluator publications
           │
           ▼
Versioned CSV evidence + source audit (data/)
           │
           ▼
Single Python analysis engine (src/frontierlab/)
       ┌───┴───────────────────┐
       ▼                       ▼
Release scoring             Historical validation
       │                       │
       └───┬───────────────────┘
           ▼
 Streamlit dashboard (app.py) + generated exports (outputs/)
           │
           ▼
 GitHub automated tests (CI) and independent source review
```

## Data is the source of truth

`data/` is the **immutable frozen six-model baseline**. `data/v5_1/` is the versioned expansion containing Meta's two distinct Muse variants. Each observation has a benchmark ID, model identity and numeric score. Metadata records original publisher, domain, family, units, provenance, configuration and source URL. `snapshots/` preserves previous numerical results.

Avoid modifying the legacy evidence in place. New scores belong in a separately named release dataset and must have a source-audit record. Never infer missing scores, overwrite historical results, or insert composite benchmarks into constituent-level scoring.

## Computation

`frontierlab.core.Evidence` reads observations and computes a connected model comparison graph. `frontierlab.validation` implements holdout validation and optional probability calibration. `app.py` is presentation only; it does not own a second scoring formula. `scripts/reproduce_v51.py` generates reproducible release results and exports.

## Quality gates

The tests check source counts, exact Meta benchmark vectors, no model-benchmark duplicates, no composite scores, model-graph connectivity, unchanged v4.2 reference outputs and historical cross-validation numbers.

The model currently targets publicly reported *best-available system* performance, not matched hardware, matched inference budget or identical agent harnesses. The statistical model and coverage limitations are documented in [METHODOLOGY.md](METHODOLOGY.md).

## Planned future architecture

As the project grows, add append-only evidence revisions, reviewer-approved ingestion, timed source snapshots and a properly pre-registered prospective evaluation dataset. DuckDB/Parquet can replace flat files later without requiring changes to the scoring API. Do not introduce an operational database until file-based evidence becomes a practical bottleneck.
