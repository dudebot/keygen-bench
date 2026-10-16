"""Synthetic XM dictionaries exercise the actual reviewed row traverser."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from benchmark import score_structure
from scripts.diagnostics.structure_diagnostics import describe_events
from scripts.diagnostics.structure_extraction import extract_xm_events


def synthetic_xm():
    return {"channels": 8, "speed": 6, "bpm": 132, "song_length": 1,
            "order": [0], "patterns": [{"rows": 128, "cells": [
                (row, row % 4, 49 + [0, 4, 7, 2][row % 4] + row // 32, 1, 0, 0, 0)
                for row in range(128)]}],
            "instruments": [{"sample_map": [0] * 96,
                             "samples": [{"frames": 128, "volume": 64, "seconds_at_c4": 0.01}]}]}


def describe_xm(xm):
    events, ticks, metadata = extract_xm_events(xm, score_structure)
    return events, ticks, describe_events(events, ticks), metadata


class NativeClockTests(unittest.TestCase):
    def test_double_rows_half_speed(self):
        base = synthetic_xm()
        changed = deepcopy(base)
        changed["speed"] = 3
        changed["patterns"][0]["rows"] *= 2
        changed["patterns"][0]["cells"] = [(row * 2, *rest) for row, *rest in changed["patterns"][0]["cells"]]
        self.assertEqual(describe_xm(base)[:3], describe_xm(changed)[:3])

    def test_channel_layouts_and_native_integer_tempo(self):
        base = synthetic_xm()
        reference = describe_xm(base)[2]
        for channels in range(8, 21):
            for bpm in (131, 132, 133):
                changed = deepcopy(base)
                changed.update(channels=channels, bpm=bpm)
                changed["patterns"][0]["cells"] = [
                    (row, (channel * 3 + channels - 1) % channels, *rest)
                    for row, channel, *rest in changed["patterns"][0]["cells"]]
                self.assertEqual(describe_xm(changed)[2], reference)

    def test_delay_portamento_cut_retrigger_flags(self):
        for effect, param, flag in ((14, 0xD1, "note_delay_EDx"), (14, 0xC1, "note_cut_ECx"),
                                    (14, 0x91, "retrigger"), (3, 1, "portamento"),
                                    (1, 1, "pitch_slide_or_modulation"), (9, 1, "sample_offset")):
            xm = synthetic_xm()
            row, channel, note, instrument, volume, _, _ = xm["patterns"][0]["cells"][1]
            xm["patterns"][0]["cells"][1] = row, channel, note, instrument, volume, effect, param
            metadata = describe_xm(xm)[3]
            self.assertTrue(metadata["effects_present"][flag])
            self.assertFalse(metadata["sounding_pitch_eligible"])
            self.assertFalse(metadata["PCM_audibility_established"])

    def test_truncated_native_traversal_is_ineligible_with_retained_descriptors(self):
        with patch.object(score_structure, "MAX_SEQUENCE_ROWS", 64):
            extracted, ticks, metadata = extract_xm_events(synthetic_xm(), score_structure)
        self.assertEqual(len(extracted), 64)
        self.assertEqual(metadata["sequence_stop_reason"], "row_limit")
        self.assertFalse(metadata["extraction_complete"])
        result = describe_events(extracted, ticks, metadata)
        self.assertFalse(result["eligibility"]["candidates"])
        self.assertIsNone(result["candidates"]["C1"])
        self.assertIsNone(result["candidates"]["C2"])
        self.assertIn("incomplete_extraction", result["eligibility"]["reasons"])
        self.assertIsNotNone(result["predictive"]["P"])
        self.assertIsNotNone(result["geometry"]["H"])


if __name__ == "__main__":
    unittest.main()
