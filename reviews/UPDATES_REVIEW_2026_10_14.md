# Model and benchmark update review — 14 October 2026

This review informed the implemented v5.4 release. The product now leads with model comparisons and conclusions, supported by evidence breadth and rank stability. Source records remain available as supporting detail. The pre-expansion v5.3 analysis below is retained as the dated baseline.

## Implemented expansion

v5.4 adds AA-3D (five observations), AA FrontierCode 1.1 (six), RareBench (six) and LabBench (three): 20 additional results, four executions and three new families. Total: 61 rows / 59 families / 326 observations / ten evaluator labels. The two FrontierCode executions share the `frontiercode` family. All earlier scores, scales and observation records are preserved.

The primary product cohort uses reporting thresholds independent of score: at least 20 results, three evaluator labels and six domains. Provisional results are off by default; the toggle includes Argon EAP and publisher-review observations. Opus leads the broad six-model cohort under all three weighting conventions and retains first place in nine of ten evaluator-removal checks under each convention. These are sensitivity counts, not calibrated probabilities. All-model fits, domain comparisons and both inclusion policies are exported in `outputs/v5_4/product_comparisons.json`; the earlier JSON review describes v5.3 only.

New-row normalizers use max(scale floor, population SD of recorded original six-model identities), fixed at first inclusion; missing scores are omitted. Earlier normalizers are unchanged. AA-3D is grouped under Multimodal, AA FrontierCode under Coding, and Gamow's two evaluations under Science. Cross-family task independence and equal computation have not been certified. The new records are auditor transcriptions of published rounded scoreboard values, not original webpage archives.

## Current portfolio and conclusions

The live v5.3 release contains 57 evaluation rows, 56 benchmark families, 306 recorded results, seven capability domains and nine evaluator labels. Its AA Intelligence Index values are external comparators, excluded from aggregation; the ten underlying AA benchmark rows are included directly.

For the original six-model cohort, Opus ranks first under Equal families, Equal domains and Super-Aggregate v4.2. Removing one evaluator at a time gives Opus rank 1–2 under each convention. Removing a family gives rank 1 throughout under Equal families and Super-Aggregate, and rank 1–2 under Equal domains. These are sensitivity results, not statistical confidence probabilities.

For the eight-model roster, Opus is first under two conventions and Muse Wonder Full under Equal domains. Muse Wonder Full has only ten recorded results, all from AA; it should be presented as a contender with narrow evidence rather than given the same evidence-strength label as Opus's 57 results across nine evaluator labels.

## Gemini 4 Argon

Google announced general availability on **13 October 2026** through the paid Gemini API / AI Studio, enterprise access and supported consumer subscriptions. Our roster already includes Argon with 34 recorded results, but its registry still says API access unknown and has no release date. Those metadata need a versioned update. Availability alone does not revise historical scores or certify that earlier evaluated snapshots match today's public endpoint.

Sources: [Google launch](https://blog.google/intl/en-in/products/introducing-gemini-4-argon/), [public API model](https://ai.google.dev/gemini-api/docs/models/gemini-4-argon).

There is a newly identified AA FrontierCode result for Argon: **42.6%**, evaluated at high effort in Stirrup. AA-3D's current 21-model board does not list Argon. Neither board lists Muse Wonder or Muse Wonder Full; Muse Spark results must not be substituted for either model.

## AA-3D

AA launched this benchmark on **12 October 2026**. It is absent from our portfolio and adds a distinct family of interactive 3D creation tasks. It evaluates 55 scene briefs using an offline Stirrup sandbox, with one attempt, a three-hour limit and up to 250 turns. Ratings come from recruited-panel blind preferences over eligible scenes.

The current AA Intelligence Index's ten constituent evaluations exclude AA-3D. The current Coding Agent Index's three components also exclude it.

| Model in our roster | AA-3D Elo | Publisher's 95% interval |
| --- | ---: | --- |
| Claude Sonnet 5.5, max with fallback | 1194 | 1160–1228 |
| Claude Opus 5.5, max with fallback | 1190 | 1155–1225 |
| GPT-6 Astra, max | 1165 | 1131–1199 |
| Claude Fable 5.1, max with fallback | 1131 | 1098–1165 |
| GPT-6.1 Sol, max | 1114 | 1081–1148 |

The point-score leader is Sonnet; the published intervals do not justify treating the exact top ordering as certain. The 55 tasks belong to one benchmark family, not 55 independent benchmark families.

Sources: [leaderboard](https://artificialanalysis.ai/evaluations/aa-3d), [methodology](https://artificialanalysis.ai/methodology/aa-3d).

## FrontierCode 1.1

**Already included:** our B036 row is Cognition's FrontierCode 1.1 Main, using vendor agent harnesses and reported effort settings. Cognition released 1.1 on **7 July 2026**. AA's **12 October** release is a new independent execution of the same Main task set, rather than a new benchmark version.

**Not included in either AA composite today:** AA explicitly excludes FrontierCode from Intelligence Index v4.3.2. Coding Agent Index v1.5 currently averages DeepSWE v1.1, Terminal-Bench 4.0 and SWE-Atlas-QnA. AA's launch article says it plans to add FrontierCode to the coding-agent leaderboard.

| Model | Current Cognition row | Additional AA run |
| --- | ---: | ---: |
| Claude Opus 5.5 | 54.6 | 52.2 |
| GPT-6 Astra | 53.3 | 47.0 |
| GPT-6.1 Sol | 50.2 | 49.1 |
| Claude Fable 5.1 | 50.9 | 49.0 |
| Claude Sonnet 5.5 | 52.1 | 45.8 |
| Gemini 4 Argon | Missing | 42.6 |

AA uses Stirrup, 100 Main tasks, three attempts per task and GPT-6 Luna medium as the rubric judge. These results must remain a separate execution row from Cognition's vendor-harness runs, with the shared FrontierCode family retained so the same tasks do not receive two families' weight. Values above are published rounded scores, not downloaded raw attempt data.

Sources: [AA results](https://artificialanalysis.ai/evaluations/frontiercode), [AA launch](https://artificialanalysis.ai/articles/frontiercode), [Cognition 1.1](https://cognition.com/blog/frontier-code-1.1), [Intelligence Index methodology](https://artificialanalysis.ai/methodology/intelligence-benchmarking), [current Coding Agent Index](https://artificialanalysis.ai/agents/coding-agents).

## Additional scientific evidence surfaced by the Gemini release

Gamow Labs publishes two families absent from our portfolio. These benchmarks predate the public Gemini launch; they are newly identified portfolio additions, not new future-study outcomes. The Argon results explicitly use **EAP** configurations in Antigravity and must retain that label rather than being represented as verified public-API runs.

| Model / evaluated agent | RareBench complete causal recall | LabBench mean task score |
| --- | ---: | ---: |
| Gemini 4 Argon EAP / Antigravity (Science on RareBench) | 57.4% · 70/122 | 52.2% · 20 tasks |
| Claude Opus 5.5 / Claude Code | 51.6% · 63/122 | 40.5% · 20 tasks |
| GPT-6 Astra / Codex | Not listed | 40.8% · 20 tasks |
| Claude Fable 5.1 / Claude Code | 40.2% · 49/122 | Not listed |
| Claude Sonnet 5.5 / Claude Code | 40.2% · 49/122 | Not listed |
| GPT-6.1 Sol / Codex | 32.0% · 39/122 | Not listed |
| Muse Wonder / Muse Code | 18.9% · 23/122 | Not listed |

Different model or agent configurations are not interchangeable. RareBench's selected metric is Rank@K complete causal recall. LabBench averages rubric criteria per task over 20 tasks; it is not a percentage of entire tasks solved. The latest displayed selected scorecards are 12 October for RareBench and 8 October for LabBench.

Sources: [current Gamow results](https://gamowlabs.com/benchmarks), [RareBench study](https://gamowlabs.com/rarebench-0-1), [LabBench study](https://gamowlabs.com/labbench-benchmarking-ai-wet-lab-decisions).

Google also reports ERQA at 87%. This is another multimodal candidate, but comparable scores for our current roster and precise evaluated conditions need checking before inclusion. The public [ERQA repository](https://github.com/embodiedreasoning/ERQA) documents 400 multimodal questions. DeepSWE v1.1 and the public SWE-Atlas-QnA component are further coding coverage candidates; check their task/harness relationship to existing rows before assigning family weights.

## Recommended next release and product order

1. Update Argon's availability metadata in a new release while retaining all frozen inputs.
2. Curate AA-3D, AA's FrontierCode run, RareBench and LabBench as distinct execution rows. This would add three distinct families and one further execution of an existing family, subject to final inclusion decisions and normalization review. Do not count AA composite scores again.
3. Recompute comparisons, domain leaders and deletion sensitivity before changing headline conclusions. Keep sparse contenders and EAP results explicitly qualified.
4. Lead the product with overall leaders, best models by task, evidence breadth, ranking stability and release changes. Place source documents and run metadata one click below the relevant result. Express confidence through measured stability and coverage, not an invented probability.

No live scores, historical releases, registered forecasts or private reviews were changed in this investigation. No paid model calls were made. These pre-registration task families must not enter the prospective study as new-family future outcomes.
