# Post-delivery change requests — Phase 04

User attached a `csvlens` screenshot of the initial CSV and asked for two
changes in one prompt:

> "Can you modify the program so that only partitions with nodes removed
> are reported. Also see if you can compact/shorten heaings so that more
> fits on a page when viewd with 'csvlens' a handy CSV viewer. The
> current view is too wide to see easily (see image)."

## CR-04.1: filter to partitions that lose >= 1 node

**File:** [`r9_pod_a_pipeline/pipeline/summarize_by_partition.py`](../../../pipeline/summarize_by_partition.py)

`write_csv(...)` and `run(...)` gain an `include_untouched: bool = False`
parameter. The standalone CLI exposes it as `--include-untouched`. The
default behavior emits only rows where `nodes_removed > 0`. The `run()`
stdout line gained a "X untouched partitions suppressed (use
--include-untouched to keep)" note so a skim of the orchestrator output
makes the filtering visible.

Effect on the smoke run: 164 -> 48 rows in `selection_summary_by_partition.csv`.

## CR-04.2: compact headers

**File:** same as CR-04.1.

Two changes in `write_csv`:

1. Suffix change: `_before / _removed / _after` -> `_pre / _rm / _post`.
2. Per-type GPU columns drop the `gpus_` prefix
   (`a100_pre / a100_rm / a100_post` instead of
   `gpus_a100_before / ...`). The total-GPU triplet keeps the prefix
   (`gpus_pre / gpus_rm / gpus_post`) so it's unambiguous.

Implementation uses a `columns` list of `(storage_prefix, header_prefix)`
tuples so the in-memory dict (still keyed by `_before / _removed`) is
unchanged -- only the header strings differ.

Header before / after a few examples:

| Old | New |
| --- | --- |
| `nodes_before` (12) | `nodes_pre` (9) |
| `cpus_removed` (12) | `cpus_rm` (7) |
| `gpus_total_after` (16) | `gpus_post` (9) |
| `gpus_rtx_pro_6000_removed` (25) | `rtx_pro_6000_rm` (15) |

Updated docs:

- [`r9_pod_a_pipeline/README.md`](../../../README.md) reduction-outputs
  section now mentions the new convention and the `--include-untouched`
  flag.
- [`r9_pod_a_pipeline/DESIGN.md`](../../../DESIGN.md) artifact entry
  updated.
- [`telegraf_data/AGENT_INSTRUCTIONS.md`](../../../../telegraf_data/AGENT_INSTRUCTIONS.md)
  opt-in-downstream description updated.

Module docstring in `summarize_by_partition.py` documents the suffix
convention so future readers don't have to grep the code.
