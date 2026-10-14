"""Export expanded evidence and the exact comparisons used in the product."""
import json
from pathlib import Path
from reproduce_v52 import main
from frontierlab.core import Evidence, METHODS
from frontierlab.explorer import product_evidence, broad_cohort, standings, domain_standings, robustness, release_changes

ROOT = Path(__file__).resolve().parents[1]


def product_report():
    output = ROOT / "outputs/v5_4"
    reports = {}
    for provisional in (False,True):
        evidence = product_evidence(Evidence(ROOT / "data/v5_4"),provisional)
        cohort = broad_cohort(evidence)
        previous = product_evidence(Evidence(ROOT / "data/v5_3"),provisional)
        reports[str(provisional).lower()] = dict(include_provisional=provisional, cohort=cohort,
            comparison_rules="At least 20 results, 3 evaluator labels, 6 domains; threshold independent of score",
            standings={m:standings(evidence,cohort,m) for m in METHODS},
            full_roster={m:standings(evidence,evidence.models,m) for m in METHODS},
            previous_release_changes={m:release_changes(previous,evidence,cohort,m) for m in METHODS},
            domain_leaders={m:{d:domain_standings(evidence,d,m) for d in evidence.domain_weights} for m in METHODS},
            evaluator_removal={m:robustness(evidence,cohort,m) for m in METHODS},
            family_removal={m:robustness(evidence,cohort,m,"family") for m in METHODS})
    (output / "product_comparisons.json").write_text(json.dumps(reports,indent=2) + "\n",encoding="utf-8")
    print("Exported both provisional-result policies, fixed broad cohorts and removal checks")


if __name__ == "__main__":
    main("v5_4")
    product_report()
