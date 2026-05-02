---
name: self-contain plus new plots
overview: Make the repo self-contained by committing a gzipped snapshot of `scontrol_show_node.json` under `data/` (with a transparent gzip-aware loader so both `.json` and `.json.gz` work) and reimplement the two legacy plot scripts (cumulative power, stacked power over time) under `pipeline/` in the repo idiom. Adds `median_power` to `node_stats.csv` so the cumulative plot can show min/median/max as in the original. Wire both plots into `run_pipeline.py` Step 3, run a full architectural and engineering review, refresh DESIGN/README/SYSTEM_CARD/AGENTS, and capture the work as Phase 07 in `provenance/`.
todos:
  - id: compress_scontrol
    content: Create r9_pod_a_pipeline/data/, gzip telegraf_data/scontrol_show_node.json into data/scontrol_show_node.json.gz, verify round-trip with gunzip + jq
    status: completed
  - id: gzip_aware_loader
    content: Add a 3-line _open_scontrol(path) helper inside select_reduction_nodes.py and summarize_by_partition.py that uses gzip.open for *.gz else regular open; update load_partitions / load_nodes to use it
    status: completed
  - id: scontrol_default
    content: Update DEFAULT_SCONTROL_JSON in select_reduction_nodes.py and summarize_by_partition.py and the --scontrol-json default in run_pipeline.py to point at REPO_DIR/data/scontrol_show_node.json.gz
    status: completed
  - id: median_schema
    content: Add median_power to sql/04_node_stats.sql via PERCENTILE_CONT(0.5) and add the column to export_node_stats.py COLUMNS in position host,min,avg,median,max,sample_count
    status: completed
  - id: plot_cumulative
    content: "Implement pipeline/plot_cumulative_power.py: read node_stats.csv, sort min/median/max independently, cumsum, plot three lines + fill_between, output cumulative_power.png; expose render(output_dir) plus main()"
    status: completed
  - id: plot_stacked
    content: "Implement pipeline/plot_stacked_power.py: read output/timeseries/cabinet_NN/*.csv with columns time,power_watts, aggregate per cabinet per timestamp, stackplot, output stacked_power.png; expose render(output_dir, row, pod) plus main()"
    status: completed
  - id: wire_orchestrator
    content: In run_pipeline.py rename Step 3 to 'cabinet plots' and call plot_cumulative_power.render() and plot_stacked_power.render() after the existing plot_cabinet_bars call
    status: completed
  - id: arch_review
    content: "Architectural / engineering review pass: convention check, single-source-of-truth check, schema additivity check, ReadLints, end-to-end smoke run with all plots, gzip round-trip, grep for residual ../telegraf_data references in live code"
    status: completed
  - id: doc_refresh
    content: Refresh DESIGN.md (artifacts table + mermaid + extend section), README.md (output layout + verification gzip check), SYSTEM_CARD.md (sections 3, 4, 8, 9 + Last updated), AGENTS.md (Scope + Last updated), telegraf_data/AGENT_INSTRUCTIONS.md addendum + the in-repo cp
    status: completed
  - id: provenance_phase07
    content: Create provenance/phases/07-self-containment-plus-plots/ with plan.md, README.md, decisions.md; extend PHASES + KNOWN_ANSWERS in extract_session.py; rerun extractor; update provenance/TIMELINE.md and provenance/README.md
    status: in_progress
  - id: commit
    content: Single commit titled 'Self-contain repo (gzipped scontrol snapshot, gzip-aware loader) + add cumulative-power and stacked-power plots' with a body that lists every change category
    status: pending
isProject: false
---

## Goals

1. Remove the only external runtime dependency: the relative path
   `../telegraf_data/scontrol_show_node.json` becomes
   `data/scontrol_show_node.json.gz` inside the repo.
2. Add the two missing visualizations as proper pipeline stages:
   cumulative power per host, and stacked power over time per cabinet.
3. Keep the codebase coherent: same conventions, single source of
   truth per behavior, all docs refreshed, provenance captured as
   Phase 07.

## Self-containment

`data/scontrol_show_node.json` is 4.0 MB. Gzipped it should be
~200-400 KB (JSON with repeating keys compresses well). Per your
selection, ship the compressed form by default and make the loader
transparent so anyone can drop in either form.

Changes:

- **New file**: `r9_pod_a_pipeline/data/scontrol_show_node.json.gz` --
  gzip-9 of the current `telegraf_data/scontrol_show_node.json` (1404
  nodes, 164 partitions). Verified by round-trip gunzip + `jq '.nodes
  | length'` before commit.
- **New helper**: `_open_scontrol(path)` inside both
  [`r9_pod_a_pipeline/pipeline/select_reduction_nodes.py`](r9_pod_a_pipeline/pipeline/select_reduction_nodes.py)
  and
  [`r9_pod_a_pipeline/pipeline/summarize_by_partition.py`](r9_pod_a_pipeline/pipeline/summarize_by_partition.py)
  -- a 3-line wrapper that selects `gzip.open(path, "rt")` if the
  filename ends in `.gz`, else regular `open(path)`. Same module
  function in both files for stdlib symmetry; no shared utility
  module is created (matches the project's "no shared lib" convention).
- **Default `--scontrol-json`** in both scripts and in
  [`r9_pod_a_pipeline/run_pipeline.py`](r9_pod_a_pipeline/run_pipeline.py)
  changes from
  `os.path.normpath(os.path.join(REPO_DIR, "..", "telegraf_data", "scontrol_show_node.json"))`
  to
  `os.path.join(REPO_DIR, "data", "scontrol_show_node.json.gz")`.
- **`.gitignore`**: no edits needed. `data/` is not under `output/` so
  it stays tracked by default.

The gzip-or-plain auto-detect means a developer who wants a
hand-editable copy can `gunzip data/scontrol_show_node.json.gz` and
the loader keeps working without code changes.

## New stat column: `median_power`

The legacy cumulative plot showed min/median/max. The new
`node_stats.csv` had only min/avg/max. Per your selection, add median:

- [`r9_pod_a_pipeline/sql/04_node_stats.sql`](r9_pod_a_pipeline/sql/04_node_stats.sql)
  gains one column:

      PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY i.value) AS median_power,

- [`r9_pod_a_pipeline/pipeline/export_node_stats.py`](r9_pod_a_pipeline/pipeline/export_node_stats.py)
  adds `median_power` to its `COLUMNS` tuple, keeping order:
  `host, min_power, avg_power, median_power, max_power, sample_count`.

This is purely additive. The existing
[`r9_pod_a_pipeline/pipeline/plot_cabinet_bars.py`](r9_pod_a_pipeline/pipeline/plot_cabinet_bars.py)
ignores the new column. The CSV header gains one entry.

## New plot: cumulative power

`r9_pod_a_pipeline/pipeline/plot_cumulative_power.py` -- reimplementation
of [`telegraf_data/plot_cumulative_power.py`](telegraf_data/plot_cumulative_power.py)
in the repo idiom.

- Reads `output/node_stats.csv`.
- Sorts each of `min_power`, `median_power`, `max_power` independently
  ascending, takes `numpy.cumsum`, divides by 1000 to get kW.
- Plots three line series (Min, Median, Max) plus a shaded
  `fill_between(min, max)`.
- X-axis: node count (1..N), the legend explains "sorted independently
  per metric".
- Output: `output/cumulative_power.png`.
- Uses `add_common_args(parser)` from `config.py` for `--output-dir`
  consistency; exposes `render(output_dir)` so `run_pipeline.py` can
  call it programmatically (matches the existing
  `plot_cabinet_bars.render(...)` shape).
- Stdout: one summary line with the three cumulative totals in kW.

## New plot: stacked power over time

`r9_pod_a_pipeline/pipeline/plot_stacked_power.py` -- reimplementation
of [`telegraf_data/plot_stacked_power.py`](telegraf_data/plot_stacked_power.py)
in the repo idiom.

- Reads `output/timeseries/cabinet_NN/<host>.csv` files. Per-host
  CSV columns are now `time, power_watts` (not `time, host, max_power`
  as in the legacy version), so the parser is adjusted accordingly.
- Aggregates per cabinet at each timestamp, builds the union of
  timestamps, fills missing cells as 0, stacks via
  `ax.stackplot(...)` with cabinets ordered alphabetically (legend
  reversed so it reads top-to-bottom in the same order as the visual
  stack).
- Output: `output/stacked_power.png`. Same CLI pattern: `render(output_dir, row, pod)` for the title.
- The dashed reference lines at 16.5 / 33 / 49.5 kW are NOT drawn
  here; this plot is total-cluster-power, not per-cabinet, and the
  reference lines are per-cabinet thresholds.

## Orchestrator wiring

[`r9_pod_a_pipeline/run_pipeline.py`](r9_pod_a_pipeline/run_pipeline.py):

- Step 3 banner changes from "cabinet bar plot" to **"cabinet plots"**.
- After `plot_cabinet_bars.render(...)` it calls
  `plot_cumulative_power.render(...)` and
  `plot_stacked_power.render(...)`.
- The two new modules are imported next to the existing plot import.
- The reduction step (Step 4 / 5) is unchanged; the with-reduction
  variants of the new plots are NOT added in this iteration (out of
  scope -- see below).

## Architectural and engineering review

A concrete review pass before commit, called out as discrete items so
the work is auditable:

1. **Convention check** -- new modules use the same shape as their
   siblings: `THIS_DIR = ...; sys.path.insert(0, ...); from config
   import add_common_args, args_from_namespace`; expose a `render(...)`
   function called from `main()` and from `run_pipeline.py`; stdout one
   summary line with kW totals.
2. **Single-source-of-truth check** -- the gzip-aware loader is
   identical in shape across the two consumer modules; the same
   `_open_scontrol` helper appears in each (no code duplication via a
   utility import because the project deliberately avoids a shared
   library, so we accept three lines of duplication for symmetry --
   document the exception in `DESIGN.md`).
3. **Schema additivity check** -- `node_stats.csv` gains a column. Run
   the canonical pipeline against the new SQL to confirm
   `plot_cabinet_bars.py` still reads it correctly (it consumes by
   name, so the new column is silently ignored).
4. **Lint check** -- `ReadLints` over the four touched/new Python
   files.
5. **End-to-end smoke** -- `python run_pipeline.py --row 09 --pod A
   --with-reduction` produces 5 PNGs (the original 2 plus the 2 new
   ones plus the with-reduction one) and the existing CSV set with
   one new column. Verify file sizes, plot visual sanity (Read each
   PNG and confirm).
6. **Gzip round-trip** -- `gunzip -c data/scontrol_show_node.json.gz
   | jq '.nodes | length'` returns `1404`; `select_reduction_nodes`
   loads the gz path and reports the same partition count as before
   (164).
7. **Coverage of the external-path caveat** -- grep the entire repo
   for `../telegraf_data` to confirm only docs (provenance, change
   logs, history) still reference it; no live code path does.

Bug fixes / refactors uncovered during the review are folded into the
same commit unless they merit independent treatment (in which case
they get their own short commit and are listed in the commit body).

## Doc updates

- `[r9_pod_a_pipeline/DESIGN.md](r9_pod_a_pipeline/DESIGN.md)`:
  - artifacts table gains two rows
    (`cumulative_power.png`, `stacked_power.png`);
  - data-flow mermaid extends with two new edges from `NSCSV` /
    `TSCSV` into the new plot nodes;
  - parameter-surface table notes that `--scontrol-json` now defaults
    to `data/scontrol_show_node.json.gz`;
  - the "How to extend" section gets one new row pointing at the new
    plot files.
- `[r9_pod_a_pipeline/README.md](r9_pod_a_pipeline/README.md)`:
  - `Output layout` lists the two new PNGs;
  - `Quickstart` mentions that one run produces three plots;
  - the `Verification` section adds a one-line gzip round-trip check.
- `[r9_pod_a_pipeline/SYSTEM_CARD.md](r9_pod_a_pipeline/SYSTEM_CARD.md)`:
  - **Section 3 (What you get end-to-end)** adds the two new PNGs;
  - **Section 4 (Reusable building blocks)** gains "cumulative-by-rank
    visualization" and "per-cabinet stacked-area-over-time visualization";
  - **Section 8 (Limitations)** -- remove the external-dependency
    bullet entirely;
  - **Section 9 (Adaptation guide)** -- one new row for "different
    plot styles -- copy `plot_cumulative_power.py` or
    `plot_stacked_power.py` and edit";
  - bump `Last updated` to `2026-05-02`.
- `[r9_pod_a_pipeline/AGENTS.md](r9_pod_a_pipeline/AGENTS.md)`:
  - `Scope` adds `data/` to the in-repo bullet list;
  - `Scope` removes the external-runtime-dependency caveat;
  - bump `Last updated` to `2026-05-02`.
- `[telegraf_data/AGENT_INSTRUCTIONS.md](telegraf_data/AGENT_INSTRUCTIONS.md)`:
  add a one-line note in the "Current status" addendum that the
  pipeline now ships a self-contained copy of
  `scontrol_show_node.json` and no longer reads from
  `telegraf_data/`. Also update the in-repo
  `provenance/context/updated_AGENT_INSTRUCTIONS.md` (which is the
  cp of this file).

## Provenance: Phase 07

Capture this work as a new phase, matching the convention from Phases
01-06:

- `provenance/phases/07-self-containment-plus-plots/` with:
  - `plan.md` -- this plan, copied verbatim from the file `CreatePlan`
    will produce.
  - `README.md` -- hand-written narrative.
  - `decisions.md` -- gzip-or-plain auto-detect, median additivity,
    "no shared util" convention exception, Step 3 multi-plot.
  - `change_requests.md` -- empty for now (added if iterations land).
  - `user_prompts.md`, `assistant_responses.md`, `clarifications.md`
    -- regenerated by `extract_session.py` after the `PHASES` table
    gets a new entry.
- Update
  [`provenance/scripts/extract_session.py`](r9_pod_a_pipeline/provenance/scripts/extract_session.py):
  - re-run `--list` to discover the new user-message indices;
  - extend `PHASES` with `("07-self-containment-plus-plots", N, None)`
    where `N` is the first index of this phase;
  - extend `KNOWN_ANSWERS` with the two AskQuestion picks from this
    plan (`scontrol_location: data_subdir + gzip` and
    `median_for_cumulative: add_median`).
- Update [`provenance/TIMELINE.md`](r9_pod_a_pipeline/provenance/TIMELINE.md)
  with a new row for Phase 07 and a new bullet block in the timeline
  mermaid.
- Update [`provenance/README.md`](r9_pod_a_pipeline/provenance/README.md)
  layout listing to include `07-self-containment-plus-plots/`.

## Compliance with the existing authoring rules

All new and modified markdown follows
[`AGENTS.md`](r9_pod_a_pipeline/AGENTS.md):

- tilde fences only;
- 4-space indented blocks for SQL snippets and shell;
- no `---` horizontal rules;
- no `<br/>` anywhere;
- bold labels above any fence;
- last-updated lines bumped on the docs that change.

## Commit strategy

Single commit titled
`Self-contain repo (gzipped scontrol snapshot, gzip-aware loader) + add cumulative-power and stacked-power plots`,
landing directly after the current head `a38aaf1`. Body lists the
gzip / loader change, the SQL median addition, the two new plot
scripts, the orchestrator wiring, the doc refresh, and the Phase 07
provenance capture. If the architectural review surfaces an
independent fix (e.g. a Bug in an unrelated file), that ships as its
own short prior commit so the main commit stays focused.

## Verification

- `ls -la r9_pod_a_pipeline/data/` -> exactly one file,
  `scontrol_show_node.json.gz`, ~200-400 KB.
- `gunzip -c r9_pod_a_pipeline/data/scontrol_show_node.json.gz | jq '.nodes | length'` -> `1404`.
- `head -1 r9_pod_a_pipeline/output/node_stats.csv` -> contains
  `median_power`.
- `ls r9_pod_a_pipeline/output/*.png` -> 4 files when run without
  `--with-reduction`, 5 with it (the existing `cabinet_power_bars.png`
  and `cabinet_power_bars_with_reduction.png`, plus the two new ones,
  plus optionally the with-reduction one).
- `grep -r '\.\./telegraf_data' r9_pod_a_pipeline/{config.py,pipeline,sql}` -> no
  matches (live code paths are clean; docs and provenance may still
  reference the legacy paths historically).
- `grep -E '^Last updated:' r9_pod_a_pipeline/AGENTS.md
  r9_pod_a_pipeline/SYSTEM_CARD.md` -> both bumped to `2026-05-02`.
- `git log --oneline` -> 6 commits.

## Out of scope

- Adapting the new plots to also render with-reduction variants (i.e.
  cumulative / stacked of the post-reduction state). Easy follow-up
  if you want it.
- Removing or rewriting any code in `telegraf_data/` (it is part of
  the surrounding workspace, not this repo).
- Building a true shared-utility module (`utils.py` / package). The
  project's stated convention is "no shared lib"; the gzip helper
  duplication is documented as the deliberate exception.
- Any `xlsx` / `parquet` export.
- Bumping the year in LICENSE or filling in the `<COPYRIGHT_HOLDER>`
  placeholder.