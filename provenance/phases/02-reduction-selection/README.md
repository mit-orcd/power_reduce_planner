# Phase 02 — Reduction selection

**When:** Friday May 1, 22:50 to Saturday May 2, 06:42 (UTC-4)
**User prompts:** 4 (indices 5-8)
**Plan:** [`plan.md`](plan.md) (`cabinet_power_reduction_selection_745e24c8.plan.md`)
**Result on disk:** `r9_pod_a_pipeline/pipeline/select_reduction_nodes.py`,
`r9_pod_a_pipeline/pipeline/plot_cabinet_bars_with_reduction.py`, the
`--with-reduction` chain in `run_pipeline.py`, and four new outputs
(`selected_nodes.csv`, `selection_summary.csv`, `partition_violations.csv`,
`cabinet_power_bars_with_reduction.png`).

## What came in

User asked for a downstream stage that:

1. randomly selects nodes per cabinet,
2. enough to bring the cabinet's instantaneous-max bar down by 40%,
3. while keeping every Slurm partition in
   [`telegraf_data/scontrol_show_node.json`](../../../../telegraf_data/scontrol_show_node.json)
   above its floor (>=2 nodes remaining; >=1 if the partition has only one).

## What was decided up front

One AskQuestion call carried two questions; both answers reshaped the
algorithm:

- **What does "down by 40%" mean?** Three options on the table:
  true-peak reduction (recompute the new max after removal and require it
  is <= 60% of the original), at-peak only (mirror the legacy
  `select_nodes.py` approach -- sum of removed-node power **at the
  cabinet's original peak time** must reach 40% of the peak total), or
  uniform count (just remove ~40% of nodes regardless of power). User
  chose **at_peak_only**. By construction this drops the at-peak total by
  exactly the target fraction, but the recomputed instantaneous max may
  drop by less if a near-equal secondary peak exists at a different time.
- **What if the partition floor is infeasible?** User chose
  **retry_seeds** with a typed addendum: "compute the partition
  constraint across all the cabinets ... if after 100 there is no
  outcome that meets the partition constraint, use the option with the
  least partition constraint violations." This made the constraint
  **global** (every cabinet's selection contributes to one shared `removed`
  set, scored against the partition table) and added the best-effort
  fallback.

See [`clarifications.md`](clarifications.md) for the verbatim AskQuestion +
choices and [`decisions.md`](decisions.md) for the reasoning.

## What was built

- `pipeline/select_reduction_nodes.py`:
  - `load_cabinets`, `cabinet_peak`, `cabinet_inst_max_after`, `load_partitions`.
  - `select_for_cabinet(rng, ...)` -- shuffle hosts and accumulate
    at-peak power until the cumulative reaches `target_fraction * peak_total`.
  - `score_attempt(removed, partitions)` -- for each partition, compute
    `(remaining = size - removed, deficit = floor - remaining)` and return
    `(n_violations, total_deficit, [violation_records])`.
  - Driver loop runs up to `--max-attempts` (default 100) seeded shuffles
    via `random.Random(seed_base + i)`. First attempt with zero violations
    wins; otherwise the lowest-violation attempt is kept and the
    shortfalls go to `output/partition_violations.csv` with a stdout warning.
- `pipeline/plot_cabinet_bars_with_reduction.py`: clone of the canonical
  plot with one extra bar (`Inst max after reduction`), preserving the
  16.5 / 33 / 49.5 kW dashed reference lines.
- `run_pipeline.py` gains `--with-reduction`, `--reduction-fraction`,
  `--max-attempts`, `--seed-base`, `--scontrol-json`. Reduction step is
  opt-in so the canonical 4-bar plot stays the default.

## Smoke run (initial)

`python run_pipeline.py --with-reduction --skip-export` reported:

- 100/100 attempts had violations (the binding constraints are 4
  size-1 partitions and 9 size-2 partitions whose entire membership lives
  in row 9 / pod A; pure random shuffles almost never avoid them).
- Best attempt: seed 2, 15 violations, total deficit 17.
- 185 hosts removed across 28 cabinets.
- Recomputed sum-of-inst-max dropped from 634.3 -> 358.1 kW (-43.5%).
- This was reported back to the user as "expected behavior given the
  density"; user then requested three changes (see
  [`change_requests.md`](change_requests.md)).

## Post-delivery refinements

Three changes shipped together:

1. **Restoration of zero-remaining partitions.** After picking the best
   attempt, walk every partition with `n_remaining == 0` and add one of
   its removed members back to `kept` (random pick via a derived RNG
   `Random(chosen_seed + 1_000_000)` for reproducibility). Re-score
   afterward. Smoke run after the change: 6 hosts restored, 0
   zero-remaining partitions, deficit dropped 17 -> 11, hosts removed 185
   -> 179, recomputed-max reduction stayed at -41.5%.
2. **`Average after reduction` bar** added to
   `plot_cabinet_bars_with_reduction.py` (now 6 bars per cabinet). Bar
   width tightened from 0.16 to 0.13 to fit and figure widened.
3. **Reduction-summary text box** rendered in the upper-left of the same
   plot showing host-count reduction, sum-inst-max reduction, sum-average
   reduction.

See [`change_requests.md`](change_requests.md) for details.

## Files in this phase directory

| File | Purpose |
| --- | --- |
| [`plan.md`](plan.md) | verbatim plan accepted at the start |
| [`user_prompts.md`](user_prompts.md) | 4 prompts, in order, with timestamps |
| [`assistant_responses.md`](assistant_responses.md) | every visible assistant text block plus tool-call stubs |
| [`clarifications.md`](clarifications.md) | the at-peak vs true-peak + infeasibility AskQuestion, with answers |
| [`decisions.md`](decisions.md) | distilled per-phase decisions, trade-offs |
| [`change_requests.md`](change_requests.md) | restoration, average-after bar, stats text box |
