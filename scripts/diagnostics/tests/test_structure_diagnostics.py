"""Offline reference, representation and null tests; no listener labels."""
from fractions import Fraction
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.diagnostics.structure_diagnostics import (
    METHOD_ID, SPEC_SHA256, canonicalize_events, circular_wasserstein,
    cycle_metrics, describe_events, prequential_losses, surrogate_streams,
    variation_metrics,
)
from scripts.diagnostics.structure_extraction import analyze_xm, extract_xm_events, load_trusted_sources


def events(pitches, step=6):
    return [{"tick": i * step, "pitch": pitch, "channel": i % 8} for i, pitch in enumerate(pitches)]


def fraction_reference(tokens, alphabet):
    """Direct rational model likelihoods, then average complete likelihoods.

    This avoids the implementation's log-weight posterior recursion entirely.
    """
    likelihoods = []
    for order in (0, 1, 2, 4, 8):
        likelihood = Fraction(1)
        for t, symbol in enumerate(tokens):
            prefix = tokens[:t]
            p0 = (prefix.count(symbol) + Fraction(1, alphabet)) / (t + 1)
            probability = p0
            if order and t >= order:
                context = tokens[t - order:t]
                matches = [j for j in range(order, t) if tokens[j - order:j] == context]
                probability = (sum(tokens[j] == symbol for j in matches) + p0) / (len(matches) + 1)
            likelihood *= probability
        likelihoods.append(likelihood)
    return -math.log2(likelihoods[0]), -math.log2(sum(likelihoods) / 5)


def assignment_transport(left, right):
    """Independent uniform transport via exhaustive discrete assignments."""
    size = math.lcm(len(left), len(right))
    left_expanded = left * (size // len(left))
    right_expanded = right * (size // len(right))
    return min(sum(min(abs(a - b), 12 - abs(a - b)) for a, b in zip(left_expanded, permutation))
               for permutation in set(itertools.permutations(right_expanded))) / (6 * size)


class PredictiveReferenceTests(unittest.TestCase):
    def test_exact_three_symbols(self):
        actual = prequential_losses([1, 1, 1], 2)
        self.assertAlmostEqual(actual["L0"], math.log2(16 / 5), places=13)
        self.assertAlmostEqual(actual["Lmixture"], math.log2(160 / 51), places=13)
        self.assertAlmostEqual(actual["raw_gain"], math.log2(51 / 50), places=13)

    def test_same_context_prefix_rational_reference(self):
        for tokens in ([1, 1, 2, 1, 2, 1], [0] * 12, list(range(12)), [1, 2, 1, 2] * 4):
            actual = prequential_losses(tokens, 4096)
            expected = fraction_reference(list(tokens), 4096)
            self.assertAlmostEqual(actual["L0"], expected[0], places=11)
            self.assertAlmostEqual(actual["Lmixture"], expected[1], places=11)

    def test_surrogate_phase_marginals_and_determinism(self):
        ticks = list(range(0, 600, 6))
        masks = [1 << (i % 12) for i in range(len(ticks))]
        gaps = [6, 12, 18, 24] * 24 + [6, 12, 18]
        bank, gap_bank, groups = surrogate_streams(ticks, masks, gaps)
        self.assertEqual((bank, gap_bank, groups), surrogate_streams(ticks, masks, gaps))
        for shuffled in bank:
            for indices in groups.values():
                self.assertEqual(sorted(masks[i] for i in indices), sorted(shuffled[i] for i in indices))
        for shuffled in gap_bank:
            self.assertEqual(sorted(gaps), sorted(shuffled))

    def test_random_ensemble_low_gain_and_bounds(self):
        rng = random.Random(60123)
        gains = []
        for _ in range(24):
            pitches = [rng.randrange(12) for _ in range(128)]
            result = describe_events(events(pitches), 768)
            gains.append(result["predictive"]["P"])
            for key in ("C1", "C2"):
                self.assertTrue(0 <= result["candidates"][key] <= 1)
            self.assertTrue(0 <= result["variation"]["V"] <= 1)
        self.assertLess(sum(gains) / len(gains), 0.1)


class GeometryReferenceTests(unittest.TestCase):
    def test_exact_distances(self):
        self.assertEqual(circular_wasserstein(1, 1), 0)
        self.assertAlmostEqual(circular_wasserstein(1, 2), 1 / 6)
        self.assertAlmostEqual(circular_wasserstein(1, 1 << 6), 1)
        self.assertAlmostEqual(circular_wasserstein((1 << 0) | (1 << 4) | (1 << 7),
                                                  (1 << 0) | (1 << 5) | (1 << 7)), 1 / 18)

    def test_independent_assignment_solver(self):
        fixtures = [([0], [11]), ([0, 4], [7]), ([0, 6], [2, 4, 9]),
                    ([0, 3, 7], [1, 4, 8]), ([1, 6], [2, 11])]
        for left, right in fixtures:
            actual = circular_wasserstein(sum(1 << p for p in left), sum(1 << p for p in right))
            self.assertAlmostEqual(actual, assignment_transport(left, right), places=12)

    def test_chromatic_walk_and_constant_aggregate(self):
        walk = describe_events(events(list(range(144))), 864)
        self.assertGreater(walk["geometry"]["H"], 0)
        constant = [{"tick": t, "pitch": p, "channel": p} for t in range(0, 864, 6) for p in range(12)]
        aggregate = describe_events(constant, 864)
        self.assertEqual(aggregate["geometry"]["H"], 0)
        self.assertEqual(aggregate["geometry"]["actual_mean_W"], 0)
        self.assertFalse(aggregate["predictive"]["pitch_null_permutable"])


class CanonicalAndScalarTests(unittest.TestCase):
    def setUp(self):
        self.original = events([((i * i + i // 16) % 12) for i in range(160)])
        self.base = describe_events(self.original, 960)

    def test_channel_padding_permutation_duplicates_split_merge(self):
        for channels in (8, 10, 16, 20):
            changed = [{**e, "channel": (e["channel"] * 3 + 1) % channels} for e in self.original]
            changed += [{**e, "pitch": e["pitch"] + 12, "channel": channels - 1} for e in self.original]
            self.assertEqual(describe_events(changed, 960), self.base)
        self.assertEqual(describe_events([{**e, "channel": 0} for e in self.original], 960), self.base)

    def test_tempo_metadata_and_origin(self):
        for tempo in (132, 131.999):
            self.assertEqual(describe_events(self.original, 960, {"bpm": tempo}), self.base)
        shifted = [{**e, "tick": e["tick"] + 73} for e in self.original]
        self.assertEqual(describe_events(shifted, 1033), self.base)

    def test_every_global_transposition(self):
        for shift in range(12):
            result = describe_events([{**e, "pitch": e["pitch"] + shift} for e in self.original], 960)
            for section, key in (("predictive", "P"), ("variation", "V"), ("cycle", "G"),
                                 ("geometry", "H"), ("candidates", "C1"), ("candidates", "C2")):
                self.assertAlmostEqual(result[section][key], self.base[section][key], places=12)

    def test_exact_cycle_and_near_cycle(self):
        for period in (1, 17, 96, 383, 384):
            canonical = [(i * period, 1) for i in range(4)]
            self.assertEqual(cycle_metrics(canonical, period * 4)["period_ticks"], period)
            self.assertEqual(cycle_metrics(canonical, period * 4 + 1)["G"], 1)
        repeated = events([0, 2, 4, 7] * 16)
        result = describe_events(repeated, 384)
        self.assertEqual(result["candidates"]["C1"], 0)
        self.assertEqual(result["candidates"]["C2"], 0)
        self.assertIsNone(cycle_metrics([], 1152)["period_ticks"])

    def test_variation_reference_empty_edges(self):
        canonical = [(0, 1), (96, 2), (192, 1), (288, 4)]
        result = variation_metrics(canonical, 384)
        self.assertEqual(result["settings"][0]["V"], 2 / 3)
        self.assertEqual(result["settings"][0]["empty_window_fraction"], 0)
        self.assertEqual(result["eligible_setting_count"], 3)
        self.assertEqual(result["V"], (2 / 3 + 1 + 1) / 3)

    def test_sparse_and_overflow(self):
        for size in (0, 1, 2, 31):
            result = describe_events(events(list(range(size))), max(1, size * 6))
            self.assertIsNone(result["candidates"]["C1"])
            self.assertFalse(result["eligibility"]["predictive"])
            json.dumps(result, allow_nan=False)
        overflow = describe_events(events(list(range(32)), step=386), 32 * 386)
        self.assertEqual(overflow["predictive"]["ioi_overflow_fraction"], 1)
        at_limit = describe_events(events(list(range(32)), step=385), 32 * 385)
        self.assertEqual(at_limit["predictive"]["ioi_overflow_fraction"], 0)

    def test_invalid_boundaries(self):
        for bad in ([{"tick": 6, "pitch": 1}], [{"tick": -1, "pitch": 1}], [{"tick": 0.5, "pitch": 1}]):
            with self.assertRaises(ValueError):
                canonicalize_events(bad, 6)
        with self.assertRaises(ValueError):
            canonicalize_events([], float("nan"))

    def test_frozen_identity(self):
        self.assertEqual(self.base["method_id"], METHOD_ID)
        self.assertEqual(self.base["spec_sha256"], SPEC_SHA256)
        spec_path = Path(__file__).resolve().parents[1] / "structure_spec.json"
        self.assertEqual(hashlib.sha256(spec_path.read_bytes()).hexdigest(), SPEC_SHA256)

    def test_incomplete_extraction_suppresses_candidates_but_retains_raw_descriptors(self):
        incomplete = describe_events(self.original, 960, {"extraction_complete": False})
        self.assertFalse(incomplete["eligibility"]["candidates"])
        self.assertIn("incomplete_extraction", incomplete["eligibility"]["reasons"])
        self.assertIsNone(incomplete["candidates"]["C1"])
        self.assertIsNone(incomplete["candidates"]["C2"])
        for section in ("predictive", "variation", "cycle", "geometry"):
            self.assertEqual(incomplete[section], self.base[section])
        self.assertEqual(incomplete["implementation_version"], "1.0.1")

    def test_timing_limited_outputs_are_explicitly_nominal(self):
        nominal = describe_events(self.original, 960, {"extraction_complete": True, "strict_timing_eligible": False})
        self.assertTrue(nominal["eligibility"]["candidates"])
        self.assertFalse(nominal["eligibility"]["strict_timing"])
        self.assertEqual(nominal["eligibility"]["candidate_scope"], "nominal_onset_symbols")
        self.assertEqual(nominal["candidates"], self.base["candidates"])


class AdapterTests(unittest.TestCase):
    def test_ast_parser_avoids_module_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "score.py").write_text('import nonexistent_platform_dependency\nraise RuntimeError("must not import")\nXM_INSTRUMENT_HEADER = 263\nXM_SAMPLE_HEADER = 40\ndef parse_xm(data):\n    return {"value": len(data) + XM_SAMPLE_HEADER}\n')
            (root / "score_structure.py").write_text('def _sequence(xm):\n    return None\n')
            parser, _, provenance = load_trusted_sources(root)
            self.assertEqual(parser(b"abc"), {"value": 43})
            self.assertEqual(len(provenance["parser_source_sha256"]), 64)

    def test_note_convention_effect_flags_and_failure_retention(self):
        class Sequence:
            @staticmethod
            def _sequence(xm):
                return [((0, 1, 1, 0),)], set(), set(), {0}, 1.0, "order_table_end", [], [0], 6

            @staticmethod
            def _development(*args):
                return {"arrangement_score": 0}
        xm = {"order": [0], "patterns": [{"cells": [(0, 0, 1, 1, 0, 14, 0xD1)]}]}
        extracted, ticks, metadata = extract_xm_events(xm, Sequence)
        self.assertEqual(extracted, [{"tick": 0, "pitch": 0, "channel": 0}])
        self.assertEqual(ticks, 6)
        self.assertTrue(metadata["effects_present"]["note_delay_EDx"])
        self.assertFalse(metadata["strict_timing_eligible"])
        failed = analyze_xm("missing.xm", ".", loaded=(lambda data: {}, Sequence, {}))
        self.assertEqual(failed["extraction"]["status"], "failed")
        self.assertIsNone(failed["candidates"]["C1"])
        self.assertIn("extraction_failed", failed["eligibility"]["reasons"])


if __name__ == "__main__":
    unittest.main()
