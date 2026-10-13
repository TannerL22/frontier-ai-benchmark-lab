# Architecture

The app and command-line exports share a small Python calculation library and versioned local CSV/JSON evidence. No database or service rewrite is needed for this portfolio.

`core.py` validates historical calculation schemas and solves sparse comparison graphs. `catalog.py` enforces new stable record relationships and source/observation agreement. `analysis.py` contains coverage, simple pair baselines, contribution and deletion/genealogy scenarios. `integrity.py` handles portable hashes. `presentation.py` provides shared exports and historical-detail fallbacks. `validation.py` retains nested historical probability calibration.

`app.py` presents seven generic release-aware pages. Coverage and co-recorded results come first; exact source/system detail and release decisions follow. Retrospective validation exposes conditional accuracy and abstention. Aggregation is explicitly optional. Research protocols are downloadable. Caches include release and selected evidence keys, so sensitivity uses the same row selection as the displayed experiment.

`study.py` seals immutable forecast drafts and validates future outcome eligibility; `pilot.py` generates public fixture tasks and grades submitted artifacts. Neither calls a provider. Task or forecast tampering fails verification. Future public registration and independent task/eligibility review are research actions, not features fabricated by the software.

CI installs the complete dependency resolution, checks contracts/seals, runs the full suite including slow calibration, reproduces all releases, exercises all app pages and archives computations. A new database, API, ingestion service or public front end should follow an actual history-querying, collaboration or usability need. Source monitoring should propose changes for review rather than silently publish observations.
