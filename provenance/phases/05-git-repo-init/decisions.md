# Decisions — Phase 05 (Git repo init)

## Scope

- **Only `r9_pod_a_pipeline/`** becomes a git repo. The rest of
  `/Users/cnh/projects/power-work-r9/` (telegraf_data/, root CSVs,
  monitoring/, node_users/) stays as plain directories on disk per the
  user's clarification. This sidestepped the entire nested-repo question
  (the AskQuestion about `monitoring/.git` and `node_users/.git` became
  moot).

## Branch and history

- **Initial branch `main`.** Modern default; matches what most hosting
  providers (GitHub / GitLab / Gitea) expect.
- **Single import commit** rather than reconstructed phase-by-phase
  history. The user asked to "convert to a git repo" -- a single
  snapshot is what that minimally means and is the least surprising
  outcome.

## Repo contents

- **Existing `.gitignore`** already correct (`output/*`,
  `!output/.gitkeep`, `__pycache__/`, `*.pyc`, `.venv/`). No edits.
- **`output/.gitkeep`** ensures the empty output directory survives the
  import.
- **Existing `__pycache__/`** directories on disk got filtered
  automatically by the `.gitignore` -- verified via the pre-commit
  `git status` sanity check.

## Identity / safety

- **No `git config` changes.** Project safety rule plus user's global
  identity (`Christopher <christophernhill@gmail.com>`) was already
  configured.
- **No remote.** User didn't ask. Adding later via
  `git remote add origin <url> && git push -u origin main` is a one-liner
  whenever a hosting destination is decided.
- **No `git push --force`, no `git config --global` writes**, per
  project safety rules.

## Sanity check before commit

`git add .` followed by `git status` to verify:

1. all 23 expected source paths listed as new,
2. `output/.gitkeep` present but no other `output/` paths,
3. no `__pycache__`, `.venv`, or `*.pyc` paths.

The plan called this out as an explicit step ("abort and report if
anything looks off"); it passed cleanly so the commit went through
without intervention.

## Out of scope (intentionally)

- **External path dependency** (`../telegraf_data/scontrol_show_node.json`)
  -- noted as future work in the README and DESIGN.md, not fixed in this
  phase.
- **Existing `monitoring/.git` and `node_users/.git`** -- left untouched
  because they're outside our new repo's scope.
