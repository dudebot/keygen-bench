# External proxy protocol

The analysis plan was frozen before joining external scores to music descriptors.
Original plan SHA256: `4a0d8db07ac445f9dfb2115358cf658715940f13a434e32042064aa307ae7b0b`.
`implementation-freeze.json` records the initial analysis-code hash and the
implementation choices made before the first join. The published script omits
the private one-time acquisition routine; its numerical analysis is unchanged.
Later changes improve report wording and show both cohorts in the scatter plot.

The primary units are named model releases, summarized by the median of their
ranked-slot music attempts. All-history medians are a sensitivity. Missing
measurements stay missing. Symbolic features need complete extraction and
their existing eligibility gates. In the separate strict-timing sensitivity,
all metrics, including audio and enjoyment, use only complete and strictly
timed symbolic attempts. No best-attempt selection, learned weights, or fitting.

Targets are EQ-Bench 4 social/emotional roleplay Elo, Creative Writing v3 prose
Elo, and SWE-rebench all-language resolved rate in its common tools harness.
Coding uses model instances only. Latest task window: May 15 to July 1, 2026;
preceding sensitivity: March 1 to May 15, 2026. These are task dates, not run dates.
Choose medium reasoning when multiple configurations exist; otherwise retain
the sole reported configuration. Other effort and provider differences remain.

For each window the 50/50 proxy averages `(average_tie_rank - 1)/(n - 1)` for
the two components on the external complete-case model intersection. That rank
population stays fixed when a music feature is missing or a family is deleted.
Components are reported separately. This mix is an external capability proxy,
not a musical-quality target. Enjoyment is another comparator, not ground truth.

All six targets, eleven descriptors, two music cohorts, and both timing modes
are reported. Spearman correlations and leave-one-name-prefix-family-out ranges
are descriptive; deletion ranges are not confidence intervals. No p-values or
significance claims. Small model/family counts cannot establish incremental
prediction, independence, or usefulness. C1/C2 remain rejected independently.

Identity review excludes known V4-Pro unchanged-name updates, Gemini3.5 redirects,
and the ambiguous SWE Gemma31B instruction variant. Official dated GPT aliases
are linked in the mapping. Accepted names identify releases, not immutable
weights, quantization, routing, or identical deployments. External raw pages
and original hashes were archived; the publication contains the selected
numeric inputs and source metadata needed to reproduce these calculations.
The Fable 5 citation is clarified in `identity-evidence-addendum.json`: its
direct legacy model page explicitly lists the API identifier; the original
overview URL now redirects. This clarification changes no mapping or value.

Run `python analyze_external_proxy.py --data .` with NumPy, SciPy, pandas, and
Matplotlib. The script performs no network calls. Runtime versions are recorded
in `results.json`. `manifest.json` hashes the exported files. Publication inputs
use UTF-8 LF; `freeze.json` preserves original source-byte hashes separately.
