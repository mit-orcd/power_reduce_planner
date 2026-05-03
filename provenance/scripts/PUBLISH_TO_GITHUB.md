# Publishing r9_pod_a_pipeline to GitHub as mit-orcd/power_reduce_planner

This document holds the `gh` commands that take the existing local
`r9_pod_a_pipeline` repository and publish it as a new public GitHub
repository at
[`https://github.com/mit-orcd/power_reduce_planner`](https://github.com/mit-orcd/power_reduce_planner).
The local history (which already contains an MIT `LICENSE`) is pushed
verbatim; nothing is rewritten. The commands are reference / copy-paste
material -- this file does not execute them.

The local directory name (`r9_pod_a_pipeline`) intentionally differs
from the GitHub repository name (`power_reduce_planner`). git's remote
configuration is independent of the local directory name, so no rename
is needed and no scripts have to change.


## 1. Preconditions

Before starting, confirm all of the following:

- `gh` (GitHub CLI) is installed and authenticated with at least the
  `repo` and `read:org` scopes.
- The authenticated GitHub account is a member of the `mit-orcd`
  organization with permission to create public repositories there.
- The local working tree is clean (no uncommitted changes) and the
  current branch is `main`.
- The local repository has no `origin` remote configured yet.
- The repository `mit-orcd/power_reduce_planner` does **not** already
  exist on GitHub.

The next section verifies all of these.


## 2. Sanity-check the local and GitHub state

Run the following from any directory; they all use absolute paths so
the working directory does not matter.

**Read-only state checks:**

    gh --version
    gh auth status
    gh api user/orgs --jq '.[].login' | grep -x mit-orcd
    gh repo view mit-orcd/power_reduce_planner 2>&1 | head -1
    git -C /Users/cnh/projects/power-work-r9/r9_pod_a_pipeline status
    git -C /Users/cnh/projects/power-work-r9/r9_pod_a_pipeline branch --show-current
    git -C /Users/cnh/projects/power-work-r9/r9_pod_a_pipeline remote -v

What each line proves:

- `gh --version` -- the CLI is on PATH.
- `gh auth status` -- the active account is logged in and the token
  scopes include at least `repo` and `read:org`.
- `gh api user/orgs ... | grep -x mit-orcd` -- the active account is a
  member of `mit-orcd`. The line should print `mit-orcd`; an empty
  result means the account either is not in the org or the token is
  missing the `read:org` scope.
- `gh repo view mit-orcd/power_reduce_planner` -- this **must fail**
  with a message like `GraphQL: Could not resolve to a Repository with
  the name 'mit-orcd/power_reduce_planner'`. A success here means the
  repo already exists; in that case skip to section 4.
- `git ... status` -- should report `nothing to commit, working tree
  clean`.
- `git ... branch --show-current` -- should print `main`.
- `git ... remote -v` -- should print nothing. If an `origin` remote is
  already set, the create command in section 3 will fail; remove it
  with `git -C /Users/cnh/projects/power-work-r9/r9_pod_a_pipeline
  remote remove origin` before continuing.


## 3. Create the repo and push existing history

A single `gh repo create` invocation creates the empty GitHub repo,
adds it as the local `origin` remote, and pushes the existing local
history.

**Create-and-push:**

    gh repo create mit-orcd/power_reduce_planner \
        --public \
        --description "Power-analysis pipeline + reduction planner for HPC row 9 / pod A" \
        --source=/Users/cnh/projects/power-work-r9/r9_pod_a_pipeline \
        --remote=origin \
        --push

What each flag does:

- `mit-orcd/power_reduce_planner` -- positional `OWNER/NAME`. Owner is
  the organization, name is the new repository.
- `--public` -- visibility. The organization must permit members to
  create public repos; otherwise `gh` will surface a permissions
  error.
- `--description "..."` -- one-line description shown on the GitHub
  repo page and in API responses. Optional; can be edited later with
  `gh repo edit`.
- `--source=/Users/cnh/projects/power-work-r9/r9_pod_a_pipeline` --
  use this existing local repository as the source. With `--source`,
  `gh` does **not** scaffold a new working tree; it only attaches the
  remote.
- `--remote=origin` -- name of the git remote to add locally. Defaults
  to `origin` but is set explicitly for clarity.
- `--push` -- push the current local branch to the new remote
  immediately. Because the local branch is `main`, GitHub's default
  branch for the new repo is set to `main` automatically.

**Note on `--license`:** the `--license MIT` flag is intentionally
omitted. That flag tells GitHub to scaffold a fresh `LICENSE` file,
which only makes sense for an empty repo created without `--source`.
The local history already includes an MIT `LICENSE` (committed in
`a38aaf1`); it lands on GitHub as part of the first push and GitHub
auto-detects it as MIT.


## 4. Verify

After section 3 succeeds, confirm the result.

**Post-push checks:**

    git -C /Users/cnh/projects/power-work-r9/r9_pod_a_pipeline remote -v
    git -C /Users/cnh/projects/power-work-r9/r9_pod_a_pipeline branch -vv
    gh repo view mit-orcd/power_reduce_planner
    gh api repos/mit-orcd/power_reduce_planner --jq '{name, visibility, default_branch, license: .license.spdx_id}'

What to look for:

- `git remote -v` -- prints `origin
  https://github.com/mit-orcd/power_reduce_planner.git (fetch)` and
  `(push)`.
- `git branch -vv` -- shows `main` tracking `origin/main`.
- `gh repo view` -- prints the description, the visibility (`public`),
  the default branch (`main`), and the most recent commit subject.
- The final `gh api ... --jq` line should print a one-line JSON object
  with `"name": "power_reduce_planner"`, `"visibility": "public"`,
  `"default_branch": "main"`, and `"license": "MIT"`. The `MIT` value
  is auto-detected from the committed `LICENSE` file; if it shows as
  `null`, GitHub has not finished its license scan yet -- re-run the
  command after a few seconds.


## 5. Optional follow-ups

These are not required to publish; they are conveniences that can be
added later.

**Open the new repo in a browser:**

    gh repo view mit-orcd/power_reduce_planner --web

This launches the default browser at the repo's GitHub page, which is
the easiest way to spot-check the rendered README and LICENSE.

**Add discoverability topics:**

    gh repo edit mit-orcd/power_reduce_planner --add-topic hpc --add-topic slurm --add-topic power-monitoring

Topics show up in the GitHub UI and improve search hits.

**Protect the `main` branch:**

    gh api -X PUT repos/mit-orcd/power_reduce_planner/branches/main/protection -f required_status_checks=null -F enforce_admins=true -f required_pull_request_reviews=null -f restrictions=null

This is a minimal protection ruleset (admin enforcement on, no PR
review requirement, no status checks). Adjust to taste; the GitHub web
UI is usually friendlier for fine-tuning protection rules.


## 6. Re-running and recovery notes

The create-and-push step in section 3 is **not** idempotent: a second
invocation against an already-created repo fails because the repo and
the local `origin` remote both already exist.

**If the create succeeded but the push failed** (e.g., transient
network error), the repo exists empty on GitHub and the local `origin`
remote is set. Recover with a plain push:

    git -C /Users/cnh/projects/power-work-r9/r9_pod_a_pipeline push -u origin main

Then jump to section 4 to verify.

**If the repo already exists on GitHub but the local `origin` is not
set**, attach it manually and push:

    git -C /Users/cnh/projects/power-work-r9/r9_pod_a_pipeline remote add origin https://github.com/mit-orcd/power_reduce_planner.git
    git -C /Users/cnh/projects/power-work-r9/r9_pod_a_pipeline push -u origin main

Then jump to section 4.

**Destructive reset (only if you really need section 3 to run from
scratch again):**

    gh repo delete mit-orcd/power_reduce_planner --yes
    git -C /Users/cnh/projects/power-work-r9/r9_pod_a_pipeline remote remove origin

This permanently deletes the GitHub repo (including any issues, PRs,
or stars it has accumulated) and clears the local remote so section 3
can be re-run. Do not run these commands unless you are certain
nothing of value lives only on the remote.
