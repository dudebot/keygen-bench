#!/usr/bin/env python3
"""Analyze one XM offline using a caller-supplied reviewed benchmark source.

python scripts/diagnostics/analyze_structure.py --root . --xm tune.xm --out result.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.diagnostics.structure_extraction import analyze_xm


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="reviewed source root containing benchmark/")
    parser.add_argument("--xm", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    result = analyze_xm(args.xm, args.root)
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return result


if __name__ == "__main__":
    result = main()
    if result["extraction"]["status"] == "failed":
        raise SystemExit(1)
