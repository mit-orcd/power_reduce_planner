# Phase 07 — Self-containment + new plots

**When:** Saturday May 2, 15:06+ (UTC-4)
**User prompts:** 2 (indices 30-31)
**Plan:** [`plan.md`](plan.md) (`self-contain_plus_new_plots_8ed9167e.plan.md`)
**Result on disk:** `data/scontrol_show_node.json.gz`, two new plot
modules under `pipeline/`, an additive `median_power` column in
`node_stats.csv`, an updated orchestrator Step 3, and refreshed
DESIGN / README / SYSTEM_CARD / AGENTS / `telegraf_data/AGENT_INSTRUCTIONS.md`.

## What came in

User asked to:

1. Make the repo self-contained by copying needed material from
   directories outside `r9_pod_a_pipeline/` (the only such file the
   pipeline actually uses is `scontrol_show_node.json`).
2. Reimplement two legacy plot styles -- cumulative power and stacked
   power over time -- that lived as fragments under
   [`telegraf_data/`](../../../../telegraf_data/), in the repo idiom.
3. Run an architectural and engineering review to keep the codebase
   coherent.

## What was decided up front

One AskQuestion call carried two questions; both answers shaped the
implementation:

- **Where to put `scontrol_show_node.json`.** User chose
  `data/scontrol_show_node.json.gz` *and* asked for the loader to
  handle both compressed and uncompressed forms. Result: a 3-line
  `_open_scontrol(path)` helper inside both
  [`pipeline/select_reduction_nodes.py`](../../../pipeline/select_reduction_nodes.py)
  and [`pipeline/summarize_by_partition.py`](../../../pipeline/summarize_by_partition.py)
  that uses `gzip.open(path, "rt")` for `*.gz` and falls through to
  plain `open(path)` otherwise. Compressed snapshot is 86 KB (~46x
  compression of the 4 MB original).
- **Whether to add `median_power` for the cumulative plot.** User
  chose `add_median`. Result: one extra `PERCENTILE_CONT(0.5)` column
  in [`sql/04_node_stats.sql`](../../../sql/04_node_stats.sql) and one
  extra entry in `COLUMNS` in
  [`pipeline/export_node_stats.py`](../../../pipeline/export_node_stats.py).
  Purely additive; the existing
  [`pipeline/plot_cabinet_bars.py`](../../../pipeline/plot_cabinet_bars.py)
  ignores the new column.

## What was built

- `data/scontrol_show_node.json.gz` -- gzipped snapshot, verified
  round-trip (1404 nodes, 164 partitions match the original).
- `pipeline/plot_cumulative_power.py` -- reimplementation of the
  legacy fragment at
  [`telegraf_data/plot_cumulative_power.py`](../../../../telegraf_data/plot_cumulative_power.py).
  Reads `output/node_stats.csv`, sorts each of `min_power`,
  `median_power`, `max_power` independently, takes `numpy.cumsum`,
  plots three line series plus `fill_between(min, max)`. Same
  `render(output_dir)` shape as the existing plots.
- `pipeline/plot_stacked_power.py` -- reimplementation of
  [`telegraf_data/plot_stacked_power.py`](../../../../telegraf_data/plot_stacked_power.py).
  Reads per-host CSVs under `output/timeseries/cabinet_NN/` (using
  the new `time, power_watts` schema, not the legacy `time, host,
  max_power` schema), aggregates per cabinet at each timestamp,
  builds the union of timestamps, fills missing cells as 0, stacks
  via `ax.stackplot(...)`. Cabinets ordered alphabetically; legend
  reversed so it reads top-to-bottom in the same order as the visual
  stack.
- `run_pipeline.py` Step 3 banner renamed from "cabinet bar plot" to
  "cabinet plots"; calls all three render functions in sequence
  (`plot_cabinet_bars`, then `plot_cumulative_power`, then
  `plot_stacked_power`).

## Architectural review pass

Discrete checks performed before the commit (called out in the plan):

1. **Convention check** -- new modules use the same shape as their
   siblings: `THIS_DIR`, `sys.path.insert`, `from config import
   add_common_args`, `render(...)` callable from `main()` and from
   `run_pipeline.py`, stdout summary line.
2. **Single-source-of-truth check** -- the gzip-aware loader is the
   same 3-line helper in both consumer modules; deliberate duplication
   per the project's "no shared lib" convention.
3. **Schema additivity check** -- `node_stats.csv` gains one column;
   `plot_cabinet_bars.py` reads by name and silently ignores it.
4. **Lint** -- `ReadLints` over the four touched/new Python files:
   no errors found.
5. **End-to-end smoke** -- `python run_pipeline.py --row 09 --pod A
   --with-reduction` produced 4 PNGs from Step 3 + 1 from Step 5,
   all 4 base CSVs, and the 4 reduction CSVs. Both new plots
   verified visually (Read on the PNGs).
6. **Gzip round-trip** -- 1404 nodes / 164 partitions read back from
   the compressed snapshot, identical to the source.
7. **Residual external-path check** -- `grep -rn '../telegraf_data'`
   over `config.py`, `pipeline/`, `sql/`, `run_pipeline.py`,
   `make_reservation.py` after the migration. The only remaining
   match was a stale doc-string line in
   `pipeline/select_reduction_nodes.py` which was fixed in the same
   commit.

## Smoke-run snapshot

After the changes, `python run_pipeline.py --row 09 --pod A
--with-reduction` reported (Step 3 portion):

    cumulative_power.png: 436 hosts; cumulative totals:
        min=278.5 kW, median=473.7 kW, max=807.8 kW
    stacked_power.png:    28 cabinets, 2219 time buckets,
        peak total = 541.6 kW

The reduction step then produced its existing 4 CSVs and the
`cabinet_power_bars_with_reduction.png` as before, picking up the
gzipped scontrol snapshot transparently:

    scontrol_json=/.../r9_pod_a_pipeline/data/scontrol_show_node.json.gz

## Files in this phase directory

| File | Purpose |
| --- | --- |
| [`plan.md`](plan.md) | the accepted plan |
| [`user_prompts.md`](user_prompts.md) | 2 prompts in order |
| [`assistant_responses.md`](assistant_responses.md) | every visible assistant text block plus tool-call stubs |
| [`clarifications.md`](clarifications.md) | the one combined AskQuestion (scontrol location + median for cumulative) with both user selections |
| [`decisions.md`](decisions.md) | distilled per-phase decisions (gzip-or-plain auto-detect, schema additivity, "no shared util" exception, multi-plot Step 3) |
