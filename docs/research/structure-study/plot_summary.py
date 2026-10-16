#!/usr/bin/env python3
"""Replot the compact public tables; requires Matplotlib, not corpus audio."""
import argparse
import json
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="PNG output; defaults to figures/study-overview.png")
    args = parser.parse_args(argv)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    root = Path(__file__).resolve().parent
    association_rows = json.loads((root / "data/associations.json").read_text())
    fixture_rows = {row["fixture_id"]: row for row in json.loads((root / "data/fixture-summary.json").read_text())}
    selected = [next(row for row in association_rows if row["cohort"] == "official_rowstart"
                     and row["analysis_horizon"] == "full_song" and row["feature"] == feature)
                for feature in ("P", "H", "current_SSM")]
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    figure, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), constrained_layout=True)
    axis = axes[0]
    for index, row in enumerate(selected):
        value = row["spearman"]
        axis.errorbar(index, value, yerr=[[value - row["pointwise_cluster_ci95_low"]],
                                          [row["pointwise_cluster_ci95_high"] - value]],
                      fmt="o", color="#235b83", capsize=5, markersize=8)
        axis.annotate(f"{value:.3f}", (index, value), xytext=(10, 0), textcoords="offset points", va="center")
    axis.axhline(0, color="#888888", linewidth=1)
    axis.set_xticks(range(3), [f"{label}\nn={row['n']}" for label, row in zip(("Predictive P", "Transport H", "Current SSM"), selected)])
    axis.set_ylabel("Spearman rho with official machine-rated enjoyment")
    axis.set_ylim(-0.22, 0.65)
    axis.set_xlim(-0.5, 2.6)
    axis.set_title("Overlap with machine-rated enjoyment\nOne criterion; pointwise 95% cluster intervals")
    axis.grid(axis="y", alpha=0.2)
    axis = axes[1]
    counts = (0, 1, 2, 4, 8)
    values = [fixture_rows[f"carrier_noise_{count}"]["rejected_C1"] for count in counts]
    axis.plot(counts, values, "o-", color="#b54242", markersize=7)
    axis.set_xticks(counts)
    axis.set_xlabel("Random pitch ornaments per recurring phrase")
    axis.set_ylabel("Rejected scalar C1")
    axis.set_ylim(-0.02, 0.45)
    axis.set_title("A decisive construct counterexample\nPredictable rhythm + unrelated pitch novelty")
    axis.grid(alpha=0.2)
    figure.suptitle("Structure diagnostics: external overlap and direct construct tests", fontsize=14)
    destination = args.out or root / "figures/study-overview.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=160, metadata={"Software": "public plot_summary.py"})
    plt.close(figure)


if __name__ == "__main__":
    main()
