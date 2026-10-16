# Experimental onset structure diagnostics

This optional offline tool describes sequential predictability and ordered
pitch-set transitions in nominal XM onset data. It does not render audio or
change the evaluator, craft diagnostics, listener score or leaderboard.
Its combined scalar hypotheses failed structural adversaries; they are retained
for reproducible analysis, not proposed as replacement quality metrics.

## Reproduce the analysis

Only Python 3.11 or later and its standard library are required. From the
repository root:

```sh
python -m unittest discover -s scripts/diagnostics/tests -v
python scripts/diagnostics/analyze_structure.py --help
python scripts/diagnostics/analyze_structure.py --root . --xm tune.xm --out /tmp/onset-diagnostics.json
python scripts/diagnostics/run_fixtures.py --upstream-root . --out /tmp/onset-fixtures.json
```

Use an explicit local XM input. `--root` selects a reviewed source tree containing
`benchmark/score.py` and `benchmark/score_structure.py`, or its benchmark
directory. Parser and traverser hashes appear in the output. The tool
AST-extracts only `parse_xm` and literal header constants from the scoring file,
avoiding its platform and audio dependencies. It loads the reviewed traverser
and uses its returned row ticks and exclusive end tick. It never executes
archived composer programs. Extraction failures remain JSON rows with null
candidates, an ineligible status and an error category; they are not zero scores.
The analysis CLI writes that retained JSON before exiting with status 1 on an
extraction failure. The fixture CLI exits with status 0 when execution completes,
including when its JSON reports rejected scalar requirements.

No Docker, native renderer, listener download or provider access is needed for
these standalone commands. This change has not been tested through a full
Docker submission/render/evaluation cycle because it does not modify that path.

## Representation and API

```python
from scripts.diagnostics.structure_diagnostics import describe_events

result = describe_events(
    [{"tick": 0, "pitch": 0, "channel": 0},
     {"tick": 6, "pitch": 4, "channel": 1}],
    total_ticks=12,
)
```

Ticks are integers on the traversed tracker speed clock, with 24 ticks per
conventional beat. The end tick is exclusive. Pitch is any integer, with C
represented by zero modulo 12; the adapter converts XM note 1 to pitch 0.
Onsets at one tick collapse to a set of pitch classes. The first onset becomes
tick zero and the exclusive end shifts with it. Leading silence is removed;
trailing silence remains in the horizon.

Channel permutation, empty slots, equivalent track split/merge, simultaneous
unison/octave doubling and external BPM metadata preserve this representation.
Global transposition preserves the numeric components within floating-point
tolerance. The feature hash can change under transposition. Fractional BPM
tests use metadata: ordinary XM BPM is integer-valued. Equivalent doubled row
resolution/halved speed requires the same actual onset clock; copying row
indices alone does not establish equivalence.

The exact method contract is
[`structure_spec.json`](../scripts/diagnostics/structure_spec.json), SHA-256
`fe7bbdec6cea28b0a87cc56a83c2ebdbe3090f879c9e728eb24b530ee9e6c86e`.
Its ID is `structured-variation-preregistered-v1`. The specification was frozen
before numerical enjoyment joins. The formulas are unchanged after the
counterexamples below. The diagnostic formulas use no corpus labels or fitted
parameters.
The ID records an internal prospective specification freeze; this was not an
externally registered or preregistered study. The existing ID and exact bytes
remain fixed for reproducibility.
Implementation patch 1.0.1 corrects extraction eligibility and the analysis CLI
failure exit status; it does not change the frozen formulas or specification
bytes. The implementation version appears separately in every result.

## Two descriptive tests

`predictive` reports marginal and Bayesian-mixture prequential code lengths for
pitch-set labels and inter-onset intervals separately. Orders 0, 1, 2, 4 and 8
predict against the same observed prefix and update afterward. Intervals above
385 ticks share an overflow token; the overflow fraction is reported. Eight
fixed-seed pitch controls shuffle labels within equal tick-modulo-24 groups;
eight IOI controls preserve the empirical interval marginal. The positive
normalized gain subtracts median surrogate gain before clipping. Raw losses,
negative raw gains, all surrogate values and degenerate-null flags remain in
the output. Eight controls are effect-size references, not calibrated
significance tests.

`geometry` reports mean adjacent-onset circular Wasserstein transport between
uniform pitch-class sets, relative to those same pitch controls. The signed
descriptor `H` measures ordered pitch-set transition economy. For monophonic
inputs it describes melodic step economy. It does not measure consonance,
realized voice leading, harmonic function or cross-part interaction. Constant
chromatic aggregates have zero transport and zero advantage over their nulls,
while retaining no information about which melody moves within that aggregate.

The output includes the existing upstream multiscale voice self-similarity
baseline, computed on the original traversed clock, with its method ID.
Practical added value and human enjoyment prediction remain unestablished.
The [research study](research/structure-study/README.md) treats enjoyment as
one comparison criterion and reports the narrowly scoped prediction test, with
source/target provenance, missingness and grouped uncertainty.

## Eligibility and extraction limits

Fewer than 32 distinct onsets, or fewer than two nonempty complete windows at
all declared variation settings, gives null scalar candidates. Undefined values
serialize as JSON null. Empty-window coverage, excluded edge ticks, distinct
onset counts, cycle evidence and eligibility reasons remain inspectable.
Explicitly incomplete extraction also suppresses C1/C2 with an
`incomplete_extraction` reason while preserving raw P, V, G and H descriptors.
`eligibility.candidates` refers to sufficient, complete nominal-onset input.
When `strict_timing` is false, any remaining candidates describe those nominal
symbols and must not be treated as eligible evidence about exact native timing.

These are nominal onset symbols. Register, channel, instrument, loudness,
duration and duplicate pitch classes disappear. Sample relative notes,
finetuning, mapping semantics, percussion, silent PCM, envelopes and sample
endings are not modeled; sounding-pitch and PCM-audibility eligibility therefore
remain false. Quiet or silent decorations can change symbolic novelty.

The adapter reports EDx delay, ECx cut, retrigger, portamento, pitch slide,
arpeggio, sample offset, volume slide and instrument-only-event flags. Delays
and retriggers do not get exact within-row onset times from the current source.
Cuts affect row eligibility and audibility rather than sounding durations.
Portamento targets remain nominal notes. Conservative timing flags cover all
cells in reached patterns, including unvisited rows. Conflicting global
commands are resolved in channel order by the traverser, so moving those
commands is outside channel-layout equivalence claims.

## Appendix: rejected combined candidates

The frozen hypotheses were `C1=P*V*G` and `C2=P*sqrt(V)*G`, where `P` averages
the corrected pitch and interval gains, `V` averages distinct nonempty complete
window fractions at 96/192 ticks and zero/half-window origins, and `G` rejects
exact complete periods at most 384 ticks repeated at least three times. C1
remains the primary recorded hypothesis. Geometry does not enter either scalar.

The independently specified synthetic battery used seed 8162026 and a 0.01
scalar-change tolerance for small edits and added loop copies. The included
subset reproduces six small-edit continuity failures and six loop-inflation
failures. `run_fixtures.py` reports these as failed requirements and retains
every input and raw result. Regression tests explicitly check the known
counterexamples; they do not mark them as expected failures or redefine the
requirements as passes.

`--upstream-root` additionally computes current `_development` results from the
same nominal events and tick horizon for all 57 fixtures. It groups events by
tick into `(channel, pitch+1, 1, 1)` rows and flags simultaneous notes on the same
channel as not native-equivalent. This is a direct nominal-event comparison,
with no rendered-PCM or common score-calibration claim.

An exact 16-beat loop has C1=0. One added silent tick makes C1 about 0.0292;
changing one pitch makes it about 0.0378. At 17 beats, adding a third complete
copy raises C1 by about 0.0565 and adding a fourth raises it by about 0.0339.
The abrupt period limit, divisibility rule, intros and tails make the exact
guard fragile. A predictable carrier can also supply predictability while
unrelated ornaments supply novelty. These results reject an unqualified claim
that the scalar measures developing music or resists trivial loop inflation.

The eight-ornament carrier fixture gives C1=0.396845 versus current upstream
SSM arrangement score 0.012355. The existing per-voice baseline handles this
particular carrier/noise challenge substantially better. The scores have
different definitions and scales; these values do not establish common
calibration or an absolute musical-quality scale.

Independent numerical-reference tests cover rational sequence likelihoods,
exhaustive small transport assignments, all twelve global transpositions,
channel layouts 8 through 20, duplicate collapse, deterministic surrogate
marginals, randomized nulls, bounds and short-input behavior. Passing these
implementation checks establishes the formulas and representation contract,
not musical-quality validity.
