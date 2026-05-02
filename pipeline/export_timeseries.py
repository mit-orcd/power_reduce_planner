#!/usr/bin/env python3
"""Spec task #2 main step: pull bucketed power time-series for every (host,
preferred_sensor) pair in host_sensor_map.csv and write one CSV per host
under output/timeseries/cabinet_NN/.
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
from collections import defaultdict

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(THIS_DIR))

from config import add_common_args, args_from_namespace
from pg_client import connect, read_sql


HOST_CSV_COLUMNS = ("time", "power_watts")


def _load_pairs(output_dir: str) -> list[tuple[str, str, str]]:
    """Return list of (host, rack, preferred_sensor) from host_sensor_map.csv."""
    path = os.path.join(output_dir, "host_sensor_map.csv")
    if not os.path.exists(path):
        sys.stderr.write(
            f"Error: {path} not found. Run export_host_sensor_map.py first.\n"
        )
        sys.exit(2)
    pairs: list[tuple[str, str, str]] = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            pairs.append((row["host"], row["rack"], row["preferred_sensor"]))
    return pairs


def export(start: str, end: str, bucket: str, output_dir: str) -> None:
    sql_template = read_sql("03_node_timeseries.sql")
    pairs = _load_pairs(output_dir)
    if not pairs:
        print("  no (host, sensor) pairs to query; nothing to do")
        return

    by_rack: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for host, rack, sensor in pairs:
        by_rack[rack].append((host, sensor))

    ts_dir = os.path.join(output_dir, "timeseries")
    if os.path.isdir(ts_dir):
        shutil.rmtree(ts_dir)

    conn = connect()
    total_rows = 0
    total_files = 0
    try:
        for rack in sorted(by_rack.keys()):
            rack_pairs = by_rack[rack]

            # Render the (host, sensor) VALUES clause via mogrify so psycopg2
            # does the quoting; %(name)s placeholders for the time window
            # remain bound by the subsequent execute() call.
            with conn.cursor() as cur:
                rendered_values = b",".join(
                    cur.mogrify("(%s,%s)", pair) for pair in rack_pairs
                ).decode()
                final_sql = sql_template.replace("{pairs_values}", rendered_values)
                cur.execute(
                    final_sql,
                    {"start": start, "end": end, "bucket": bucket},
                )
                rows = cur.fetchall()

            rack_dir = os.path.join(ts_dir, f"cabinet_{rack}")
            os.makedirs(rack_dir, exist_ok=True)

            by_host: dict[str, list[tuple]] = defaultdict(list)
            for ts, host, watts in rows:
                by_host[host].append((ts, watts))

            for host, host_rows in sorted(by_host.items()):
                fpath = os.path.join(rack_dir, f"{host}.csv")
                with open(fpath, "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(HOST_CSV_COLUMNS)
                    w.writerows(host_rows)
                total_files += 1
            total_rows += len(rows)

            print(f"  cabinet {rack}: {len(rack_pairs)} hosts, "
                  f"{len(rows)} bucketed rows, {len(by_host)} files")
    finally:
        conn.close()

    print(f"  total: {total_rows} rows across {total_files} per-host CSV files "
          f"under {ts_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    args = args_from_namespace(parser.parse_args())
    print(f"Exporting per-host time-series (bucket={args.bucket})...")
    export(args.start, args.end, args.bucket, args.output_dir)


if __name__ == "__main__":
    main()
