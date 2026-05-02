# Session provenance

This directory captures the entire agentic session that produced the
`r9_pod_a_pipeline` codebase: the original spec, every formal plan
verbatim, every verbatim user prompt, every visible assistant response,
the AskQuestion clarifications and the user's selections, distilled
per-phase decisions, and per-phase narrative summaries.

Source of truth is **parent transcript UUID**
`fec1d6d6-3e05-4db6-99ec-6d712cea59ee`. Anyone who has access to the
local Cursor agent-transcripts directory can re-run
[`scripts/extract_session.py`](scripts/extract_session.py) to verify
that the verbatim files in `phases/*/user_prompts.md` and
`phases/*/assistant_responses.md` match the transcript.

## Layout

The directory tree, with one-line annotations:

    provenance/
        README.md          (this file)
        TIMELINE.md        chronological one-pager linking every phase
        context/
            original_AGENT_INSTRUCTIONS.md   pre-session spec
            updated_AGENT_INSTRUCTIONS.md    post-session spec
        scripts/
            extract_session.py               one-shot transcript extractor
        phases/
            01-pipeline-bootstrap/
            02-reduction-selection/
            03-reservation-generator/
            04-partition-summary/
            05-git-repo-init/
            06-provenance/

Each phase directory contains:

| File | Source | Hand-written? |
| --- | --- | --- |
| `plan.md` | copied verbatim from `~/.cursor/plans/` | no |
| `user_prompts.md` | extracted verbatim from the transcript | no |
| `assistant_responses.md` | extracted from the transcript (text + tool stubs) | no |
| `clarifications.md` (when applicable) | extracted from the transcript with user choices from `KNOWN_ANSWERS` | partly (the answers) |
| `README.md` | narrative of what came in, was decided, was built, was iterated | yes |
| `decisions.md` | distilled key trade-offs, mid-flight bug fixes | yes |
| `change_requests.md` (when applicable) | post-delivery refinements | yes |

## What is not captured

- **Internal `thinking` blocks.** Never user-facing; voluminous; would
  triple the size of the provenance for marginal narrative value.
- **Full tool-call payloads** (Shell stdout, file contents). Replaced by
  one-line italic stubs like
  `_[Shell(description='git init -b main inside r9_pod_a_pipeline/')]_`
  inside `assistant_responses.md`.
- **Subagent transcripts.** None were spawned this session.
- **The raw transcript JSONL.** External, large, would diverge if the
  transcript is updated. The extractor script is enough to rebuild from
  it.

## Authoring rule compliance

The hand-written files in this directory follow the markdown and
Mermaid rules in [`../AGENTS.md`](../AGENTS.md) (which points at
[`../agent-rules/`](../agent-rules/)).

The verbatim files (`plan.md`, `user_prompts.md`,
`assistant_responses.md`, `context/updated_AGENT_INSTRUCTIONS.md`) are
intentionally exempt because their value depends on bit-for-bit fidelity
to their source. The extractor script's output wrappers are
rule-compliant; the prompt / response bodies inside the wrappers are
not edited.

## Re-extracting from the transcript

If the parent transcript is updated (or a new one is created and you
want to reset this directory), from the `provenance/scripts/` directory:

    python extract_session.py --list

prints all user-message timestamps. Edit `PHASES` at the top of
`extract_session.py` to match the new boundaries; add any new
`question_id` keys to `KNOWN_ANSWERS`. Then re-run without `--list`:

    python extract_session.py

That rewrites all `user_prompts.md`, `assistant_responses.md`, and
`clarifications.md` files. Hand-written files (`README.md`,
`decisions.md`, `change_requests.md`) are not touched and need updating
manually.

## Where to start reading

- For a one-page overview: [`TIMELINE.md`](TIMELINE.md).
- For the original problem statement: [`context/original_AGENT_INSTRUCTIONS.md`](context/original_AGENT_INSTRUCTIONS.md).
- For "how did this end up the way it did": each phase's `README.md`.
- For "what was the literal back-and-forth": each phase's
  `user_prompts.md` and `assistant_responses.md`.
