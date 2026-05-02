# AGENT_INSTRUCTIONS

This file is the source-of-truth context for any agent or human picking up
work on the row-9 / pod-A power analysis. The original spec is preserved
verbatim in [Original spec](#original-spec). Everything above that section
captures what we have learned about the data, the existing implementations,
and how to extend the work.

---

## Current status (as of May 1, 2026)

All three tasks in the [original spec](#original-spec) have a working,
spec-compliant implementation in `**../r9_pod_a_pipeline/**` at the repo
root. A live smoke run produced:


| Artifact                                  | Result                                                                             |
| ----------------------------------------- | ---------------------------------------------------------------------------------- |
| `output/dcim_nodes.csv`                   | 3,089 rows (matches `SELECT COUNT(*) FROM public.dcim_nodes`)                      |
| `output/host_sensor_map.csv`              | 436 hosts in row 09 / pod A with power data; 187 compute nodes had none            |
| `output/timeseries/cabinet_NN/<host>.csv` | 28 cabinets, 436 per-host CSVs, 215,809 rows total at 10-min buckets               |
| `output/node_stats.csv`                   | per-host min / avg / max / sample_count for the 436 hosts                          |
| `output/cabinet_power_bars.png`           | 28 cabinets x 4 bars (instantaneous min / avg / instantaneous max / potential max) |


Sums across all 28 cabinets in the smoke run:
`inst_min = 88.9 kW, avg = 434.1 kW, inst_max = 634.3 kW, pot_max = 799.7 kW`.

Sensor breakdown for those 436 hosts:
`instantaneous_power_reading = 409, pwr_consumption = 7, sys_power = 20`.

### Opt-in downstream: reduction-node selection

`r9_pod_a_pipeline/pipeline/select_reduction_nodes.py` (run via
`run_pipeline.py --with-reduction` or standalone) randomly picks nodes per
cabinet whose **at-original-peak** power sums to >=`--reduction-fraction`
(default `0.4`) of the cabinet's instantaneous-max bar, while keeping every
Slurm partition in `scontrol_show_node.json` above its floor (>=2 nodes
remaining; >=1 if the partition only had 1 node). Up to `--max-attempts`
(default 100) seeded shuffles; first feasible wins, otherwise the
lowest-violation attempt is kept and the shortfalls are written to
`partition_violations.csv` with a stdout warning.

**Important semantic detail**: the at-peak total drops by exactly the
target fraction, but the recomputed instantaneous max -- `max_t (T(t) -
sum_h power(h, t))` over the remaining hosts -- can drop by less if a
secondary peak is nearly as high as the original. Both numbers are written
to `output/selection_summary.csv`. The fifth bar in
`output/cabinet_power_bars_with_reduction.png` shows the recomputed new
max so the difference is visible. This is the same semantics as the legacy
`telegraf_data/select_nodes.py` -- the user picked it deliberately over a
true peak-shaving algorithm.

Outputs (under `r9_pod_a_pipeline/output/`):
`selected_nodes.csv`, `selection_summary.csv`, `partition_violations.csv`,
`selection_summary_by_partition.csv` (per-partition `nodes / cpus / gpus`
with compact `_pre / _rm / _post` suffixes; GPUs broken out by accelerator
type from `scontrol_show_node.json`; only partitions that lose >=1 node
appear by default -- pass `--include-untouched` to keep all 164;
auto-generated alongside the other CSVs and also runnable standalone via
`pipeline/summarize_by_partition.py`),
`cabinet_power_bars_with_reduction.png`.

### Self-contained snapshot of `scontrol_show_node.json`

As of May 2 2026 the `r9_pod_a_pipeline/` repo ships a gzipped copy of
this directory's `scontrol_show_node.json` at
`r9_pod_a_pipeline/data/scontrol_show_node.json.gz` (~86 KB compressed;
~46x compression of the 4 MB original). The pipeline's gzip-aware loader
accepts either `.json` or `.json.gz`. Live code paths in
`r9_pod_a_pipeline/` no longer reach into `telegraf_data/`. If you
refresh this directory's `scontrol_show_node.json` you should also
re-gzip it into the repo (`gzip -9 -c <path>/scontrol_show_node.json >
r9_pod_a_pipeline/data/scontrol_show_node.json.gz`) so the snapshot
stays current.

### New canonical plots (May 2 2026)

The repo gained two new plot stages:
`r9_pod_a_pipeline/pipeline/plot_cumulative_power.py` (per-host
min/median/max sorted independently and cumulated) and
`r9_pod_a_pipeline/pipeline/plot_stacked_power.py` (total power over
time, stacked by cabinet). They are wired into `run_pipeline.py` Step
3 alongside the existing `plot_cabinet_bars.py`. The cumulative plot
relies on a new `median_power` column in `node_stats.csv`; the SQL in
`r9_pod_a_pipeline/sql/04_node_stats.sql` was extended additively
(existing columns unchanged).

There is **also** an older, partial implementation right here in
`telegraf_data/` (`query_pg.py`, `plot_cabinet_bars.py`, etc.). It predates
this spec and **does not** implement the `sys_power`-authoritative rule, does
not export `pod`, and excludes cabinets `01` / `31`. Treat it as legacy: read
it for reference, do not extend it. Build on `r9_pod_a_pipeline/` going
forward.

---

## Two implementations -- which one to use


| Path                                                                                          | Status                | When to use                                                                                                                   |
| --------------------------------------------------------------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `../r9_pod_a_pipeline/`                                                                       | spec-compliant, fresh | All new work. Documented in its own `README.md` and `DESIGN.md`.                                                              |
| `telegraf_data/query_pg.py`, `telegraf_data/plot_cabinet_bars*.py`, `telegraf_data/get_*.sql` | legacy, partial       | Read-only reference. Has a DuckDB cache, masking variants, and per-partition split that the new pipeline intentionally drops. |


Do not "merge" the two; the bar-plot semantics and sensor handling are
different on purpose.

---

## Database access (verified working)

SSH tunnel must be open on `127.0.0.1:5433` before any query runs. The
project's `commands` file documents:

```
ssh perfdb        # opens the tunnel
PGPASSWORD=orcd_rw psql -h 127.0.0.1 -p 5433 -U readonly_user -d timedb
```

Quick check that the tunnel is up:

```
lsof -iTCP:5433 -sTCP:LISTEN
```

Connection settings in `r9_pod_a_pipeline/config.py`:
`host=127.0.0.1, port=5433, user=readonly_user, dbname=timedb`. The password
is read from `PGPASSWORD`; do not hard-code it.

The legacy `telegraf_data/query_pg.py` uses `user=postgres` instead. Both
users work against the tunnel; `readonly_user` is preferred for any query
that should be safe.

---

## Confirmed schema details

### `public.dcim_nodes`

Columns used by the pipeline:


| Column           | Notes                                                                   |
| ---------------- | ----------------------------------------------------------------------- |
| `node_name`      | dcim's idea of the node name. May contain a dash, e.g. `nodeXXXX-YYYY`. |
| `row_number`     | string like `'09'` (zero-padded).                                       |
| `pod`            | single letter, e.g. `'A'`.                                              |
| `cabinet_number` | string like `'02'` (zero-padded). Used as `rack` downstream.            |


Total rows: **3,089** (verified by direct count).

Two name irregularities are the source of most pipeline complexity:

1. **Dashed names**: `dcim_nodes.node_name = 'nodeXXXX-YYYY'` corresponds to
  `telegraf.ipmi_sensor.host = 'nodeXXXX'`. Join with
   `split_part(node_name, '-', 1) = i.host` -- this also handles undashed
   names correctly because `split_part` returns the whole string when the
   delimiter is absent.
2. `**-chassis` rows**: `dcim_nodes` contains rows ending in `-chassis` that
  have no telegraf counterpart. Filter with
   `node_name NOT LIKE '%-chassis'`.

### `telegraf.ipmi_sensor`

Time-series readings, one row per (host, sensor name, timestamp). Columns
used:


| Column  | Notes                                                |
| ------- | ---------------------------------------------------- |
| `time`  | timestamptz                                          |
| `host`  | matches `split_part(dcim_nodes.node_name, '-', 1)`   |
| `name`  | sensor name                                          |
| `value` | numeric reading; for power sensors the unit is watts |


Power sensors of interest, in priority order:

1. `sys_power` -- authoritative when present
2. `instantaneous_power_reading`
3. `pwr_consumption`

In the row 09 / pod A sample, only 20 hosts (out of 436 with any power
data) report `sys_power`, but for those 20 hosts it overrides
`instantaneous_power_reading`. The priority is encoded once in
`r9_pod_a_pipeline/sql/02_host_sensor_map.sql` via a `bool_or` `CASE`.

### `scontrol_show_node.json`

Slurm `scontrol show nodes` JSON dump (~4 MB). 1,404 nodes, 164 partitions.
Used by the legacy `telegraf_data/partition_nodes.py` to split nodes by
partition. The new pipeline does not consume it -- mention only because the
file is a useful sanity-check for which nodes are actually in service.

---

## Defaults the new pipeline uses

In `r9_pod_a_pipeline/config.py`:


| Setting           | Default                                                         | CLI flag                  |
| ----------------- | --------------------------------------------------------------- | ------------------------- |
| Row               | `09`                                                            | `--row`                   |
| Pod               | `A`                                                             | `--pod`                   |
| Time window start | `2026-04-22T17:27:22.547Z`                                      | `--start`                 |
| Time window end   | `2026-05-30T17:27:22.547Z`                                      | `--end`                   |
| Time bucket       | `10m` (timescaledb interval)                                    | `--bucket`                |
| Output dir        | `r9_pod_a_pipeline/output/`                                     | `--output-dir`            |
| Sensor priority   | `('sys_power','instantaneous_power_reading','pwr_consumption')` | not exposed (domain rule) |


The full month at 10-min buckets returns ~216k rows in ~13 s end-to-end on
a warm DB.

---

## Pipeline at a glance

```
PG (timedb)
 |-- 01_dcim_nodes.sql           --> output/dcim_nodes.csv
 |-- 02_host_sensor_map.sql      --> output/host_sensor_map.csv  (one row per host, with rack and preferred sensor)
 |     (encodes split_part rule + sys_power priority)
 |
 |-- 03_node_timeseries.sql      --> output/timeseries/cabinet_NN/<host>.csv  (10-min buckets)
 |     (joins on the (host, sensor) values list from host_sensor_map)
 |
 |-- 04_node_stats.sql           --> output/node_stats.csv  (per-host min/avg/max from raw samples)
 |
 +-- plot_cabinet_bars.py        --> output/cabinet_power_bars.png  (4 bars per cabinet)
```

Driver: `python run_pipeline.py --row 09 --pod A`. See
`r9_pod_a_pipeline/README.md` for per-step invocation.

---

## Bar plot semantics (read carefully -- this differs from the legacy code)

For each cabinet, with `T(t) = sum over hosts h in cabinet of power(h, t)`
(taken from the per-host bucketed CSVs):


| Bar               | Definition                                                                                                 |
| ----------------- | ---------------------------------------------------------------------------------------------------------- |
| Instantaneous min | `min over t of T(t)`                                                                                       |
| Average           | `mean over t of T(t)`                                                                                      |
| Instantaneous max | `max over t of T(t)`                                                                                       |
| Potential max     | `sum over h of max over t of power(h, t)` (per-host peaks need not be simultaneous; from `node_stats.csv`) |


The legacy `telegraf_data/plot_cabinet_bars.py` plots **sum of per-node
mins** and **sum of per-node means** for the first two bars, which is a
different number and **does not match the spec**. The new
`r9_pod_a_pipeline/pipeline/plot_cabinet_bars.py` is the one to trust.

---

## Pitfalls and gotchas (learned the hard way)

- **psycopg2 does not strip SQL comments before scanning for `%(name)s`
placeholders.** Writing `%(pairs)s` inside a `--` comment will raise
`KeyError: 'pairs'` at execute time. Either avoid the percent syntax in
comments or use `psycopg2.sql.SQL` composables.
- `**%` inside `LIKE` patterns must be doubled** when using psycopg2's
parameterized statements (e.g. `LIKE '%%-chassis'`). Already handled in
`02_host_sensor_map.sql`.
- **Mixing positional and named bind parameters in one call is unreliable.**
The pipeline renders the `(host, sensor)` VALUES clause with
`cursor.mogrify(...)` and then passes a single dict for the time-window
binds. Don't try to pass both at once.
- `**row_number` is also a SQL window function name.** When aliasing
`n.row_number AS row` in a `SELECT`, quote `"row"` only if a downstream
consumer needs that exact name. The pipeline currently emits a CSV header
of `row` (lowercase, unquoted in the CSV).
- **The PG tunnel can drop silently.** If a script hangs at connect, run
`lsof -iTCP:5433 -sTCP:LISTEN` and re-open with `ssh perfdb` if missing.
- **Cabinets `01` and `31` exist** in row 09 / pod A; do not exclude them.
The legacy `query_pg.py` does, the new pipeline does not.

---

## How to continue / extend the work

Common next steps and where to make the change:


| Goal                                             | What to edit                                                                                                                                                         |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Run for a different `(row, pod)`                 | `python run_pipeline.py --row XX --pod Y`. No code change.                                                                                                           |
| Change the time window                           | `--start` / `--end` flags, or update `DEFAULT_START` / `DEFAULT_END` in `r9_pod_a_pipeline/config.py`.                                                               |
| Change the time bucket                           | `--bucket 5m`, etc. Passed straight to `time_bucket(...)`.                                                                                                           |
| Add or reorder power sensors                     | Edit `SENSOR_PRIORITY` in `config.py` **and** the `IN (...)` list and `CASE` in `r9_pod_a_pipeline/sql/02_host_sensor_map.sql`.                                      |
| Different host-name irregularity (other cluster) | Change the `split_part` rule in `02_host_sensor_map.sql`. Everything downstream consumes the (host, sensor) tuples and stays generic.                                |
| Add a new chart                                  | Create a sibling under `r9_pod_a_pipeline/pipeline/`; it can read the existing CSVs without re-querying PG. Use `--skip-export` on the orchestrator while iterating. |
| Verify a single host against PG                  | Use `telegraf_data/example_node_ts_query.sql` as a template.                                                                                                         |
| Cross-check dcim CSV row count                   | `PGPASSWORD=orcd_rw psql ... -tAc 'SELECT COUNT(*) FROM public.dcim_nodes;'` should match `wc -l output/dcim_nodes.csv` minus 1 for the header.                      |


The pipeline reuses the venv at `telegraf_data/.venv/` (Python 3.14 with
`psycopg2`, `matplotlib`, `numpy`). If you would rather give
`r9_pod_a_pipeline/` its own venv, `r9_pod_a_pipeline/requirements.txt`
lists the three deps.

---

## Process note (for the four-role spec section below)

The original spec asks for four specialist subagents (DB expert, software
engineer, architect, docs). For this round, a single agent played all four
roles sequentially. Artifacts produced per role:


| Role              | Artifact                                                                                                                                |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| DB expert         | `r9_pod_a_pipeline/sql/01..04_*.sql`                                                                                                    |
| Software engineer | `r9_pod_a_pipeline/pipeline/*.py`, `r9_pod_a_pipeline/run_pipeline.py`, `r9_pod_a_pipeline/pg_client.py`, `r9_pod_a_pipeline/config.py` |
| Architect         | `r9_pod_a_pipeline/DESIGN.md`                                                                                                           |
| Docs              | `r9_pod_a_pipeline/README.md`                                                                                                           |


Future iterations are free to literally spawn subagents (one per role) if
the work needs parallelism or fresh perspectives. The artifact map above
is the natural division of labour.

---

## Original spec

> This project uses the following sources:
>
> ```
> public.dcim_nodes: a database table with names of computer nodes and their row, pod and rack location within a datacenter.
>
> telegraf.ipmi_sensor: a timeseries database table with readings from sensors
>                       the timeseries host names map to computer node names in public.dcim_nodes, but the match has some
>                       irregularities. Some computer nodes have names XXXX-YYYY where the timeseries "host" name is just XXXX.
>                       There are some XXXX-chassis names in computer nodes that are not in the timeseries db.
>                       The sensors of interest in the time series measue power use, they have different names
>                       pwr_consumption
>                       instantaneous_power_reading
>                       sys_power
>                       some hosts have both "sys_power" and "instantaneous_power_reading"
>                       for thise the "sys_power" value is the authoratative value
>
> scontrol_show_node.json: a file of JSON output from the Slurm command "scontrol show nodes" on the HPC cluster
> ```
>
> Tools:
>
>    the database can be accessed by
>        PGPASSWORD=orcd_rw psql -h 127.0.0.1 -p 5433 -U readonly_user -d timedb
>
>    there is a virutal environment .venv/ in which python tools can be found and that can be updated
>
> Project Tasks:
>    I want a set of python code written to a new git sub-directory.
>    The python codes should
>
> 1. get all the rows from public.dcim_nodes into a local CSV with values for
>  name of compute node
>  row
>  pod
>  rack
> 2. get all the sensor time series from nodes in row 9, pod A into a set of CSV files,
> one for each host that matches a node (following the macthing rules with irregularities)
> 3. write python code to produce a bar plot with 4 bars for each cabinet (aka rack).
> one bar should show the instantaneous minimum power for the cabinet, one should show the average power,
> one should show the instantaneous max power, one should show the "potential" max power - which is
> the sum of the per computer max for all the computers in that rack - not all at the same time.
>
> Process:
>   Create several agents.
>
> 1. a database expert agent who will develop queries for the database
> 2. a very experienced software engineer who will develop python to execute the database queries and write CSVs in a
> logical structure
> 3. a system architect who will review the way in which the code is orchestrated and what items are paramterized
> so that the code can be applied to different problems.
> 4. a documentation expert who will write clear explanations of how the code works so that an agent or a human
> can check the approach

