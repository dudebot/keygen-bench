"""Small synthetic subset of an independently frozen falsification battery.

The generator contains no candidate imports. Seed, event recipes, loop periods
and 0.01 continuity tolerance were declared before executing the candidate.
Counterexamples describe the frozen formula; they are not desired behavior for
a future replacement method. No listener labels enter these fixtures.
"""
from __future__ import annotations

import random

SEED = 8162026
SMALL_EDIT_TOLERANCE = 0.01


def event(tick, pitch, channel=0):
    return {"tick": tick, "pitch": pitch, "channel": channel}


def block(period):
    return [event(t, 48 + [0, 4, 7, 4][i % 4] + (i // 16) % 5)
            for i, t in enumerate(range(0, period, 6))]


def tile(events, period, count):
    return [dict(e, tick=e["tick"] + k * period) for k in range(count) for e in events]


def build_fixtures():
    cases = {}

    def put(name, events, total):
        cases[name] = {"events": events, "total_ticks": total}

    period = 384
    base = tile(block(period), period, 8)
    put("loop_16beat_8copies", base, period * 8)
    put("loop_plus_silent_tick", base, period * 8 + 1)
    put("loop_partial_tail", base + [event(period * 8, 48)], period * 8 + 6)
    changed = [dict(e) for e in base]
    changed[-1]["pitch"] += 1
    put("loop_one_pitch_changed", changed, period * 8)
    put("loop_one_note_removed", base[:-1], period * 8)
    put("loop_one_event_intro", [event(0, 61)] + [dict(e, tick=e["tick"] + 6) for e in base], period * 8 + 6)
    put("loop_one_event_outro", base + [event(period * 8, 61)], period * 8 + 6)
    for beats in (15, 16, 17, 31, 32, 33):
        for copies in (2, 3, 4, 8, 16):
            width = beats * 24
            put(f"loop_{beats}beat_{copies}copies", tile(block(width), width, copies), width * copies)
    rich = [event(i * 6, 48 + [0, 4, 7, 2, 5, 9, 4, 7][i % 8] + (i // 32) % 4, i % 4)
            for i in range(256)]
    put("invariance_base", rich, 1536)
    for channels in range(8, 21):
        put(f"layout_{channels}", [dict(e, channel=(e["channel"] * 3 + channels - 1) % channels) for e in rich], 1536)
    for count in (0, 1, 2, 4, 8):
        rng = random.Random(SEED)
        scaffold = tile(block(96), 96, 16)
        ornaments = [event(phrase * 96 + 1 + j * 11, 60 + rng.randrange(12), 7)
                     for phrase in range(16) for j in range(count)]
        put(f"carrier_noise_{count}", scaffold + ornaments, 1536)
    put("geometry_semitone", [event(i * 6, 48 + i % 12) for i in range(192)], 1152)
    pitches = [48 + i % 12 for i in range(192)]
    random.Random(SEED).shuffle(pitches)
    put("geometry_semitone_shuffled", [event(i * 6, pitch) for i, pitch in enumerate(pitches)], 1152)
    return cases
