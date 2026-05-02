# Phase 06 — Provenance subdirectory

**When:** Saturday May 2, 09:10+ (UTC-4)
**User prompts:** 2+ (indices 22+, open-ended)
**Plan:** [`plan.md`](plan.md) (`provenance_subdirectory_c4417ba1.plan.md`)
**Result on disk:** the entire `provenance/` subdirectory you are reading
right now, captured by a follow-up commit on top of `d6bb680`.

## What came in

> "Make a detailed plan for adding the background prompting and plan
> information that the agentic session has used so far. I want the git
> repository to include all the agentic steps and reasoning for tracking
> provenance and tracking future development. Make a plan for a sequence
> and/or hierarchy of information that is stored in a sub-directory in
> the repository. Then plan to populate with all the plans and initial
> context provided and all the prompts and key pieces of reasoning."

## What was decided up front

One AskQuestion: how deep should the captured reasoning go? Three
options (lean / narrative / full_log). User chose **full_log** -- that's
why every phase has both `decisions.md` (distilled) and
`assistant_responses.md` (verbatim text from the transcript).

See [`clarifications.md`](clarifications.md) for the verbatim choice and
[`decisions.md`](decisions.md) for the reasoning.

## What was built

A six-phase hierarchy under `provenance/`:

    provenance/
        README.md, TIMELINE.md
        context/    -- original and updated AGENT_INSTRUCTIONS specs
        scripts/    -- one-shot extract_session.py
        phases/01..06/
            README.md, plan.md, user_prompts.md, assistant_responses.md,
            clarifications.md (when applicable),
            decisions.md, change_requests.md (when applicable)

The extractor [`scripts/extract_session.py`](../../scripts/extract_session.py)
is std-lib only and can be re-run any time the parent transcript is
updated. AskQuestion answers are looked up from a `KNOWN_ANSWERS` table
inside the script because the transcript itself does not preserve
user-side selections (they're processed silently between assistant
records).

## Self-reference

This is the only phase whose own files document themselves -- the
`assistant_responses.md` here is the running log of the work that wrote
the surrounding markdown. That's deliberate: provenance for the
provenance phase keeps the recursion sharp.

## Files in this phase directory

| File | Purpose |
| --- | --- |
| [`plan.md`](plan.md) | the accepted plan for this phase |
| [`user_prompts.md`](user_prompts.md) | the prompts that drove this phase |
| [`assistant_responses.md`](assistant_responses.md) | every visible assistant text block plus tool-call stubs |
| [`clarifications.md`](clarifications.md) | the depth question (lean / narrative / full_log) |
| [`decisions.md`](decisions.md) | distilled per-phase decisions for the structure / tooling |
