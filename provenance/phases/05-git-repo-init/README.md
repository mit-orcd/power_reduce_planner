# Phase 05 — Git repository init

**When:** Saturday May 2, 08:53 to 09:10 (UTC-4)
**User prompts:** 4 (indices 18-21)
**Plan:** [`plan.md`](plan.md) (`init_r9_pipeline_git_repo_11e69107.plan.md`)
**Result on disk:** `.git/` inside `r9_pod_a_pipeline/`, single root commit
`d6bb680` titled "Initial import: row 9 / pod A power-reduction pipeline" on
branch `main`.

## What came in

User pointed out the directory was not a git repo and asked to convert it.
Initial AskQuestion explored what to do with two existing inner repos at
`monitoring/.git` and `node_users/.git`, but the user didn't pick an
option and instead clarified the actual scope:

> "Apologies - I meant make /Users/cnh/projects/power-work-r9/r9_pod_a_pipeline
> into a git repository. That is where the reference code belongs. The
> other directories and content are older experimental and learning
> material."

So the scope was just `r9_pod_a_pipeline/` -- the rest of the workspace
stayed untouched. (The user re-sent the same clarification message twice
during a workspace-folder change; both copies are visible in
`user_prompts.md` at indices 19 and 20.)

## What was decided up front

After the scope clarification, no further AskQuestion was needed:

- Single repo at `r9_pod_a_pipeline/` only.
- Initial branch `main`.
- Single import commit (no attempt to reconstruct logical history).
- `.gitignore` already correct (`output/*`, `__pycache__/`, `*.pyc`,
  `.venv/`) -- no edits.
- No git config changes (project rule + user identity already configured
  globally).

See [`decisions.md`](decisions.md) for the reasoning.

## What was built

`git init -b main` then `git add .` then a single commit. 23 files
tracked: 22 source files plus `output/.gitkeep`. No `output/` data files,
no `__pycache__/`, no `.venv/`, no `*.pyc` leaked in -- the existing
`.gitignore` did the filtering.

Final state:

```
commit d6bb680ec50f711db6b80bc225d9d9284d2bc606 (HEAD -> main)
Author: Christopher <christophernhill@gmail.com>
Date:   Sat May 2 09:03:47 2026 -0400

    Initial import: row 9 / pod A power-reduction pipeline
    [body listing the major pieces]

 23 files changed, 2268 insertions(+)
```

## Known follow-ups (not done in this phase)

- **External path dependency.**
  [`pipeline/select_reduction_nodes.py`](../../../pipeline/select_reduction_nodes.py)
  and
  [`pipeline/summarize_by_partition.py`](../../../pipeline/summarize_by_partition.py)
  default `--scontrol-json` to `../telegraf_data/scontrol_show_node.json`,
  which only resolves from the original working copy. Anyone cloning this
  repo elsewhere needs to either provide the file at the same relative
  path or pass `--scontrol-json PATH`. Tracked but not fixed; possible
  fixes (snapshot into `data/` under the repo, change the default,
  add a setup script).
- **No remote.** `git remote add origin ...` and an initial `git push -u
  origin main` to be added when a hosting destination exists.
- **`commands` file.** 3-line scratch with the basic invocation; mostly
  duplicates the README quickstart. Included in the import; trivial to
  remove later if undesired.

## Files in this phase directory

| File | Purpose |
| --- | --- |
| [`plan.md`](plan.md) | the accepted plan |
| [`user_prompts.md`](user_prompts.md) | 4 prompts in order |
| [`assistant_responses.md`](assistant_responses.md) | every visible assistant text block plus tool-call stubs |
| [`clarifications.md`](clarifications.md) | the nested-repo AskQuestion that the user side-stepped via clarification |
| [`decisions.md`](decisions.md) | distilled per-phase decisions |
