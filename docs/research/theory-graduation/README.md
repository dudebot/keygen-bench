# Mercury counterexample and theory-led scoring findings

## Question and predeclared experiment

Can static recurrence, melodic information, repeated variation and phrase/rhythm
descriptors recover useful musical attributes and predict Audiobox production
complexity? An R-squared near 0.8 was a user hypothesis to test, not a fitting target.
This study tests it rather than assuming theory rules cannot help.

The corpus has 51 available ranked attempts from 18 exact model groups and 9 makers.
It retains all available attempts of the 6 previously examined groups, then samples
12 additional eligible model keys with `random.Random(20261024)`, retaining all
available attempts. The [manifest](corpus-manifest.json) records the exact sample,
public source URLs, input hashes, published listener attributes, specification
hash and protocol. This is an exploratory convenience sample from one benchmark,
not independent human-labelled music. Synthetic-contract fixes were made before
real-score comparison; there was no formal external preregistration.

The v1 specification SHA-256 is
`17c0ee848a59af41f36fabf62ace8823a4007e81b8a0f9b14b70afb6b485b131`.
The no-entropy ablation, entropy-only predictor, constant predictor,
duration/density baseline and fixed-lambda 1 ridge feature model were declared
before the corpus comparison. No thresholds/weights were tuned to R² = 0.8 or to
rank Prism Relay first. Code/API correctness fixes preserve frozen numeric results.

## Mercury: monotony is real, but not literally a single pitch

- Attempt 1, **KEYGEN TUNE**: one 32 row pattern played 4 times. The nominal lead
  alternates between 2 pitches; bass uses 3 and arp 3. No note effects rescue hidden
  variation. This is a strong fixed-template counterexample.
- Attempt 2, **KeyGen 2024**:16 patterns; the lead has 5 pitches, with 136/224 events
  (60.7%) on one pitch. Bass has 2 pitches and changes on only about 1.3% of
  successive attacks. The lead pitch changes on about 25.6% of attacks.
- Attempt 3 failed and has no published valid module. It is not assigned a zero
  musical-quality score or silently replaced by another attempt.

Static note codes do not establish the full sample's audible content. These
statements concern the trusted nominal event traversal and independently
inspected source cells, not a claim of having listened to every render.

## Frozen v1 failure and the separate evolution attribute

| Module | V1 organization hypothesis | Evolution-required attribute |
| --- | ---: | ---: |
| Mercury 1 |23.2990|0.0000|
| Mercury 2 |6.0082|1.0013|
| Sol 1 Phosphor Afterhours |13.3776|0.0000|
| Sol 2 Neon Parallax |12.7307|1.3663|
| Sol 3 Prism Relay |19.1573|4.8512|

The frozen v1 candidate **fails the requested Mercury 1 versus Prism quality
contrast**. It assigns up to 25 points for recurrence without evolution; Mercury's
several parts supply pooled pitch entropy near the heuristic preference. This
is a construct failure, not a bug to hide. The failed candidate and ablation
remain available for falsification, not as validated ranking recommendations.

A separate evolution-required feature gives unchanged loops 0 by the definition
of development. It retains the v1 controls/core/variant recipe and removes the
recurrence-only allowance. It was added AFTER seeing the failure, so these same
corpus results are exploratory follow-up, not a fresh held-out confirmation.
Prism has more supported evolution than Mercury in this definition; that is
not a proof that every zero-development melody is unattractive.

Reviewed lead-only sensitivity (explicit selection, not automatic voice finding)
also exposes the mixture confound: Mercury 1 ch 2 v1=3.791; Mercury 2 ch 5=1.924;
Prismch 9=18.652. These results are not silently substituted for primary scores.

## Complexity cross-reference

All means/scales, model coefficients and ridge fits use training folds only.
Exact model attempts stay together. A second analysis holds out whole makers.
R² is 1−heldout squared error/global target sum of squares; negative values are
retained. Exact-model holdout is not called independent model-family holdout.

| Predictor of production complexity | Hold out model | Hold out maker |
| --- | ---: | ---: |
| Intercept only |−.110|−.111|
| Raw pitch entropy |.515|.516|
| Duration + onset density |.287|.229|
| Frozen v1 bell-shaped score |−.151|−.185|
| No-entropy score ablation |−.151|−.182|
| Fixed ridge over static attributes |.527|.463|

The raw static attributes carry predictive information about production complexity.
The hypothesized 0.8 heldoutR²was not reached. The bell-shaped combined index does
not predict complexity here. The richer vector adds little over entropy in
model holdout and worsens in maker holdout; it is not established as a better
predictor than entropy alone. Complexity is a production-related machine label,
not independently measured catchiness, pleasantness, or human melodic quality.

Other fixed-ridge heldoutR²values(model/maker): content enjoyment.315/.234;
production quality−.045/−.132; content usefulness−.037/−.113. No multiple-model
selection, significance or generalization-to-all-music claim is made. Related
versions and the shared dataset can remain dependent even across maker folds.

[All attributes](attributes.csv), [all complexity heldout predictions](predictions.csv),
[all validation rows](validation.csv), [machine-readable summary](results.json).
The [reproducer](crossvalidate.py) needs NumPy; runtime scoring is stdlib-only.

## Tests, review and promotion boundary

The local verification passed 75 diagnostic tests and 24 unchanged baseline tests (99 total).
The regression battery includes drones, fixed chords, exact loops, corroborated
variant fixtures, random notes, random ornaments, channel splits/unison doubles,
octave shifts, trailing silence,15/17 beat phase walk, iterator inputs and resource
bounds. Astra independently tested 72 ornament cases (24 seeds×densities 1/2/4),
all below the exact-loop baseline with zero confirmed variation, and independently
reproduced every entropy-only and bell-score complexity prediction to 1e-9.

The code is graduated into a versioned **experimental feature API**, with separate
values, scope/eligibility, provenance, and reproducible recipes. It is not a
production evaluator change, universal aesthetic verdict, or calibrated human
preference model. Harmony descriptions and onset-gap phrase proxies remain
available separately. Future work includes sustained-note/acoustic pitch
recovery, blind motif/phrase annotations, automatic voice selection, broader
corpora, and additional theory-led hypotheses tested without desired-rank tuning.

Relevant empirical motivation: [Gold et al.  2019](https://www.jneurosci.org/content/39/47/9397)
studies predictability/uncertainty and musical pleasure. It does not establish
that 2 bits of global pitch entropy is universally optimal. The Gaussian here is
a declared heuristic being falsified, not a result claimed from that paper.
