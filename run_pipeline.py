#!/usr/bin/env python3
"""One-shot orchestrator for the r9_pod_a_pipeline.

Chains the four export steps and the plot step. Each step is also runnable
on its own from the pipeline/ directory.

When --with-reduction is set, runs two additional downstream steps after the
canonical plot: select_reduction_nodes (random per-cabinet selection that
brings each cabinet's at-peak total down by --reduction-fraction subject to
a global Slurm partition floor) and plot_cabinet_bars_with_reduction.
"""

from __future__ import annotations

import argparse
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)
sys.path.insert(0, os.path.join(THIS_DIR, "pipeline"))

from config import add_common_args, args_from_namespace

from pipeline import export_dcim_nodes
from pipeline import export_host_sensor_map
from pipeline import export_node_stats
from pipeline import export_timeseries
from pipeline import plot_cabinet_bars
from pipeline import plot_cabinet_bars_with_reduction
from pipeline import plot_cumulative_power
from pipeline import plot_cumulative_power_with_reduction
from pipeline import plot_stacked_power
from pipeline import plot_stacked_power_with_reduction
from pipeline import select_reduction_nodes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="skip all SQL exports and only re-render the plot from existing CSVs",
    )
    parser.add_argument(
        "--with-reduction",
        action="store_true",
        help="after the main pipeline, run select_reduction_nodes and the "
             "with-reduction plot",
    )
    parser.add_argument(
        "--reduction-fraction", type=float,
        default=select_reduction_nodes.DEFAULT_REDUCTION_FRACTION,
        help="target fraction of each cabinet's at-peak total to remove "
             "(default: 0.4)",
    )
    parser.add_argument(
        "--max-attempts", type=int,
        default=select_reduction_nodes.DEFAULT_MAX_ATTEMPTS,
        help="number of seeded shuffle attempts (default: 100)",
    )
    parser.add_argument(
        "--seed-base", type=int,
        default=select_reduction_nodes.DEFAULT_SEED_BASE,
        help="seed for attempt 0; attempt i uses seed_base+i",
    )
    parser.add_argument(
        "--scontrol-json",
        default=select_reduction_nodes.DEFAULT_SCONTROL_JSON,
        help="path to scontrol_show_node.json (or .json.gz; gzip "
             "auto-detected by extension)",
    )
    ns = parser.parse_args()
    args = args_from_namespace(ns)

    os.makedirs(args.output_dir, exist_ok=True)

    if not ns.skip_export:
        print("=== Step 1: dcim_nodes inventory ===")
        export_dcim_nodes.export(args.output_dir)

        print(f"\n=== Step 2a: host -> preferred sensor (row={args.row} pod={args.pod}) ===")
        export_host_sensor_map.export(
            args.row, args.pod, args.start, args.end, args.output_dir,
        )

        print(f"\n=== Step 2b: per-host time-series (bucket={args.bucket}) ===")
        export_timeseries.export(args.start, args.end, args.bucket, args.output_dir)

        print("\n=== Step 2c: per-host raw-sample stats ===")
        export_node_stats.export(args.start, args.end, args.output_dir)
    else:
        print("--skip-export set: re-using existing CSVs in", args.output_dir)

    print(f"\n=== Step 3: cabinet plots ===")
    plot_cabinet_bars.render(args.output_dir, args.row, args.pod)
    plot_cumulative_power.render(args.output_dir)
    plot_stacked_power.render(args.output_dir, args.row, args.pod)

    if ns.with_reduction:
        print(f"\n=== Step 4: reduction-node selection ===")
        select_reduction_nodes.run(
            target_fraction=ns.reduction_fraction,
            max_attempts=ns.max_attempts,
            seed_base=ns.seed_base,
            scontrol_path=ns.scontrol_json,
            output_dir=args.output_dir,
        )

        print(f"\n=== Step 5: cabinet plots with reduction ===")
        plot_cabinet_bars_with_reduction.render(
            args.output_dir, args.row, args.pod,
        )
        plot_cumulative_power_with_reduction.render(args.output_dir)
        plot_stacked_power_with_reduction.render(
            args.output_dir, args.row, args.pod,
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
