# Post-delivery change requests — Phase 02

User asked for three changes after the initial reduction implementation
landed. They came in one prompt:

> "Make three changes to the node reduction computation.
>  1. if, after making a final node selection, some partitions have zero
>     remaining nodes then add back one node from that partition.
>  2. on the cabinet_power_bars_with_reduction.png include another bar
>     which shows the new average based on the reduction.
>  3. include some summary statistics on the
>     cabinet_power_bars_with_reduction.png plot to show reductions in
>     node counts and inst max and average power."

## CR-02.1: restore zero-remaining partitions

**File:** [`r9_pod_a_pipeline/pipeline/select_reduction_nodes.py`](../../../pipeline/select_reduction_nodes.py)

New `restore_zero_remaining(per_cab_selection, removed, partitions, rng)`
function called from `run()` immediately after the best attempt is
chosen, before any CSV is written. It loops while any partition has
`n_remaining == 0`:

1. Pick a partition with zero remaining.
2. Select one of its removed hosts (random via the provided RNG).
3. Remove the host from the cabinet's `selected` list and from `removed`.
4. Repeat.

A single restoration may clear multiple zero-remaining partitions if the
restored host belongs to several. After restoration the chosen attempt is
re-scored so `partition_violations.csv` reflects the post-fix state.

The restoration RNG uses seed `chosen_seed + 1_000_000` so the run stays
reproducible without conflicting with the per-cabinet shuffle RNG.

**Smoke run after the change:** 6 hosts restored, partitions touched:
`pi_tsmidt`, `pi_linaresr`, `pi_gaias`, `pi_psinha`, `pi_dbertsim`,
`pi_rahulmaz`. Zero-remaining count after restoration: 0. Total deficit:
17 -> 11 (the residual 11 are size-2 partitions where one of two members
was removed -- still floor-violations but not empty).

## CR-02.2: `avg_after` bar on the with-reduction plot

**File:** [`r9_pod_a_pipeline/pipeline/plot_cabinet_bars_with_reduction.py`](../../../pipeline/plot_cabinet_bars_with_reduction.py)

Computes
`avg_after = mean over t of (sum over h in remaining of power(h, t))` per
cabinet. The "after" series uses the same set of timestamps as the "before"
series (a bucket where no remaining host reported counts as 0 W cabinet
total) so the two averages are comparable.

Added as the 5th bar (later positioned alongside `inst_max_after` as the
6th). Hatched with `..` to distinguish from the unhatched "before" bars.

Bar width tightened from 0.16 to 0.13 to fit 6 bars per cabinet
comfortably; figure width adjusted from `max(12, 0.85*n+4)` to
`max(13, 0.95*n+4)`.

## CR-02.3: in-plot summary statistics box

**File:** same as CR-02.2.

A monospaced text box in the upper-left of the figure renders:

```
Reduction summary (sum across N cabinets)
  Hosts removed: <m> / <total>  (<pct>%)
  Inst max:  <before> kW -> <after> kW   (-<pct>%)
  Average:   <before> kW -> <after> kW   (-<pct>%)
```

Drawn via `ax.text(..., transform=ax.transAxes,
bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.85,
edgecolor="gray", linewidth=0.6))`. The same stats line is also printed
to stdout from `render()` so the numbers are visible without opening the
PNG.
