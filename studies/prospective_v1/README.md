# Publicly registered prospective comparison

The study is publicly registered in [issue #5](https://github.com/TannerL22/frontier-ai-benchmark-lab/issues/5). `publication.json` records GitHub's server timestamp as the actual start and the fixed 180-day end. No future outcomes have been acquired. `protocol.json` defines the fixed-roster target, seven estimators, information cutoff, eligibility, abstention policy, scoring and stopping rule. `registered/` preserves the original locally sealed draft bytes, now adopted by the public registration; it freezes 1,372 forecasts and hashes the original code, evidence and protocol.

```bash
python scripts/prospective_registry.py verify
python scripts/prospective_registry.py score
```

Use the later public-registration timestamp as the acquisition cutoff. A digest alone cannot prove when the researcher saw an outcome. Public issue timing and pinned commits provide traceability, not acceptance by an external preregistration service. The forecast mapping is uncalibrated and is itself being tested. The project owner is the designated independent reviewer; actual eligibility decisions remain pending until future proposals exist.

To amend before registration, create a new study version and an unused bundle directory with `prospective_study.py seal --bundle ...`; the tool refuses overwrite. Code or input changes invalidate the existing input seal. After registration, retain the old bundle and disclose deviations rather than re-sealing its content.

Outcome JSONL records need `benchmark_id`, new `family_id` and `genealogy_id`, a registered `domain`, `direction`, `published_at` with timezone, `source_url`, `review_accepted: true`, `review_reason`, `scores` keyed by registered model IDs, and `system_records` keyed by those same IDs. Each system record explicitly declares snapshot, endpoint, reasoning, harness, fallback, budget and evaluation date, including unknowns. The reviewer must also assess previous exposure, configuration scope and genuine family novelty; string identity checks cannot establish scientific independence.

```bash
python scripts/prospective_registry.py score --proposals reviewed_outcome_proposals.jsonl --output outputs/prospective_report.json
```

The report retains rejected proposals and reasons, observed ties, abstentions, family-macro accuracy with half credit for abstention, Brier loss and model-level coverage. The public scorer requires acquisition after registration and publication, no prior exposure, a publication within the 180-day window, and an actual dated review by TannerL22. The earlier preparation-only scorer is not the registered collection entry point. The consecutive-publication process still requires oversight; the software does not manufacture an eligible sample. Do not relabel synthetic test fixtures as acquired future results. v5.3 corrections never alter the frozen forecasts.
