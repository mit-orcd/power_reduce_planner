# Clarifications (AskQuestion) for 01-pipeline-bootstrap

Each entry shows the question, the offered options, and the user's selection. User selections are looked up in the `KNOWN_ANSWERS` table inside `extract_session.py` because the transcript does not preserve them.

## Clarification #1
### Question `location`: Where should the new code live? The spec says 'new git sub-directory' but a partial implementation already exists in telegraf_data/.

- **new_subdir_under_telegraf**: New sub-directory inside telegraf_data/ (e.g. telegraf_data/r9_pod_a_pipeline/), reusing config conventions but writing fresh, spec-compliant code
- **new_top_level**: Brand-new top-level directory (e.g. r9_pod_a_pipeline/) at the repo root, fully independent from telegraf_data/
- **refactor_in_place**: Skip the 'new directory' wording and refactor existing telegraf_data/ scripts in place to match the spec (sys_power rule, pod column, include all cabinets)

**User answer:** new_top_level

### Question `agents`: How should the 4-role 'Process' section be handled?

- **literal_subagents**: Literally spawn 4 specialist subagents in parallel (DB expert, software engineer, architect, docs) via the Task tool, each producing their artifact
- **single_agent_roles**: I (single agent) do all four roles sequentially, producing the same artifacts (queries, code, design notes, docs) without spawning subagents
- **ignore_process**: Treat the 4-role section as flavor text - just produce working, well-documented code without role-based artifacts

**User answer:** single_agent_roles

## Clarification #2
### Question `pg_creds`: PGPASSWORD is not set in this shell. The tunnel on :5433 is up. How should I authenticate for the smoke run?

- **claude_md**: Use the convention from telegraf_data/CLAUDE.md (user 'postgres', PGPASSWORD from my environment) - I'll set it manually and re-run
- **agent_md**: Use AGENT_INSTRUCTIONS.md value (user 'readonly_user' / password 'orcd_rw') - which would mean updating config.py to that user
- **skip_smoke**: Skip the live DB smoke run entirely - mark the todo done based on syntax/import checks only

**User answer:** agent_md

