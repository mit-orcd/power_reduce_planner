# Session timeline

One row per phase, in order, with the user-prompt range, plan file, and
the artifacts on disk that landed in that phase.

| # | Phase | When (UTC-4) | User prompts | Plan | Code artifacts |
| --- | --- | --- | --- | --- | --- |
| 01 | [Pipeline bootstrap](phases/01-pipeline-bootstrap/) | Fri 22:06 - 22:34 | indices 0-4 (5 prompts) | `r9_pod_a_power_pipeline_87f66f38.plan.md` | `sql/01..04_*.sql`, `pipeline/export_*.py`, `pipeline/plot_cabinet_bars.py`, `run_pipeline.py`, `config.py`, `pg_client.py`, first drafts of `README.md` and `DESIGN.md` |
| 02 | [Reduction selection](phases/02-reduction-selection/) | Fri 22:50 - Sat 06:42 | indices 5-8 (4 prompts) | `cabinet_power_reduction_selection_745e24c8.plan.md` | `pipeline/select_reduction_nodes.py`, `pipeline/plot_cabinet_bars_with_reduction.py`, `--with-reduction` chain in `run_pipeline.py`, four output CSVs / PNG |
| 03 | [Reservation generator](phases/03-reservation-generator/) | Sat 06:42 - 06:54 | indices 9-13 (5 prompts) | `slurm_reservation_generator_ea0910d3.plan.md` | `make_reservation.py` (standalone) |
| 04 | [Partition impact summary](phases/04-partition-summary/) | Sat 08:16 - 08:53 | indices 14-17 (4 prompts) | `partition_impact_summary_11bf9529.plan.md` | `pipeline/summarize_by_partition.py`, auto-call from `select_reduction_nodes.run()`, `output/selection_summary_by_partition.csv` |
| 05 | [Git repo init](phases/05-git-repo-init/) | Sat 08:53 - 09:10 | indices 18-21 (4 prompts) | `init_r9_pipeline_git_repo_11e69107.plan.md` | `.git/` and root commit `d6bb680` on branch `main` |
| 06 | [Provenance subdirectory](phases/06-provenance/) | Sat 09:10 - 10:48 | indices 22-29 (8 prompts) | `provenance_subdirectory_c4417ba1.plan.md` | the `provenance/` directory itself, plus three subsequent commits done in the same span (rules+sweep, master AGENTS.md, SYSTEM_CARD+LICENSE) that share Phase 06's prompt range |
| 07 | [Self-containment + new plots](phases/07-self-containment-plus-plots/) | Sat 15:06+ | indices 30+ (2 prompts) | `self-contain_plus_new_plots_8ed9167e.plan.md` | `data/scontrol_show_node.json.gz`, `pipeline/plot_cumulative_power.py`, `pipeline/plot_stacked_power.py`, `median_power` column, multi-plot Step 3 |

## What happened in each phase, at a glance

~~~mermaid
timeline
    title Session arc
    Phase 01 : "initial pipeline (PostgreSQL to CSVs to 4-bar plot)"
             : "sys_power priority + host-name irregularity in one SQL"
             : "reference lines added at 16.5 / 33 / 49.5 kW"
    Phase 02 : "random per-cabinet selection to drop peak by 40%"
             : "global Slurm partition floor with seeded retries"
             : "restoration of zero-remaining partitions"
             : "average-after bar + summary stats text box on plot"
    Phase 03 : "standalone scontrol reservation command generator"
             : "SPEC_NODES added then removed (Slurm sets it itself)"
    Phase 04 : "per-partition impact CSV"
             : "auto-discover GPU types from gres regex"
             : "filter to non-empty rows + compact _pre/_rm/_post headers"
    Phase 05 : "git init r9_pod_a_pipeline only, branch main"
             : "single import commit d6bb680"
    Phase 06 : "provenance subdirectory captures everything above"
             : "agent-rules + AGENTS.md as canonical entry point"
             : "SYSTEM_CARD.md and MIT LICENSE"
    Phase 07 : "ship gzipped scontrol snapshot, gzip-aware loader"
             : "cumulative-power and stacked-power plots reimplemented"
             : "median_power added to node_stats; multi-plot Step 3"
~~~

## Cross-references

- Plans live in `~/.cursor/plans/` outside the repo and are also copied
  verbatim to each phase's `plan.md`.
- The parent transcript is at
  `~/.cursor/projects/Users-cnh-projects-power-work-r9/agent-transcripts/fec1d6d6-3e05-4db6-99ec-6d712cea59ee/fec1d6d6-3e05-4db6-99ec-6d712cea59ee.jsonl`.
- The original problem statement is at
  [`context/original_AGENT_INSTRUCTIONS.md`](context/original_AGENT_INSTRUCTIONS.md).
- The post-session updated spec (with new sections describing the
  delivered pipeline, pitfalls, and "how to extend") is at
  [`context/updated_AGENT_INSTRUCTIONS.md`](context/updated_AGENT_INSTRUCTIONS.md).
