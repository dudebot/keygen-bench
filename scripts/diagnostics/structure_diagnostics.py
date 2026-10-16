"""Frozen onset-symbol diagnostics; these are not musical-quality ratings.

Only integer musical ticks and nominal pitch classes enter the formulas. See
the returned limitations before interpreting the output as sounding music.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
import hashlib
import json
import math
import random
from statistics import median

METHOD_ID = "structured-variation-preregistered-v1"
IMPLEMENTATION_VERSION = "1.0.1"
SPEC_SHA256 = "fe7bbdec6cea28b0a87cc56a83c2ebdbe3090f879c9e728eb24b530ee9e6c86e"
ORDERS = (0, 1, 2, 4, 8)
SEED = 20261016
SURROGATES = 8
LIMITATIONS = [
    "Onset symbols are not a universal musical-quality or listener-enjoyment measure.",
    "Register, channel, instrument, amplitude, duration and duplicate pitch classes are discarded.",
    "Nominal note numbers ignore sample tuning/mapping and percussion pitch semantics.",
    "PCM silence, envelopes, sample endings and realized voice leading are not established.",
    "Eight surrogates are effect-size controls, not calibrated significance tests.",
    "The exact complete short-cycle guard can be defeated by an intro, tail or one changed event.",
    "Hard complete windows depend on alignment and exclude incomplete edge windows.",
    "Global tempo changes are ignored; local onset or clock changes are not invariant.",
]


def canonicalize_events(events, total_ticks):
    """Return sorted first-onset-relative (tick, mask) pairs and exclusive end.

    Reject invalid data rather than silently dropping an onset at the exclusive
    end. Pitch is any integer (including negative transpositions), channel is
    ignored. Events must already be eligible nominal onsets.
    """
    if isinstance(total_ticks, bool) or not isinstance(total_ticks, int) or total_ticks < 0:
        raise ValueError("total_ticks must be a nonnegative integer")
    masks = defaultdict(int)
    for event in events:
        tick, pitch = event["tick"], event["pitch"]
        if (isinstance(tick, bool) or not isinstance(tick, int) or tick < 0
                or tick >= total_ticks):
            raise ValueError("onset tick must be an integer in [0,total_ticks)")
        if isinstance(pitch, bool) or not isinstance(pitch, int):
            raise ValueError("pitch must be an integer")
        masks[tick] |= 1 << (pitch % 12)
    if not masks:
        return [], total_ticks
    origin = min(masks)
    return [(tick - origin, masks[tick]) for tick in sorted(masks)], total_ticks - origin


def prequential_losses(tokens, alphabet_size):
    """Score each symbol before updates, using the same observed prefix for
    every order. Posterior model weights are maintained in natural-log space.
    """
    marginal = Counter()
    contexts = {k: {} for k in ORDERS if k}
    log_weights = [-math.log(len(ORDERS))] * len(ORDERS)
    loss0 = loss_mix = 0.0
    for t, symbol in enumerate(tokens):
        p0 = (marginal[symbol] + 1.0 / alphabet_size) / (t + 1)
        probabilities = [p0]
        current_contexts = {}
        for order in ORDERS[1:]:
            if t < order:
                probabilities.append(p0)
                continue
            context = tuple(tokens[t - order:t])
            current_contexts[order] = context
            counts, total = contexts[order].get(context, ({}, 0))
            probabilities.append((counts.get(symbol, 0) + p0) / (total + 1))
        terms = [weight + math.log(p) for weight, p in zip(log_weights, probabilities)]
        largest = max(terms)
        log_mixture = largest + math.log(sum(math.exp(term - largest) for term in terms))
        loss0 -= math.log2(p0)
        loss_mix -= log_mixture / math.log(2)
        log_weights = [term - log_mixture for term in terms]
        marginal[symbol] += 1
        for order, context in current_contexts.items():
            if context not in contexts[order]:
                contexts[order][context] = ({}, 0)
            counts, total = contexts[order][context]
            counts[symbol] = counts.get(symbol, 0) + 1
            contexts[order][context] = counts, total + 1
    return {"L0": loss0, "Lmixture": loss_mix, "raw_gain": loss0 - loss_mix}


def surrogate_streams(ticks, masks, gaps):
    """Generate one shared deterministic pitch bank and one IOI bank.

    Group order and index order depend only on canonical time. No pitch value,
    raw-file byte, channel number or source metadata seeds the permutations.
    """
    groups = defaultdict(list)
    for index, tick in enumerate(ticks):
        groups[tick % 24].append(index)
    pitch_rng, gap_rng = random.Random(SEED), random.Random(SEED)
    pitch_bank, gap_bank = [], []
    for _ in range(SURROGATES):
        shuffled = list(masks)
        for phase in sorted(groups):
            indices = groups[phase]
            values = [masks[index] for index in indices]
            pitch_rng.shuffle(values)
            for index, value in zip(indices, values):
                shuffled[index] = value
        pitch_bank.append(shuffled)
        gap_copy = list(gaps)
        gap_rng.shuffle(gap_copy)
        gap_bank.append(gap_copy)
    return pitch_bank, gap_bank, groups


def _predictive_view(tokens, alphabet_size, bank):
    actual = prequential_losses(tokens, alphabet_size)
    nulls = [prequential_losses(shuffled, alphabet_size) for shuffled in bank]
    center = median(row["raw_gain"] for row in nulls)
    gain = max(0.0, min(1.0, (actual["raw_gain"] - center) / max(actual["L0"], 1)))
    return {**actual, "surrogate_raw_gains": [row["raw_gain"] for row in nulls],
            "surrogate_losses": nulls, "surrogate_median_raw_gain": center,
            "gain": gain, "null_unique_stream_count": len({tuple(row) for row in bank}),
            "null_changes_observed": any(list(row) != list(tokens) for row in bank)}


@lru_cache(maxsize=65536)
def circular_wasserstein(left_mask, right_mask):
    """Exact uniform pitch-set transport on a twelve-semitone circle."""
    if not (0 < left_mask < 4096 and 0 < right_mask < 4096):
        raise ValueError("pitch-set masks must be nonempty twelve-bit masks")
    left_count, right_count = left_mask.bit_count(), right_mask.bit_count()
    running, differences = 0.0, []
    for pitch in range(12):
        running += ((1.0 / left_count if left_mask & (1 << pitch) else 0.0)
                    - (1.0 / right_count if right_mask & (1 << pitch) else 0.0))
        differences.append(running)
    center = median(differences)
    return sum(abs(value - center) for value in differences) / 6


def _transport_mean(masks):
    if len(masks) < 2:
        return None
    return sum(circular_wasserstein(a, b) for a, b in zip(masks, masks[1:])) / (len(masks) - 1)


def variation_metrics(canonical, total_ticks):
    settings = []
    for width in (96, 192):
        for offset in (0, width // 2):
            count = max(0, (total_ticks - offset) // width)
            windows = defaultdict(list)
            for tick, mask in canonical:
                index = (tick - offset) // width
                if 0 <= index < count:
                    windows[index].append(((tick - offset) % width, mask))
            nonempty = len(windows)
            unique = len({tuple(window) for window in windows.values()})
            value = (unique - 1) / (nonempty - 1) if nonempty >= 2 else None
            covered_ticks = count * width
            settings.append({"width_ticks": width, "offset_ticks": offset,
                             "complete_windows": count, "nonempty_windows": nonempty,
                             "unique_nonempty_fingerprints": unique,
                             "empty_window_fraction": (count - nonempty) / count if count else None,
                             "excluded_edge_ticks": total_ticks - covered_ticks,
                             "V": value})
    values = [row["V"] for row in settings if row["V"] is not None]
    return {"V": sum(values) / len(values) if values else None,
            "eligible_setting_count": len(values), "settings": settings}


def cycle_metrics(canonical, total_ticks):
    """Compare sparse period occupancy without allocating a tick-sized array."""
    period = None
    if canonical:
        for candidate in range(1, 385):
            if total_ticks % candidate or total_ticks // candidate < 3:
                continue
            repetitions = total_ticks // candidate
            phase_masks, phase_counts = {}, Counter()
            valid = True
            for tick, mask in canonical:
                phase = tick % candidate
                if phase in phase_masks and phase_masks[phase] != mask:
                    valid = False
                    break
                phase_masks[phase] = mask
                phase_counts[phase] += 1
            if valid and all(count == repetitions for count in phase_counts.values()):
                period = candidate
                break
    return {"G": 0 if period is not None else 1, "period_ticks": period,
            "complete_repetitions": total_ticks // period if period else None,
            "maximum_period_ticks": 384}


def describe_events(events, total_ticks, source_metadata=None):
    """Describe eligible nominal onsets under the internal prospective freeze.

    Metadata is evidence about extraction, never an input to a metric or RNG.
    Incomplete source extraction suppresses candidates but retains descriptors.
    A false strict_timing_eligible flag limits the interpretation of otherwise
    sufficient nominal-onset inputs; it never certifies native playback timing.
    """
    canonical, end = canonicalize_events(events, total_ticks)
    ticks = [tick for tick, _ in canonical]
    masks = [mask for _, mask in canonical]
    raw_gaps = [b - a for a, b in zip(ticks, ticks[1:])]
    gaps = [min(gap, 385) for gap in raw_gaps]
    pitch_bank, gap_bank, groups = surrogate_streams(ticks, masks, gaps)
    variation = variation_metrics(canonical, end)
    metadata = source_metadata or {}
    extraction_complete = metadata.get("extraction_complete") is not False
    predictive_eligible = len(masks) >= 32
    scalar_eligible = predictive_eligible and variation["V"] is not None and extraction_complete
    pitch = _predictive_view(masks, 4096, pitch_bank) if masks else None
    ioi = _predictive_view(gaps, 386, gap_bank) if gaps else None
    p = (pitch["gain"] + ioi["gain"]) / 2 if predictive_eligible else None
    predictive = {"P": p, "pitch": pitch, "ioi": ioi,
                  "ioi_overflow_fraction": sum(gap > 385 for gap in raw_gaps) / len(raw_gaps) if raw_gaps else None,
                  "phase_group_count": len(groups),
                  "pitch_null_permutable": any(len({masks[i] for i in indices}) > 1 for indices in groups.values()),
                  "ioi_null_permutable": len(set(gaps)) > 1,
                  "surrogates": SURROGATES, "seed": SEED}
    actual = _transport_mean(masks)
    null_distances = [_transport_mean(shuffled) for shuffled in pitch_bank]
    null_median = median(null_distances) if actual is not None else None
    geometry = {"actual_mean_W": actual, "null_mean_W_values": null_distances,
                "null_median_mean_W": null_median,
                "H": (null_median - actual) / max(null_median, 1 / 12) if actual is not None else None,
                "polyphonic_onset_fraction": sum(mask.bit_count() > 1 for mask in masks) / len(masks) if masks else None,
                "unique_pitch_set_count": len(set(masks)),
                "interpretation": "melodic step economy" if masks and all(mask.bit_count() == 1 for mask in masks) else "onset pitch-set transport organization"}
    cycle = cycle_metrics(canonical, end)
    eligibility = {"has_onsets": bool(masks), "distinct_onset_count": len(masks),
                   "predictive": predictive_eligible, "variation": variation["V"] is not None,
                   "geometry": len(masks) >= 2, "candidates": scalar_eligible,
                   "extraction_complete": metadata.get("extraction_complete"),
                   "strict_timing": metadata.get("strict_timing_eligible"),
                   "candidate_scope": "nominal_onset_symbols",
                   "reasons": (["no_onsets"] if not masks else [])
                   + (["fewer_than_32_distinct_onsets"] if not predictive_eligible else [])
                   + (["fewer_than_two_nonempty_complete_windows"] if variation["V"] is None else [])
                   + (["incomplete_extraction"] if not extraction_complete else [])}
    feature_bytes = json.dumps({"method_id": METHOD_ID, "events": canonical, "total_ticks": end},
                              sort_keys=True, separators=(",", ":")).encode()
    result = {"method_id": METHOD_ID, "implementation_version": IMPLEMENTATION_VERSION,
              "spec_sha256": SPEC_SHA256, "eligibility": eligibility,
              "limitations": list(LIMITATIONS),
              "invariants": ["channel_permutation", "empty_channel_padding", "simultaneous_duplicate_pitch_classes",
                             "equivalent_track_split_merge", "global_tempo_metadata", "global_pitch_transposition_up_to_float_tolerance"],
              "feature_hash": hashlib.sha256(feature_bytes).hexdigest(),
              "canonical": {"total_ticks": end, "onset_count": len(masks)},
              "predictive": predictive, "variation": variation, "cycle": cycle, "geometry": geometry,
              "candidates": {"C1": p * variation["V"] * cycle["G"] if scalar_eligible else None,
                             "C2": p * math.sqrt(variation["V"]) * cycle["G"] if scalar_eligible else None,
                             "primary": "C1", "family_size": 2}}
    # Check the contract at the API boundary. Nonfinite metadata is never copied.
    json.dumps(result, allow_nan=False)
    return result
