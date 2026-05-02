# Decisions — Phase 07 (Self-containment + new plots)

## Self-containment

- **Compressed snapshot in `data/`.** The user's selection paired
  "put it in the repo" with "make it gzip-or-plain transparent". A
  4 MB raw file would noticeably bloat clones; the 86 KB gzipped form
  (~46x compression) is comfortable. The transparent loader keeps a
  hand-editable workflow available without any code change.
- **Gzip auto-detect by file extension**, not by magic bytes. Simpler
  and unambiguous. Same 3-line helper duplicated in both consumer
  modules (`select_reduction_nodes.py` and `summarize_by_partition.py`)
  per the project's "no shared lib" convention; the cost is small
  enough that the convention wins.
- **No `data/` exclusion in `.gitignore`.** `data/` is committed; it
  ships with the repo. Anyone who wants to refresh the snapshot
  re-runs the gzip step into `data/`.

## Schema additivity (`median_power`)

- **Add `median_power` to `node_stats.csv`** rather than dropping
  median from the new cumulative plot. Three reasons:
    1. The legacy plot showed min/median/max -- preserving that
       semantic is closer to "reimplementation" than dropping a
       curve.
    2. PostgreSQL `PERCENTILE_CONT(0.5) WITHIN GROUP (...)` is a
       single SQL line; cost is trivial.
    3. Adding a column to a CSV that downstream consumers read
       by name is a non-breaking change.
- **Column order**: `host, min_power, avg_power, median_power,
  max_power, sample_count`. Median between avg and max so the
  central-tendency stats sit together in natural ascending order.

## New plot conventions

- **`render(output_dir)` and `render(output_dir, row, pod)`** as the
  programmatic entry points. The cumulative plot has no `(row, pod)`
  in its title (the data is whatever `node_stats.csv` contains) so
  it doesn't take those arguments; the stacked plot does title with
  `(row, pod)` so the file is self-describing when shared.
- **No reference dashed lines on the new plots.** The 16.5 / 33 /
  49.5 kW lines are per-cabinet thresholds. Cumulative is per-host
  cumulated across the cluster; stacked is total cluster power. The
  thresholds wouldn't help on either.
- **Stdout one summary line** with kW totals matches the existing
  plot convention.

## Multi-plot Step 3

- **Three plots in one Step 3** rather than three separate steps. The
  plots are cheap (~1-3 sec each), they all read CSVs only, and
  nobody wants one without the others. Keeping them as a single step
  also keeps `--skip-export` semantics simple ("regenerate all the
  plots from cached CSVs").
- **No CLI gating.** A future flag like `--plots min,stacked` could
  be added if someone has a reason; not needed now.

## Architectural-review structure

- **Seven discrete review items** (convention, SOT, schema
  additivity, lint, smoke, gzip round-trip, residual external paths)
  stated explicitly in the plan and re-checked in this phase's
  README. Pattern worth re-using for any future change that touches
  multiple files plus docs.

## What was deliberately NOT done

- **No shared `utils.py`.** The project convention is "no shared
  lib"; the `_open_scontrol` 3-line helper lives in two places by
  design. Documented in the plan as the explicit exception.
- **No reduction-aware variants of the new plots.** Cumulative-after
  and stacked-after would be useful but are out of scope per the
  plan. Easy follow-up.
- **No removal of the legacy fragments under `telegraf_data/`.** Not
  this repo; user explicitly noted those directories are "older
  experimental and learning material".
- **No `xlsx` / `parquet`.** Same as the broader project policy.
