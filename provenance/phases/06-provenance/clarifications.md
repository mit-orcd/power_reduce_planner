# Clarifications (AskQuestion) for 06-provenance

Each entry shows the question, the offered options, and the user's selection. User selections are looked up in the `KNOWN_ANSWERS` table inside `extract_session.py` because the transcript does not preserve them.

## Clarification #1
### Question `depth`: How deep should the captured 'reasoning' go for each phase?

- **lean**: Lean: per phase capture verbatim plan + verbatim user prompts + a short decisions.md (3-8 bullet points covering the major trade-offs the plan resolved). ~30 short markdown files, ~100KB total. Easy to skim.
- **narrative**: Narrative: same as Lean PLUS a hand-written README.md per phase that tells the story (what came in, what was decided, what was built, what was fixed mid-flight, what was iterated on after delivery). ~35 files, ~150KB. Reads like a project history.
- **full_log**: Full log: same as Narrative PLUS a per-phase assistant_responses.md extracting every assistant reply from the transcript. ~40 files, ~250-300KB. Captures my visible reasoning and corrections in real time but a lot of it duplicates the plan / responses already cited elsewhere.

**User answer:** full_log

