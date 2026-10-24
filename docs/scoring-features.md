# Static scoring features: reusable experimental API

The research interface exposes separate attributes for later modelling. It does
not change the production evaluator or select overall leaderboard weights.
Python 3.11+ standard library suffices for extraction and scoring; the optional
cross-validation reproducer needs NumPy.

## Use now

```sh
python3 -m scripts.diagnostics.scoring_features /path/tune.xm \
  --root . --out /existing/directory/features.json
python3 -m scripts.diagnostics.scoring_features /path/tune.xm \
  --root . --source-visit 1 --source-channel 9 \
  --pitched-instruments 5,6,7,8,9,10,11,12,13,17,18,19 \
  --out /existing/directory/selected-features.json
```

Library entry point: `scripts.diagnostics.scoring_features.score_xm(path, root,
*, pitched_instruments=None, melody_channels=None, source_visit=None,
source_channel=None)`. Schema `keygen-static-features-v1` retains source/input
hashes, nominal extraction eligibility, selection scope, values, units, and
status. Channels/instruments are one-based decimal; visits are zero-based.
No source/voice selection is required for the primary point-set attributes.
Optional masks change the construct and must stay recorded; do not substitute a
favorable selected-part score for an unfavorable whole-mixture score silently.

Available outputs include:

- saturated recurrence support and matched-core content;
- fixed-alphabet pitch-class entropy, IOI entropy, and pitch-set motion;
- corroborated changed-shape evidence and an evolution-required score 0–100;
- periodic overlap, including off-grid 15/17 beat loops;
- interval/scale-collection and long-gap phrase-boundary descriptors;
- all unordered common-onset channel interval/motion relationships;
- optional seed-to-occurrence and motif-conditioned harmonic-context witnesses.

Zero evolution means no supported variation under this conservative recipe. A
simple, appealing recurring hook can have zero development. Phrase-gap proxies
are not a measurement of vocal prosody. Unknown percussion, sample tuning,
sustain, slide realization and chord/phrase samples limit nominal-note claims.

## Score definitions and validation status

The frozen [specification](../scripts/diagnostics/theory_score_spec.json) defines
`static-thematic-organization-v1`. A matched core must have 6 points at 4 onsets
spanning 24 ticks and at least.60 coverage on each side. Core content requires
pitch-class diversity AND changing onset pitch sets, so a fixed repeated note
or chord cannot gain melody credit. Controls rerun all pair/partner searches.
Control maxima are descriptive and conservative, not calibrated p-values.

A changed shape needs at least 2 exact copies of each signature, same passage
phase, and at least 2 residual points on one side. Its own recurrence support
weights it before family pooling. A one-position edit is still a possible motif
match but does not automatically earn development. A near-period off the fixed
window grid discounts phase-walk variation. Periodicity alone is not bad music.

The v1 organization hypothesis is 100×core-content×recurrence×(.25+.75×variation)
with a Gaussian preference for 2 bits of matched-core pitch-class entropy, sigma 1.
These entropy constants are declared heuristic priors, not music-theory laws.
An ablation omits the Gaussian. The shared-core gate, not added residual entropy,
determines content. The full-search null maximum is duration/search-size sensitive.

**V1 is retained as a failed general-quality hypothesis.** Mercury 1 whole-mixture
scores 23.30 versus Prism 19.16, despite its fixed-pattern repetition. Its several
parts provide pooled pitch diversity; a recurrence-only allowance can still be
misleading. Do not promote this index as an enjoyment/default benchmark total.

The separately named `supported_thematic_development` feature removes the
recurrence-only allowance:100×core-content×recurrence×confirmed-variation×entropy
preference. It was introduced after observing the v1 failure and is exploratory,
not independently validated aesthetic quality. Mercury 1 has 0, Mercury 2 has 1.00,
Prism has 4.85. Those values indicate supported evolution, not subjective goodness.

See [findings and reproduction](research/theory-graduation/README.md) for the
frozen 51 attempt test, all failures, grouped predictions, and theory hypothesis.

## Reproduce the corpus and predictive check

```sh
python3 -m scripts.diagnostics.run_scoring_study \
  --manifest docs/research/theory-graduation/corpus-manifest.json \
  --root . --cache /path/to/xm-cache --out /path/to/static-results \
  --workers 2 --download
python3 docs/research/theory-graduation/crossvalidate.py \
  --input /path/to/static-results --out /path/to/validation
python3 -m unittest discover -s scripts/diagnostics/tests
python3 -m unittest discover -s benchmark/tests -p test_score_structure.py
```

Omit `--download` for offline analysis of hash-verified cached inputs. Downloads
are read-only public source retrieval, not model calls. Incomplete traversals,
invalid selections, more than 256 windows, or more than 65536 events fail rather
than silently truncating. No claim of exact native rendering equivalence is made.
