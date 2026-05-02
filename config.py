"""Default configuration and CLI helpers for the r9_pod_a_pipeline.

All knobs collected here so a single place defines the parameter surface
visible in `DESIGN.md`. Individual scripts call `add_common_args()` to share
flags, and read `PG_*` constants for connection settings.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

PG_HOST = "127.0.0.1"
PG_PORT = 5433
PG_USER = "readonly_user"
PG_DB = "timedb"

DEFAULT_ROW = "09"
DEFAULT_POD = "A"
DEFAULT_START = "2026-04-01T17:27:22.547Z"
DEFAULT_END = "2026-05-30T17:27:22.547Z"
DEFAULT_BUCKET = "10m"

# Sensor priority: when a host reports more than one of these, the earlier
# entry wins. Encoded as a domain rule -- not exposed on the CLI.
SENSOR_PRIORITY = (
    "sys_power",
    "instantaneous_power_reading",
    "pwr_consumption",
)

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT_DIR = os.path.join(REPO_DIR, "output")
SQL_DIR = os.path.join(REPO_DIR, "sql")


@dataclass
class PipelineArgs:
    row: str
    pod: str
    start: str
    end: str
    bucket: str
    output_dir: str


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--row", default=DEFAULT_ROW,
                        help=f"datacenter row number (default: {DEFAULT_ROW})")
    parser.add_argument("--pod", default=DEFAULT_POD,
                        help=f"pod letter (default: {DEFAULT_POD})")
    parser.add_argument("--start", default=DEFAULT_START,
                        help="ISO-8601 start of time window")
    parser.add_argument("--end", default=DEFAULT_END,
                        help="ISO-8601 end of time window")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET,
                        help="time bucket for the time-series query (default: 10m)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help="directory to write CSV / PNG outputs into")


def args_from_namespace(ns: argparse.Namespace) -> PipelineArgs:
    return PipelineArgs(
        row=ns.row,
        pod=ns.pod,
        start=ns.start,
        end=ns.end,
        bucket=ns.bucket,
        output_dir=ns.output_dir,
    )
