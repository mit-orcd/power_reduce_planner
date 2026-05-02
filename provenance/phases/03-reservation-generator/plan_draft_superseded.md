---
name: slurm reservation generator
overview: Add a small standalone Python program in `r9_pod_a_pipeline/` that reads `output/selected_nodes.csv`, deduplicates the `host` column, and prints a single `scontrol create reservation` command with `Flags=MAINT,IGNORE_JOBS`, configurable start/end (default 2026-05-10T09:00 to 2026-05-17T09:00), and a unique-but-readable name containing `temp_power_reduce`.
todos: []
isProject: false
---

## Goal

A standalone command-line tool, fully decoupled from the pipeline orchestrator, that turns the existing `[r9_pod_a_pipeline/output/selected_nodes.csv](r9_pod_a_pipeline/output/selected_nodes.csv)` (179 hosts in the smoke run, one row per selected host with column `host`) into a Slurm reservation command an operator can copy/paste or pipe to a remote shell.

## File to add

`[r9_pod_a_pipeline/make_reservation.py](r9_pod_a_pipeline/make_reservation.py)` -- sibling of `run_pipeline.py`, no new dependencies. Standard library only.

## CLI

```text
usage: make_reservation.py [--start YYYY-MM-DDTHH:MM[:SS]]
                           [--end   YYYY-MM-DDTHH:MM[:SS]]
                           [--selected-csv PATH]
                           [--name NAME]
                           [--user USER]
                           [--output-script PATH]
```

| Flag | Default | Notes |
| --- | --- | --- |
| `--start` | `2026-05-10T09:00` | combined date + time of day |
| `--end`   | `2026-05-17T09:00` | combined date + time of day |
| `--selected-csv` | `output/selected_nodes.csv` (relative to script dir) | input CSV |
| `--name` | auto, see below | full reservation name override |
| `--user` | `root` | required by `scontrol create reservation`; one of `User=` / `Accounts=` must be set |
| `--output-script` | none | optional path to write a shell script wrapping the command |

`--start` / `--end` are parsed via `datetime.fromisoformat`, which accepts `YYYY-MM-DDTHH:MM` and `YYYY-MM-DDTHH:MM:SS`. Both are validated; `end` must be strictly later than `start`.

## Reservation name (auto-generated when `--name` is not given)

Format: `temp_power_reduce_<YYYYMMDD>_<HHMM>_<NNN>`

- `<YYYYMMDD>_<HHMM>` is the start time, so the name reads naturally and stays unique across distinct reservation windows ("`temp_power_reduce_20260510_0900_179`").
- `<NNN>` is the host count from the CSV, which doubles as a sanity check at-a-glance.
- All characters are alphanumeric / underscore -- safe for Slurm.

## Output (printed to stdout)

A single `scontrol create reservation ...` line with key=value tokens space-separated, e.g.:

```text
scontrol create reservation ReservationName=temp_power_reduce_20260510_0900_179 \
    StartTime=2026-05-10T09:00:00 EndTime=2026-05-17T09:00:00 \
    User=root Flags=MAINT,IGNORE_JOBS \
    Nodes=node3000,node3003,node3004,...
```

When `--output-script PATH` is given, the same command is also written to `PATH` with a `#!/bin/sh` header and `set -euo pipefail`, plus `chmod 755` on the file. Stdout still prints the command verbatim either way.

## Module sketch

```python
def load_hosts(csv_path: Path) -> list[str]:
    """Read selected_nodes.csv, return sorted unique non-empty 'host' values.
    Sort uses a natural key (numeric suffix) so node10 sorts after node2."""

def build_reservation_command(
    name: str, start: datetime, end: datetime,
    user: str, hosts: list[str],
) -> str: ...

def main() -> None:
    # argparse, parse times, validate, load CSV, build command, print,
    # optionally write script
```

Dedup is done with `dict.fromkeys` over the column to preserve insertion order; the natural-sort returns a list so `Nodes=` is deterministic across runs (helps diffs / review).

## Edge cases to handle explicitly

- `selected_nodes.csv` missing or empty: clear stderr error, exit 2.
- `host` column missing: clear stderr error naming the columns we did find.
- `--start >= --end`: stderr error, exit 2.
- Whitespace / blank `host` cells: ignored after `strip()`.
- Very long Nodes= list: emit on a single line (Slurm parses it fine; no need for the line-continuation backslash format -- we only use backslashes in the optional `--output-script` for human readability).

## Doc updates (one-line each)

- `[r9_pod_a_pipeline/README.md](r9_pod_a_pipeline/README.md)`: append a short "Slurm reservation" subsection under "Reduction selection" with the quickstart command.
- No changes to `DESIGN.md` or `AGENT_INSTRUCTIONS.md` -- this is a leaf utility, not a pipeline stage.

## Verification

Run with defaults and inspect stdout: confirm Flags / Nodes / Name match. Sanity-check `Nodes=$(echo ... | tr , '\n' | wc -l)` equals the unique host count in `selected_nodes.csv`.

## Out of scope

- Talking to a Slurm controller directly. The tool only emits the command; running it is left to an operator with `scontrol` privileges.
- Hostlist-syntax compression (`node[3000-3010]`). Comma-separated names are unambiguous and easier to audit.
- Any orchestrator hook in `run_pipeline.py`. The user asked for a standalone program.