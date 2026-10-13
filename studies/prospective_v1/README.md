# Prepared prospective comparison

`protocol.json` defines the fixed-roster target, seven estimators, information cutoff, eligibility, abstention policy, scoring and stopping rule. `registered/` contains a **locally sealed draft**, not a completed or independently registered experiment. It freezes 1,372 domain/pair/method predictions and hashes the code, evidence and protocol.

```bash
python scripts/prospective_study.py verify
```

Publish the bundle with an independently visible timestamp before collecting any outcomes. Record the actual public-registration time and use that later time as the acquisition cutoff. A digest alone cannot prove when the researcher saw an outcome. The draft's forecast mapping is uncalibrated and is itself being tested. No future outcomes have been collected here.

To amend before registration, create a new study version and an unused bundle directory with `prospective_study.py seal --bundle ...`; the tool refuses overwrite. Code or input changes invalidate the existing input seal. After registration, retain the old bundle and disclose deviations rather than re-sealing its content.

Outcome JSONL records need `benchmark_id`, new `family_id` and `genealogy_id`, a registered `domain`, `direction`, `published_at` with timezone, `source_url`, `review_accepted: true`, `review_reason`, `scores` keyed by registered model IDs, and `system_records` keyed by those same IDs. Each system record explicitly declares snapshot, endpoint, reasoning, harness, fallback, budget and evaluation date, including unknowns. The reviewer must also assess previous exposure, configuration scope and genuine family novelty; string identity checks cannot establish scientific independence.

```bash
python scripts/prospective_study.py score --outcomes reviewed_outcomes.jsonl --output outputs/prospective_report.json
```

The report retains rejected outcomes and reasons, observed ties, abstentions, family-macro accuracy with half credit for abstention, Brier loss and model-level coverage. It scores only observed pairs without inventing missing scores. The protocol's consecutive-publication window and review ledger require researcher oversight; the software does not scrape publications or manufacture an eligible sample. Do not relabel synthetic test fixtures as acquired future results.
