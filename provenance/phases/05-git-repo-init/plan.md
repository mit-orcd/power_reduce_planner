---
name: init r9 pipeline git repo
overview: Convert `/Users/cnh/projects/power-work-r9/r9_pod_a_pipeline` (and only that directory) into a standalone git repository with `main` as the initial branch and a single import commit. Existing `.gitignore` is already correct, so no source changes are needed -- this is purely a `git init` + `git commit` exercise.
todos:
  - id: init
    content: git init -b main inside r9_pod_a_pipeline/
    status: completed
  - id: stage_check
    content: git add . then run git status; verify the 22 expected source files plus output/.gitkeep are staged and that no output/, __pycache__/, .venv/, or *.pyc paths leaked in
    status: completed
  - id: commit
    content: Create the single initial commit with a descriptive title and a body listing the major pieces (SQL exports, plots, reduction selection, partition summary, reservation generator)
    status: completed
  - id: verify
    content: git log --stat -1 and git status to confirm a clean working tree on main with one commit
    status: completed
isProject: false
---

## What gets initialized

`/Users/cnh/projects/power-work-r9/r9_pod_a_pipeline/` becomes its own repo. Sibling directories (`telegraf_data/`, `monitoring/`, `node_users/`, root-level CSVs, etc.) are out of scope per your clarification -- they remain plain directories on disk, untouched.

## State of the world (verified)

- No existing `.git` inside `r9_pod_a_pipeline/` -- `git init` will not collide with anything.
- `[r9_pod_a_pipeline/.gitignore](r9_pod_a_pipeline/.gitignore)` already excludes the right things: `output/*` (with `!output/.gitkeep` to keep the directory), `__pycache__/`, `*.pyc`, `.venv/`. **No edits needed.**
- Global `git config user.name` / `user.email` are set, so `git commit` will succeed without touching git config.
- 22 files will be tracked: `.gitignore`, `README.md`, `DESIGN.md`, `requirements.txt`, `commands` (3-line shell scratch with `export PGPASSWORD=...; python run_pipeline.py ...`), `config.py`, `pg_client.py`, `run_pipeline.py`, `make_reservation.py`, the seven `pipeline/*.py` files (incl. `__init__.py`), and the four `sql/0?_*.sql` files. Plus `output/.gitkeep` so the empty directory survives.
- Existing `__pycache__/` and `pipeline/__pycache__/` directories on disk will be ignored automatically.

## Steps

1. **Init the repo with `main` as the default branch.** Modern default; matches what most hosting providers expect.
   ```bash
   cd /Users/cnh/projects/power-work-r9/r9_pod_a_pipeline
   git init -b main
   ```
2. **Stage everything.** The existing `.gitignore` does the filtering for us.
   ```bash
   git add .
   ```
3. **Sanity-check what's about to be committed.** Print `git status` and verify (a) all 22 source files are listed as new, (b) `output/.gitkeep` is present but no other `output/` files appear, (c) no `__pycache__` or `.venv` paths are staged. Abort and report if anything looks off.
4. **Single import commit.**
   ```bash
   git commit -m "Initial import: row 9 / pod A power-reduction pipeline"
   ```
   Body of the commit message will list the high-level pieces (SQL exports, plot, reduction selection, partition summary, reservation generator) so `git log -1` reads usefully.
5. **Verify** with `git log --stat -1` and `git status` (should be clean working tree on `main`).

## Notes / non-blocking caveats

- **External path dependency on `../telegraf_data/scontrol_show_node.json`.** `[r9_pod_a_pipeline/pipeline/select_reduction_nodes.py](r9_pod_a_pipeline/pipeline/select_reduction_nodes.py)` and `[r9_pod_a_pipeline/pipeline/summarize_by_partition.py](r9_pod_a_pipeline/pipeline/summarize_by_partition.py)` default to `../telegraf_data/scontrol_show_node.json`. After the repo is independent, anyone cloning it elsewhere will need to either provide that file at the same relative path or pass `--scontrol-json PATH`. Not fixing in this plan; happy to follow up with one of: copy a snapshot into `r9_pod_a_pipeline/data/`, change the default to a path inside the repo, or add a setup script to fetch/symlink the file.
- **No remote added.** You didn't ask for one. `git remote add origin ...` and an initial `git push -u origin main` can be tacked on whenever you have a hosting URL.
- **`commands` file** -- it's a 3-line scratch that mostly duplicates the README quickstart. Including it in the import; trivial to remove later if you'd rather it not live in version control.
- **No git config changes.** Your global identity is already set; the project rules forbid me from touching `git config` regardless.

## What I will NOT do (per project safety rules)

- No `git push` (no remote anyway).
- No `git config` changes.
- No `--force` of any kind.
- No edits to source files; the `.gitignore` is already correct.