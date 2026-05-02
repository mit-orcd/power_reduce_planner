# SYSTEM_CARD.md

Discovery / evaluation card for the `r9_pod_a_pipeline` codebase. Read
this if you are an outside agent or human deciding whether to adopt,
adapt, or lift parts of this code into another project. For how to run
it, see [`README.md`](README.md). For where every file lives, see
[`AGENTS.md`](AGENTS.md).

## At a glance

A small, opinionated, MIT-licensed Python toolchain for HPC datacenter
power analysis built on PostgreSQL + TimescaleDB telegraf data and a
Slurm `scontrol show nodes` snapshot. It targets one specific row + pod
of an MGHPCC-style cluster but is parameterized so the same code, with
modest edits, applies to any Slurm cluster instrumented the same way.

It can:

- export DCIM node inventory and per-host bucketed power time-series for
  any `(row, pod)` to CSV;
- pick the authoritative power sensor per host from
  `sys_power / instantaneous_power_reading / pwr_consumption`,
  encoding the priority once in SQL;
- render a 4-bar-per-cabinet plot (instantaneous min / average /
  instantaneous max / potential max);
- random-select nodes per cabinet to drop the at-peak cabinet total by
  a target fraction (default 40 percent), subject to a global Slurm
  partition floor (>=2 nodes remaining), with seeded retries and a
  best-effort fallback;
- emit a per-partition impact CSV (CPUs and GPUs broken out by type)
  and a `scontrol create reservation Flags=MAINT,IGNORE_JOBS ...`
  command covering the selected hosts.

## Domain and context

The code lives at the intersection of HPC operations, energy-aware
scheduling research, and datacenter capacity planning. People most
likely to find it useful: HPC site reliability engineers planning
maintenance windows or power-cap demonstrations; researchers prototyping
energy-aware Slurm policies; datacenter operators modeling the impact
of pulling N% of a row's compute offline. The dataset shape it expects
(telegraf IPMI sensors stored in TimescaleDB plus a NetBox-style DCIM
table) is common at university and lab clusters.

## What you get end-to-end

Run `python run_pipeline.py --row 09 --pod A --with-reduction` and you
get, under `output/`:

- `dcim_nodes.csv` -- every DCIM node with `name, row, pod, rack`.
- `host_sensor_map.csv` -- one row per powered host with its
  `(rack, preferred_sensor)`.
- `node_stats.csv` -- per-host raw `min / avg / max` of the chosen
  sensor across the time window.
- `timeseries/cabinet_NN/<host>.csv` -- per-host bucketed power
  time-series (default 10-minute buckets).
- `cabinet_power_bars.png` -- 4-bar-per-cabinet plot with reference
  lines at 16.5 / 33 / 49.5 kW.
- `selected_nodes.csv` and `selection_summary.csv` -- the reduction
  selection, with both at-peak and recomputed-new-max metrics.
- `partition_violations.csv` -- partitions still below floor after
  selection (header-only when feasible).
- `selection_summary_by_partition.csv` -- per-partition impact with
  `nodes / cpus / gpus / <gpu_type>` triplets `_pre / _rm / _post`.
- `cabinet_power_bars_with_reduction.png` -- 6-bar plot with
  before / after bars and a reduction-summary stats box.

`python make_reservation.py` then emits a single
`scontrol create reservation` command from `selected_nodes.csv`.

## Reusable building blocks

Pieces that solve common sub-problems and could be lifted into other
projects:

- **`sys_power`-priority sensor selection** encoded once in
  [`sql/02_host_sensor_map.sql`](sql/02_host_sensor_map.sql) via a
  `bool_or` `CASE`. Downstream stages just join on the produced
  `(host, preferred_sensor)` pairs.
- **Host-name irregularity matching pattern** -- `split_part(node_name,
  '-', 1) = i.host` handles dashed and undashed names uniformly. Same
  SQL file.
- **Per-cabinet random selection with global Slurm partition floor** in
  [`pipeline/select_reduction_nodes.py`](pipeline/select_reduction_nodes.py)
  -- shuffle-and-accumulate at the cabinet's at-peak time, score the
  union against partition floors, retry with seeded RNGs, fall back to
  best-effort with a violations report. Includes a "restore one host
  per zero-remaining partition" defensive pass.
- **Slurm `scontrol create reservation` command generator** in
  [`make_reservation.py`](make_reservation.py) -- standalone, std-lib
  only, optional shell-script output.
- **Per-partition impact CSV** with auto-discovered GPU types in
  [`pipeline/summarize_by_partition.py`](pipeline/summarize_by_partition.py)
  -- a regex over the Slurm `gres` string surfaces every accelerator
  type that exists in the cluster.

## Patterns demonstrated

Design approaches with value beyond this specific problem:

- **Spec to SQL to Python to CSV to plot** stage separation. Each stage
  is independently runnable with the same CLI flags; downstream stages
  read CSVs only and never re-query the DB. Iteration on plots is a
  ~1-second `--skip-export` re-render.
- **Constraint-with-seeded-retry plus best-effort fallback.** Hard
  constraints (Slurm partition floors) are checked globally; up to N
  seeded shuffles are tried; the lowest-violation attempt is kept and
  the shortfalls are written out for review.
- **Provenance-as-code.** The entire agentic build session that
  produced this repo is captured verbatim under
  [`provenance/`](provenance/) -- plans, prompts, AskQuestion choices,
  decisions, post-delivery refinements, all linked from a chronological
  [`provenance/TIMELINE.md`](provenance/TIMELINE.md).
- **Compact CSV headers for terminal viewers.** The
  `_pre / _rm / _post` triplet convention keeps wide partition-impact
  tables readable in `csvlens` and similar viewers without sacrificing
  meaning.

## Tech stack and dependencies

- **Runtime:** Python 3.10 or newer. Pipeline tested with 3.14.
- **Libraries:** `psycopg2-binary`, `matplotlib`, `numpy`. Standalone
  helpers (`make_reservation.py`,
  `pipeline/summarize_by_partition.py`,
  `provenance/scripts/extract_session.py`) are standard library only.
- **External systems:** PostgreSQL 14+ with TimescaleDB (the
  `time_bucket(...)` function); a Slurm `scontrol show nodes --json`
  snapshot; an IPMI sensor stream collected by telegraf.
- **No DuckDB, no Pandas.** The pipeline writes plain CSVs and uses the
  `csv` module to read them.

## Data assumptions / interface contracts

Fixed schemas this code expects:

- **`public.dcim_nodes`** with at minimum
  `node_name, row_number, pod, cabinet_number`. See
  [`sql/01_dcim_nodes.sql`](sql/01_dcim_nodes.sql) for the canonical
  query.
- **`telegraf.ipmi_sensor`** with `time, host, name, value`. The three
  power sensor names recognized are `sys_power`,
  `instantaneous_power_reading`, `pwr_consumption` -- in that priority
  order. See [`sql/02_host_sensor_map.sql`](sql/02_host_sensor_map.sql).
- **`scontrol show nodes` JSON** with `nodes[*].{name, cpus, gres,
  partitions[]}`. The `gres` string is parsed by the regex
  `gpu:(?:<type>:)?<count>`, which accepts both typed
  (`gpu:h100:4(S:0-1)`) and untyped (`gpu:4`) entries.

## Limitations and non-goals

- **No streaming / live mode.** Analysis is offline against a fixed
  time window; long windows are full table scans against TimescaleDB.
- **Reduction selection uses at-original-peak semantics**, not true
  new-max optimization -- removing nodes can shift the peak to a
  secondary timestamp where the cabinet total is still high. Both
  numbers are reported; the algorithm does not chase the moving target.
- **Pure shuffle, no ILP / weighted greedy.** "Random" was the
  user-specified primitive; deterministic with a seed.
- **One cluster's host-name irregularity is hard-coded** in the
  `split_part` rule. Other clusters may need a different rule.
- **External runtime dependency** on
  `../telegraf_data/scontrol_show_node.json` until that file is moved
  into the repo or `--scontrol-json PATH` is passed at every invocation.
- **No xlsx / parquet / pandas dataframe output.** CSV only.

## Adaptation guide

Common forks, each with the specific file to edit:

- **Other `(row, pod)`** -- pure CLI flag (`--row XX --pod Y`); no
  edits.
- **Other power sensors or different priority** -- edit
  `SENSOR_PRIORITY` in [`config.py`](config.py) and the `IN (...)` list
  plus `CASE` in [`sql/02_host_sensor_map.sql`](sql/02_host_sensor_map.sql).
- **Other host-name irregularity** -- change the `split_part` rule in
  the same SQL file.
- **Other cluster's Slurm partition floors** -- adjust the
  `floor = 1 if size == 1 else 2` line in `score_attempt` inside
  [`pipeline/select_reduction_nodes.py`](pipeline/select_reduction_nodes.py).
- **Other GPU types** -- automatic; the regex auto-discovers types from
  the JSON snapshot.
- **Other time bucket** -- pass `--bucket 5m` (or any TimescaleDB
  interval string).

## License and attribution

Released under the **MIT License**. See [`LICENSE`](LICENSE).

> Copyright (c) 2026 `<COPYRIGHT_HOLDER>`. The `<COPYRIGHT_HOLDER>`
> placeholder must be replaced with the actual copyright holder before
> distribution. The same placeholder appears in `LICENSE`.

If you use this code or its patterns in academic work, a citation hint
(replace the bracketed fields):

    <COPYRIGHT_HOLDER>. r9_pod_a_pipeline: HPC datacenter power
    analysis and reduction-selection toolchain. 2026.
    [URL once published]

## Provenance

This codebase was built in an agentic session whose plans, verbatim
user prompts, AskQuestion clarifications, distilled per-phase
decisions, and visible assistant responses are all captured under
[`provenance/`](provenance/). That directory is useful as a transparency
record for derivative work and as a worked example of how a six-phase,
~24-prompt session translates into a tracked, reviewable codebase. Start
at [`provenance/TIMELINE.md`](provenance/TIMELINE.md).

## Maintenance

Update this file in the same commit when:

- a new pipeline stage or standalone tool lands -- update **What you
  get** and **Reusable building blocks**;
- a capability is removed or deprecated -- same;
- a schema or external interface assumption changes -- update **Data
  assumptions**;
- a new design pattern emerges that is worth lifting -- update
  **Patterns demonstrated**;
- license or copyright holder changes -- update **License and
  attribution** AND the [`LICENSE`](LICENSE) file in the same commit;
- the **Adaptation guide** gains a new common fork -- add a row.

When you do update, bump the date below.

Last updated: 2026-05-02
