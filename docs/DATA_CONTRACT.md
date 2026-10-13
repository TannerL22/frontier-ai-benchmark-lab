# Versioned evidence contract

Historical schemas remain readable and immutable. New evidence releases require these records:

| File | Key and contract |
| --- | --- |
| `model_identities.csv` | Unique stable `model_id`, unique display name, developer, provider snapshot ID or explicit unknown |
| `systems.csv` | Unique `system_id` referencing model and benchmark; snapshot, endpoint, reasoning, harness/version/tools, fallback, retries, budget and evaluation date |
| `benchmarks.csv` | Unique task/metric ID, fine family and broader ancestry, version/configuration, domain, evaluator, creator/operator/publisher, direction, metric definition, units and quality status |
| `observations.jsonl` | Unique observation ID referencing system, model, benchmark and source; score, inclusion boolean/reason, run ID, sample/trial count, judge, original uncertainty interpretation and derivation where applicable |
| `sources.jsonl` | Unique source ID, original URL, corroborating URLs, retrieval/publication date or unknown, capture type and qualifications |
| `missingness.csv` | Exactly one reason for every absent model/benchmark cell |
| `scores.csv` | Calculation projection; must exactly agree with all included observations |
| `normalization_reference.csv` | Unique benchmark denominators, finite/positive and at least the floor, with declared frozen reference |
| `decisions.json`, `release.json` | Dated inclusion/correction decisions, review state and scope |

Required unknown conditions are the literal `unknown`; an empty field is not a silent inference. Current missing cells use `unknown_not_recorded_in_this_release`. A curator may later establish `untested`, `unsupported_modality`, `inaccessible_endpoint`, `incomplete_run`, `unavailable_publication` or `deliberately_excluded`, with supporting reasons in a new release. Absence alone establishes none of those.

Included status distinguishes `numeric_corroborated`, `inherited_not_rechecked`, `derived_from_rounded_components`, and their provisional variants. Excluded variants retain `alternative_configuration` and an inclusion reason. Future superseded/disputed states require a versioned contract update and review, rather than silently treating them as included. The loader fails unknown foreign keys, duplicate identities/observations, disagreement between source transcriptions and observations, invalid URLs, nonfinite scores/floors and percentages outside [0,100]. AA reliability index uses [-100,100]; Elo has no arbitrary finite range. A new metric requires an explicit range/direction rule.

The current source digest covers the curated transcription object. It does **not** hash an original webpage. A future original artifact capture must declare its capture format, permitted redistribution, original content digest, retrieval timestamp and exact observation locator. A source link and matching number alone do not establish complete run provenance. Current task/trial counts remain unknown at observation level even when benchmark prose describes a study design.

`scripts/build_v52.py` deterministically rebuilds the proposed migration from frozen inputs and the auditor ledger; it makes no network request. Review its changes before refreshing the canonical manifest. `scripts/check_release.py` validates contracts and canonical hashes. Its `--write-manifest` option is an explicit maintainer action, never an automatic response to a mismatch. UTF-8 without BOM and LF hashing avoids Windows checkout differences; the original legacy manifest remains available.
