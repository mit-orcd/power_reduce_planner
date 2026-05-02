#!/usr/bin/env python3
"""Extract verbatim user prompts, assistant responses, and clarifications
from the parent agent transcript into the provenance/phases/ directory.

This is a one-shot tool. Once it has populated the per-phase markdown files,
those files are the source of truth that lives in git. Re-running the script
overwrites them, which is useful only when refreshing from an updated
transcript.

USAGE
-----
  python extract_session.py --list
      Print one line per user message: '<idx>  <timestamp>  <first 80 chars>'.
      Use this once to determine the right phase boundaries, then update the
      PHASES table below and re-run without --list.

  python extract_session.py
      Write user_prompts.md, assistant_responses.md, and (when applicable)
      clarifications.md into each phase directory under ../phases/.

CONFIGURATION
-------------
TRANSCRIPT path is hard-coded to the parent session's JSONL. PHASES is a
list of (directory_name, first_user_msg_idx, last_user_msg_idx_or_None).
last index is inclusive; None means open-ended (catches everything to the
end of the transcript).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
PROVENANCE_DIR = THIS_DIR.parent
PHASES_DIR = PROVENANCE_DIR / "phases"

PARENT_UUID = "fec1d6d6-3e05-4db6-99ec-6d712cea59ee"
TRANSCRIPT = (
    Path.home()
    / ".cursor"
    / "projects"
    / "Users-cnh-projects-power-work-r9"
    / "agent-transcripts"
    / PARENT_UUID
    / f"{PARENT_UUID}.jsonl"
)

# Phase boundaries are user-message indices (0-based, inclusive). The last
# tuple element is the inclusive end index, or None for "to end of transcript".
PHASES: list[tuple[str, int, int | None]] = [
    ("01-pipeline-bootstrap",     0,  4),
    ("02-reduction-selection",    5,  8),
    ("03-reservation-generator",  9, 13),
    ("04-partition-summary",     14, 17),
    ("05-git-repo-init",         18, 21),
    ("06-provenance",            22, None),
]

# The transcript does NOT preserve the user's AskQuestion selections (they
# are processed silently and never appear as their own record). The choices
# are recorded by hand here, keyed by "phase_name:question_id". For
# multi-question AskQuestion calls, list one entry per question.
KNOWN_ANSWERS: dict[str, str] = {
    "01-pipeline-bootstrap:location": "new_top_level",
    "01-pipeline-bootstrap:agents":   "single_agent_roles",
    "01-pipeline-bootstrap:pg_creds": "agent_md",
    "02-reduction-selection:reduction_meaning":  "at_peak_only",
    "02-reduction-selection:infeasible_behavior":
        "retry_seeds (user typed addendum: 'compute the partition constraint "
        "across all the cabinets. Use the 100 attempts for a limit to number "
        "of tries. Use the option with the least partition constraint "
        "violations if after 100 there is none outcome that meets the "
        "partition constraint.')",
    "05-git-repo-init:nested_repos":
        "(no option selected; user clarified separately that the request "
        "was actually about r9_pod_a_pipeline/ only)",
    "06-provenance:depth":            "full_log",
}

# Tags that wrap or precede the actual prompt text in the transcript. We
# strip them out so the captured prompt reads cleanly. Anything between
# matching <tag>...</tag> pairs gets collapsed; the raw text inside the
# <user_query> tag is what we want.
USER_QUERY_RE = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.DOTALL)
TIMESTAMP_RE = re.compile(r"<timestamp>\s*(.*?)\s*</timestamp>", re.DOTALL)
ATTACHED_FILES_RE = re.compile(r"<attached_files>.*?</attached_files>", re.DOTALL)
SYSTEM_REMINDER_RE = re.compile(r"<system_reminder>.*?</system_reminder>", re.DOTALL)
OPEN_FILES_RE = re.compile(
    r"<open_and_recently_viewed_files>.*?</open_and_recently_viewed_files>",
    re.DOTALL,
)
IMAGE_FILES_RE = re.compile(r"<image_files>.*?</image_files>", re.DOTALL)


def _content_text(content) -> str:
    """Return the text content of a message (concatenating list entries)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                t = c.get("text") or ""
                if t:
                    chunks.append(t)
        return "\n".join(chunks)
    return ""


def _user_text(raw: str) -> tuple[str, str]:
    """Pull (timestamp, prompt_body) out of the raw user-message text.

    Falls back to (raw_first_line, raw) if the framing is missing.
    """
    ts_m = TIMESTAMP_RE.search(raw)
    timestamp = ts_m.group(1).strip() if ts_m else ""
    q_m = USER_QUERY_RE.search(raw)
    if q_m:
        return timestamp, q_m.group(1).strip()
    cleaned = SYSTEM_REMINDER_RE.sub("", raw)
    cleaned = OPEN_FILES_RE.sub("", cleaned)
    cleaned = ATTACHED_FILES_RE.sub("", cleaned)
    cleaned = IMAGE_FILES_RE.sub("", cleaned)
    cleaned = TIMESTAMP_RE.sub("", cleaned).strip()
    return timestamp, cleaned


def _iter_records():
    if not TRANSCRIPT.exists():
        sys.stderr.write(f"Error: transcript not found at {TRANSCRIPT}\n")
        sys.exit(2)
    with TRANSCRIPT.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _collect_messages():
    """Return parallel lists: (user_records, all_records).

    user_records[i] = (idx_into_all_records, message_dict)
    all_records[k]  = full record at position k
    """
    all_records = list(_iter_records())
    user_records: list[tuple[int, dict]] = []
    for k, rec in enumerate(all_records):
        if rec.get("role") == "user":
            user_records.append((k, rec))
    return user_records, all_records


def cmd_list() -> None:
    user_records, _ = _collect_messages()
    for i, (_, rec) in enumerate(user_records):
        raw = _content_text(rec.get("message", {}).get("content"))
        ts, body = _user_text(raw)
        first = body.replace("\n", " ").strip()[:80]
        print(f"  [{i:2d}]  {ts:42s}  {first!r}")


def _format_user_prompt(idx: int, timestamp: str, body: str) -> str:
    out = [f"## User prompt #{idx}"]
    if timestamp:
        out.append(f"_{timestamp}_")
    out.append("")
    out.append("~~~")
    out.append(body)
    out.append("~~~")
    out.append("")
    return "\n".join(out)


def _assistant_chunks(message_content) -> list[tuple[str, str]]:
    """Return list of (kind, payload) for an assistant message.

    kind is one of 'text', 'tool_use'. We deliberately drop 'thinking'
    blocks (per-plan: visible reasoning only). For tool_use we keep just
    the tool name and a one-line stub.
    """
    out: list[tuple[str, str]] = []
    if isinstance(message_content, list):
        for c in message_content:
            if not isinstance(c, dict):
                continue
            ctype = c.get("type")
            if ctype == "text":
                t = (c.get("text") or "").strip()
                if t:
                    out.append(("text", t))
            elif ctype == "tool_use":
                name = c.get("name") or "?"
                inp = c.get("input") or {}
                stub_parts: list[str] = []
                for k in ("description", "command", "path", "target_directory",
                         "glob_pattern", "pattern", "query", "url", "prompt"):
                    v = inp.get(k)
                    if v:
                        s = str(v).split("\n", 1)[0]
                        if len(s) > 100:
                            s = s[:100] + "..."
                        stub_parts.append(f"{k}={s!r}")
                        break
                stub = ", ".join(stub_parts) if stub_parts else ""
                out.append(("tool_use", f"{name}({stub})" if stub else name))
    return out


def _format_assistant_message(asst_idx: int, chunks: list[tuple[str, str]]) -> str:
    if not chunks:
        return ""
    out = [f"### Assistant message #{asst_idx}"]
    out.append("")
    for kind, payload in chunks:
        if kind == "text":
            out.append(payload)
            out.append("")
        elif kind == "tool_use":
            out.append(f"_[{payload}]_")
            out.append("")
    return "\n".join(out)


_ASKQ_PATTERN = re.compile(r"\bAskQuestion\b")


def _ask_question_payloads(message_content) -> list[dict]:
    """Return any AskQuestion tool_use payloads in this assistant message."""
    out: list[dict] = []
    if isinstance(message_content, list):
        for c in message_content:
            if isinstance(c, dict) and c.get("type") == "tool_use" \
                    and c.get("name") == "AskQuestion":
                out.append(c.get("input") or {})
    return out


def _format_clarification(idx: int, payload: dict, phase_name: str) -> str:
    out = [f"## Clarification #{idx}"]
    title = payload.get("title")
    if title:
        out.append(f"**{title}**")
        out.append("")
    for q in payload.get("questions", []) or []:
        qid = q.get("id") or "?"
        out.append(f"### Question `{qid}`: {q.get('prompt') or '(no prompt)'}")
        out.append("")
        opts = q.get("options") or []
        for opt in opts:
            out.append(f"- **{opt.get('id')}**: {opt.get('label')}")
        out.append("")
        ans = KNOWN_ANSWERS.get(f"{phase_name}:{qid}")
        out.append("**User answer:** "
                   + (ans if ans else "(not recorded; transcript does not preserve AskQuestion responses)"))
        out.append("")
    return "\n".join(out)


def cmd_extract() -> None:
    user_records, all_records = _collect_messages()

    for phase_name, first, last in PHASES:
        if last is None:
            last = len(user_records) - 1
        if first >= len(user_records):
            sys.stderr.write(
                f"Skipping {phase_name}: first index {first} beyond {len(user_records)} user messages.\n"
            )
            continue
        last = min(last, len(user_records) - 1)

        out_dir = PHASES_DIR / phase_name
        out_dir.mkdir(parents=True, exist_ok=True)

        # --- user_prompts.md ---
        prompts_path = out_dir / "user_prompts.md"
        with prompts_path.open("w") as f:
            f.write(f"# User prompts for {phase_name}\n\n")
            f.write(
                f"Extracted from transcript `{PARENT_UUID}.jsonl`. "
                f"User-message indices {first} through {last}.\n\n"
            )
            for i in range(first, last + 1):
                _, rec = user_records[i]
                raw = _content_text(rec.get("message", {}).get("content"))
                ts, body = _user_text(raw)
                f.write(_format_user_prompt(i, ts, body))
                f.write("\n")

        # --- assistant_responses.md ---
        # All assistant messages between user_records[first] and the message
        # immediately after user_records[last]. The slice in all_records is
        # (start, end_exclusive) where:
        #   start = user_records[first][0]   (the user msg itself; we want the assistant
        #                                     replies that follow it, so we go +1)
        #   end_exclusive = user_records[last+1][0] if last+1 < len(user_records)
        #                   else len(all_records)
        start_k = user_records[first][0] + 1
        end_k = (user_records[last + 1][0]
                 if last + 1 < len(user_records)
                 else len(all_records))

        responses_path = out_dir / "assistant_responses.md"
        clar_path = out_dir / "clarifications.md"
        clar_records: list[tuple[int, dict]] = []  # (asst_idx, payload)

        with responses_path.open("w") as f:
            f.write(f"# Assistant responses for {phase_name}\n\n")
            f.write(
                f"Extracted from transcript `{PARENT_UUID}.jsonl`. "
                f"Includes every visible assistant message between user prompts "
                f"#{first} and #{last} (inclusive). `text` blocks are quoted "
                f"verbatim; `tool_use` is rendered as a one-line italic stub "
                f"such as `[Shell(description='...')]`. Internal `thinking` "
                f"blocks are deliberately omitted.\n\n"
            )
            asst_idx = 0
            for k in range(start_k, end_k):
                rec = all_records[k]
                if rec.get("role") != "assistant":
                    # User-side records mid-phase (e.g. the user-clicked
                    # tool_result echoed back) are ignored; clarifications
                    # are picked up from the AskQuestion that preceded them.
                    continue
                msg = rec.get("message", {})
                content = msg.get("content")
                chunks = _assistant_chunks(content)
                rendered = _format_assistant_message(asst_idx, chunks)
                if rendered:
                    f.write(rendered)
                    f.write("\n")

                # AskQuestion handling: the user's selected option does
                # not appear as its own record in the transcript, so we
                # look it up in KNOWN_ANSWERS at write time.
                for payload in _ask_question_payloads(content):
                    clar_records.append((asst_idx, payload))
                asst_idx += 1

        # --- clarifications.md (only if any) ---
        if clar_records:
            with clar_path.open("w") as f:
                f.write(f"# Clarifications (AskQuestion) for {phase_name}\n\n")
                f.write(
                    f"Each entry shows the question, the offered options, and "
                    f"the user's selection. User selections are looked up in "
                    f"the `KNOWN_ANSWERS` table inside `extract_session.py` "
                    f"because the transcript does not preserve them.\n\n"
                )
                for n, (asst_idx, payload) in enumerate(clar_records, 1):
                    f.write(_format_clarification(n, payload, phase_name))
                    f.write("\n")

        n_prompts = last - first + 1
        n_clar = len(clar_records)
        sys.stderr.write(
            f"  {phase_name}: wrote {n_prompts} prompt(s), "
            f"assistant responses, {n_clar} clarification(s)\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--list", action="store_true",
                        help="print one line per user message and exit")
    args = parser.parse_args()
    if args.list:
        cmd_list()
    else:
        cmd_extract()


if __name__ == "__main__":
    main()
