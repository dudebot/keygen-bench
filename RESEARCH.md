# Research fork: structure diagnostics study

This fork investigates whether additional structure measurements can improve a
music benchmark. It supplies two reproducible note-event diagnostics, controlled
counterexamples, and comparisons with the current voice SSM and external
capability benchmarks.

The directly reusable contribution is a set of controlled stress tests and
timing/channel invariance checks. They expose specific scoring failures without
requiring agreement on an overall musical-quality score.

**[Read the study and graph gallery](docs/research/structure-study/README.md).**

![Structure study overview](docs/research/structure-study/figures/study-overview.png)

The snapshot covers 730 archived attempt records and 409 available renders.
The question is whether structure diagnostics add a useful, distinct measurement.
Audiobox enjoyment is one comparison criterion, not the standard they must
reproduce: weak enjoyment correlation alone cannot establish or reject usefulness.
The combined scalar candidates failed synthetic controls independently of that
comparison. The [external capability comparison](docs/research/structure-study/external/results.md)
reports conversational roleplay, creative writing and agentic coding separately,
plus the requested 50/50 roleplay/coding reference. Current SSM correlates .672
with roleplay and .501 with creative writing. The new pitch-transport measure's
.837 correlation with the seven-model mix falls to .036 when historical runs
are included. That result does not establish a robust additional scoring benefit.
The original benchmark and production scoring are unchanged.

[Methods and results](docs/research/structure-study/methods-and-results.md) ·
[Compact public tables](docs/research/structure-study/data/README.md) ·
[Offline CLI and tests](docs/structure-diagnostics.md) ·
[Original project and attribution](README.md)
