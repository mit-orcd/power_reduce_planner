# Post-delivery change requests — Phase 07

The original Phase 07 plan listed reduction-aware variants of the new
plots as out-of-scope. A follow-up prompt added them.

## CR-07.1: with-reduction variants of cumulative and stacked plots

> "can you update code to make stacked_power_with_reduction.png plots
> and cumulative_power_with_reduction.png as well."

**New files:**

- [`r9_pod_a_pipeline/pipeline/plot_cumulative_power_with_reduction.py`](../../../pipeline/plot_cumulative_power_with_reduction.py)
  -- 6-line cumulative plot. Same per-host min/median/max
  independently-sorted-cumulated shape as the canonical
  `plot_cumulative_power.py`, drawn twice on one axis: solid lines for
  the original (all hosts) and dashed lines (same colors) for the
  after-reduction subset (hosts NOT in `selected_nodes.csv`). Shaded
  `fill_between` for the after-reduction envelope. Title shows
  "removed N of M hosts"; stdout reports cumulative reductions in
  percent for min / median / max.
- [`r9_pod_a_pipeline/pipeline/plot_stacked_power_with_reduction.py`](../../../pipeline/plot_stacked_power_with_reduction.py)
  -- stacked-area plot of after-reduction power per cabinet over time.
  Same `ax.stackplot` shape as `plot_stacked_power.py`, but each
  cabinet's per-time contribution counts only its kept hosts. The
  original cluster total is overlaid as a dashed black line so the
  reader can see the removed-power envelope as the gap between the
  dashed line and the top of the stack.

**Orchestrator wiring:** `run_pipeline.py` Step 5 banner renamed from
"cabinet bar plot with reduction" to "cabinet plots with reduction";
the two new render functions are called after the existing
`plot_cabinet_bars_with_reduction.render(...)`.

**Smoke results** (with the same reduction selection as before, 181
hosts removed of 436):

- `cumulative_power_with_reduction.png`: cumulative reductions
  min -43.4%, median -42.8%, max -44.0%.
- `stacked_power_with_reduction.png`: peak total
  541.6 kW -> 299.2 kW (-44.8%).

**Doc updates:** [`DESIGN.md`](../../../DESIGN.md) artifacts table
gains two rows and the data-flow mermaid extends with two new edges;
[`README.md`](../../../README.md) reduction-outputs listing gains the
two PNGs with descriptions; [`SYSTEM_CARD.md`](../../../SYSTEM_CARD.md)
section 3 (What you get end-to-end) gains two bullets;
[`telegraf_data/AGENT_INSTRUCTIONS.md`](../../../../telegraf_data/AGENT_INSTRUCTIONS.md)
(and the in-repo cp) "New canonical plots" section gains a
"short follow-up" paragraph documenting the with-reduction variants.

**Convention notes:** both new plots follow the existing repo idiom
(THIS_DIR boilerplate, `from config import add_common_args`,
`render(...)` callable from `main()` and `run_pipeline.py`, stdout
summary line). The cumulative variant exposes `render(output_dir)`;
the stacked variant exposes `render(output_dir, row, pod)` so the
title can name the row/pod -- mirroring their non-reduction siblings.
