#!/usr/bin/env python3
"""Cumulative-power plot: sort each per-host stat (min, median, max)
independently and plot the cumulative kW as more hosts are added.

Useful for "if we had only the N least power-hungry hosts, what would the
cluster total look like" -- and the symmetric question for the worst N.

Inputs:
  output/node_stats.csv   (host, min_power, avg_power, median_power,
                           max_power, sample_count)

Output:
  output/cumulative_power.png
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(THIS_DIR))

from config import add_common_args, args_from_namespace


def _load_stats(stats_csv: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (min, median, max) numpy arrays in raw watts."""
    if not os.path.exists(stats_csv):
        sys.stderr.write(
            f"Error: {stats_csv} not found. Run export_node_stats.py first.\n"
        )
        sys.exit(2)
    mins, medians, maxes = [], [], []
    with open(stats_csv) as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "median_power" not in reader.fieldnames:
            sys.stderr.write(
                f"Error: {stats_csv} has no 'median_power' column. "
                f"Re-run export_node_stats.py with the updated SQL.\n"
            )
            sys.exit(2)
        for row in reader:
            mins.append(float(row["min_power"]))
            medians.append(float(row["median_power"]))
            maxes.append(float(row["max_power"]))
    return np.array(mins), np.array(medians), np.array(maxes)


def render(output_dir: str) -> str:
    stats_csv = os.path.join(output_dir, "node_stats.csv")
    out_png = os.path.join(output_dir, "cumulative_power.png")

    mins, medians, maxes = _load_stats(stats_csv)
    n = len(mins)
    if n == 0:
        sys.stderr.write("No host rows in node_stats.csv; nothing to plot.\n")
        sys.exit(1)

    cum_min = np.cumsum(np.sort(mins)) / 1000.0
    cum_median = np.cumsum(np.sort(medians)) / 1000.0
    cum_max = np.cumsum(np.sort(maxes)) / 1000.0
    x = np.arange(1, n + 1)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(x, cum_max, label="Cumulative Max", linewidth=1.5)
    ax.plot(x, cum_median, label="Cumulative Median", linewidth=1.5)
    ax.plot(x, cum_min, label="Cumulative Min", linewidth=1.5)
    ax.fill_between(x, cum_min, cum_max, alpha=0.12)

    ax.set_xlabel("Host count (each metric sorted independently, ascending)")
    ax.set_ylabel("Cumulative power (kW)")
    ax.set_title("Cumulative per-host power: Min / Median / Max")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim(1, n)

    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)

    print(f"  wrote {out_png}")
    print(f"  {n} hosts; cumulative totals: "
          f"min={cum_min[-1]:.1f} kW, median={cum_median[-1]:.1f} kW, "
          f"max={cum_max[-1]:.1f} kW")
    return out_png


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    args = args_from_namespace(parser.parse_args())
    print("Plotting cumulative per-host power...")
    render(args.output_dir)


if __name__ == "__main__":
    main()
