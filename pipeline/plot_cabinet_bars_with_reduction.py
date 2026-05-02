#!/usr/bin/env python3
"""Cabinet bar plot with two extra bars showing what the cabinet looks like
after the selected reduction nodes are removed.

Inputs:
  output/timeseries/cabinet_NN/<host>.csv  (per-host bucketed power)
  output/node_stats.csv                    (per-host raw min/avg/max)
  output/selected_nodes.csv                (from select_reduction_nodes.py)

Output:
  output/cabinet_power_bars_with_reduction.png

The first four bars match plot_cabinet_bars.py exactly (instantaneous min,
average, instantaneous max, potential max). Two additional bars are added:

  inst_max_after = max  over t of (sum_{h not in selected} power(h, t))
  avg_after      = mean over t of (sum_{h not in selected} power(h, t))

A summary-stats text box in the corner shows host counts and overall
reductions in instantaneous max and average power. The same dashed
reference lines at 16.5 / 33 / 49.5 kW are drawn.
"""

from __future__ import annotations

import argparse
import csv
import glob
import os
import sys
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(THIS_DIR))

from config import add_common_args, args_from_namespace


def _per_time_per_host(ts_dir: str
                       ) -> dict[str, dict[str, dict[str, float]]]:
    """Return {cabinet: {host: {time_str: watts}}}."""
    out: dict[str, dict[str, dict[str, float]]] = {}
    for cab_dir in sorted(glob.glob(os.path.join(ts_dir, "cabinet_*"))):
        cab = os.path.basename(cab_dir).replace("cabinet_", "")
        per_host: dict[str, dict[str, float]] = {}
        for host_csv in glob.glob(os.path.join(cab_dir, "*.csv")):
            host = os.path.splitext(os.path.basename(host_csv))[0]
            readings: dict[str, float] = {}
            with open(host_csv) as f:
                for row in csv.DictReader(f):
                    readings[row["time"]] = float(row["power_watts"])
            if readings:
                per_host[host] = readings
        if per_host:
            out[cab] = per_host
    return out


def _selected_per_cabinet(sel_csv: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    if not os.path.exists(sel_csv):
        return out
    with open(sel_csv) as f:
        for row in csv.DictReader(f):
            out[row["cabinet"]].add(row["host"])
    return out


def _potential_per_cabinet(stats_csv: str,
                           host_to_cab: dict[str, str]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    if not os.path.exists(stats_csv):
        return totals
    with open(stats_csv) as f:
        for row in csv.DictReader(f):
            cab = host_to_cab.get(row["host"])
            if cab is None:
                continue
            totals[cab] += float(row["max_power"])
    return totals


def render(output_dir: str, row: str, pod: str) -> str:
    ts_dir = os.path.join(output_dir, "timeseries")
    stats_csv = os.path.join(output_dir, "node_stats.csv")
    sel_csv = os.path.join(output_dir, "selected_nodes.csv")
    out_png = os.path.join(output_dir, "cabinet_power_bars_with_reduction.png")

    if not os.path.isdir(ts_dir):
        sys.stderr.write(
            f"Error: {ts_dir} not found. Run export_timeseries.py first.\n"
        )
        sys.exit(2)
    if not os.path.exists(sel_csv):
        sys.stderr.write(
            f"Error: {sel_csv} not found. Run select_reduction_nodes.py first.\n"
        )
        sys.exit(2)

    per_host = _per_time_per_host(ts_dir)
    selected = _selected_per_cabinet(sel_csv)
    host_to_cab = {h: c for c, hosts in per_host.items() for h in hosts}
    potentials = _potential_per_cabinet(stats_csv, host_to_cab)

    cabinets = sorted(c for c, hosts in per_host.items() if hosts)
    if not cabinets:
        sys.stderr.write("No cabinet data to plot.\n")
        sys.exit(1)

    inst_min, avg, inst_max, pot_max = [], [], [], []
    inst_max_after, avg_after = [], []
    counts, removed_counts = [], []
    for c in cabinets:
        hosts = per_host[c]
        totals_full: dict[str, float] = defaultdict(float)
        totals_after: dict[str, float] = defaultdict(float)
        sel = selected.get(c, set())
        for h, readings in hosts.items():
            for t, w in readings.items():
                totals_full[t] += w
                if h not in sel:
                    totals_after[t] += w
        full_vals = list(totals_full.values())
        # After-reduction series uses the same set of timestamps as the full
        # series so the average is comparable: a bucket where no remaining
        # host reported still counts as 0 W cabinet total.
        after_vals = [totals_after.get(t, 0.0) for t in totals_full.keys()] or [0.0]
        inst_min.append(min(full_vals) / 1000.0)
        avg.append(sum(full_vals) / len(full_vals) / 1000.0)
        inst_max.append(max(full_vals) / 1000.0)
        pot_max.append(potentials.get(c, 0.0) / 1000.0)
        inst_max_after.append(max(after_vals) / 1000.0)
        avg_after.append(sum(after_vals) / len(after_vals) / 1000.0)
        counts.append(len(hosts))
        removed_counts.append(len(sel))

    inst_min = np.array(inst_min)
    avg = np.array(avg)
    inst_max = np.array(inst_max)
    pot_max = np.array(pot_max)
    inst_max_after = np.array(inst_max_after)
    avg_after = np.array(avg_after)

    x = np.arange(len(cabinets))
    width = 0.13

    fig, ax = plt.subplots(figsize=(max(13, 0.95 * len(cabinets) + 4), 6.5))
    ax.bar(x - 2.5 * width, inst_min,       width, label="Instantaneous min")
    ax.bar(x - 1.5 * width, avg,            width, label="Average")
    ax.bar(x - 0.5 * width, inst_max,       width, label="Instantaneous max")
    ax.bar(x + 0.5 * width, pot_max,        width, label="Potential max (sum of per-node peaks)")
    ax.bar(x + 1.5 * width, avg_after,      width,
           label="Average after reduction", hatch="..")
    ax.bar(x + 2.5 * width, inst_max_after, width,
           label="Instantaneous max after reduction", hatch="//")

    for i, level in enumerate((16.5, 33.0, 49.5)):
        ax.axhline(
            level,
            color="black",
            linestyle="--",
            linewidth=0.8,
            label="Reference levels (16.5 / 33 / 49.5 kW)" if i == 0 else None,
        )

    n_total_hosts = sum(counts)
    n_selected_total = sum(removed_counts)
    sum_inst_max_before = float(inst_max.sum())
    sum_inst_max_after = float(inst_max_after.sum())
    sum_avg_before = float(avg.sum())
    sum_avg_after = float(avg_after.sum())
    pct_max = (1 - sum_inst_max_after / sum_inst_max_before) * 100 if sum_inst_max_before else 0.0
    pct_avg = (1 - sum_avg_after / sum_avg_before) * 100 if sum_avg_before else 0.0
    pct_hosts = (n_selected_total / n_total_hosts) * 100 if n_total_hosts else 0.0

    labels = [f"{c}\n({n}, -{r})" for c, n, r in zip(cabinets, counts, removed_counts)]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_xlabel("Cabinet (host count, removed count)")
    ax.set_ylabel("Power (kW)")
    ax.set_title(
        f"Row {row} Pod {pod} cabinet power "
        f"(reduction selection: {n_selected_total} hosts removed)"
    )
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.3, axis="y")

    stats_text = (
        f"Reduction summary (sum across {len(cabinets)} cabinets)\n"
        f"  Hosts removed: {n_selected_total} / {n_total_hosts}  ({pct_hosts:.1f}%)\n"
        f"  Inst max:  {sum_inst_max_before:6.1f} kW \u2192 "
        f"{sum_inst_max_after:6.1f} kW   (-{pct_max:.1f}%)\n"
        f"  Average:   {sum_avg_before:6.1f} kW \u2192 "
        f"{sum_avg_after:6.1f} kW   (-{pct_avg:.1f}%)"
    )
    ax.text(
        0.005, 0.985, stats_text,
        transform=ax.transAxes,
        fontsize=8.5,
        family="monospace",
        verticalalignment="top",
        horizontalalignment="left",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.85,
                  edgecolor="gray", linewidth=0.6),
    )

    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)

    print(f"  wrote {out_png}")
    print(f"  {len(cabinets)} cabinets, "
          f"sum inst_max={sum_inst_max_before:.1f} kW -> "
          f"{sum_inst_max_after:.1f} kW (-{pct_max:.1f}%); "
          f"sum avg={sum_avg_before:.1f} kW -> "
          f"{sum_avg_after:.1f} kW (-{pct_avg:.1f}%); "
          f"hosts removed={n_selected_total}/{n_total_hosts} ({pct_hosts:.1f}%)")
    return out_png


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    args = args_from_namespace(parser.parse_args())
    print(f"Plotting cabinet bars with reduction for row={args.row} pod={args.pod}...")
    render(args.output_dir, args.row, args.pod)


if __name__ == "__main__":
    main()
