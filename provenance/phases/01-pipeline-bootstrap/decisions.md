# Decisions — Phase 01 (Pipeline bootstrap)

## Structural

- **New top-level directory** chosen over refactoring `telegraf_data/`.
  The legacy `telegraf_data/query_pg.py` deviated from the spec on three
  points (no `sys_power`, no `pod` column in the dcim CSV, excluded
  cabinets `01`/`31`); fixing those in place would have entangled the
  rewrite with old DuckDB-cache code and the partition-split tooling.
  Result: `r9_pod_a_pipeline/` has no dependency on `telegraf_data/` other
  than the `scontrol_show_node.json` snapshot referenced by later phases.
- **Single agent plays all four spec roles** instead of literally spawning
  one specialist subagent per role. The artifact mapping was preserved
  faithfully (DB expert -> SQL; software engineer -> Python; architect
  -> DESIGN.md; docs -> README.md), so the spec's intent is honored even
  though the work was sequential.

## Domain

- **`sys_power` priority encoded once** in `sql/02_host_sensor_map.sql`
  as a `bool_or` `CASE`, picking `sys_power > instantaneous_power_reading
  > pwr_consumption` per host. Downstream stages join on the produced
  `(host, preferred_sensor)` pairs and never re-derive the priority.
- **Host-name irregularity confined to the same SQL file.**
  `split_part(node_name, '-', 1) = i.host` handles dashed names
  (`nodeXXXX-YYYY` -> telegraf host `nodeXXXX`) and leaves undashed names
  unchanged. `node_name NOT LIKE '%-chassis'` excludes the no-counterpart
  rows. Once the CSV is written, no other script needs to know.
- **Bar-plot semantics literal to spec.** The "instantaneous min" bar is
  `min over t of (sum over h of power(h, t))` -- different from the legacy
  `plot_cabinet_bars.py`, which plots `sum over h of (min over t of
  power(h, t))` (per-node min summed). Same correction applies to
  "average" and "instantaneous max". The "potential max" bar matches the
  legacy script's intent: per-node `max_t` summed (not necessarily
  simultaneous).
- **Time bucketing at 10 minutes** (matches the legacy script and is the
  default in `--bucket`). Configurable.
- **Time window default** copied from the legacy scripts:
  `2026-04-22T17:27:22.547Z` to `2026-05-30T17:27:22.547Z`.

## Engineering

- **No DuckDB cache** -- the spec deliverables are CSVs.
- **Per-cabinet batching of the time-series query** carried over from the
  legacy code. Keeps result sets bounded and produces a natural per-cabinet
  layout under `output/timeseries/cabinet_NN/`.
- **Mixing positional and named bind parameters in one psycopg2 call is
  unreliable.** The `(host, sensor)` VALUES clause is rendered with
  `cursor.mogrify(...)` and the time-window binds are passed separately
  as a dict of named parameters.

## Bug fixes discovered mid-flight

- **psycopg2 does not strip `--` SQL comments before scanning for
  `%(name)s` placeholders.** A comment containing `%(pairs)s` raised
  `KeyError: 'pairs'` at execute time. Fix: remove the percent-formatted
  placeholders from the comment text. Listed in the "Pitfalls" section of
  the updated `AGENT_INSTRUCTIONS.md`.
- **`config.py` initially had `PG_USER='postgres'`.** The spec's example
  psql line uses `readonly_user`. Smoke run failed -> changed to
  `readonly_user` (clarification #3 in this phase).

## What was intentionally NOT exposed as a CLI flag

- **`SENSOR_PRIORITY`** lives in `config.py` and the SQL `CASE` and is a
  domain rule, not a tuning knob. Changing it requires editing both code
  and SQL on purpose -- prevents accidental override at runtime.
