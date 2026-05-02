#!/usr/bin/env python3
"""Stacked-area plot of after-reduction power over time, broken out by
cabinet, with the original cluster total overlaid as a dashed comparison
line.

Same semantics as plot_stacked_power.py except each cabinet's per-time
contribution counts only hosts that are NOT in selected_nodes.csv. The
dashed black line shows what the original cluster total looked like at
each timestamp so the gap (= removed power) is visible.

Inputs:
  output/timeseries/cabinet_NN/<host>.csv  (time, power_watts)
  output/selected_nodes.csv                (cabinet, host, ...)

Output:
  output/stacked_power_with_reduction.png
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


def _load_cabinet_split(ts_dir: str, removed: set[str]
                        ) -> tuple[dict[str, dict[str, float]],
                                   dict[str, dict[str, float]]]:
    """Return ({cabinet: {time_str: full_total}}, {cabinet: {time_str: kept_total}})."""
    full: dict[str, dict[str, float]] = {}
    kept: dict[str, dict[str, float]] = {}
    for cab_dir in sorted(glob.glob(os.path.join(ts_dir, "cabinet_*"))):
        cab = os.path.basename(cab_dir)
        full_t: dict[str, float] = defaultdict(float)
        kept_t: dict[str, float] = defaultdict(float)
        for host_csv in glob.glob(os.path.join(cab_dir, "*.csv")):
            host = os.path.splitext(os.path.basename(host_csv))[0]
            is_removed = host in removed
            with open(host_csv) as f:
                for row in csv.DictReader(f):
                    w = float(row["power_watts"])
                    full_t[row["time"]] += w
                    if not is_removed:
                        kept_t[row["time"]] += w
        if full_t:
            full[cab] = dict(full_t)
            kept[cab] = dict(kept_t)
    return full, kept


def _parse_time(s: str) -> datetime:
    s = s.replace("T", " ")
    if "+" in s or s.endswith("Z"):
        s = s.rstrip("Z").split("+", 1)[0].split(".", 1)[0]
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def render(output_dir: str, row: str, pod: str) -> str:
    ts_dir = os.path.join(output_dir, "timeseries")
    sel_csv = os.path.join(output_dir, "selected_nodes.csv")
    out_png = os.path.join(output_dir, "stacked_power_with_reduction.png")

    if not os.path.isdir(ts_dir):
        sys.stderr.write(
            f"Error: {ts_dir} not found. Run export_timeseries.py first.\n"
        )
        sys.exit(2)

    removed = _load_removed(sel_csv)
    full, kept = _load_cabinet_split(ts_dir, removed)
    if not kept:
        sys.stderr.write("No cabinet timeseries data found.\n")
        sys.exit(1)

    all_times = sorted({t for cp in full.values() for t in cp})
    time_dt = np.array([_parse_time(t) for t in all_times])

    cabinets = sorted(full.keys())
    arrays_kept = []
    for cab in cabinets:
        cp = kept[cab]
        arrays_kept.append(
            np.array([cp.get(t, 0.0) for t in all_times]) / 1000.0
        )
    stacked_kept = np.vstack(arrays_kept)

    full_total = np.array([
        sum(full[c].get(t, 0.0) for c in cabinets) / 1000.0
        for t in all_times
    ])
    kept_total = stacked_kept.sum(axis=0)

    labels = [c.replace("cabinet_", "Cab ") for c in cabinets]

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.stackplot(time_dt, stacked_kept, labels=labels, linewidth=0.3)
    ax.plot(time_dt, full_total, color="black", linestyle="--",
            linewidth=1.0, label="Original total (before reduction)")

    ax.set_xlabel("Time")
    ax.set_ylabel("Total power (kW)")
    ax.set_title(
        f"Row {row} Pod {pod}: instantaneous total power AFTER reduction, "
        f"stacked by cabinet ({len(removed)} hosts removed)"
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

    peak_full = float(full_total.max())
    peak_kept = float(kept_total.max())
    pct_peak = (1 - peak_kept / peak_full) * 100 if peak_full > 0 else 0.0
    print(f"  wrote {out_png}")
    print(f"  {len(cabinets)} cabinets, {len(all_times)} time buckets, "
          f"{len(removed)} hosts removed; "
          f"peak total {peak_full:.1f} kW -> {peak_kept:.1f} kW "
          f"(-{pct_peak:.1f}%)")
    return out_png


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    args = args_from_namespace(parser.parse_args())
    print(f"Plotting stacked-power-with-reduction for row={args.row} pod={args.pod}...")
    render(args.output_dir, args.row, args.pod)


if __name__ == "__main__":
    main()
