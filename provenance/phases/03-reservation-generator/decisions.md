# Decisions — Phase 03 (Reservation generator)

## Placement

- **Standalone, top-level** (sibling of `run_pipeline.py`) rather than a
  pipeline stage. The user said "stand alone" and the work is purely
  post-processing on a CSV that may have been hand-edited. No hook in
  `run_pipeline.py`.
- **Standard library only.** No psycopg / matplotlib / numpy import; the
  script is portable enough to run anywhere `selected_nodes.csv` lands.

## CLI surface

- **Combined date+time per flag** (`--start 2026-05-10T09:00`) instead of
  separate `--start-date` / `--start-time`. ISO 8601 round-trips through
  `datetime.fromisoformat`, accepts both `YYYY-MM-DDTHH:MM` and
  `YYYY-MM-DDTHH:MM:SS`. Validation: `--end > --start`.
- **`--user` defaults to `root`.** Slurm requires either `User=` or
  `Accounts=` on a reservation; this is the most common admin choice and
  is overridable.
- **`--output-script` optional.** Stdout always carries the command for
  piping (`make_reservation.py | ssh slurm-controller sh -`). When the
  user wants something to commit / email, the script form has comment
  headers and `set -eu`.

## Reservation name

- **Format:** `temp_power_reduce_<YYYYMMDD>_<HHMM>_<host_count>`.
- **Why:** "easy to understand" -> human-readable date/time prefix;
  "can be unique" -> embedding the start time keeps the name unique
  per window without a UUID; embedding the host count doubles as a
  sanity check at-a-glance ("did the right CSV feed the script?").
- **Slurm-safe characters only** (alphanumeric and underscore).

## Output behavior

- **Stdout = command only.** All informational lines
  (`# reservation '...' covers N hosts`, `# wrote executable script`)
  go to **stderr** so stdout stays pipe-clean.
- **Hosts naturally sorted** (`node3 < node10`) and deduplicated via
  `dict.fromkeys` so the same selection produces the same `Nodes=` list
  every time -- helps diffs / review.
- **Long Nodes= list on one line.** Slurm parses comma-separated lists
  fine. Backslash-continued multi-line form is reserved for the
  `--output-script` output where readability matters.

## Slurm flag handling

- **`Flags=MAINT,IGNORE_JOBS`** as the user specified.
- **`SPEC_NODES`** -- briefly added per user request, then removed when
  the user clarified that Slurm sets that flag itself on any reservation
  naming specific nodes. See [`change_requests.md`](change_requests.md).

## What was intentionally NOT done

- **No talking to a Slurm controller.** Tool emits a command; running it
  is left to an operator with `scontrol` privileges.
- **No hostlist-syntax compression** (`node[3000-3010]`). Comma-separated
  names are unambiguous and easier to audit.
- **No `run_pipeline.py` hook.** Standalone tool by design.
