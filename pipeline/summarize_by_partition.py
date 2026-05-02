#!/usr/bin/env python3
"""Per-partition impact summary for the reduction selection.

For every Slurm partition that loses at least one node, report how many
nodes, CPUs, and GPUs (broken out by accelerator type) the partition had
before the reduction, how many are being removed, and how many remain.

Use --include-untouched to also emit rows for partitions where no node was
removed (these all have `*_rm == 0` and `*_pre == *_post`).

Header convention is compact so the table fits in csvlens-style viewers:
  *_pre   = before reduction
  *_rm    = removed
  *_post  = after reduction
Per-type GPU columns drop the redundant `gpus_` prefix; the cabinet-wide
total stays as `gpus_pre / gpus_rm / gpus_post`.

Inputs:
  output/selected_nodes.csv                (which hosts are removed)
  data/scontrol_show_node.json[.gz]        (cpus + gres + partitions per node)

Output:
  output/selection_summary_by_partition.csv
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import re
import sys
from collections import defaultdict

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(THIS_DIR))

from config import REPO_DIR

DEFAULT_SELECTED_CSV = os.path.join(REPO_DIR, "output", "selected_nodes.csv")
DEFAULT_OUTPUT_CSV = os.path.join(
    REPO_DIR, "output", "selection_summary_by_partition.csv",
)
DEFAULT_SCONTROL_JSON = os.path.join(
    REPO_DIR, "data", "scontrol_show_node.json.gz"
)

# Captures both `gpu:h100:4` (typed) and `gpu:4` (untyped). Group 1 is the
# type (None for untyped); group 2 is the count.
GRES_GPU = re.compile(r"gpu:(?:([A-Za-z0-9_\-]+):)?(\d+)")


def parse_gres(gres: str | None) -> dict[str, int]:
    """Return {gpu_type_lowercase: count} extracted from a Slurm gres string.

    Untyped gpu entries (`gpu:4`) bucket as type 'untyped'. Empty / null /
    non-gpu gres yields {}.
    """
    if not gres:
        return {}
    out: dict[str, int] = defaultdict(int)
    for m in GRES_GPU.finditer(gres):
        gpu_type = (m.group(1) or "untyped").lower()
        out[gpu_type] += int(m.group(2))
    return dict(out)


def _open_scontrol(path: str):
    """Open scontrol_show_node.json{,.gz}; gzip auto-detected by extension."""
    if path.endswith(".gz"):
        return gzip.open(path, "rt")
    return open(path)


def load_nodes(scontrol_path: str) -> tuple[dict[str, dict], list[str]]:
    """Return ({node_name: {cpus, gpus_by_type, partitions}}, sorted_gpu_types).

    sorted_gpu_types is the global alphabetical list of GPU types observed
    anywhere in the JSON, used to build the per-type CSV columns.
    """
    with _open_scontrol(scontrol_path) as f:
        data = json.load(f)
    nodes: dict[str, dict] = {}
    seen_types: set[str] = set()
    for n in data.get("nodes", []):
        name = n.get("name")
        if not name:
            continue
        cpus = int(n.get("cpus") or 0)
        gpus = parse_gres(n.get("gres") or "")
        seen_types.update(gpus.keys())
        parts = list(n.get("partitions") or [])
        nodes[name] = {"cpus": cpus, "gpus": gpus, "partitions": parts}
    return nodes, sorted(seen_types)


def load_removed(selected_csv: str) -> set[str]:
    if not os.path.exists(selected_csv):
        sys.stderr.write(
            f"Error: {selected_csv} not found. "
            f"Run select_reduction_nodes.py first.\n"
        )
        sys.exit(2)
    out: set[str] = set()
    with open(selected_csv) as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "host" not in reader.fieldnames:
            sys.stderr.write(
                f"Error: {selected_csv} has no 'host' column.\n"
            )
            sys.exit(2)
        for row in reader:
            h = (row.get("host") or "").strip()
            if h:
                out.add(h)
    return out


def aggregate(nodes: dict[str, dict],
              removed: set[str],
              gpu_types: list[str]
              ) -> dict[str, dict]:
    """Return {partition: {nodes, cpus, gpus_total, gpus_<type>: (before, removed)}}.

    `_after` is computed at write time as `before - removed`.
    """
    blank = {
        "nodes_before": 0, "nodes_removed": 0,
        "cpus_before": 0, "cpus_removed": 0,
        "gpus_total_before": 0, "gpus_total_removed": 0,
    }
    for t in gpu_types:
        blank[f"gpus_{t}_before"] = 0
        blank[f"gpus_{t}_removed"] = 0

    by_part: dict[str, dict] = defaultdict(lambda: dict(blank))
    for name, info in nodes.items():
        is_removed = name in removed
        cpus = info["cpus"]
        gpus = info["gpus"]
        gpus_total = sum(gpus.values())
        for part in info["partitions"]:
            row = by_part[part]
            row["nodes_before"] += 1
            row["cpus_before"] += cpus
            row["gpus_total_before"] += gpus_total
            for t, c in gpus.items():
                row[f"gpus_{t}_before"] += c
            if is_removed:
                row["nodes_removed"] += 1
                row["cpus_removed"] += cpus
                row["gpus_total_removed"] += gpus_total
                for t, c in gpus.items():
                    row[f"gpus_{t}_removed"] += c
    return by_part


def write_csv(out_path: str,
              by_part: dict[str, dict],
              gpu_types: list[str],
              include_untouched: bool = False) -> int:
    """Write the per-partition impact CSV. Returns the number of rows written.

    Header suffixes are compacted to `_pre / _rm / _post` so the table fits on
    a screen in csvlens-style viewers. Per-type GPU columns drop the
    redundant `gpus_` prefix because the type name itself is unambiguous;
    the cabinet-wide GPU total keeps the `gpus_` prefix as `gpus_pre/_rm/_post`.

    Rows are filtered to partitions with at least one removed node unless
    `include_untouched=True`.
    """
    # (storage_prefix used for the in-memory dict, header_prefix used in the
    # CSV header). storage_prefix matches what `aggregate()` populated.
    columns: list[tuple[str, str]] = [
        ("nodes",      "nodes"),
        ("cpus",       "cpus"),
        ("gpus_total", "gpus"),
    ]
    columns += [(f"gpus_{t}", t) for t in gpu_types]

    header = ["partition"]
    for _, hp in columns:
        header.extend([f"{hp}_pre", f"{hp}_rm", f"{hp}_post"])

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    n_written = 0
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for part in sorted(by_part.keys()):
            row = by_part[part]
            if not include_untouched and row["nodes_removed"] == 0:
                continue
            out_row: list = [part]
            for sp, _ in columns:
                before = row[f"{sp}_before"]
                rem = row[f"{sp}_removed"]
                out_row.extend([before, rem, before - rem])
            w.writerow(out_row)
            n_written += 1
    return n_written


def run(selected_csv: str = DEFAULT_SELECTED_CSV,
        scontrol_path: str = DEFAULT_SCONTROL_JSON,
        output_path: str = DEFAULT_OUTPUT_CSV,
        include_untouched: bool = False) -> str:
    nodes, gpu_types = load_nodes(scontrol_path)
    removed = load_removed(selected_csv)
    by_part = aggregate(nodes, removed, gpu_types)
    n_written = write_csv(output_path, by_part, gpu_types, include_untouched)

    n_touched = sum(
        1 for r in by_part.values() if r["nodes_removed"] > 0
    )
    suppressed = "" if include_untouched else (
        f"; {len(by_part) - n_touched} untouched partitions suppressed "
        f"(use --include-untouched to keep)"
    )
    print(f"  wrote {output_path} "
          f"({n_written} rows; {n_touched} of {len(by_part)} partitions "
          f"touched by removal{suppressed}; "
          f"gpu types: {', '.join(gpu_types) if gpu_types else 'none'})")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--selected-csv", default=DEFAULT_SELECTED_CSV,
                        help="path to selected_nodes.csv")
    parser.add_argument("--scontrol-json", default=DEFAULT_SCONTROL_JSON,
                        help="path to scontrol_show_node.json (or .json.gz)")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_CSV,
                        help="output CSV path")
    parser.add_argument("--include-untouched", action="store_true",
                        help="also include partitions with no node removed "
                             "(default: only partitions with nodes_rm > 0)")
    ns = parser.parse_args()
    print("Building per-partition impact summary...")
    run(ns.selected_csv, ns.scontrol_json, ns.output,
        include_untouched=ns.include_untouched)


if __name__ == "__main__":
    main()
