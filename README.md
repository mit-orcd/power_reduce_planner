# r9_pod_a_pipeline

> **New here?** Start with [`AGENTS.md`](AGENTS.md) for project purpose,
> the navigation map to every other document, and the authoring rules.

Spec-compliant power-analysis pipeline for the row 9 / pod A section of the
HPC cluster. Implements the three tasks in
[`telegraf_data/AGENT_INSTRUCTIONS.md`](../telegraf_data/AGENT_INSTRUCTIONS.md):
dump the dcim node inventory, pull per-host power time-series for a chosen
`(row, pod)`, and plot four bars per cabinet (instantaneous min / average /
instantaneous max / potential max).

For the why and how, see [`DESIGN.md`](DESIGN.md). For markdown / Mermaid
authoring rules used in this repo, see [`AGENTS.md`](AGENTS.md).

## Setup

Set up a virtualenv and install the deps:

    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

The pipeline talks to PostgreSQL via the SSH tunnel that the rest of this
repo uses. Set the password before running:

    export PGPASSWORD='your_password'

Connection settings (`127.0.0.1:5433`, user `readonly_user`, db `timedb`)
live in `config.py`.

## Quickstart

Run the whole pipeline:

    python run_pipeline.py --row 09 --pod A

Re-render only the plot from already-exported CSVs (no DB round-trip):

    python run_pipeline.py --skip-export

Each step is also runnable on its own:

    python pipeline/export_dcim_nodes.py
    python pipeline/export_host_sensor_map.py --row 09 --pod A
    python pipeline/export_timeseries.py     --row 09 --pod A --bucket 10m
    python pipeline/export_node_stats.py     --row 09 --pod A
    python pipeline/plot_cabinet_bars.py     --row 09 --pod A

CLI flags accepted by every script: `--row`, `--pod`, `--start`, `--end`,
`--bucket`, `--output-dir`. Defaults are in `config.py`.

## Output layout

    output/
        dcim_nodes.csv
        host_sensor_map.csv
        node_stats.csv
        timeseries/
            cabinet_02/
                node3000.csv
                node3001.csv
            cabinet_03/
        cabinet_power_bars.png
        cumulative_power.png
        stacked_power.png

`dcim_nodes.csv` has columns `name, row, pod, rack`. `host_sensor_map.csv`
has `host, rack, preferred_sensor`. `node_stats.csv` has `host,
min_power, avg_power, median_power, max_power, sample_count`. Each
per-host CSV under `timeseries/cabinet_NN/` has `time, power_watts` at
10-minute buckets. The canonical run produces three plots: the
4-bar-per-cabinet `cabinet_power_bars.png`, the
independently-sorted-cumulative `cumulative_power.png`, and the
per-cabinet stacked-area `stacked_power.png`.

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

* dcim node `XXXX-YYYY` is reported in telegraf as host `XXXX` -- joined
  via `split_part(node_name, '-', 1)`.
* `*-chassis` rows in `dcim_nodes` have no telegraf counterpart -- excluded.
* When a host reports both `sys_power` and `instantaneous_power_reading`,
  `sys_power` wins. Priority order:
  `sys_power > instantaneous_power_reading > pwr_consumption`.

## Verification

After a run, sanity checks worth doing.

**Row count of `dcim_nodes.csv` should match `psql` directly:**

    PGPASSWORD=$PGPASSWORD psql -h 127.0.0.1 -p 5433 -U readonly_user -d timedb \
        -tAc 'SELECT COUNT(*) FROM public.dcim_nodes;'
    wc -l output/dcim_nodes.csv

The `wc -l` count should be one more than the `psql` count (the extra
line is the CSV header).

**`host_sensor_map.csv` should show `sys_power` for every host that has it.**
Spot-check with:

    PGPASSWORD=$PGPASSWORD psql -h 127.0.0.1 -p 5433 -U readonly_user -d timedb \
        -tAc "SELECT DISTINCT host FROM telegraf.ipmi_sensor WHERE name='sys_power' LIMIT 5;"

Each of those hosts (if in row 9 pod A) should have `sys_power` in the CSV.

A per-host CSV under `timeseries/` can also be cross-checked against the
single-node example query
[`telegraf_data/example_node_ts_query.sql`](../telegraf_data/example_node_ts_query.sql).
The legend on `cabinet_power_bars.png` should show four bars per cabinet
in the order min / avg / max / potential.

**The bundled `data/scontrol_show_node.json.gz` round-trips cleanly:**

    gunzip -c data/scontrol_show_node.json.gz | python -c \
        "import json, sys; d = json.load(sys.stdin); print(len(d['nodes']))"

should print `1404` (the node count in the snapshot). The gzip-aware
loader inside `pipeline/select_reduction_nodes.py` and
`pipeline/summarize_by_partition.py` accepts either `.json` or
`.json.gz` -- a developer who wants a hand-editable copy can `gunzip
data/scontrol_show_node.json.gz` and the loader keeps working without
code changes.

## Reduction selection (downstream, opt-in)

The pipeline can also pick a random set of nodes whose at-peak power sums
to at least 40% of each cabinet's instantaneous-max bar, while keeping
every Slurm partition above its floor (>=2 nodes remaining; >=1 if the
partition only had 1 node to start with). Membership comes from
[`telegraf_data/scontrol_show_node.json`](../telegraf_data/scontrol_show_node.json).

Quickstart (re-uses already-exported CSVs):

    python run_pipeline.py --skip-export --with-reduction

Standalone equivalent:

    python pipeline/select_reduction_nodes.py --reduction-fraction 0.4
    python pipeline/plot_cabinet_bars_with_reduction.py --row 09 --pod A

Flags (in addition to the common ones):

| Flag | Default | Meaning |
| --- | --- | --- |
| `--with-reduction` | off | enables the two extra steps in `run_pipeline.py` |
| `--reduction-fraction` | `0.4` | per-cabinet target: cumulative removed power at the cabinet's peak time must reach this fraction of the peak total |
| `--max-attempts` | `100` | seeded shuffle attempts; the first attempt with zero partition violations wins |
| `--seed-base` | `0` | attempt `i` uses `random.Random(seed_base + i)` |
| `--scontrol-json` | `../telegraf_data/scontrol_show_node.json` | path to the Slurm `scontrol show nodes` JSON dump |

If no attempt is fully feasible, the script keeps the attempt with the
fewest partition violations (tiebreaker: smallest total deficit) and
writes the shortfalls to `output/partition_violations.csv` along with a
warning on stdout.

### Selection semantics (matches `[telegraf_data/select_nodes.py](../telegraf_data/select_nodes.py)`)

For each cabinet:

1. `peak_time` = timestamp at which the cabinet-wide total `T(t)` is
   highest.
2. `host_power_at_peak[h]` = each host's reading at that one timestamp.
3. Shuffle the hosts and add them to the selection one by one,
   accumulating `host_power_at_peak`, until cumulative >=
   `reduction_fraction * T(peak_time)`.

This means the **at-peak** total drops by exactly the target fraction
(by construction). The **recomputed instantaneous max** -- `max_t (T(t)
- sum_{h in selected} power(h, t))` -- may drop by less if there is a
near-equal secondary peak at a different timestamp. Both numbers are
written to `selection_summary.csv`, and the with-reduction plot shows
the recomputed new max as its fifth bar.

### Reduction outputs

    output/
        selected_nodes.csv
        selection_summary.csv
        partition_violations.csv
        selection_summary_by_partition.csv
        cabinet_power_bars_with_reduction.png
        cumulative_power_with_reduction.png
        stacked_power_with_reduction.png

`selected_nodes.csv` carries one row per selected host with `cabinet,
host, peak_time, host_power_at_peak_w, ...`. `selection_summary.csv`
has one row per cabinet (`peak_total_kw, removed_at_peak_kw,
achieved_fraction, recomputed_new_inst_max_kw`).
`partition_violations.csv` has one row per partition still below floor
(`partition, partition_size, n_removed, n_remaining, floor, deficit`),
header-only when feasible. `selection_summary_by_partition.csv` is the
per-partition impact view (only partitions losing a node by default;
`nodes / cpus / gpus / <gpu_type>` triplets `_pre / _rm / _post`; GPUs
broken out by accelerator type from `scontrol_show_node.json`).
`cabinet_power_bars_with_reduction.png` adds the after-reduction bars to
the canonical 4-bar plot. `cumulative_power_with_reduction.png` overlays
the after-reduction cumulative curves (dashed) on the original ones
(solid) for direct min/median/max comparison.
`stacked_power_with_reduction.png` stacks only the kept hosts'
contributions per cabinet over time and overlays the original cluster
total as a dashed black line so the removed envelope is visible.

`selection_summary_by_partition.csv` is generated automatically by
`select_reduction_nodes.py`. Re-run it standalone if you hand-edit the
selection or want to point it at a different scontrol snapshot:

    python pipeline/summarize_by_partition.py \
        --selected-csv output/selected_nodes.csv \
        --scontrol-json ../telegraf_data/scontrol_show_node.json \
        --output output/selection_summary_by_partition.csv

Pass `--include-untouched` to keep every partition (164 rows) instead of
only the ones losing a node (~48 rows).

### Slurm reservation command

`make_reservation.py` is a standalone helper (no DB or pipeline
dependency) that turns `output/selected_nodes.csv` into a single
`scontrol create reservation ...` command with `Flags=MAINT,IGNORE_JOBS`
covering every distinct host in the CSV.

Defaults match the example reduction window (2026-05-10 09:00 to
2026-05-17 09:00). The auto-generated reservation name embeds the start
time and host count so it stays unique per window:
`temp_power_reduce_20260510_0900_<N>`.

Print the command with all defaults (User=root, the example window):

    python make_reservation.py

Custom window and user, also writing an executable script:

    python make_reservation.py \
        --start 2026-06-01T09:00 --end 2026-06-08T09:00 \
        --user slurm-admin \
        --output-script output/reservation.sh

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

## Authoring rules

When modifying any markdown in this repo, follow
[`AGENTS.md`](AGENTS.md), which points to the rule files under
[`agent-rules/`](agent-rules/).

## License

Released under the MIT License -- see [`LICENSE`](LICENSE) and
[`SYSTEM_CARD.md`](SYSTEM_CARD.md) for an outside-evaluator overview of
what the code does, which pieces are reusable, and how to adapt it.
