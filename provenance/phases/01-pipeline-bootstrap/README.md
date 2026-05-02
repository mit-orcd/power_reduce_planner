# Phase 01 — Pipeline bootstrap

**When:** Friday May 1, 2026, 22:06 to 22:34 (UTC-4)
**User prompts:** 5 (indices 0-4)
**Plan:** [`plan.md`](plan.md) (`r9_pod_a_power_pipeline_87f66f38.plan.md`)
**Result on disk:** the entire `r9_pod_a_pipeline/` directory minus the
later downstream stages — all the SQL, the four export scripts, the canonical
`plot_cabinet_bars.py`, the orchestrator, the README and DESIGN drafts.

## What came in

User asked me to read `telegraf_data/AGENT_INSTRUCTIONS.md` (preserved here
under [`../../context/original_AGENT_INSTRUCTIONS.md`](../../context/original_AGENT_INSTRUCTIONS.md))
and produce a plan for the three-task spec it contains:

1. dump `public.dcim_nodes` to a CSV (`name, row, pod, rack`),
2. extract per-host power time-series for row 9 / pod A,
3. produce a 4-bar-per-cabinet plot
   (instantaneous min, average, instantaneous max, potential max).

The spec also asked for a multi-agent process (DB expert, software engineer,
architect, docs).

## What was decided up front

Two AskQuestion clarifications resolved the structural ambiguities:

- **Where to put the new code.** A partial implementation already lived in
  `telegraf_data/` (see [`telegraf_data/query_pg.py`](../../../../telegraf_data/query_pg.py)
  and friends) but it had three deviations from the spec. User chose
  `new_top_level` -- write fresh in a new top-level directory, leave
  `telegraf_data/` untouched.
- **How to handle the four-role process.** User chose `single_agent_roles`
  -- one agent (me) plays all four roles sequentially and produces the
  corresponding artifacts (SQL = DB expert; `pipeline/*.py` = software
  engineer; `DESIGN.md` = architect; `README.md` = docs).

A third AskQuestion later in the phase resolved a credential mismatch
(`postgres` vs `readonly_user` -- chose `agent_md` to match the spec).

See [`clarifications.md`](clarifications.md) and [`decisions.md`](decisions.md)
for the full reasoning.

## What was built

- `sql/01_dcim_nodes.sql` -- inventory dump.
- `sql/02_host_sensor_map.sql` -- single source of truth for the host-name
  irregularity (`split_part(node_name,'-',1)`) and the
  `sys_power`-authoritative sensor-priority rule (encoded as `bool_or` `CASE`).
- `sql/03_node_timeseries.sql` and `sql/04_node_stats.sql` -- consume the
  preferred (host, sensor) pairs.
- `pipeline/export_*.py` -- four stages writing CSVs.
- `pipeline/plot_cabinet_bars.py` -- 4 bars per cabinet with the spec-literal
  `min_t(sum_h)` / `mean_t(sum_h)` / `max_t(sum_h)` / `sum_h(max_t)` definitions.
- `run_pipeline.py` -- orchestrator with `--row`, `--pod`, `--start`,
  `--end`, `--bucket`, `--output-dir`, `--skip-export`.
- `config.py`, `pg_client.py`, `requirements.txt`, plus the first drafts of
  `README.md` and `DESIGN.md`.

## Mid-flight bug fixes

- **psycopg2 doesn't strip SQL comments before scanning for `%(name)s`
  placeholders.** A comment containing `%(pairs)s` raised
  `KeyError: 'pairs'`. Fixed by removing the percent-formatted markers from
  the comment text in `sql/03_node_timeseries.sql` and `sql/04_node_stats.sql`.
- **PG user mismatch.** `config.py` shipped with `postgres`, but the spec's
  example psql line uses `readonly_user`. Switched to `readonly_user`
  before the smoke run.

Both are listed in the "Pitfalls" section of the post-session
[`AGENT_INSTRUCTIONS.md`](../../context/updated_AGENT_INSTRUCTIONS.md) so
future agents don't repeat them.

## Delivered + verified

`python run_pipeline.py --row 09 --pod A` ran end-to-end in ~13 seconds and
produced:

- `output/dcim_nodes.csv` (3,089 rows; matches `SELECT COUNT(*) FROM
  public.dcim_nodes` exactly),
- `output/host_sensor_map.csv` (436 hosts kept; 187 dropped for no power
  data; sensor mix `instantaneous_power_reading=409, pwr_consumption=7,
  sys_power=20`),
- 28 cabinets x per-host CSVs under `output/timeseries/cabinet_NN/`,
- `output/cabinet_power_bars.png`.

## Post-delivery refinement

User asked to add three dashed reference lines at 16.5 / 33 / 49.5 kW to
the cabinet bars plot. Done in
[`r9_pod_a_pipeline/pipeline/plot_cabinet_bars.py`](../../../pipeline/plot_cabinet_bars.py)
via `ax.axhline(...)` with one entry carrying the legend label. See
[`change_requests.md`](change_requests.md).

## Files in this phase directory

| File | Purpose |
| --- | --- |
| [`plan.md`](plan.md) | verbatim plan accepted at the start |
| [`user_prompts.md`](user_prompts.md) | 5 prompts, in order, with timestamps |
| [`assistant_responses.md`](assistant_responses.md) | every visible assistant text block plus tool-call stubs |
| [`clarifications.md`](clarifications.md) | the 3 AskQuestion calls in this phase, with the user's selections filled in |
| [`decisions.md`](decisions.md) | distilled per-phase decisions, trade-offs, and bug fixes |
| [`change_requests.md`](change_requests.md) | post-delivery refinements (here: reference lines) |
