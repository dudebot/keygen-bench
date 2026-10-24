# Experimental channel-free event recurrence

This offline research prototype compares nominal onset/pitch point sets. It is
not a replacement evaluator, a recovered perceptual melody, or a quality score.
It requires only Python 3.11+ standard library and the reviewed source tree.

```sh
python3 -m scripts.diagnostics.motif_events --help
python3 -m scripts.diagnostics.motif_events /absolute/path/tune.xm \
  --root . --controls 8 --out /absolute/existing/directory/result.json
python3 -m unittest scripts.diagnostics.tests.test_motif_events -v
```

The adapter AST-loads the existing trusted parser and imports the reviewed
sequence module. Submitted code is never executed. Provenance hashes and existing
nominal extraction flags are retained. No audio, model, provider, or network call
is made by the analyzer.

## Representation and search

Ignore channel and instrument IDs in the primary comparison. Collapse exact
simultaneous unisons; retain absolute tracker pitch. Fixed 96/192-tick windows
(4/8 conventional beats) align by one constant pitch shift -12..12 semitones
and one time shift -18..18 ticks in steps of 6. Exactly matching points give
one-to-one witnesses. F1 = 2 * matched / (left count + right count); both-side
coverage and unmatched material remain distinct. An early ornament does not
re-anchor all subsequent pitches. The bitset representation is an exact search
optimization, checked against independent direct set intersections.

Candidate pairs in the summaries require at least six matched points at four
onsets spanning at least 24 ticks. Raw matrices are also provided. The report
retains the occurrence order as matrix coordinates; it does not assert a
scalar judgment of long-range form.

## Controls

For eight deterministic controls, canonicalize onset/pitch sets and permute whole
simultaneous pitch tuples within onset-cardinality and tick-modulo-24 strata.
This preserves the onset clock, onset cardinality, global pitch marginals, and
chord geometry. No channel labels enter controls. Degenerate strata remain
unchanged. Re-run every pairwise alignment/maximization on each control.

Observed F1 minus the maximum control F1 is a descriptive effect-size reference,
not a p-value or calibrated confidence. `mean_best_excess` averages each window's
best eligible margin. `positive_best_match_fraction` uses an exploratory display
threshold of .05. These numbers are not comparable with the old development
score's scale and must not be blended into leaderboard rankings without further
validation. Both pair and partner searches create selection effects.

## Additional witness tables

`carrier_candidates` lists channel-local pitch/event/instrument evidence; it
neither chooses nor certifies a main voice. `lane_relations` separately detects
short-lag unison copies and synchronous constant-interval parallels. Constant
or near-constant pitch lanes are labelled rhythmic-copy candidates. These
channel-local tables do not inherit the primary channel-splitting invariance.

`delayed_copy_sensitivity` hypothetically removes matched target events from
acyclic pitched-copy pairs with F1 >= .9 and repeats the analysis. It
retains unmatched target events. This is a sensitivity view, not a claim that
copies were audio echoes. A canon and a sheet-coded delay may be symbolically
identical. No explicit row volume is used to infer decay.

## Known limits

- Whole-mixture matches can reflect accompaniment instead of melody. A matched
  point path does not establish a perceptual voice or thematic family.
- No automatic main-voice selection, diatonic harmony model, inversion,
  augmentation, duration matching, or arbitrary timing warping is implemented.
- Fixed windows split motifs and cannot establish invariance to arbitrary
  leading silence, phrase length, or local rhythmic displacement. Trailing
  silent padding alone adds no windows; internal silence remains meaningful.
- Exact tick matching inherits the upstream adapter's timing limits, especially
  EDx/retriggers, portamento, slides, and instrument-only effects. Written pitch
  is not calibrated sample acoustic pitch; PCM audibility is unverified.
- A 17-beat loop can create changing bar phase. The program reports recurrence,
  not a claim of development. More recurrence is not necessarily better music.
- Incomplete traversals and inputs above 256 windows are rejected instead of silently truncated.

Before adding a structural score, define the construct, annotate blinded motif
correspondences, validate false positives and the full discovery search under
matched nulls, and assess error on held-out module families. Enjoyment is a
separate target. The previous study's rejected scalar failures remain relevant:
[methods and results](research/structure-study/methods-and-results.md).

For section-to-section motif identity, channel/instrument handoffs, and conditional
harmonic context, see [phrase relationships](phrase-relationships.md).
