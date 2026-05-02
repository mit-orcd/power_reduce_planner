#!/usr/bin/env python3
"""Spec task #3 input: per-host min/avg/max from raw samples of the
preferred sensor. Feeds the "potential max" bar in the cabinet plot."""

from __future__ import annotations

import argparse
import csv
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(THIS_DIR))

from config import add_common_args, args_from_namespace
from pg_client import connect, read_sql


COLUMNS = ("host", "min_power", "avg_power", "max_power", "sample_count")


def _load_pairs(output_dir: str) -> list[tuple[str, str]]:
    path = os.path.join(output_dir, "host_sensor_map.csv")
    if not os.path.exists(path):
        sys.stderr.write(
            f"Error: {path} not found. Run export_host_sensor_map.py first.\n"
        )
        sys.exit(2)
    pairs: list[tuple[str, str]] = []
    with open(path) as f:
        for row in csv.DictReader(f):
            pairs.append((row["host"], row["preferred_sensor"]))
    return pairs


def export(start: str, end: str, output_dir: str) -> str:
    sql_template = read_sql("04_node_stats.sql")
    pairs = _load_pairs(output_dir)
    out_path = os.path.join(output_dir, "node_stats.csv")
    os.makedirs(output_dir, exist_ok=True)

    if not pairs:
        with open(out_path, "w", newline="") as f:
            csv.writer(f).writerow(COLUMNS)
        print(f"  no (host, sensor) pairs to query; wrote empty {out_path}")
        return out_path

    conn = connect()
    try:
        with conn.cursor() as cur:
            rendered_values = b",".join(
                cur.mogrify("(%s,%s)", pair) for pair in pairs
            ).decode()
            final_sql = sql_template.replace("{pairs_values}", rendered_values)
            cur.execute(final_sql, {"start": start, "end": end})
            rows = cur.fetchall()
    finally:
        conn.close()

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(rows)

    print(f"  wrote {out_path} ({len(rows)} hosts)")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    args = args_from_namespace(parser.parse_args())
    print("Exporting per-host min/avg/max...")
    export(args.start, args.end, args.output_dir)


if __name__ == "__main__":
    main()
