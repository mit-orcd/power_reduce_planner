#!/usr/bin/env python3
"""Downstream selection: pick random nodes per cabinet whose at-peak power
sums to >= target_fraction of the cabinet's instantaneous max, subject to
a global Slurm partition floor (>=2 remaining per partition; >=1 if the
partition only had 1 node to begin with).

Up to --max-attempts seeded shuffles. The first attempt with zero partition
violations is accepted; otherwise the lowest-violation attempt wins
(tiebreaker: lowest total deficit).

Inputs:
  output/timeseries/cabinet_NN/<host>.csv  (from export_timeseries.py)
  --scontrol-json  (defaults to ../telegraf_data/scontrol_show_node.json)

Outputs (all under --output-dir):
  selected_nodes.csv
  selection_summary.csv
  partition_violations.csv  (header-only when feasible)
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import random
import sys
from collections import defaultdict

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(THIS_DIR))

from config import add_common_args, args_from_namespace, REPO_DIR


DEFAULT_REDUCTION_FRACTION = 0.4
DEFAULT_MAX_ATTEMPTS = 100
DEFAULT_SEED_BASE = 0
DEFAULT_SCONTROL_JSON = os.path.normpath(
    os.path.join(REPO_DIR, "..", "telegraf_data", "scontrol_show_node.json")
)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_cabinets(ts_dir: str) -> dict[str, dict[str, dict[str, float]]]:
    """Return {cabinet: {host: {time_str: watts}}}.

    Per-host CSV columns (from export_timeseries.py): time, power_watts.
    """
    out: dict[str, dict[str, dict[str, float]]] = {}
    for cab_dir in sorted(glob.glob(os.path.join(ts_dir, "cabinet_*"))):
        cab = os.path.basename(cab_dir).replace("cabinet_", "")
        per_host: dict[str, dict[str, float]] = {}
        for path in sorted(glob.glob(os.path.join(cab_dir, "*.csv"))):
            host = os.path.splitext(os.path.basename(path))[0]
            readings: dict[str, float] = {}
            with open(path) as f:
                for row in csv.DictReader(f):
                    readings[row["time"]] = float(row["power_watts"])
            if readings:
                per_host[host] = readings
        if per_host:
            out[cab] = per_host
    return out


def cabinet_peak(host_readings: dict[str, dict[str, float]]
                 ) -> tuple[str, float, dict[str, float]]:
    """Return (peak_time, peak_total_watts, host_power_at_peak)."""
    totals: dict[str, float] = defaultdict(float)
    for readings in host_readings.values():
        for t, w in readings.items():
            totals[t] += w
    peak_time = max(totals, key=totals.get)
    peak_total = totals[peak_time]
    host_at_peak = {h: r.get(peak_time, 0.0) for h, r in host_readings.items()}
    return peak_time, peak_total, host_at_peak


def cabinet_inst_max_after(host_readings: dict[str, dict[str, float]],
                           removed_hosts: set[str]) -> float:
    """Recompute max_t (sum_{h not in removed} power(h, t))."""
    totals: dict[str, float] = defaultdict(float)
    for h, readings in host_readings.items():
        if h in removed_hosts:
            continue
        for t, w in readings.items():
            totals[t] += w
    return max(totals.values()) if totals else 0.0


def load_partitions(scontrol_path: str) -> dict[str, list[str]]:
    """Return {partition: [node_name, ...]} from scontrol_show_node.json."""
    with open(scontrol_path) as f:
        data = json.load(f)
    partitions: dict[str, list[str]] = defaultdict(list)
    for node in data.get("nodes", []):
        name = node.get("name")
        for p in node.get("partitions", []) or []:
            partitions[p].append(name)
    return dict(partitions)


# ---------------------------------------------------------------------------
# Per-attempt logic
# ---------------------------------------------------------------------------

def select_for_cabinet(rng: random.Random,
                       host_at_peak: dict[str, float],
                       peak_total: float,
                       target_fraction: float) -> list[tuple[str, float]]:
    """Shuffle hosts, accumulate until cumulative at-peak watts >= target.

    Returns list of (host, host_power_at_peak_w) in selection order.
    If even removing every host can't reach the target (e.g. peak_total
    came from a single moment of a few hosts but several hosts had near-zero
    contribution), returns whatever is needed plus everything else; the
    caller decides what to do with achieved_fraction.
    """
    target = target_fraction * peak_total
    hosts = list(host_at_peak.keys())
    rng.shuffle(hosts)
    selected: list[tuple[str, float]] = []
    running = 0.0
    for h in hosts:
        selected.append((h, host_at_peak[h]))
        running += host_at_peak[h]
        if running >= target:
            break
    return selected


def restore_zero_remaining(per_cab_selection: dict[str, list[tuple[str, float]]],
                           removed: set[str],
                           partitions: dict[str, list[str]],
                           rng: random.Random) -> list[tuple[str, str, str]]:
    """For every partition with zero remaining nodes, add one of its removed
    hosts back to "kept" so the partition has at least one node.

    Mutates ``per_cab_selection`` and ``removed`` in place. Returns a list of
    (partition, host, cabinet) records describing each restoration. A single
    restoration may resolve multiple zero-remaining partitions at once if the
    restored host belongs to several of them.
    """
    host_to_cab: dict[str, str] = {
        h: cab for cab, sel in per_cab_selection.items() for h, _ in sel
    }
    restorations: list[tuple[str, str, str]] = []

    while True:
        zero_parts = [
            p for p, members in partitions.items()
            if len(members) - sum(1 for m in members if m in removed) == 0
        ]
        if not zero_parts:
            break
        target_part = zero_parts[0]
        candidates = [m for m in partitions[target_part] if m in removed]
        if not candidates:
            break
        candidates.sort()
        host = rng.choice(candidates)
        cab = host_to_cab.get(host)
        if cab is None:
            removed.discard(host)
            continue
        per_cab_selection[cab] = [
            (h, w) for (h, w) in per_cab_selection[cab] if h != host
        ]
        removed.discard(host)
        restorations.append((target_part, host, cab))

    return restorations


def score_attempt(removed: set[str],
                  partitions: dict[str, list[str]]
                  ) -> tuple[int, int, list[tuple[str, int, int, int, int, int]]]:
    """Score one attempt's removal set against partition constraints.

    Returns (n_violations, total_deficit, [violation_records]).
    Each violation record is (partition, size, n_removed, n_remaining,
    floor, deficit).
    """
    violations: list[tuple[str, int, int, int, int, int]] = []
    total_deficit = 0
    for part, members in partitions.items():
        size = len(members)
        n_removed = sum(1 for m in members if m in removed)
        remaining = size - n_removed
        floor = 1 if size == 1 else 2
        if remaining < floor:
            deficit = floor - remaining
            violations.append((part, size, n_removed, remaining, floor, deficit))
            total_deficit += deficit
    return len(violations), total_deficit, violations


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run(target_fraction: float,
        max_attempts: int,
        seed_base: int,
        scontrol_path: str,
        output_dir: str) -> dict:
    ts_dir = os.path.join(output_dir, "timeseries")
    if not os.path.isdir(ts_dir):
        sys.stderr.write(
            f"Error: {ts_dir} not found. Run export_timeseries.py first.\n"
        )
        sys.exit(2)

    cabinets = load_cabinets(ts_dir)
    if not cabinets:
        sys.stderr.write(f"Error: no cabinet timeseries under {ts_dir}.\n")
        sys.exit(2)
    partitions = load_partitions(scontrol_path)

    cab_meta: dict[str, dict] = {}
    for cab, host_readings in cabinets.items():
        peak_time, peak_total, host_at_peak = cabinet_peak(host_readings)
        cab_meta[cab] = {
            "n_hosts": len(host_readings),
            "peak_time": peak_time,
            "peak_total": peak_total,
            "host_at_peak": host_at_peak,
        }

    print(f"  loaded {len(cabinets)} cabinets, "
          f"{sum(m['n_hosts'] for m in cab_meta.values())} hosts; "
          f"{len(partitions)} partitions")
    print(f"  target_fraction={target_fraction}, "
          f"max_attempts={max_attempts}, seed_base={seed_base}")
    print(f"  scontrol_json={scontrol_path}")

    best: dict | None = None
    for i in range(max_attempts):
        seed = seed_base + i
        rng = random.Random(seed)
        per_cab_selection: dict[str, list[tuple[str, float]]] = {}
        for cab in sorted(cab_meta.keys()):
            meta = cab_meta[cab]
            per_cab_selection[cab] = select_for_cabinet(
                rng, meta["host_at_peak"], meta["peak_total"], target_fraction,
            )
        removed: set[str] = {h for sel in per_cab_selection.values() for h, _ in sel}
        n_viol, total_def, viols = score_attempt(removed, partitions)

        if best is None or (n_viol, total_def) < (best["n_viol"], best["total_deficit"]):
            best = {
                "seed": seed,
                "n_viol": n_viol,
                "total_deficit": total_def,
                "violations": viols,
                "per_cab_selection": per_cab_selection,
                "removed": removed,
            }
        if n_viol == 0:
            print(f"  attempt {i + 1}/{max_attempts} (seed={seed}): "
                  f"feasible, accepting")
            break
    else:
        print(f"  exhausted {max_attempts} attempts; "
              f"best had {best['n_viol']} partition violations "
              f"(total deficit {best['total_deficit']}). "
              f"WARNING: writing best-effort selection.")

    chosen = best
    assert chosen is not None

    # Restore one host per zero-remaining partition. This guarantees no
    # partition is fully emptied, even when no attempt was fully feasible.
    restoration_rng = random.Random(chosen["seed"] + 1_000_000)
    restorations = restore_zero_remaining(
        chosen["per_cab_selection"],
        chosen["removed"],
        partitions,
        restoration_rng,
    )
    if restorations:
        n_viol2, total_def2, viols2 = score_attempt(chosen["removed"], partitions)
        print(f"  restored {len(restorations)} host(s) to clear "
              f"zero-remaining partitions:")
        for part, host, cab in restorations:
            print(f"    + {host} (cabinet {cab}) -> partition {part}")
        chosen["n_viol"] = n_viol2
        chosen["total_deficit"] = total_def2
        chosen["violations"] = viols2

    # Write outputs.
    sel_path = os.path.join(output_dir, "selected_nodes.csv")
    sum_path = os.path.join(output_dir, "selection_summary.csv")
    viol_path = os.path.join(output_dir, "partition_violations.csv")

    with open(sel_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "cabinet", "host", "peak_time", "host_power_at_peak_w",
            "cabinet_peak_total_w", "achieved_fraction", "target_fraction",
            "attempt_seed", "attempt_violations",
        ])
        for cab, sel in chosen["per_cab_selection"].items():
            meta = cab_meta[cab]
            removed_w = sum(p for _, p in sel)
            achieved = (removed_w / meta["peak_total"]) if meta["peak_total"] > 0 else 0.0
            for host, p in sel:
                w.writerow([
                    cab, host, meta["peak_time"], f"{p:.1f}",
                    f"{meta['peak_total']:.1f}", f"{achieved:.4f}",
                    f"{target_fraction:.4f}",
                    chosen["seed"], chosen["n_viol"],
                ])

    with open(sum_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "cabinet", "n_hosts", "peak_time", "peak_total_kw",
            "n_selected", "removed_at_peak_kw", "achieved_fraction",
            "target_fraction", "recomputed_new_inst_max_kw",
        ])
        for cab in sorted(cab_meta.keys()):
            meta = cab_meta[cab]
            sel = chosen["per_cab_selection"][cab]
            removed_w = sum(p for _, p in sel)
            achieved = (removed_w / meta["peak_total"]) if meta["peak_total"] > 0 else 0.0
            removed_set = {h for h, _ in sel}
            new_max_w = cabinet_inst_max_after(cabinets[cab], removed_set)
            w.writerow([
                cab, meta["n_hosts"], meta["peak_time"],
                f"{meta['peak_total'] / 1000:.2f}",
                len(sel), f"{removed_w / 1000:.2f}",
                f"{achieved:.4f}", f"{target_fraction:.4f}",
                f"{new_max_w / 1000:.2f}",
            ])

    with open(viol_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["partition", "partition_size", "n_removed",
                    "n_remaining", "floor", "deficit"])
        for v in sorted(chosen["violations"]):
            w.writerow(v)

    n_removed = len(chosen["removed"])
    print(f"  chosen seed={chosen['seed']}; "
          f"removed {n_removed} hosts across {len(cabinets)} cabinets; "
          f"partition violations={chosen['n_viol']} "
          f"(total deficit {chosen['total_deficit']})")
    print(f"  wrote {sel_path}")
    print(f"  wrote {sum_path}")
    print(f"  wrote {viol_path}")

    # Per-partition impact summary lands beside selection_summary.csv every
    # time this stage runs. Standalone re-runs are still possible via
    # `python pipeline/summarize_by_partition.py`.
    from pipeline import summarize_by_partition
    by_part_path = os.path.join(output_dir, "selection_summary_by_partition.csv")
    summarize_by_partition.run(
        selected_csv=sel_path,
        scontrol_path=scontrol_path,
        output_path=by_part_path,
    )

    return chosen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    parser.add_argument("--reduction-fraction", type=float,
                        default=DEFAULT_REDUCTION_FRACTION,
                        help="target fraction of each cabinet's at-peak total "
                             "to remove (default: 0.4)")
    parser.add_argument("--max-attempts", type=int,
                        default=DEFAULT_MAX_ATTEMPTS,
                        help="number of seeded shuffle attempts (default: 100)")
    parser.add_argument("--seed-base", type=int,
                        default=DEFAULT_SEED_BASE,
                        help="seed for attempt 0; attempt i uses seed_base+i")
    parser.add_argument("--scontrol-json",
                        default=DEFAULT_SCONTROL_JSON,
                        help="path to scontrol_show_node.json")
    ns = parser.parse_args()
    args = args_from_namespace(ns)
    print("Selecting reduction nodes...")
    run(
        target_fraction=ns.reduction_fraction,
        max_attempts=ns.max_attempts,
        seed_base=ns.seed_base,
        scontrol_path=ns.scontrol_json,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
