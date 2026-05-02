#!/usr/bin/env python3
"""Spec task #3: bar plot with 4 bars per cabinet.

Bar definitions (taken literally from AGENT_INSTRUCTIONS.md):

  inst_min      = min over time of (sum across nodes in cabinet at time t)
  avg           = mean over time of (sum across nodes in cabinet at time t)
  inst_max      = max over time of (sum across nodes in cabinet at time t)
  potential_max = sum across nodes of (each node's individual peak)
                  -- not necessarily simultaneous

Inputs:
  output/timeseries/cabinet_NN/<host>.csv  -- bucketed power per host
  output/node_stats.csv                    -- raw per-host max for potential bar
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


def _cabinet_totals(ts_dir: str) -> dict[str, list[float]]:
    """For each cabinet, return list of cabinet-wide totals, one per time bucket.

    A time bucket only contributes a total if at least one host reported in it.
    Hosts that did not report at a given bucket are treated as 0 contribution
    to the cabinet total at that timestamp.
    """
    out: dict[str, list[float]] = {}
    for cab_dir in sorted(glob.glob(os.path.join(ts_dir, "cabinet_*"))):
        cab = os.path.basename(cab_dir).replace("cabinet_", "")
        per_time: dict[str, float] = defaultdict(float)
        for host_csv in glob.glob(os.path.join(cab_dir, "*.csv")):
            with open(host_csv) as f:
                for row in csv.DictReader(f):
                    per_time[row["time"]] += float(row["power_watts"])
        out[cab] = sorted(per_time.values()) if per_time else []
    return out


def _potential_max_per_cabinet(stats_csv: str, host_to_cab: dict[str, str]) -> dict[str, float]:
    """Sum each host's max_power into its cabinet."""
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


def _host_to_cabinet(ts_dir: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for cab_dir in glob.glob(os.path.join(ts_dir, "cabinet_*")):
        cab = os.path.basename(cab_dir).replace("cabinet_", "")
        for host_csv in glob.glob(os.path.join(cab_dir, "*.csv")):
            host = os.path.splitext(os.path.basename(host_csv))[0]
            mapping[host] = cab
    return mapping


def _host_count(ts_dir: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for cab_dir in glob.glob(os.path.join(ts_dir, "cabinet_*")):
        cab = os.path.basename(cab_dir).replace("cabinet_", "")
        counts[cab] = len(glob.glob(os.path.join(cab_dir, "*.csv")))
    return counts


def render(output_dir: str, row: str, pod: str) -> str:
    ts_dir = os.path.join(output_dir, "timeseries")
    stats_csv = os.path.join(output_dir, "node_stats.csv")
    out_png = os.path.join(output_dir, "cabinet_power_bars.png")

    if not os.path.isdir(ts_dir):
        sys.stderr.write(
            f"Error: {ts_dir} not found. Run export_timeseries.py first.\n"
        )
        sys.exit(2)

    totals = _cabinet_totals(ts_dir)
    host_to_cab = _host_to_cabinet(ts_dir)
    potentials = _potential_max_per_cabinet(stats_csv, host_to_cab)
    counts = _host_count(ts_dir)

    cabinets = sorted(c for c, vals in totals.items() if vals)
    if not cabinets:
        sys.stderr.write("No cabinet data to plot.\n")
        sys.exit(1)

    # Convert watts -> kilowatts for readability.
    inst_min = np.array([min(totals[c]) / 1000.0 for c in cabinets])
    avg      = np.array([sum(totals[c]) / len(totals[c]) / 1000.0 for c in cabinets])
    inst_max = np.array([max(totals[c]) / 1000.0 for c in cabinets])
    pot_max  = np.array([potentials.get(c, 0.0) / 1000.0 for c in cabinets])

    x = np.arange(len(cabinets))
    width = 0.2

    fig, ax = plt.subplots(figsize=(max(10, 0.7 * len(cabinets) + 4), 6))
    ax.bar(x - 1.5 * width, inst_min, width, label="Instantaneous min")
    ax.bar(x - 0.5 * width, avg,      width, label="Average")
    ax.bar(x + 0.5 * width, inst_max, width, label="Instantaneous max")
    ax.bar(x + 1.5 * width, pot_max,  width, label="Potential max (sum of per-node peaks)")

    # Reference power levels (kW). One bar per level so the first one carries
    # a single legend entry and the rest are unlabelled.
    for i, level in enumerate((16.5, 33.0, 49.5)):
        ax.axhline(
            level,
            color="black",
            linestyle="--",
            linewidth=0.8,
            label="Reference levels (16.5 / 33 / 49.5 kW)" if i == 0 else None,
        )

    labels = [f"{c}\n({counts.get(c, 0)})" for c in cabinets]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_xlabel("Cabinet (host count)")
    ax.set_ylabel("Power (kW)")
    ax.set_title(
        f"Row {row} Pod {pod} cabinet power: "
        f"instantaneous min / avg / instantaneous max / potential max"
    )
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)

    print(f"  wrote {out_png}")
    print(f"  {len(cabinets)} cabinets, "
          f"sum inst_min={inst_min.sum():.1f} kW, "
          f"sum avg={avg.sum():.1f} kW, "
          f"sum inst_max={inst_max.sum():.1f} kW, "
          f"sum pot_max={pot_max.sum():.1f} kW")
    return out_png


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    args = args_from_namespace(parser.parse_args())
    print(f"Plotting cabinet bars for row={args.row} pod={args.pod}...")
    render(args.output_dir, args.row, args.pod)


if __name__ == "__main__":
    main()
