# External proxies: frozen descriptive analysis

This analysis asks whether structural descriptors vary with external conversational and coding capabilities. Enjoyment is a separate comparator. None of these labels defines musical quality. C1/C2 remain rejected by their independent adversarial tests and were not reconsidered here.

Current voice SSM shows positive descriptive associations with EQ4 (+0.672, n=20) and prose creativity (+0.501, n=31). P and H have much weaker associations with those two targets. H has a strong latest-mix association in ranked attempts (+0.837, n=7), but this drops to +0.036 with all-history medians and -0.091 with strict all-history medians. That cohort sensitivity prevents treating the strongest result as a stable capability relationship or a validated metric improvement.

## Protocol and identity

Frozen protocol SHA256: `4a0d8db07ac445f9dfb2115358cf658715940f13a434e32042064aa307ae7b0b`. No fitting, optimized weights, benchmark switching, p-values, or significance verdicts. Exact displayed/API release names and documented aliases were reviewed before joining music data. These are named-release matches, not proof of identical weights or deployments.

Excluded: DeepSeek V4-Pro (known unchanged-name update), Gemini3.5Flash (known redirection to3.6), and SWE-rebench Gemma31B (instruction variant unspecified). Official GPT5.4/5.5 pages document the dated snapshot aliases. The external cohort contains EQ4=21, CW3=32, latest coding=8, preceding coding=10; the equal-weight mix contains latest=7 and preceding=10 before music missingness. Latest coding alone additionally includes Grok4.5.

## Main results

Each cell is Spearman rho (number of model versions). Models contribute medians over their ranked-slot attempts, never their best outcome. Unequal available attempt counts are in the data. In the primary row-start analysis, symbolic metrics require complete extraction and their own diagnostic eligibility; audio metrics and CE retain their own available audio rows. The strict-timing sensitivity filters the entire cohort, including audio metrics and CE, to complete and strictly timed symbolic extraction. Unsupported symbolic timing remains a nominal row-start description.

| Descriptor | EQ4 | Prose CW3 | Coding latest | Mix latest | Coding preceding | Mix preceding |
| --- | --- | --- | --- | --- | --- | --- |
| Current voice SSM | +0.672 (20) | +0.501 (31) | +0.333 (8) | +0.400 (7) | +0.418 (10) | +0.491 (10) |
| Predictive organization P | +0.033 (19) | +0.150 (31) | +0.119 (8) | -0.109 (7) | +0.176 (10) | +0.309 (10) |
| Pitch transport H | +0.078 (20) | +0.123 (31) | +0.905 (8) | +0.837 (7) | +0.321 (10) | +0.394 (10) |
| Official enjoyment | +0.701 (20) | +0.687 (31) | +0.167 (8) | +0.673 (7) | +0.224 (10) | +0.321 (10) |
| Local enjoyment sensitivity | +0.701 (20) | +0.662 (31) | +0.167 (8) | +0.673 (7) | +0.224 (10) | +0.321 (10) |
| Mel SSM nonlocal mean | -0.203 (20) | -0.045 (31) | -0.381 (8) | -0.600 (7) | +0.018 (10) | -0.176 (10) |
| Chroma SSM nonlocal mean | +0.415 (20) | -0.101 (31) | -0.381 (8) | -0.164 (7) | -0.345 (10) | -0.091 (10) |
| Old symbolic SSM nonlocal mean | -0.305 (20) | -0.594 (31) | -0.381 (8) | -0.855 (7) | +0.115 (10) | -0.006 (10) |
| Current voice SSM, prefix | +0.666 (20) | +0.452 (31) | +0.333 (8) | +0.400 (7) | +0.418 (10) | +0.491 (10) |
| Predictive P, prefix | +0.033 (19) | +0.150 (31) | +0.119 (8) | -0.109 (7) | +0.176 (10) | +0.309 (10) |
| Pitch transport H, prefix | +0.078 (20) | +0.123 (31) | +0.905 (8) | +0.837 (7) | +0.321 (10) | +0.394 (10) |

## Family sensitivity for the latest mix

The interval below is the minimum and maximum after deleting one observed name-prefix family. It is a sensitivity range, not a confidence interval. The external percentile ranks remain frozen while music rows/families are removed.

| Cohort | Timing | Descriptor | n / families | rho | Family deletion range |
| --- | --- | --- | --- | --- | --- |
| ranked_slots | row_start | current_SSM | 7 / 4 | +0.400 | +0.203 to +0.949 |
| ranked_slots | row_start | P | 7 / 4 | -0.109 | -0.406 to +0.211 |
| ranked_slots | row_start | H | 7 / 4 | +0.837 | +0.738 to +0.872 |
| ranked_slots | row_start | official_ce | 7 / 4 | +0.673 | +0.493 to +0.738 |
| ranked_slots | strict | current_SSM | 7 / 4 | +0.636 | +0.464 to +0.949 |
| ranked_slots | strict | P | 7 / 4 | -0.527 | -0.754 to +0.211 |
| ranked_slots | strict | H | 7 / 4 | +0.655 | +0.464 to +0.765 |
| ranked_slots | strict | official_ce | 7 / 4 | +0.600 | +0.377 to +0.738 |
| all_history | row_start | current_SSM | 7 / 4 | +0.600 | +0.435 to +0.949 |
| all_history | row_start | P | 7 / 4 | -0.145 | -0.308 to +0.211 |
| all_history | row_start | H | 7 / 4 | +0.036 | -0.949 to +0.319 |
| all_history | row_start | official_ce | 7 / 4 | +0.673 | +0.493 to +0.738 |
| all_history | strict | current_SSM | 7 / 4 | +0.455 | +0.203 to +0.949 |
| all_history | strict | P | 7 / 4 | -0.564 | -0.667 to +0.211 |
| all_history | strict | H | 7 / 4 | -0.091 | -0.949 to +0.051 |
| all_history | strict | official_ce | 7 / 4 | +0.600 | +0.377 to +0.738 |

## What the study can establish

Different associations describe differences within this selected corpus; they do not by themselves establish statistical independence, musical usefulness, or a causal relationship with general capability. A structural dimension earns its interpretation through controlled examples and invariance tests. Its practical usefulness would require a defined downstream decision or human comparison, not merely agreement with a model leaderboard. No replacement scoring formula is proposed.

The two coding windows use different task sets and are never pooled: latest is 2026-05-15 to 2026-07-01; preceding is 2026-03-01 to 2026-05-15. These are task-date windows, not evaluation dates. The source model release dates are metadata and not evidence of when a run occurred. SWE effort is medium where multiple configurations exist, otherwise the single recorded setting. Music often used max effort.

EQ4 evaluates simulated multi-turn social/emotional interaction; CW3 evaluates single-turn prose. Model judges, selected frontier families, provider routes, prompts, attempt failures, time, and differing effort can all confound these retrospective correlations. External uncertainty is not estimated by treating multiple music attempts as independent models. Small n and few families preclude a reliable incremental-prediction claim.

## Horizons and reproducibility

Full symbolic metrics describe the full parsed traversal. Prefix P/H/current SSM use complete rows ending no later than120 seconds. Mel/chroma SSM and listener CE use the first120 seconds of audio. Old symbolic SSM remains full traversal. Corresponding horizon labels accompany every numerical association.

`associations.csv` contains every predeclared target, metric, ranked/all-history cohort, and row-start/strict sensitivity. `family-deletions.csv` contains each omitted family. `model-medians.csv`, `joined-models.csv`, and `external-scores.json` expose denominators and component ranks. `descriptor-pairs.csv` reports descriptor-to-descriptor model-level relationships without an external target. `identity-mapping.json` gives accepted/excluded mappings and primary source links. No raw prompts, local paths, credentials, or route configuration are required by the reproduction inputs.

Reproduce with `python analyze_external_proxy.py --data .` from this directory after installing numpy, scipy, pandas, and matplotlib. `music-input.csv` is an allowlisted730-row extract. The script uses only saved inputs and has no network calls.

Sources: [EQ4](https://eqbench.com/), [Creative Writing v3](https://eqbench.com/creative_writing.html), [SWE-rebench](https://swe-rebench.com/leaderboard), [SWE-rebench methodology](https://swe-rebench.com/about).
