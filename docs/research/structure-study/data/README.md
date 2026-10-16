# Public summary data

These are compact allowlisted exports of the reported results. They contain no
local resolver, filesystem cache, raw transcript, provider account inventory
or authentication fields. Public attempt IDs and pinned audio links identify
already published upstream artifacts. JSON uses null for undefined values.

| Files | Rows / content | Meaning |
| --- | --- | --- |
| `associations.csv`, `.json` | 104 | 13 fixed features × four cohorts × full/prefix horizons; feature-specific n/models, rho and pointwise 95% model-cluster interval. C1/C2 remain adversarially rejected. |
| `heldout-summary.csv`, `.json` | 16 | Four cohorts × four grouping/horizon choices; RMSE and equal-model MSE improvement with fixed-prediction bootstrap intervals. |
| `audio-stability.csv`, `.json` | 48 | Two public exemplars, mel/chroma, tempo/phase/context settings, aligned matrix differences and decoded-PCM hashes. |
| `fixture-summary.csv`, `.json` | 57 | The shipped synthetic subset: P/V/G/H and explicitly rejected C1/C2. Reproduce inputs and raw outputs with `run_fixtures.py`. |
| `selected-listening.csv`, `.json` | 4 | Retrospective historical listening queue, local CE, diagnostic disagreements, strict-timing flag, public source ID/audio link and Git blob SHA-1. |
| `coverage.json` | Counts | Attempt/artifact/label coverage, validation counts and official/local listener agreement. |
| `provenance.json` | Identity | Upstream commit; frozen spec/statistical-input/source hashes; listener identity and versions; source/public PNG hashes; table hashes. |
| `statistical-input.csv` | 730 | Allowlisted joined statistical rows: public IDs, official/local CE kept separate, eligibility flags and features. No route, authentication, raw log or local-path fields. Used by the minimal association reproducer. |

`analysis_horizon` labels the analysis comparison. `feature_horizon` separately
records the actual feature input: older mel/chroma always use audio first 120
seconds; older symbolic SSM always uses full-traversal row windows, including
in prefix tables. Only the `prefix_*` event/current-SSM features use the matched
complete-row prefix. This distinction prevents a prefix table heading from
implying every legacy feature was recomputed on that prefix.

`official_rowstart` means complete row-start extraction with official CE;
`official_strict` additionally requires supported nominal-onset timing. `local_*`
use local listener inference separately. `prefix_*` features exclude a complete
row that would cross 120 seconds. Older symbolic SSM remains full-song even
in prefix association tables. `prefix_model`/`prefix_family` transfer groups
use prefix-horizon inputs; family is a model-name-prefix grouping.

Association intervals are pointwise from 2,000 model-cluster resamples, seed
20261016. Related models/campaigns may remain dependent. Transfer intervals
resample fixed model-level cross-fitted errors and omit retraining uncertainty.
These are observational summaries, not causal or human-quality estimates.

All listening selections were made retrospectively by the announced percentile
disagreement/high-local-CE rules. They are neither independent discoveries nor
unbiased estimates of musical quality. No labels influenced diagnostic formula
parameters. [Methods and limitations](../methods-and-results.md).

Public tables permit inspection, overview plotting and exact reproduction of
the 12 official P/H/current-SSM association/interval results using
[`reproduce_associations.py`](../reproduce_associations.py). That requires
NumPy 2.2.6 and SciPy 1.16.1 for the recorded environment. It makes no API calls.
The input is an allowlisted statistical join, not the underlying audio, XM or
complete extraction artifacts. It does not replace the unshipped acquisition,
audio-analysis, inference or held-out regression pipeline.
The 246-fixture archived validation count is distinct from the 57 rows shipped
here. Source hashes are identity records, not claims that the corresponding
large private work artifacts are published.

The [external capability comparison](../external/protocol.md) ships its complete
numerical reproduction inputs and code separately. Its `music-input.csv` is an
allowlisted 730-row subset with recorded music effort; `external-scores.json`
contains selected leaderboard scores and task windows. `identity-mapping.json`
and source metadata document accepted releases and exclusions. Model medians,
component percentile ranks, 264 correlations and all family-deletion results
are exposed in that directory. Its own `manifest.json` binds every exported
file. The 50/50 mix is an exploratory reference, not a musical-quality label.
