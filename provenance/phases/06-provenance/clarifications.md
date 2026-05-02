# Clarifications (AskQuestion) for 06-provenance

Each entry shows the question, the offered options, and the user's selection. User selections are looked up in the `KNOWN_ANSWERS` table inside `extract_session.py` because the transcript does not preserve them.

## Clarification #1
### Question `depth`: How deep should the captured 'reasoning' go for each phase?

- **lean**: Lean: per phase capture verbatim plan + verbatim user prompts + a short decisions.md (3-8 bullet points covering the major trade-offs the plan resolved). ~30 short markdown files, ~100KB total. Easy to skim.
- **narrative**: Narrative: same as Lean PLUS a hand-written README.md per phase that tells the story (what came in, what was decided, what was built, what was fixed mid-flight, what was iterated on after delivery). ~35 files, ~150KB. Reads like a project history.
- **full_log**: Full log: same as Narrative PLUS a per-phase assistant_responses.md extracting every assistant reply from the transcript. ~40 files, ~250-300KB. Captures my visible reasoning and corrections in real time but a lot of it duplicates the plan / responses already cited elsewhere.

**User answer:** full_log

## Clarification #2
### Question `copyright_holder`: Who should be named as the copyright holder in SYSTEM_CARD.md (and in any LICENSE file)?

- **christopher_hill**: Christopher N. Hill (the git author identity christophernhill@gmail.com)
- **mit**: Massachusetts Institute of Technology (consistent with the mit_* Slurm partitions and the MGHPCC context the data implies)
- **mit_and_chnh**: Both: 'Christopher N. Hill / Massachusetts Institute of Technology' as joint copyright
- **other_specify**: Something else - I'll specify in a follow-up message; assume placeholder '<COPYRIGHT_HOLDER>' for the plan

**User answer:** (not recorded; transcript does not preserve AskQuestion responses)

### Question `license_file`: Should this same plan also create a real LICENSE file (so the MIT license actually applies), or is the plan strictly about SYSTEM_CARD.md and LICENSE comes later?

- **include_license**: Include both: write SYSTEM_CARD.md and a standard MIT LICENSE file with the chosen copyright holder + year 2026 in this same plan
- **system_card_only**: Just SYSTEM_CARD.md for now; LICENSE is a follow-up
- **license_placeholder**: Create a LICENSE file with a TODO placeholder that points back to SYSTEM_CARD.md so the intent is recorded but the legal text waits for a confirmed copyright holder

**User answer:** (not recorded; transcript does not preserve AskQuestion responses)

