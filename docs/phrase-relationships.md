# Motif continuity across sections and voices

The research objective is multiple separate scoring attributes. Motif recurrence,
variation, cross-part interval/motion relationships, enjoyment and cost efficiency
retain their own measurements. Their eventual combination is deferred.

## Offline query

Python 3.11+ standard library; no model or network calls. From the reviewed root:

```sh
python3 -m scripts.diagnostics.phrase_relationships --help
python3 -m scripts.diagnostics.phrase_relationships /path/tune.xm \
  --root . --source-visit 1 --source-channel 9 \
  --pitched-instruments 5,6,7,8,9,10,11,12,13,17,18,19 \
  --out /existing/directory/phrase-result.json
python3 -m unittest scripts.diagnostics.tests.test_phrase_relationships -v
```

Source visits are zero-based played section visits. Channels and CLI instrument
IDs are one-based decimal. Pattern IDs displayed in the study are hexadecimal.
The query example refers to Prism Relay. It is not a universal lead classifier.

The original trusted traverser is AST-instrumented to retain order/pattern/row
addresses; its original nine return values are unchanged. A new section visit
starts on an order/pattern change or nonconsecutive source row. A repeated stored
pattern remains a separately labelled played occurrence.

## Motif identity and occurrence provenance

The seed is a caller-selected lane in a section; target searches pool all channels.
Identity uses relative onset time and nominal pitch under a constant chromatic
shift of at most 12 semitones. Channel and resolved instrument IDs only label
matched witnesses. Whole-phrase and 96 tick opening-cell queries keep section-start
phase fixed and return source recall, target purity and F1 separately.

A second search finds contiguous 4–8 note seed fragments anywhere in another section,
with exact relative rhythm and a constant pitch translation. Target additions do
not erase intact seed points. Nested matches are thinned only under the same
pitch AND time translation. Maximal means within this bounded search, not longest
possible themes; outputs display at most 30 matches per target section. A four-note
scale fragment alone does not establish thematic identity.

The primary match tolerates meaning-preserving channel/instrument reassignment,
including a motif distributed across channels inside the target phrase. A target
may still contain a dense chord cloud that happens to include every seed point.
Pooled recall cannot establish a coherent audible voice: keep purity, local note
witnesses and single-lane realization evidence visible. `duplicate_provenance_fraction`
only measures multiple channels supplying the same matched point; it is not a
voice-path ambiguity probability. Candidate source selection remains an analyst
hypothesis, not an automatic mainvoice guarantee.

Instrument-change evidence for a complete single-lane realization is computed
from the instruments at those matched events. Another simultaneous lane does not
make an unchanged realization count as a timbre change. Instrument ID changes
are provenance; identity and matching do not depend on names or IDs.

## Harmonic relationships

`cross_part_intervals` reports reference-lane versus other-lane common onsets:
signed and modulo 12 interval histograms, support/coverage, third/sixth and
unison/octave fractions, and parallel/similar/contrary/oblique motion counts.
Motion transitions connect successive shared singleton onsets, possibly skipping
other attacks. No universal better/worse interpretation is assigned.

Each matched occurrence also has harmonic-context witnesses. Context follows the
matched carrier channel at EACH point, including a within-phrase handoff, rather
than always inspecting the original lane. Source/target context includes only
new pitches at that onset; sustained sonorities are not reconstructed. A changed
context fraction is a descriptive attribute, not certified reharmonization.
Always report how many points have usable context on both sides.

The study supplies explicit reviewed pitched-instrument masks to exclude nominal
drum-note codes. The mask, instrument names and excluded event count are retained.
Masks affect only harmonic context and interval summaries, never motif matching.
Excluded or ambiguous carriers have unavailable context. Omitting a mask keeps
all nominal notes and does not certify them as harmonic pitches. Automatic
percussion classification, acoustic tuning, chord/phrase samples, durations and
tick pitch effects remain open work.

## Evidence and limits

- PrismRelay 01/ch 9 has 23 written pitch commands. 0 B/ch 9 repeats 23/23;
  03/0 Dmatch 17/23. A4 note descending fragment at source rows 2 C,30,32,34
  appears in 05/07 on ch 9 instrument 18 decimal, transposed+5 semitones.
- Opus 5.5 attempt 3:02/ch 1→08/ch 12 has 23/23 same-phase points an octave down,
  changing PWMLead to FMBell. This is a strong full-phrase handoff example.
- Opus 5.5 attempt 2:02/ch 8 gains another full 23 note realization in 0 C/ch 7,
  an octave lower on square double, while the original lead continues. This is
  additional realization/doubling, not exclusive voice replacement.
- Opus likely main lanes 7/8/1 are analyst hypotheses corroborated independently
  by Astra. Instrument labels support interpretation but do not enter matching.

This experiment does not search short-lag copies. The requested construct is a
phrase stated again in another played section, possibly on another voice or sound.
No fixed weighted score, production evaluator change, listener replacement, or
validated statistical independence claim is made. R-squared with enjoyment is
not the definition of structural validity; lack of correlation alone does not
establish a useful new attribute either.
