# r9_pod_a_pipeline

Spec-compliant power-analysis pipeline for the row 9 / pod A section of the
HPC cluster. Implements the three tasks in
[`telegraf_data/AGENT_INSTRUCTIONS.md`](../telegraf_data/AGENT_INSTRUCTIONS.md):
dump the dcim node inventory, pull per-host power time-series for a chosen
`(row, pod)`, and plot four bars per cabinet (instantaneous min / average /
instantaneous max / potential max).

For the why and how, see [`DESIGN.md`](DESIGN.md).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The pipeline talks to PostgreSQL via the SSH tunnel that the rest of this
repo uses. Set the password before running:

```bash
export PGPASSWORD='your_password'
```

Connection settings (`127.0.0.1:5433`, user `readonly_user`, db `timedb`) live in
`config.py`.

## Quickstart

```bash
python run_pipeline.py --row 09 --pod A
```

This runs all four export steps and the plot. To re-render only the plot
from already-exported CSVs:

```bash
python run_pipeline.py --skip-export
```

Each step is also runnable on its own; for example:

```bash
python pipeline/export_dcim_nodes.py
python pipeline/export_host_sensor_map.py --row 09 --pod A
python pipeline/export_timeseries.py     --row 09 --pod A --bucket 10m
python pipeline/export_node_stats.py     --row 09 --pod A
python pipeline/plot_cabinet_bars.py     --row 09 --pod A
```

CLI flags accepted by every script: `--row`, `--pod`, `--start`, `--end`,
`--bucket`, `--output-dir`. Defaults are in `config.py`.

## Output layout

```text
output/
  dcim_nodes.csv            # all dcim_nodes rows: name,row,pod,rack
  host_sensor_map.csv       # host,rack,preferred_sensor
  node_stats.csv            # host,min_power,avg_power,max_power,sample_count
  timeseries/
    cabinet_02/
      node3000.csv          # time,power_watts (10-minute buckets)
      node3001.csv
      ...
    cabinet_03/
      ...
  cabinet_power_bars.png    # final plot
```

## How the four bars are computed

For each cabinet, with `T(t) = sum over hosts h in cabinet of power(h, t)`
(taken from the per-host bucketed CSVs):

| Bar | Definition |
| --- | --- |
| Instantaneous min | `min over t of T(t)` |
| Average | `mean over t of T(t)` |
| Instantaneous max | `max over t of T(t)` |
| Potential max | `sum over h of max over t of power(h, t)` (from `node_stats.csv`; per-host peaks need not be simultaneous) |

## Known data irregularities (handled in `sql/02_host_sensor_map.sql`)

* dcim node `XXXX-YYYY` is reported in telegraf as host `XXXX` -- joined via
  `split_part(node_name, '-', 1)`.
* `*-chassis` rows in `dcim_nodes` have no telegraf counterpart -- excluded.
* When a host reports both `sys_power` and `instantaneous_power_reading`,
  `sys_power` wins. Priority order:
  `sys_power > instantaneous_power_reading > pwr_consumption`.

## Verification

After a run, sanity checks worth doing:

1. Row count of `dcim_nodes.csv` should match `psql` directly:
   ```bash
   PGPASSWORD=$PGPASSWORD psql -h 127.0.0.1 -p 5433 -U postgres -d timedb \
       -tAc 'SELECT COUNT(*) FROM public.dcim_nodes;'
   wc -l output/dcim_nodes.csv  # should be one more (header)
   ```
2. `host_sensor_map.csv` should show `sys_power` for every host that has it.
   Spot-check with:
   ```bash
   PGPASSWORD=$PGPASSWORD psql -h 127.0.0.1 -p 5433 -U postgres -d timedb \
       -tAc "SELECT DISTINCT host FROM telegraf.ipmi_sensor
             WHERE name='sys_power' LIMIT 5;"
   ```
   Each of those hosts (if in row 9 pod A) should have `sys_power` in the CSV.
3. A per-host CSV under `timeseries/` can be cross-checked against the
   single-node example query
   [`telegraf_data/example_node_ts_query.sql`](../telegraf_data/example_node_ts_query.sql).
4. The legend on `cabinet_power_bars.png` should show four bars per cabinet
   in the order min / avg / max / potential.

## Reduction selection (downstream, opt-in)

The pipeline can also pick a random set of nodes whose at-peak power sums to
at least 40% of each cabinet's instantaneous-max bar, while keeping every
Slurm partition above its floor (>=2 nodes remaining; >=1 if the partition
only had 1 node to start with). Membership comes from
[`telegraf_data/scontrol_show_node.json`](../telegraf_data/scontrol_show_node.json).

Quickstart (re-uses already-exported CSVs):

```bash
python run_pipeline.py --skip-export --with-reduction
```

Standalone equivalent:

```bash
python pipeline/select_reduction_nodes.py --reduction-fraction 0.4
python pipeline/plot_cabinet_bars_with_reduction.py --row 09 --pod A
```

Flags (in addition to the common ones):

| Flag | Default | Meaning |
| --- | --- | --- |
| `--with-reduction` | off | enables the two extra steps in `run_pipeline.py` |
| `--reduction-fraction` | `0.4` | per-cabinet target: cumulative removed power at the cabinet's peak time must reach this fraction of the peak total |
| `--max-attempts` | `100` | seeded shuffle attempts; the first attempt with zero partition violations wins |
| `--seed-base` | `0` | attempt `i` uses `random.Random(seed_base + i)` |
| `--scontrol-json` | `../telegraf_data/scontrol_show_node.json` | path to the Slurm `scontrol show nodes` JSON dump |

If no attempt is fully feasible, the script keeps the attempt with the
fewest partition violations (tiebreaker: smallest total deficit) and writes
the shortfalls to `output/partition_violations.csv` along with a warning
on stdout.

### Selection semantics (matches `[telegraf_data/select_nodes.py](../telegraf_data/select_nodes.py)`)

For each cabinet:

1. `peak_time` = timestamp at which the cabinet-wide total `T(t)` is highest.
2. `host_power_at_peak[h]` = each host's reading at that one timestamp.
3. Shuffle the hosts and add them to the selection one by one, accumulating
   `host_power_at_peak`, until cumulative >= `reduction_fraction *
   T(peak_time)`.

This means the **at-peak** total drops by exactly the target fraction (by
construction). The **recomputed instantaneous max** -- `max_t (T(t) - sum_{h
in selected} power(h, t))` -- may drop by less if there is a near-equal
secondary peak at a different timestamp. Both numbers are written to
`selection_summary.csv`, and the with-reduction plot shows the recomputed
new max as its fifth bar.

### Reduction outputs

```text
output/
  selected_nodes.csv                       # per-host: cabinet, host, peak_time, host_power_at_peak_w, ...
  selection_summary.csv                    # per-cabinet: peak_total_kw, removed_at_peak_kw, achieved_fraction, recomputed_new_inst_max_kw
  partition_violations.csv                 # partition, partition_size, n_removed, n_remaining, floor, deficit (header-only when feasible)
  selection_summary_by_partition.csv       # per-partition (only those losing a node): nodes/cpus/gpus _pre/_rm/_post triplets, GPUs broken out by type
  cabinet_power_bars_with_reduction.png    # 5 bars per cabinet (the original 4 + "after reduction")
```

`selection_summary_by_partition.csv` is generated automatically by
`select_reduction_nodes.py` (it joins the chosen `selected_nodes.csv` with
`scontrol_show_node.json`). By default only partitions that lose at least
one node appear; pass `--include-untouched` to keep every partition for a
full picture. Column suffixes are compact (`_pre / _rm / _post`) and
per-type GPU columns drop the `gpus_` prefix (`a100_pre, h100_rm, ...`)
so the table fits in `csvlens`. Standalone re-run:

```bash
python pipeline/summarize_by_partition.py \
    --selected-csv output/selected_nodes.csv \
    --scontrol-json ../telegraf_data/scontrol_show_node.json \
    --output output/selection_summary_by_partition.csv \
    [--include-untouched]
```

### Slurm reservation command

`make_reservation.py` is a standalone helper (no DB or pipeline dependency)
that turns `output/selected_nodes.csv` into a single
`scontrol create reservation ...` command with `Flags=MAINT,IGNORE_JOBS`
covering every distinct host in the CSV.

Defaults match the example reduction window (2026-05-10 09:00 to 2026-05-17
09:00). The auto-generated reservation name embeds the start time and host
count so it stays unique per window: `temp_power_reduce_20260510_0900_<N>`.

```bash
# Print the command (defaults: 2026-05-10T09:00 to 2026-05-17T09:00, User=root):
python make_reservation.py

# Custom window and user, also write an executable script:
python make_reservation.py \
    --start 2026-06-01T09:00 --end 2026-06-08T09:00 \
    --user slurm-admin \
    --output-script output/reservation.sh
```

| Flag | Default | Notes |
| --- | --- | --- |
| `--start` | `2026-05-10T09:00` | ISO 8601 date+time |
| `--end` | `2026-05-17T09:00` | ISO 8601 date+time; must be strictly after `--start` |
| `--selected-csv` | `output/selected_nodes.csv` | input |
| `--name` | auto: `temp_power_reduce_<YYYYMMDD>_<HHMM>_<host_count>` | full override |
| `--user` | `root` | Slurm requires `User=` (or `Accounts=`) on a reservation |
| `--output-script` | (none) | optional path to write an executable `sh` script wrapping the command |

## Session provenance

The `provenance/` subdirectory captures the entire agentic session that
produced this code: the original spec, every formal plan verbatim, every
verbatim user prompt, every visible assistant response, the AskQuestion
clarifications and user selections, plus distilled per-phase decisions
and narratives. Start at [`provenance/TIMELINE.md`](provenance/TIMELINE.md)
or [`provenance/README.md`](provenance/README.md) for navigation.
