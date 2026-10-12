# Methodology and limitations

## Research question

Which aggregation method generalises best to **unseen benchmark families**, and what do available original evaluations say about comparative frontier-model capabilities?

This project compares **reported benchmark systems**, not model weights evaluated under universally identical compute, tool budgets or agent implementations.

## Observation unit and provenance

The primary scored observation is one model's score on one independently published benchmark execution. Benchmarks belong to families and evaluators, with domain and configuration metadata. Two evaluations from the same benchmark family must not be treated as two independent families. Publisher-generated composite indices are not direct scoring votes.

## Three predeclared estimators

- **Equal benchmark families:** each unique benchmark family receives the same total weight, shared among its recorded evaluations.
- **Equal domains:** evidence is balanced across capability domains rather than allowing densely measured domains to dominate.
- **Super-Aggregate v4.2:** an experimental evaluator-aware, sparse-coverage-adjusted estimator.

Each benchmark's model scores are normalised by the maximum of the observed population standard deviation and a predeclared scale floor; extreme relative differences are clipped. The joint estimator fits differences on a common comparison graph, using only model pairs with **both scores observed**. Missing pairs get zero influence rather than receiving an imputed value or redistributed weight.

The display scale, anchored to Opus = 100, is arbitrary:

```text
Index(model) = 100 + 20 × (latent_value(model) − latent_value(Opus))
```

It is **not** a percent intelligence, a measurement of absolute ability, or a calibrated probability.

## Historical validation

For each benchmark family (then evaluator and domain), remove all its rows, refit the ranking models without the withheld evidence, and predict held-out pairwise rank directions. Comparisons are averaged **within** the held-out family/evaluator before macro-averaging across groups. Benchmarks with tied observed outcomes do not identify a winning direction.

The v4.4 six-model cross-validation found 61.0% accuracy for equal-family weighting, 56.1% for equal-domain weighting and 57.3% for the complex index. This did **not** establish a benefit from complex weighting. The nested probability calibration gave Brier scores of 0.2433 (equal families), 0.2447 (equal domains) and 0.2411 (advanced), a very small, uncertain difference.

### Important statistical cautions

- Multiple pairwise predictions from one benchmark are correlated, so **pair counts are not independent sample sizes**.
- Historical cross-validation is not an uncontaminated prospective test: evaluation selection and some methodological decisions were informed by the existing landscape.
- The earlier four-family external holdout was narrow and mostly retrospective.
- Differences of less than one percentage point on observed tasks may not represent stable true differences.
- Publisher weights, domain definitions and standardisation assumptions remain contestable.
- An external publisher's composite such as the AA Intelligence Index cannot be scored as if it were a leave-one-family-out baseline when it already includes some test families.

## Why Muse rankings are provisional

Muse Wonder Full and Muse Wonder each have **ten original AA constituent scores** in v5.1, against as many as 57 observations for the established models. There is no independently verified Muse coverage from the other eight evaluator groups in the current release. Their estimated positions are substantially sensitive to domain weighting. The dataset records the AA original scores and publication information in `data/v5_1/source_audit.csv`.

Do not claim an eight-model universal winner based on a 10-versus-57 coverage imbalance. Track future independent evaluations under a new evidence release and retain historical outputs unchanged.

## Next scientific milestone

Pre-register predictions on genuinely **future independent benchmark releases** without altering the frozen estimators after observing results. Assess calibration and direction by truly independent benchmark family, version and evaluator; extend model coverage and configuration documentation first.
