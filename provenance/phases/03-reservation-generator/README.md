# Phase 03 — Reservation generator

**When:** Saturday May 2, 06:42 to 06:54 (UTC-4)
**User prompts:** 5 (indices 9-13)
**Plan:** [`plan.md`](plan.md) (`slurm_reservation_generator_ea0910d3.plan.md`)
**Earlier draft:** [`plan_draft_superseded.md`](plan_draft_superseded.md)
(`slurm_reservation_generator_57dffe96.plan.md`, written ~3 minutes earlier
and replaced by the user-confirmed version)
**Result on disk:** `r9_pod_a_pipeline/make_reservation.py` (standalone, no
hook into `run_pipeline.py`).

## What came in

User asked for a standalone Python program that:

- reads `output/selected_nodes.csv`,
- emits a `scontrol create reservation` command with `Flags=MAINT,IGNORE_JOBS`,
- covers all unique hosts in the CSV,
- accepts `--start` / `--end` (default 2026-05-10T09:00 to 2026-05-17T09:00),
- has a unique-but-readable name containing `temp_power_reduce`.

No clarifying AskQuestion needed; the request was clear enough to plan
directly. The 3-minute gap between the two plan files is from a draft
revision before publishing the final.

## What was built

[`r9_pod_a_pipeline/make_reservation.py`](../../../make_reservation.py) --
standard library only (no psycopg, matplotlib, etc.). CLI flags:

| Flag | Default |
| --- | --- |
| `--start` | `2026-05-10T09:00` |
| `--end` | `2026-05-17T09:00` |
| `--selected-csv` | `output/selected_nodes.csv` |
| `--name` | auto: `temp_power_reduce_<YYYYMMDD>_<HHMM>_<host_count>` |
| `--user` | `root` |
| `--output-script` | (none) |

Sample output (single line on stdout, pipe-clean):

```text
scontrol create reservation ReservationName=temp_power_reduce_20260510_0900_179 \
    StartTime=2026-05-10T09:00:00 EndTime=2026-05-17T09:00:00 \
    User=root Flags=MAINT,IGNORE_JOBS \
    Nodes=node1603,node1604,...
```

Hosts are deduplicated via `dict.fromkeys` (preserves order) then
naturally sorted (`node3 < node10`) so the same selection produces the
same `Nodes=` list every time.

When `--output-script PATH` is given, the same command is also written to
PATH with a `#!/bin/sh` header, `set -eu`, three header comment lines
(reservation name, window, host count), and `chmod 755`. Stdout still
prints the command verbatim.

## Verification

| Check | Result |
| --- | --- |
| `Flags=MAINT,IGNORE_JOBS` present in stdout | yes |
| Auto name contains `temp_power_reduce` and host count | `temp_power_reduce_20260510_0900_179` |
| `Nodes=` count matches unique hosts in CSV | 179 == 179 |
| `--start 2026-06-01T09:00 --end 2026-06-08T09:00 --user slurm-admin` overrides | all three propagate; auto name updates to `..._20260601_0900_179` |
| `--end <= --start` | clear stderr error, exit 2 |
| Missing CSV | clear stderr error, exit 2 |
| `--output-script /tmp/reservation.sh` | writes executable shell script (`-rwxr-xr-x`) |

## Post-delivery refinements

User added then immediately removed the `SPEC_NODES` flag. See
[`change_requests.md`](change_requests.md) for the back-and-forth and the
domain reason (`SPEC_NODES` is set implicitly by Slurm whenever a
reservation names specific nodes; passing it explicitly is redundant /
likely an error).

## Files in this phase directory

| File | Purpose |
| --- | --- |
| [`plan.md`](plan.md) | the accepted plan |
| [`plan_draft_superseded.md`](plan_draft_superseded.md) | earlier draft (~3 min before the accepted plan); kept for transparency |
| [`user_prompts.md`](user_prompts.md) | 5 prompts including the SPEC_NODES add and undo |
| [`assistant_responses.md`](assistant_responses.md) | every visible assistant text block plus tool-call stubs |
| [`decisions.md`](decisions.md) | distilled per-phase decisions |
| [`change_requests.md`](change_requests.md) | SPEC_NODES added and immediately removed |
