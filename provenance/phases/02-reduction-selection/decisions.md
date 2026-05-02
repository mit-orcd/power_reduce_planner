# Decisions — Phase 02 (Reduction selection)

## Algorithmic

- **At-peak vs true-peak interpretation of "40% reduction"** -- chose
  at-peak (matches legacy `telegraf_data/select_nodes.py`). This makes
  the algorithm a simple shuffle-and-accumulate on each cabinet's at-peak
  host powers; the cumulative is guaranteed to reach the target by
  construction. The recomputed instantaneous max (`max_t (T(t) - sum_h
  removed)`) is computed and reported separately so the gap is visible.
- **Constraint scope is global, not per cabinet.** Every cabinet's
  selection contributes to a single `removed` set. The partition floor
  is checked against that union once per attempt. Per the user's typed
  addendum on the infeasibility question.
- **Best-effort fallback after 100 attempts.** Score = `(n_violations,
  total_deficit)` -- primary on count of partitions in violation,
  tiebreaker on summed deficit. The first attempt with `n_violations == 0`
  wins; otherwise the lowest-scoring attempt wins after the budget is
  exhausted, with a stdout warning and `partition_violations.csv` listing
  the shortfalls.
- **Restoration step (added in CR-02.1).** After picking the best
  attempt, walk partitions whose `n_remaining == 0` and add back one of
  their removed members. Loop until none remain. A single restoration may
  resolve multiple zero-remaining partitions if the restored host belongs
  to several. Random pick (deterministic via `Random(chosen_seed +
  1_000_000)`) so the run stays reproducible.

## Output schema

- **`selected_nodes.csv`** -- per-host row: `cabinet, host, peak_time,
  host_power_at_peak_w, cabinet_peak_total_w, achieved_fraction,
  target_fraction, attempt_seed, attempt_violations`.
- **`selection_summary.csv`** -- per-cabinet row: includes both
  `removed_at_peak_kw` (the metric the algorithm optimizes) and
  `recomputed_new_inst_max_kw` (the metric the user might actually care
  about). Showing both is the explicit hedge against the at-peak-vs-true
  difference.
- **`partition_violations.csv`** -- header-only when feasible. Same
  schema as the existing per-violation tuple.

## Plot

- **5-bars-per-cabinet** (later 6 after CR-02.2): inst min, average,
  inst max, potential max, inst max after reduction (hatched), average
  after reduction (hatched). Bar width 0.13 with 6 bars; figure widens
  with cabinet count.
- **Reference lines preserved** (16.5 / 33 / 49.5 kW dashed) -- same
  loop pattern as the canonical plot.
- **Stats text box** in the upper-left (added in CR-02.3) reports host
  count, inst-max, and average reductions at one glance.

## What was intentionally NOT done

- **No optimization-based selection** (no ILP, no greedy-by-power, no
  weighted random). User asked for "randomly". Pure shuffle.
- **No iteration toward a true 40% drop in the recomputed max.** User
  explicitly chose at-peak, so we don't chase the moving target.

## Why none of the 100 seeds were feasible

15 partitions exist whose entire membership is inside the removable pool
(row 9 / pod A nodes with power data): 4 size-1 partitions and 9 size-2
partitions plus a couple of size-3/4 partitions. Random shuffles
overwhelmingly hit at least one. Three options for future work:

1. lower `--reduction-fraction` (e.g. 0.25),
2. pre-mask hosts that belong to a "fully-in-pool" small partition so
   they're never eligible (algorithm change),
3. accept best-effort -- the current default. CR-02.1 (restoration) is
   the cheapest defensive fix and resolves zero-remaining cases without
   changing the algorithm.
