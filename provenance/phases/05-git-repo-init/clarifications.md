# Clarifications (AskQuestion) for 05-git-repo-init

Each entry shows the question, the offered options, and the user's selection. User selections are looked up in the `KNOWN_ANSWERS` table inside `extract_session.py` because the transcript does not preserve them.

## Clarification #1
### Question `nested_repos`: How should I handle the existing inner repos at monitoring/ and node_users/ when initializing the outer repo?

- **ignore**: Ignore them (add monitoring/ and node_users/ to the root .gitignore). Their independent histories stay intact and the outer repo never tracks them. Simplest, no risk to existing history.
- **submodules**: Make them git submodules. Preserves their independent histories and lets contributors clone them on demand. Requires each inner repo to have an 'origin' remote set; if they don't, I'll need to ask you for one or skip them.
- **absorb**: Absorb them as plain directories of the outer repo. Deletes their inner .git folders (irreversibly loses their independent history) and tracks all their files directly. Most invasive.

**User answer:** (no option selected; user clarified separately that the request was actually about r9_pod_a_pipeline/ only)

