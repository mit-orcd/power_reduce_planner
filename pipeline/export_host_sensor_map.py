#!/usr/bin/env python3
"""Spec task #2 setup: choose the preferred power sensor for each compute node
in (row, pod) and write it to output/host_sensor_map.csv.

This is the single source of truth for two domain rules:
  * dcim node "XXXX-YYYY" maps to telegraf host "XXXX"
  * sys_power > instantaneous_power_reading > pwr_consumption when more than
    one sensor is reported by a host

Downstream scripts join on this CSV.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(THIS_DIR))

from config import add_common_args, args_from_namespace
from pg_client import connect, read_sql


COLUMNS = ("host", "rack", "preferred_sensor")


def export(row: str, pod: str, start: str, end: str, output_dir: str) -> str:
    sql = read_sql("02_host_sensor_map.sql")
    out_path = os.path.join(output_dir, "host_sensor_map.csv")
    os.makedirs(output_dir, exist_ok=True)

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, {"row": row, "pod": pod, "start": start, "end": end})
            rows = cur.fetchall()
    finally:
        conn.close()

    kept = [r for r in rows if r[2] is not None]
    dropped = len(rows) - len(kept)

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(kept)

    print(f"  wrote {out_path} ({len(kept)} hosts with power data, "
          f"{dropped} compute nodes dropped for having none)")
    if kept:
        sensor_counts: dict[str, int] = {}
        for _, _, sensor in kept:
            sensor_counts[sensor] = sensor_counts.get(sensor, 0) + 1
        breakdown = ", ".join(f"{s}={c}" for s, c in sorted(sensor_counts.items()))
        print(f"  preferred sensor mix: {breakdown}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    args = args_from_namespace(parser.parse_args())
    print(f"Choosing preferred sensor per host for row={args.row} pod={args.pod}...")
    export(args.row, args.pod, args.start, args.end, args.output_dir)


if __name__ == "__main__":
    main()
