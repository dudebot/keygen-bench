#!/usr/bin/env python3
"""Reproduce the small synthetic falsification battery without listener labels."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.diagnostics.fixtures import SEED, SMALL_EDIT_TOLERANCE, build_fixtures
from scripts.diagnostics.structure_diagnostics import METHOD_ID, SPEC_SHA256, describe_events
from scripts.diagnostics.structure_extraction import load_trusted_sources


def compare_upstream_events(fixture, sequence_module):
    """Compare nominal events on the same tick horizon, without PCM claims."""
    grouped = defaultdict(list)
    occupied = set()
    duplicate_positions = set()
    for event in fixture["events"]:
        position = event["tick"], event["channel"]
        if position in occupied:
            duplicate_positions.add(position)
        occupied.add(position)
        grouped[event["tick"]].append((event["channel"], event["pitch"] + 1, 1, 1))
    row_ticks = sorted(grouped)
    rows = [tuple(sorted(grouped[tick])) for tick in row_ticks]
    try:
        measurement = sequence_module._development(rows, row_ticks, fixture["total_ticks"])
        return {"status": "ok", "comparison_scope": "direct nominal events on common tick clock; no PCM",
                "duplicate_channel_tick_count": len(duplicate_positions),
                "native_equivalent_event_layout": not duplicate_positions, **measurement}
    except Exception as exc:
        return {"status": "unavailable", "error_type": type(exc).__name__,
                "duplicate_channel_tick_count": len(duplicate_positions),
                "native_equivalent_event_layout": not duplicate_positions}


def run_fixtures(upstream_root=None):
    fixtures = build_fixtures()
    results = {name: describe_events(**fixture) for name, fixture in fixtures.items()}
    checks = []

    def check(name, passed, **evidence):
        checks.append({"requirement": name, "passed": bool(passed), **evidence})

    for channels in range(8, 21):
        check(f"channel_layout_{channels}", results[f"layout_{channels}"] == results["invariance_base"])
    baseline = results["loop_16beat_8copies"]["candidates"]["C1"]
    for name in ("loop_plus_silent_tick", "loop_partial_tail", "loop_one_pitch_changed",
                 "loop_one_note_removed", "loop_one_event_intro", "loop_one_event_outro"):
        difference = results[name]["candidates"]["C1"] - baseline
        check(f"small_edit_continuity:{name}", abs(difference) <= SMALL_EDIT_TOLERANCE, delta_C1=difference)
    for beats in (17, 31, 33):
        for left, right in ((2, 3), (3, 4)):
            difference = (results[f"loop_{beats}beat_{right}copies"]["candidates"]["C1"]
                          - results[f"loop_{beats}beat_{left}copies"]["candidates"]["C1"])
            check(f"no_loop_inflation:{beats}beats:{left}_to_{right}",
                  difference <= SMALL_EDIT_TOLERANCE, delta_C1=difference)
    failed = sum(not row["passed"] for row in checks)
    directory = Path(__file__).resolve().parent
    source_hashes = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                     for name in ("structure_diagnostics.py", "fixtures.py", "run_fixtures.py")}
    payload = {"method_id": METHOD_ID, "spec_sha256": SPEC_SHA256,
            "fixture_seed": SEED, "small_edit_tolerance": SMALL_EDIT_TOLERANCE,
            "source_sha256": source_hashes, "case_count": len(results),
            "candidate_status": "rejected_by_structural_requirements" if failed else "not_established",
            "failed_requirement_count": failed, "requirements": checks,
            "fixtures": fixtures, "results": results}
    if upstream_root is not None:
        try:
            _, sequence_module, provenance = load_trusted_sources(upstream_root)
            payload["upstream_comparison"] = {
                "provenance": provenance,
                "scope": "direct nominal-event comparison on identical tick horizon; no PCM or common score calibration",
                "results": {name: compare_upstream_events(fixture, sequence_module) for name, fixture in fixtures.items()}}
        except Exception as exc:
            payload["upstream_comparison"] = {"status": "unavailable", "error_type": type(exc).__name__}
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="optional JSON output; otherwise print to stdout")
    parser.add_argument("--upstream-root", type=Path, help="optional reviewed source root for current nominal-event baseline")
    args = parser.parse_args(argv)
    result = run_fixtures(args.upstream_root)
    rendered = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return result


if __name__ == "__main__":
    main()
