"""Offline adapter for a caller-supplied, reviewed benchmark source tree.

Only parse_xm and its literal constants are AST-extracted from score.py; this
avoids importing rendering/scoring dependencies or platform-only fcntl. No
archived generator code or XM-embedded program is executed.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
from pathlib import Path
import struct

from .structure_diagnostics import describe_events


def load_trusted_sources(root):
    root = Path(root)
    directory = root / "benchmark" if (root / "benchmark").is_dir() else root
    score_path, sequence_path = directory / "score.py", directory / "score_structure.py"
    source = score_path.read_bytes()
    tree = ast.parse(source)
    constants = {"XM_INSTRUMENT_HEADER", "XM_SAMPLE_HEADER"}
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "parse_xm":
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in constants for target in node.targets):
            ast.literal_eval(node.value)  # enforce literal-only constant definitions
            nodes.append(node)
    if not any(isinstance(node, ast.FunctionDef) for node in nodes):
        raise ValueError("trusted source does not define parse_xm")
    namespace = {"struct": struct, "hashlib": hashlib}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<trusted-xm-parser>", "exec"), namespace)
    module_spec = importlib.util.spec_from_file_location("_trusted_structure_source", sequence_path)
    sequence_module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(sequence_module)
    provenance = {"parser_source_sha256": hashlib.sha256(source).hexdigest(),
                  "sequence_source_sha256": hashlib.sha256(sequence_path.read_bytes()).hexdigest(),
                  "parser_loading": "AST parse_xm plus literal constants; no score.py module import"}
    return namespace["parse_xm"], sequence_module, provenance


def extract_xm_events(xm, sequence_module):
    sequence = sequence_module._sequence(xm)
    if len(sequence) < 9:
        raise ValueError("trusted sequence source must return row_ticks and total ticks")
    rows, _, _, reached, seconds, reason, warnings, row_ticks, ticks = sequence
    if len(rows) != len(row_ticks):
        raise ValueError("sequence rows and row tick clock have different lengths")
    # XM note 1 is C-0; convert once at the boundary, not in the metric.
    events = [{"tick": tick, "pitch": note - 1, "channel": channel}
              for tick, row in zip(row_ticks, rows) for channel, note, _, _ in row]
    used_patterns = {xm["order"][index] for index in reached if index < len(xm["order"])}
    cells = [cell for index in sorted(used_patterns) for cell in xm["patterns"][index]["cells"]]
    flags = {
        "note_delay_EDx": any(c[5] == 14 and c[6] >> 4 == 13 and c[6] & 15 for c in cells),
        "note_cut_ECx": any(c[5] == 14 and c[6] >> 4 == 12 for c in cells),
        "retrigger": any((c[5] == 14 and c[6] >> 4 == 9) or c[5] == 0x1B for c in cells),
        "portamento": any(c[5] in (3, 5) or c[4] >> 4 == 15 for c in cells),
        "pitch_slide_or_modulation": any(c[5] in (1, 2, 4, 6) or (c[5] == 14 and c[6] >> 4 in (1, 2, 5))
                                         or c[4] >> 4 in (10, 11, 12, 13, 14) for c in cells),
        "arpeggio": any(c[5] == 0 and c[6] != 0 for c in cells),
        "sample_offset": any(c[5] == 9 for c in cells),
        "volume_slide": any(c[5] in (5, 6, 10, 17) or c[4] >> 4 in (6, 7, 8, 9) for c in cells),
        "instrument_only_events": any(c[2] == 0 and c[3] != 0 for c in cells),
    }
    complete = reason in ("order_table_end", "repeated_control_state")
    metadata = {"extraction_complete": complete,
                "strict_timing_eligible": complete and not (flags["note_delay_EDx"] or flags["retrigger"] or flags["volume_slide"]),
                "sounding_pitch_eligible": False, "PCM_audibility_established": False,
                "nominal_onsets_only": True, "effects_present": flags,
                "sequence_stop_reason": reason, "sequence_warnings": warnings,
                "sequence_seconds": seconds, "sequence_rows": len(rows),
                "sample_tuning_and_mapping_modeled": False,
                "note_number_convention": "XM note 1 converted to pitch 0 (C-0)",
                "limitations": ["EDx delays and retriggers are not emitted at exact within-row tick positions.",
                                "Cuts affect row eligibility/audibility, not sounding note durations.",
                                "Portamento targets and tick pitch effects are nominal symbols, not realized sounding pitches.",
                                "Sample relative notes, finetuning, silent PCM, envelopes and sample endings are not modeled.",
                                "Effect flags conservatively cover all cells in reached patterns, including unvisited rows.",
                                "Conflicting global commands depend on channel order and are outside layout-equivalence claims."]}
    try:
        baseline = {"status": "ok", **sequence_module._development(rows, row_ticks, ticks)}
    except Exception as exc:
        baseline = {"status": "unavailable", "error_type": type(exc).__name__}
    metadata["current_upstream_baseline"] = baseline
    return events, ticks, metadata


def analyze_xm(path, root, loaded=None):
    """Return a retained row for both successful and failed extraction."""
    provenance = {}
    try:
        parser, sequence_module, provenance = loaded or load_trusted_sources(root)
        data = Path(path).read_bytes()
        xm = parser(data)
        events, ticks, metadata = extract_xm_events(xm, sequence_module)
        result = describe_events(events, ticks, metadata)
        result["extraction"] = {"status": "ok", **provenance, **metadata,
                                "xm_sha256": hashlib.sha256(data).hexdigest()}
        return result
    except Exception as exc:
        result = describe_events([], 0)
        result["eligibility"].update({"extraction_complete": False, "strict_timing": False})
        result["eligibility"]["reasons"].append("extraction_failed")
        # Exception messages can contain caller paths; retain category only.
        result["extraction"] = {"status": "failed", "error_type": type(exc).__name__, **provenance}
        return result
