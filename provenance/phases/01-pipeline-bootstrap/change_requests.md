# Post-delivery change requests — Phase 01

After the initial pipeline landed and the smoke run succeeded, the user
requested one refinement to the canonical bar plot.

## CR-01.1: dashed reference lines on `cabinet_power_bars.png`

> "In the plot made by `plot_cabinet_bars.py` can you add code to plot
> dashed horizontal lines at 16.5KW, 33KW, 49.5KW"

**Implementation.** A short loop in
[`r9_pod_a_pipeline/pipeline/plot_cabinet_bars.py`](../../../pipeline/plot_cabinet_bars.py)
calls `ax.axhline(level, color="black", linestyle="--", linewidth=0.8, ...)`
for each of `(16.5, 33.0, 49.5)`. The first axhline carries a single legend
entry `"Reference levels (16.5 / 33 / 49.5 kW)"`; the others pass `label=None`
so the legend stays clean.

**Re-render.** `python run_pipeline.py --row 09 --pod A --skip-export`
re-renders the plot from cached CSVs in ~1 second without touching the DB.

**Note on history.** The `--skip-export` flag is what makes iteration on
cosmetics cheap -- this is the first time it was used, but it became the
standard "edit plot, re-render" workflow for the rest of the session.
