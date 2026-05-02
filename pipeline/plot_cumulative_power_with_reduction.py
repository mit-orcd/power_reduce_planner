#!/usr/bin/env python3
"""Cumulative-power plot with the selected reduction subset overlaid.

Same 3-curve shape as plot_cumulative_power.py (per-host min, median, max
sorted independently and cumulated), drawn twice on one axis:

  - solid lines for the original (all hosts)
  - dashed lines for the after-reduction subset (hosts NOT in
    selected_nodes.csv); the dashed cumulative still terminates at the
    original total minus the removed contribution

The shaded fill_between(min, max) is drawn for the after-reduction
series so the reader can see the residual envelope.

Inputs:
  output/node_stats.csv      (host, min_power, avg_power, median_power,
                              max_power, sample_count)
  output/selected_nodes.csv  (cabinet, host, ...; from select_reduction_nodes.py)

Output:
  output/cumulative_power_with_reduction.png
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


def _load_stats(stats_csv: str) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    """Return (hosts, mins, medians, maxes) parallel arrays in raw watts."""
    if not os.path.exists(stats_csv):
        sys.stderr.write(
            f"Error: {stats_csv} not found. Run export_node_stats.py first.\n"
        )
        sys.exit(2)
    hosts, mins, medians, maxes = [], [], [], []
    with open(stats_csv) as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "median_power" not in reader.fieldnames:
            sys.stderr.write(
                f"Error: {stats_csv} has no 'median_power' column.\n"
            )
            sys.exit(2)
        for row in reader:
            hosts.append(row["host"])
            mins.append(float(row["min_power"]))
            medians.append(float(row["median_power"]))
            maxes.append(float(row["max_power"]))
    return hosts, np.array(mins), np.array(medians), np.array(maxes)


def _load_removed(sel_csv: str) -> set[str]:
    if not os.path.exists(sel_csv):
        sys.stderr.write(
            f"Error: {sel_csv} not found. Run select_reduction_nodes.py first.\n"
        )
        sys.exit(2)
    removed: set[str] = set()
    with open(sel_csv) as f:
        for row in csv.DictReader(f):
            removed.add(row["host"])
    return removed


def render(output_dir: str) -> str:
    stats_csv = os.path.join(output_dir, "node_stats.csv")
    sel_csv = os.path.join(output_dir, "selected_nodes.csv")
    out_png = os.path.join(output_dir, "cumulative_power_with_reduction.png")

    hosts, mins, medians, maxes = _load_stats(stats_csv)
    removed = _load_removed(sel_csv)
    if not hosts:
        sys.stderr.write("No host rows in node_stats.csv; nothing to plot.\n")
        sys.exit(1)

    keep_mask = np.array([h not in removed for h in hosts])
    n_total = len(hosts)
    n_keep = int(keep_mask.sum())
    n_removed = n_total - n_keep

    cum_min_full = np.cumsum(np.sort(mins)) / 1000.0
    cum_med_full = np.cumsum(np.sort(medians)) / 1000.0
    cum_max_full = np.cumsum(np.sort(maxes)) / 1000.0
    x_full = np.arange(1, n_total + 1)

    cum_min_keep = np.cumsum(np.sort(mins[keep_mask])) / 1000.0
    cum_med_keep = np.cumsum(np.sort(medians[keep_mask])) / 1000.0
    cum_max_keep = np.cumsum(np.sort(maxes[keep_mask])) / 1000.0
    x_keep = np.arange(1, n_keep + 1)

    fig, ax = plt.subplots(figsize=(12, 6))
    l1, = ax.plot(x_full, cum_max_full, label="Cumulative Max (all)", linewidth=1.5)
    l2, = ax.plot(x_full, cum_med_full, label="Cumulative Median (all)", linewidth=1.5)
    l3, = ax.plot(x_full, cum_min_full, label="Cumulative Min (all)", linewidth=1.5)
    ax.plot(x_keep, cum_max_keep, label="Cumulative Max (after reduction)",
            linewidth=1.5, linestyle="--", color=l1.get_color())
    ax.plot(x_keep, cum_med_keep, label="Cumulative Median (after reduction)",
            linewidth=1.5, linestyle="--", color=l2.get_color())
    ax.plot(x_keep, cum_min_keep, label="Cumulative Min (after reduction)",
            linewidth=1.5, linestyle="--", color=l3.get_color())
    ax.fill_between(x_keep, cum_min_keep, cum_max_keep, alpha=0.10)

    ax.set_xlabel("Host count (each metric sorted independently, ascending)")
    ax.set_ylabel("Cumulative power (kW)")
    ax.set_title(
        f"Cumulative per-host power: original vs. after reduction "
        f"({n_removed} of {n_total} hosts removed)"
    )
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(1, n_total)

    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)

    pct_max = (1 - cum_max_keep[-1] / cum_max_full[-1]) * 100 if n_keep else 0.0
    pct_med = (1 - cum_med_keep[-1] / cum_med_full[-1]) * 100 if n_keep else 0.0
    pct_min = (1 - cum_min_keep[-1] / cum_min_full[-1]) * 100 if n_keep else 0.0
    print(f"  wrote {out_png}")
    print(f"  removed {n_removed}/{n_total} hosts; cumulative reductions: "
          f"min -{pct_min:.1f}%, median -{pct_med:.1f}%, max -{pct_max:.1f}%")
    return out_png


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    args = args_from_namespace(parser.parse_args())
    print("Plotting cumulative per-host power with reduction overlay...")
    render(args.output_dir)


if __name__ == "__main__":
    main()
