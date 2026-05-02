# Decisions — Phase 04 (Partition impact summary)

## Format

- **Wide CSV (one row per partition)** rather than long
  (`partition x metric` rows). Easier to compare across partitions and
  diffs in `git`. Trade-off: wide tables are uncomfortable in narrow
  terminals -- mitigated by CR-04.2 (compact headers) and CR-04.1
  (filter to non-empty rows).
- **CSV (not xlsx).** The user's default name was `.csv` and the
  project is std-lib only. An `openpyxl`-based xlsx writer would be
  ~5 lines if needed later without changing the schema.

## Auto-discover GPU types

- **GPU types are not enumerated up front.** A single regex
  `gpu:(?:([A-Za-z0-9_\-]+):)?(\d+)` walks every node's `gres` string
  and the union of seen types becomes the per-type column set
  (alphabetical: `a100, a40, h100, h200, l4, l40s, rtx_a6000,
  rtx_pro_6000, untyped`). This is robust to new types appearing in
  future scontrol snapshots.
- **Type-less `gpu:N` entries bucket as `untyped`.** ~80 nodes in the
  current snapshot. Easier to see "what didn't get a label" than to
  silently drop them.

## Filter (CR-04.1)

- **Default: only partitions with `nodes_removed > 0`.** Reduces visual
  noise from ~164 rows to ~48; the suppressed rows are by definition
  uninteresting (their `_after == _before` everywhere).
- **`--include-untouched` opt-out** for the full picture. Both the
  standalone CLI and the `run()` function accept it.

## Compact headers (CR-04.2)

- **Suffix scheme `_pre / _rm / _post`** chosen over alternatives like
  `_b/_r/_a` (too cryptic) or `_was/_rm/_now` (cute). Saves 3-5
  characters per column.
- **Drop `gpus_` prefix on per-type GPU columns.** The type name itself
  (`a100`, `h100`, ...) implies GPU. `gpus_` stays only on the total
  triplet (`gpus_pre/_rm/_post`) so it's distinguishable.
- **Longest header dropped from 25 to 17 chars** (`rtx_pro_6000_post`),
  most others 7-10 chars -- comfortable in `csvlens` and similar viewers.

## Wiring

- **Auto-chained from `select_reduction_nodes.run()`** so the partition
  CSV always lands beside `selection_summary.csv`. One line of import +
  one call right after the existing writes.
- **Standalone re-run** still works:
  `python pipeline/summarize_by_partition.py [--include-untouched]`.
  Useful for hand-edited selections or different scontrol snapshots.

## What was intentionally NOT done

- **No utilization (`gres_used`) tracking.** User asked about totals;
  utilization can become another triplet later if needed.
- **No xlsx output** (see "Format" above).
- **No long format.** See "Format" above.
