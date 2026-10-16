"""Retain independent falsifications as explicit regression evidence.

These assertions verify known outputs of version 1. They do not turn failed
continuity or loop-inflation requirements into accepted musical properties.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.diagnostics.fixtures import SMALL_EDIT_TOLERANCE, build_fixtures
from scripts.diagnostics.structure_diagnostics import describe_events
from scripts.diagnostics.run_fixtures import compare_upstream_events
from benchmark import score_structure


class FrozenCounterexampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = build_fixtures()
        cls.results = {name: describe_events(**fixture) for name, fixture in cls.cases.items()}

    def test_all_8_through_20_channel_layouts(self):
        base = self.results["invariance_base"]
        for channels in range(8, 21):
            self.assertEqual(self.results[f"layout_{channels}"], base)

    def test_exact_short_cycle_rejection(self):
        for beats in (15, 16):
            for copies in (3, 4, 8, 16):
                result = self.results[f"loop_{beats}beat_{copies}copies"]
                self.assertEqual(result["cycle"]["G"], 0)
                self.assertEqual(result["candidates"]["C1"], 0)
                self.assertEqual(result["candidates"]["C2"], 0)

    def test_documented_small_edit_continuity_failures_are_reproduced(self):
        base = self.results["loop_16beat_8copies"]
        for name in ("loop_plus_silent_tick", "loop_partial_tail", "loop_one_pitch_changed",
                     "loop_one_note_removed", "loop_one_event_intro", "loop_one_event_outro"):
            result = self.results[name]
            with self.subTest(name=name):
                self.assertEqual(result["cycle"]["G"], 1)
                self.assertGreater(result["candidates"]["C1"] - base["candidates"]["C1"], SMALL_EDIT_TOLERANCE)

    def test_documented_long_loop_inflation_is_reproduced(self):
        for beats in (17, 31, 33):
            first = self.results[f"loop_{beats}beat_2copies"]["candidates"]["C1"]
            third = self.results[f"loop_{beats}beat_3copies"]["candidates"]["C1"]
            fourth = self.results[f"loop_{beats}beat_4copies"]["candidates"]["C1"]
            self.assertGreater(third - first, SMALL_EDIT_TOLERANCE)
            self.assertGreater(fourth - third, SMALL_EDIT_TOLERANCE)

    def test_ornament_audibility_is_not_observed(self):
        fixture = self.cases["carrier_noise_4"]
        reference = self.results["carrier_noise_4"]
        for amplitude in (0.0, 1e-6, 1.0):
            altered = [dict(e, amplitude=amplitude if e["channel"] == 7 else 1) for e in fixture["events"]]
            self.assertEqual(describe_events(altered, fixture["total_ticks"]), reference)

    def test_documented_carrier_noise_inflation_is_reproduced(self):
        plain = self.results["carrier_noise_0"]["candidates"]["C1"]
        noise = self.results["carrier_noise_8"]["candidates"]["C1"]
        self.assertGreater(noise, plain)
        self.assertAlmostEqual(noise, 0.396845, places=6)
        baseline = compare_upstream_events(self.cases["carrier_noise_8"], score_structure)
        self.assertAlmostEqual(baseline["arrangement_score"], 0.012355, places=6)
        self.assertTrue(baseline["native_equivalent_event_layout"])

    def test_baseline_flags_simultaneous_same_channel_notes(self):
        fixture = {"events": [{"tick": 0, "pitch": 0, "channel": 0},
                              {"tick": 0, "pitch": 4, "channel": 0}], "total_ticks": 192}
        result = compare_upstream_events(fixture, score_structure)
        self.assertEqual(result["duplicate_channel_tick_count"], 1)
        self.assertFalse(result["native_equivalent_event_layout"])

    def test_geometric_direction(self):
        self.assertGreater(self.results["geometry_semitone"]["geometry"]["H"],
                           self.results["geometry_semitone_shuffled"]["geometry"]["H"])

    def test_cli_help_and_failure_json(self):
        root = Path(__file__).resolve().parents[3]
        script = root / "scripts" / "diagnostics" / "analyze_structure.py"
        help_run = subprocess.run([sys.executable, str(script), "--help"], check=True, capture_output=True, text=True)
        self.assertIn("--xm", help_run.stdout)
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "missing.json"
            failed_run = subprocess.run([sys.executable, str(script), "--root", str(root), "--xm", str(Path(directory) / "absent.xm"),
                                         "--out", str(out)], capture_output=True, text=True)
            self.assertEqual(failed_run.returncode, 1)
            result = json.loads(out.read_text())
            self.assertEqual(result["extraction"]["status"], "failed")
            self.assertIsNone(result["candidates"]["C1"])
            self.assertNotIn(str(directory), out.read_text())
            fixture_script = root / "scripts" / "diagnostics" / "run_fixtures.py"
            fixture_out = Path(directory) / "fixtures.json"
            subprocess.run([sys.executable, str(fixture_script), "--upstream-root", str(root), "--out", str(fixture_out)],
                           check=True, capture_output=True, text=True)
            compared = json.loads(fixture_out.read_text())
            self.assertEqual(compared["case_count"], 57)
            self.assertEqual(len(compared["upstream_comparison"]["results"]), 57)
            self.assertEqual(compared["upstream_comparison"]["results"]["carrier_noise_8"]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
