#!/usr/bin/env python3
"""Stacked-area plot of total power over time, broken out by cabinet.

For each timestamp in the bucketed time-series, sums all hosts in each
cabinet to get the cabinet's contribution, then stacks the contributions
into a single area plot. Each cabinet shows up as a distinct band whose
thickness is its instantaneous total power.

Inputs:
  output/timeseries/cabinet_NN/<host>.csv  (time, power_watts)

Output:
  output/stacked_power.png
"""

from __future__ import annotations

import argparse
import csv
import glob
import os
import sys
from collections import defaultdict
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(THIS_DIR))

from config import add_common_args, args_from_namespace


def _load_cabinet_totals(ts_dir: str) -> dict[str, dict[str, float]]:
    """Return {cabinet: {time_str: total_watts_at_that_time}}."""
    out: dict[str, dict[str, float]] = {}
    for cab_dir in sorted(glob.glob(os.path.join(ts_dir, "cabinet_*"))):
        cab = os.path.basename(cab_dir)
        totals: dict[str, float] = defaultdict(float)
        for host_csv in glob.glob(os.path.join(cab_dir, "*.csv")):
            with open(host_csv) as f:
                for row in csv.DictReader(f):
                    totals[row["time"]] += float(row["power_watts"])
        if totals:
            out[cab] = dict(totals)
    return out


def _parse_time(s: str) -> datetime:
    """Accept either 'YYYY-MM-DD HH:MM:SS' or ISO-with-T."""
    s = s.replace("T", " ")
    if "+" in s or s.endswith("Z"):
        s = s.rstrip("Z").split("+", 1)[0].split(".", 1)[0]
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def render(output_dir: str, row: str, pod: str) -> str:
    ts_dir = os.path.join(output_dir, "timeseries")
    out_png = os.path.join(output_dir, "stacked_power.png")

    if not os.path.isdir(ts_dir):
        sys.stderr.write(
            f"Error: {ts_dir} not found. Run export_timeseries.py first.\n"
        )
        sys.exit(2)

    cabinet_totals = _load_cabinet_totals(ts_dir)
    if not cabinet_totals:
        sys.stderr.write("No cabinet timeseries data found.\n")
        sys.exit(1)

    all_times = sorted({t for cp in cabinet_totals.values() for t in cp})
    time_dt = np.array([_parse_time(t) for t in all_times])

    cabinets = sorted(cabinet_totals.keys())
    arrays = []
    for cab in cabinets:
        cp = cabinet_totals[cab]
        arrays.append(np.array([cp.get(t, 0.0) for t in all_times]) / 1000.0)
    stacked = np.vstack(arrays)

    labels = [c.replace("cabinet_", "Cab ") for c in cabinets]

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.stackplot(time_dt, stacked, labels=labels, linewidth=0.3)

    ax.set_xlabel("Time")
    ax.set_ylabel("Total power (kW)")
    ax.set_title(
        f"Row {row} Pod {pod}: instantaneous total power, stacked by cabinet"
    )
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.DayLocator())
    fig.autofmt_xdate(rotation=30)
    ax.set_xlim(time_dt[0], time_dt[-1])
    ax.set_ylim(0)
    ax.grid(True, alpha=0.3, axis="y")

    handles, leg_labels = ax.get_legend_handles_labels()
    ax.legend(
        handles[::-1], leg_labels[::-1],
        loc="upper left", bbox_to_anchor=(1.01, 1),
        fontsize=8, ncol=1, frameon=False,
    )

    fig.tight_layout()
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)

    peak_kw = float(stacked.sum(axis=0).max())
    print(f"  wrote {out_png}")
    print(f"  {len(cabinets)} cabinets, {len(all_times)} time buckets, "
          f"peak total = {peak_kw:.1f} kW")
    return out_png


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    args = args_from_namespace(parser.parse_args())
    print(f"Plotting stacked-power-over-time for row={args.row} pod={args.pod}...")
    render(args.output_dir, args.row, args.pod)


if __name__ == "__main__":
    main()
