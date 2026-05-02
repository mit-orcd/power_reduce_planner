#!/usr/bin/env python3
"""Standalone tool: turn output/selected_nodes.csv into a Slurm reservation
command (`scontrol create reservation ...`) with Flags=MAINT,IGNORE_JOBS.

Prints the command to stdout; can also write it as an executable shell
script via --output-script PATH.

Defaults are tuned for the row-9 / pod-A reduction window the rest of the
pipeline produces:

    --start 2026-05-10T09:00     --end 2026-05-17T09:00
    --selected-csv output/selected_nodes.csv
    --user root

The reservation name (when not overridden via --name) embeds the start time
and the host count so it stays unique per window and is easy to read at a
glance, e.g. "temp_power_reduce_20260510_0900_179".
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import stat
import sys
from datetime import datetime
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent

DEFAULT_START = "2026-05-10T09:00"
DEFAULT_END = "2026-05-17T09:00"
DEFAULT_SELECTED_CSV = THIS_DIR / "output" / "selected_nodes.csv"
DEFAULT_USER = "root"
NAME_PREFIX = "temp_power_reduce"


def _natural_key(name: str) -> tuple:
    """Split into chunks so node3 < node10 (numeric runs sort numerically)."""
    return tuple(int(part) if part.isdigit() else part
                 for part in re.split(r"(\d+)", name))


def load_hosts(csv_path: Path) -> list[str]:
    """Return sorted unique non-empty host names from selected_nodes.csv."""
    if not csv_path.exists():
        sys.stderr.write(f"Error: {csv_path} not found.\n")
        sys.exit(2)

    with csv_path.open() as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            sys.stderr.write(f"Error: {csv_path} is empty.\n")
            sys.exit(2)
        if "host" not in reader.fieldnames:
            sys.stderr.write(
                f"Error: {csv_path} has no 'host' column. "
                f"Found columns: {reader.fieldnames}\n"
            )
            sys.exit(2)
        hosts: dict[str, None] = {}
        for row in reader:
            h = (row.get("host") or "").strip()
            if h:
                hosts[h] = None

    if not hosts:
        sys.stderr.write(f"Error: {csv_path} has no host rows.\n")
        sys.exit(2)

    return sorted(hosts.keys(), key=_natural_key)


def parse_iso(s: str, label: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except ValueError as e:
        sys.stderr.write(
            f"Error: --{label} value {s!r} is not ISO 8601 "
            f"(YYYY-MM-DDTHH:MM[:SS]): {e}\n"
        )
        sys.exit(2)


def slurm_time(dt: datetime) -> str:
    """Slurm StartTime/EndTime format: YYYY-MM-DDTHH:MM:SS (no timezone)."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def auto_name(start: datetime, host_count: int) -> str:
    return f"{NAME_PREFIX}_{start.strftime('%Y%m%d_%H%M')}_{host_count}"


def build_reservation_command(name: str,
                              start: datetime,
                              end: datetime,
                              user: str,
                              hosts: list[str]) -> str:
    nodes = ",".join(hosts)
    return (
        "scontrol create reservation "
        f"ReservationName={name} "
        f"StartTime={slurm_time(start)} "
        f"EndTime={slurm_time(end)} "
        f"User={user} "
        "Flags=MAINT,IGNORE_JOBS "
        f"Nodes={nodes}"
    )


def write_script(path: Path, command: str, name: str,
                 start: datetime, end: datetime, host_count: int) -> None:
    # Wrap onto multiple lines for human readability in the script form;
    # the actual command is a single shell line via the `\` continuations.
    pretty = command.replace(" ReservationName=", " \\\n    ReservationName=") \
                    .replace(" StartTime=", " \\\n    StartTime=") \
                    .replace(" EndTime=", " \\\n    EndTime=") \
                    .replace(" User=", " \\\n    User=") \
                    .replace(" Flags=", " \\\n    Flags=") \
                    .replace(" Nodes=", " \\\n    Nodes=")
    body = (
        "#!/bin/sh\n"
        "set -eu\n"
        f"# Reservation: {name}\n"
        f"# Window:      {slurm_time(start)} -> {slurm_time(end)}\n"
        f"# Hosts:       {host_count}\n"
        f"{pretty}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--start", default=DEFAULT_START,
                        help=f"reservation start (ISO 8601). default {DEFAULT_START}")
    parser.add_argument("--end", default=DEFAULT_END,
                        help=f"reservation end (ISO 8601). default {DEFAULT_END}")
    parser.add_argument("--selected-csv", default=str(DEFAULT_SELECTED_CSV),
                        help="path to selected_nodes.csv")
    parser.add_argument("--name", default=None,
                        help="reservation name override (default: auto-generated, "
                             f"includes '{NAME_PREFIX}')")
    parser.add_argument("--user", default=DEFAULT_USER,
                        help=f"User= field for the reservation. default {DEFAULT_USER}")
    parser.add_argument("--output-script", default=None,
                        help="optional path to write the command as an executable "
                             "shell script in addition to printing it")
    ns = parser.parse_args()

    start = parse_iso(ns.start, "start")
    end = parse_iso(ns.end, "end")
    if end <= start:
        sys.stderr.write(
            f"Error: --end ({ns.end}) must be strictly after --start ({ns.start}).\n"
        )
        sys.exit(2)

    hosts = load_hosts(Path(ns.selected_csv))
    name = ns.name if ns.name else auto_name(start, len(hosts))

    cmd = build_reservation_command(name, start, end, ns.user, hosts)
    print(cmd)

    if ns.output_script:
        out_path = Path(ns.output_script)
        write_script(out_path, cmd, name, start, end, len(hosts))
        sys.stderr.write(f"# wrote executable script: {out_path}\n")

    sys.stderr.write(
        f"# reservation '{name}' covers {len(hosts)} hosts "
        f"from {slurm_time(start)} to {slurm_time(end)}\n"
    )


if __name__ == "__main__":
    main()
