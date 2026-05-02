# AGENTS.md

Single entry point for any AI agent (or human) working in this repository.
Read this first; the navigation map below points at every other document
of record. Update this file whenever you change something it points at.

## Purpose

`r9_pod_a_pipeline` is a spec-compliant power-analysis pipeline for the
row 9 / pod A section of an HPC cluster, plus an opt-in downstream
toolchain (random-selection-based reduction, partition-impact summary,
Slurm reservation generator) built on top of it. It implements the
three-task spec in
[`../telegraf_data/AGENT_INSTRUCTIONS.md`](../telegraf_data/AGENT_INSTRUCTIONS.md)
(in-repo snapshot:
[`provenance/context/original_AGENT_INSTRUCTIONS.md`](provenance/context/original_AGENT_INSTRUCTIONS.md)).

## Scope

In this repo:

- the four-stage SQL + Python pipeline that exports `dcim_nodes`, picks
  the preferred power sensor per host (`sys_power`-authoritative), pulls
  per-host bucketed time-series, and renders a 4-bar-per-cabinet plot;
- the opt-in reduction stage (`select_reduction_nodes.py`,
  `summarize_by_partition.py`,
  `plot_cabinet_bars_with_reduction.py`);
- the standalone reservation generator (`make_reservation.py`);
- the agent-rules under [`agent-rules/`](agent-rules/);
- the session provenance under [`provenance/`](provenance/);
- the bundled Slurm partition snapshot under [`data/`](data/)
  (`scontrol_show_node.json.gz`, ~86 KB compressed; the gzip-aware
  loader in `pipeline/` accepts the `.gz` form by default and
  transparently falls through to plain `.json`).

Not in this repo (kept in adjacent directories of the surrounding
`power-work-r9/` workspace):

- `telegraf_data/` -- legacy / experimental scripts that predate this
  repo; read-only reference. No live code path in this repo depends
  on it now.
- `monitoring/`, `node_users/` -- unrelated experimental subdirectories
  in the surrounding workspace.

## Navigation map

If you want to know X, read Y:

| Want | Read |
| --- | --- |
| What this code does and how to run it | [`README.md`](README.md) |
| Why it is structured this way; parameter surface; data flow diagram | [`DESIGN.md`](DESIGN.md) |
| Outside-evaluator overview: capabilities, reusable parts, adaptation guide | [`SYSTEM_CARD.md`](SYSTEM_CARD.md) |
| License terms (MIT) | [`LICENSE`](LICENSE) |
| Markdown / Mermaid authoring rules used in this repo | [`agent-rules/RULES_FOR_MDR_MARKDOWN.md`](agent-rules/RULES_FOR_MDR_MARKDOWN.md), [`agent-rules/MERMAID_DIAGRAM_RULES.md`](agent-rules/MERMAID_DIAGRAM_RULES.md) |
| The original problem statement that started everything | [`provenance/context/original_AGENT_INSTRUCTIONS.md`](provenance/context/original_AGENT_INSTRUCTIONS.md) |
| Chronological session history (plans + prompts + decisions per phase) | [`provenance/TIMELINE.md`](provenance/TIMELINE.md) and [`provenance/README.md`](provenance/README.md) |
| SQL queries (postgresql; sys_power priority + host-name irregularity encoded here) | [`sql/`](sql/) |
| Python pipeline stages (one file per export / plot / select step) | [`pipeline/`](pipeline/) |
| Top-level orchestrator | [`run_pipeline.py`](run_pipeline.py) |
| Standalone reservation generator | [`make_reservation.py`](make_reservation.py) |

## Authoring rules at a glance

Full text in [`agent-rules/`](agent-rules/). The big ones:

- Use tilde fences `~~~`, never backticks. No language hints (one
  exception: keep `~~~mermaid` so renderers parse the diagram).
- Use 4-space indented blocks for SQL, JSON, file trees, and shell
  command listings.
- No `---` horizontal rules. Use numbered `##` headings instead.
- Bold labels above fences, with a blank line between label and fence.
- Always have prose between adjacent fences.
- No `#` lines inside fenced blocks.
- In Mermaid: no spaces in node IDs, no `<br/>` in labels, double-quote
  labels containing parentheses / colons / forward slashes, give every
  subgraph an explicit ID.

## Verbatim-content exemption

These files are intentionally exempt from the authoring rules because
their value depends on bit-for-bit fidelity to their source:

- `provenance/phases/*/plan.md` -- direct copies of files in
  `~/.cursor/plans/`. Their format is determined by Cursor's plan tool.
- `provenance/phases/*/user_prompts.md` -- verbatim user prompts from
  the parent transcript. Wrapper formatting is rule-compliant; the
  prompt bodies inside the wrappers are not edited.
- `provenance/phases/*/assistant_responses.md` -- same convention as
  `user_prompts.md`.
- `provenance/context/updated_AGENT_INSTRUCTIONS.md` -- direct copy of
  `../telegraf_data/AGENT_INSTRUCTIONS.md`; do not edit here, edit the
  source.

If you re-run [`provenance/scripts/extract_session.py`](provenance/scripts/extract_session.py),
the regenerated prompt / response / clarification files will use
rule-compliant wrappers automatically.

## Maintenance

When you add a section to this file, change a pointed-at document, or
materially change the project's scope or structure, update the
**Last updated** date below in the same commit. Keep this file under
about 100 lines; offload detail to the documents it points at.

Last updated: 2026-05-02
