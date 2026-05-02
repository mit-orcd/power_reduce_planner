# Design notes (architect role)

> Session provenance (plans, prompts, decisions, narrative for every phase
> that produced this code) lives under [`provenance/`](provenance/);
> start at [`provenance/TIMELINE.md`](provenance/TIMELINE.md).

## What the pipeline produces

For a given `(row, pod)` selection of compute nodes in the datacenter, the
pipeline emits five artifacts under `output/`:


| Artifact                           | Producer                    | Shape                                                                       |
| ---------------------------------- | --------------------------- | --------------------------------------------------------------------------- |
| `dcim_nodes.csv`                   | `export_dcim_nodes.py`      | every dcim row: `name,row,pod,rack`                                         |
| `host_sensor_map.csv`              | `export_host_sensor_map.py` | one row per compute node host with power data: `host,rack,preferred_sensor` |
| `timeseries/cabinet_NN/<host>.csv` | `export_timeseries.py`      | `time,power_watts` rows, one CSV per host                                   |
| `node_stats.csv`                   | `export_node_stats.py`      | per-host `min/avg/max` of raw samples                                       |
| `cabinet_power_bars.png`           | `plot_cabinet_bars.py`      | 4-bars-per-cabinet PNG                                                      |


Opt-in downstream artifacts (when `--with-reduction` is set):


| Artifact                                | Producer                              | Shape                                                                                                                                          |
| --------------------------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `selected_nodes.csv`                    | `select_reduction_nodes.py`           | per-host: `cabinet,host,peak_time,host_power_at_peak_w,cabinet_peak_total_w,achieved_fraction,target_fraction,attempt_seed,attempt_violations` |
| `selection_summary.csv`                 | `select_reduction_nodes.py`           | per-cabinet: `peak_total_kw,n_selected,removed_at_peak_kw,achieved_fraction,recomputed_new_inst_max_kw`                                        |
| `partition_violations.csv`              | `select_reduction_nodes.py`           | per-violating-partition: `partition,partition_size,n_removed,n_remaining,floor,deficit` (header-only when feasible)                            |
| `selection_summary_by_partition.csv`    | `summarize_by_partition.py` (auto-chained from `select_reduction_nodes.py`) | per-partition wide CSV (only partitions that lose a node, unless `--include-untouched`): `partition` plus `nodes / cpus / gpus / <gpu_type>` triplets with compact suffixes `_pre, _rm, _post`. GPU types enumerated from scontrol JSON. |
| `cabinet_power_bars_with_reduction.png` | `plot_cabinet_bars_with_reduction.py` | 5-bars-per-cabinet PNG (the original 4 plus "inst max after reduction")                                                                        |


## Data flow

~~~mermaid
flowchart TD
    PG[("PostgreSQL timedb")]
    PG -->|"01_dcim_nodes.sql"| DCIM["output/dcim_nodes.csv"]
    PG -->|"02_host_sensor_map.sql (row, pod)"| MAP["output/host_sensor_map.csv"]
    MAP --> TS_STEP["export_timeseries.py"]
    PG -->|"03_node_timeseries.sql"| TS_STEP
    TS_STEP --> TSCSV["output/timeseries/cabinet_NN/host.csv"]
    MAP --> STATS_STEP["export_node_stats.py"]
    PG -->|"04_node_stats.sql"| STATS_STEP
    STATS_STEP --> NSCSV["output/node_stats.csv"]
    TSCSV --> PLOT["plot_cabinet_bars.py"]
    NSCSV --> PLOT
    PLOT --> PNG["output/cabinet_power_bars.png"]
    TSCSV --> SEL["select_reduction_nodes.py"]
    SCONTROL["telegraf_data/scontrol_show_node.json"] --> SEL
    SEL --> SELOUT["output/selected_nodes.csv"]
    SEL --> SUMMARY["output/selection_summary.csv"]
    SEL --> VIOL["output/partition_violations.csv"]
    SELOUT --> BYPART["summarize_by_partition.py"]
    SCONTROL --> BYPART
    BYPART --> BYPARTOUT["output/selection_summary_by_partition.csv"]
    TSCSV --> PLOT2["plot_cabinet_bars_with_reduction.py"]
    NSCSV --> PLOT2
    SELOUT --> PLOT2
    PLOT2 --> PNG2["output/cabinet_power_bars_with_reduction.png"]
~~~



## Parameter surface

Everything below is exposed by `add_common_args()` in `config.py` and accepted
by every script and the orchestrator:


| Flag           | Default                    | Used by                                         |
| -------------- | -------------------------- | ----------------------------------------------- |
| `--row`        | `09`                       | `02_host_sensor_map.sql`, plot title            |
| `--pod`        | `A`                        | `02_host_sensor_map.sql`, plot title            |
| `--start`      | `2026-04-22T17:27:22.547Z` | every SQL with a time window                    |
| `--end`        | `2026-05-30T17:27:22.547Z` | every SQL with a time window                    |
| `--bucket`     | `10m`                      | `03_node_timeseries.sql` (timescaledb interval) |
| `--output-dir` | `r9_pod_a_pipeline/output` | every script                                    |


Plus, on `run_pipeline.py` only, `--skip-export` for re-rendering the plot
from an already-populated `output/`.

The downstream reduction step adds these (in `select_reduction_nodes.py`,
also accepted by `run_pipeline.py` when `--with-reduction` is set):


| Flag                   | Default                                    | Used by                                                                      |
| ---------------------- | ------------------------------------------ | ---------------------------------------------------------------------------- |
| `--with-reduction`     | off                                        | `run_pipeline.py` toggle for the two extra steps                             |
| `--reduction-fraction` | `0.4`                                      | per-cabinet at-peak-power removal target                                     |
| `--max-attempts`       | `100`                                      | seeded shuffle budget; the first attempt with zero partition violations wins |
| `--seed-base`          | `0`                                        | attempt `i` uses `random.Random(seed_base + i)`                              |
| `--scontrol-json`      | `../telegraf_data/scontrol_show_node.json` | source of partition membership                                               |


### Intentionally NOT a CLI flag

The sensor priority list (`sys_power > instantaneous_power_reading > pwr_consumption`) lives in `config.SENSOR_PRIORITY` and in the `CASE` of
`02_host_sensor_map.sql`. It is a domain rule (the spec calls `sys_power`
"authoritative"), not a tuning knob, so changing it is a code edit and a SQL
edit, by design.

## Where the irregularities are handled

Both quirks the spec calls out are confined to **one place**:
`sql/02_host_sensor_map.sql`.

- `**-chassis` rows in dcim have no telegraf counterpart.** Filtered with
`node_name NOT LIKE '%-chassis'`.
- **dcim node `XXXX-YYYY` matches telegraf host `XXXX`.** Joined via
`split_part(node_name, '-', 1) = i.host`. Nodes without a dash join trivially
because `split_part` returns the whole string.

Downstream scripts only see the cleaned `(host, rack, preferred_sensor)`
tuples, so they never have to know about the irregularities again.

## What was reused vs. rewritten

The starting point was `[telegraf_data/query_pg.py](../telegraf_data/query_pg.py)`
and friends. Patterns kept:

- `psycopg2` connection convention, `PGPASSWORD` env var.
- `split_part(node_name, '-', 1) = i.host` host-name match.
- Per-cabinet batching of the time-series query to keep result sets bounded.
- Per-host CSV layout under `cabinet_NN/`.

Rewritten / added because of spec gaps:

- `sys_power` was not in the old query at all -> new `02_host_sensor_map.sql`
encodes the priority and injects the chosen sensor into the time-series
query, instead of hard-coding `IN (...)` everywhere.
- Old code dropped cabinets `01` / `31`. New pipeline includes every cabinet
the SQL returns; the spec asks for "all of row 9 pod A".
- Old DuckDB cache removed -- the spec deliverables are CSVs.
- Bar plot semantics changed. The old `plot_cabinet_bars.py` plotted **sum of
per-node mins** and **sum of per-node means** as the first two bars. The
spec asks for **instantaneous** min and the **average** of the cabinet-wide
total, which are different numbers. The new plot computes the cabinet total
per time bucket and then takes min / mean / max of that series.

## Extending to other rows / pods / clusters

- `--row` / `--pod` are pure parameters; swap them and re-run.
- For other Slurm clusters that name nodes differently, edit
`sql/02_host_sensor_map.sql`'s `split_part` rule -- everything else is
generic.
- For other sensors entirely (e.g. inlet temperature), copy
`02_host_sensor_map.sql` and change the `IN (...)` list and `CASE`.

## Reduction-selection semantics: at-peak vs. true new max

`select_reduction_nodes.py` matches `[telegraf_data/select_nodes.py](../telegraf_data/select_nodes.py)`'s
"at-original-peak" criterion: for each cabinet, it picks a random subset of
hosts whose summed power **at the cabinet's original peak time** reaches
`reduction_fraction * peak_total`. By construction the at-peak total drops
by exactly that fraction.

The recomputed instantaneous max -- `max_t (T(t) - sum_{h in selected} power(h, t))` -- can drop by **less** than the target fraction if a
secondary peak at a different timestamp was nearly as high as the original
peak. The pipeline does not try to chase a true 40% drop in the recomputed
max because the spec explicitly asks for the at-peak interpretation. Both
numbers are written to `selection_summary.csv` (`removed_at_peak_kw` vs.
`recomputed_new_inst_max_kw`) and both are visible side-by-side in
`cabinet_power_bars_with_reduction.png` (the third "Instantaneous max" bar
vs. the fifth "Instantaneous max after reduction" bar).

The partition-floor check is **global** across all cabinets: every Slurm
partition in `scontrol_show_node.json` must keep `>=2` nodes (or `>=1` if
the partition has only one). Nodes outside row 9 / pod A and nodes in row 9
/ pod A without power data are not removable, so they always count toward
"remaining". An attempt is feasible iff every partition stays at or above
its floor; up to `--max-attempts` (default 100) seeded shuffles are tried,
and the lowest-violation attempt is kept if none is feasible.