# Decisions — Phase 06 (Provenance subdirectory)

## Hierarchy

- **Per-phase directories** instead of by-type top-level
  (`plans/`, `prompts/`, `decisions/`). Stories of features are easier to
  follow when everything is in one place; cross-cutting browsing is
  served by `TIMELINE.md` + `README.md`.
- **Six phases**, matching the natural rhythm of the session
  (bootstrap, reduction, reservation, partition summary, git init,
  provenance itself). Boundaries chosen by user-message index ranges
  rather than wall-clock; locked into the extractor's `PHASES` table.

## Depth (clarification answer)

User chose **full_log** -- so each phase carries:

- `plan.md` (verbatim from `~/.cursor/plans/`),
- `user_prompts.md` (verbatim from the parent transcript),
- `assistant_responses.md` (verbatim text + tool_use stubs from the same
  transcript),
- `clarifications.md` (verbatim AskQuestion + the user's selected
  option),
- `decisions.md` (hand-written distillation of the trade-offs the phase
  resolved + bug fixes),
- `change_requests.md` (post-delivery refinements).

## What was deliberately stripped

- **Internal `thinking` blocks.** They are user-invisible by design and
  voluminous; including them would triple the size of the provenance
  for little narrative value beyond what `decisions.md` already captures.
- **Full tool_use payloads.** Replaced by one-line italic stubs like
  `[Shell(description='...')]`. Keeps `assistant_responses.md` readable
  without dumping multi-megabyte command outputs.
- **The transcript JSONL itself.** External and large. The extractor
  script is enough to rebuild the markdown if the transcript is
  refreshed; keeping a frozen copy in git would just diverge.

## Where the user answers come from

- **The transcript does not preserve AskQuestion selections.** Verified
  by walking the JSONL for `tool_result` records (none exist) and by
  reading every user record in the stream (24 of them, all surface
  prompts with no answer-only entries between them and the next
  assistant record).
- **Answers are recorded in `KNOWN_ANSWERS` inside `extract_session.py`**
  keyed by `"<phase_name>:<question_id>"`. The script populates the
  `**User answer:**` line in each `clarifications.md` from this table.
  If a transcript refresh introduces new questions, they need adding
  here too; the script will print
  `(not recorded; transcript does not preserve AskQuestion responses)`
  for missing entries.

## Self-reference

- **Phase 06's own README, decisions, and change_requests are written
  by hand** during the same task that creates the rest of the directory
  -- they describe themselves. The `assistant_responses.md` for this
  phase is the running log of that work.
- **Plan 06 is checked in just like the others** so the structure is
  uniform across all six phases.

## Out of scope

- **Subagent transcripts.** None spawned this session. The system
  instructions also forbid citing subagent UUIDs.
- **Markdown rendering tooling** (e.g., a static-site generator).
  Plain markdown is sufficient for git diff and casual browsing.
