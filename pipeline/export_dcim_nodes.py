#!/usr/bin/env python3
"""Spec task #1: export every dcim_nodes row as name, row, pod, rack."""

from __future__ import annotations

import argparse
import csv
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(THIS_DIR))

from config import add_common_args, args_from_namespace
from pg_client import connect, read_sql


COLUMNS = ("name", "row", "pod", "rack")


def export(output_dir: str) -> str:
    sql = read_sql("01_dcim_nodes.sql")
    out_path = os.path.join(output_dir, "dcim_nodes.csv")
    os.makedirs(output_dir, exist_ok=True)

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    finally:
        conn.close()

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(rows)

    print(f"  wrote {out_path} ({len(rows)} rows)")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    args = args_from_namespace(parser.parse_args())
    print("Exporting dcim_nodes inventory...")
    export(args.output_dir)


if __name__ == "__main__":
    main()
