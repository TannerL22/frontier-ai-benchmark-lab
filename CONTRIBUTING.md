# Contributing

Thank you for helping improve reproducibility and source accuracy.

## Evidence changes

Please supply the original evaluator URL, tested model/version, benchmark identifier/version, reported score and unit, evaluation date, reasoning mode, harness and tool configuration where disclosed, and any overlap with a currently included benchmark. If a score is reconstructed from published sub-scores, state the formula and group sizes explicitly.

Changes to research observations should be proposed in a **new versioned release dataset**; never overwrite the frozen `data/` baseline. Composite leaderboard indices should remain outside constituent-level scoring.

## Code changes

Install the package, run `python -m pytest -q -m 'not slow'` and both reproduction scripts. Add regression tests for any mathematical or data-processing changes. Explain methodology changes separately from new score observations; do not modify evaluation weights to improve historical holdout accuracy without a clearly labelled development/test split.

## External contributions

This repository has no open-source licence yet. Please do not submit copyrighted third-party benchmark datasets unless their redistribution is authorised. Cite original evaluator sources and do not commit credentials, tokens, personal data or confidential results.
