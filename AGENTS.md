# AGENTS.md

Authoring rules for any AI agent (or human) modifying markdown in this
repository. Read these before editing or adding any `.md` file.

## Required reading

- [`agent-rules/RULES_FOR_MDR_MARKDOWN.md`](agent-rules/RULES_FOR_MDR_MARKDOWN.md)
  -- 9 rules for writing markdown that renders correctly under the `mdr`
  viewer (works around mdr issue 30 and other fence-rendering bugs).
- [`agent-rules/MERMAID_DIAGRAM_RULES.md`](agent-rules/MERMAID_DIAGRAM_RULES.md)
  -- Mermaid syntax rules and a checking procedure derived from real bugs
  in adjacent repositories.

## Quick summary

The big ones (full text in the rules files):

- Use tilde fences `~~~`, never backticks. No language hints.
- Use 4-space indented blocks for SQL, JSON, file trees, and shell
  command listings.
- No `---` horizontal rules. Use numbered `##` headings instead.
- Bold labels above fences, with a blank line between label and fence.
- Always have prose between adjacent fences.
- No `#` lines inside fenced blocks.
- In Mermaid: no spaces in node IDs, no `<br/>` in labels, double-quote
  labels containing parentheses / colons / forward slashes, give every
  subgraph an explicit ID.

## Scope of compliance in this repo

All hand-written markdown under this repository follows these rules.

The following files are **intentionally exempt** because they are
verbatim historical artifacts whose value depends on bit-for-bit fidelity
to their source:

- `provenance/phases/*/plan.md` -- direct copies of files in
  `~/.cursor/plans/`. Their format is determined by Cursor's plan tool.
- `provenance/phases/*/user_prompts.md` -- verbatim user prompts from the
  parent transcript. Wrapper formatting is updated to comply, but the
  prompt bodies (inside the wrappers) are not edited.
- `provenance/phases/*/assistant_responses.md` -- same convention as
  `user_prompts.md`.
- `provenance/context/updated_AGENT_INSTRUCTIONS.md` -- direct copy of
  `telegraf_data/AGENT_INSTRUCTIONS.md`; do not edit here, edit the
  source.

If you re-run `provenance/scripts/extract_session.py`, the regenerated
prompt / response / clarification files will use rule-compliant wrappers.
