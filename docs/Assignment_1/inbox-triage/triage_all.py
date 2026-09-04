"""
triage_all.py

Plain-English purpose: run the same Claude triage that triage_one.py does,
but across every message in the inbox/ folder in one go. Writes one row per
message to triage_results.csv, keeps going even if a message fails, and
prints a summary (successes, failures, elapsed time, total tokens) at the end.

Also applies a quality gate: a message only counts as "settled" if the model
was confident about it AND didn't flag it as high urgency. Anything else -
low confidence, high urgency, or a processing failure - is held in a human
review queue instead. A plain-English run_report.md is written summarizing
all of this for someone who isn't going to open the CSV.

Reuses triage_one.py's schema (TriageResult), model settings, and API key
loading - so the two scripts always triage messages the same way. It does
NOT reuse triage_one's per-call error handling, because that script is
built to stop immediately on any problem, and this one is built to survive
a bad message and keep going.

How to run it:
    python triage_all.py
"""

import csv
import glob
import os
import sys
import time
from collections import Counter
from datetime import datetime

import anthropic

from triage_one import MAX_TOKENS, MODEL, Category, TriageResult, Urgency, get_api_key

INBOX_DIR = "inbox"
RESULTS_CSV = "triage_results.csv"
REPORT_MD = "run_report.md"
MAX_ATTEMPTS = 2  # first try + one retry
CONFIDENCE_THRESHOLD = 0.75  # below this, a message needs a human look

CSV_FIELDS = [
    "file",
    "urgency",
    "category",
    "one_line_summary",
    "suggested_next_action",
    "owner",
    "confidence",
    "gate",
    "gate_reason",
    "status",
    "error",
]


def gate_decision(urgency, confidence):
    """Decide whether a triaged message can be auto-cleared or needs a
    person to look at it. A message that couldn't even be triaged also
    needs a person - there's no confidence score to trust for it."""
    if confidence is None:
        return "needs_review", "could not be triaged (see error)"
    reasons = []
    if confidence < CONFIDENCE_THRESHOLD:
        reasons.append(f"confidence {confidence:.2f} is below the {CONFIDENCE_THRESHOLD:.2f} threshold")
    if urgency == Urgency.high.value:
        reasons.append("flagged high urgency")
    if reasons:
        return "needs_review", "; ".join(reasons)
    return "auto_cleared", ""


def read_message_safe(path: str) -> str:
    """Read a message file. Raises instead of exiting, so a bad file can be
    recorded as a failed row instead of stopping the whole batch."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def call_claude(client: anthropic.Anthropic, message_text: str):
    """One attempt at the triage call. Returns (TriageResult, usage).
    Raises on failure - the caller decides whether to retry."""
    response = client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{
            "role": "user",
            "content": (
                "Triage this inbox message for a mid-size company's shared "
                "inbox. Judge urgency and category from what the message "
                "actually says, not just its subject line.\n\n"
                f"Message:\n\"\"\"\n{message_text}\n\"\"\""
            ),
        }],
        output_format=TriageResult,
    )
    return response.parsed_output, response.usage


def triage_with_retry(client: anthropic.Anthropic, message_text: str):
    """Try the call, retry once on failure. An authentication error is not
    retried - a bad key fails every message the same way, so we stop the
    whole run immediately instead of burning through retries on every file."""
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return call_claude(client, message_text), None
        except anthropic.AuthenticationError:
            print("Claude rejected the API key - stopping the whole run.")
            print("Check ANTHROPIC_API_KEY in your .env file and try again.")
            sys.exit(1)
        except Exception as e:
            last_error = e
            if attempt < MAX_ATTEMPTS:
                print(f"    attempt {attempt} failed ({e}) - retrying once...")
    return None, last_error


def success_row(filename: str, result: TriageResult) -> dict:
    gate, gate_reason = gate_decision(result.urgency.value, result.confidence)
    return {
        "file": filename,
        "urgency": result.urgency.value,
        "category": result.category.value,
        "one_line_summary": result.one_line_summary,
        "suggested_next_action": result.suggested_next_action,
        "owner": result.owner,
        "confidence": f"{result.confidence:.2f}",
        "gate": gate,
        "gate_reason": gate_reason,
        "status": "ok",
        "error": "",
    }


def failure_row(filename: str, error_text: str) -> dict:
    gate, gate_reason = gate_decision(None, None)
    return {
        "file": filename,
        "urgency": "",
        "category": "",
        "one_line_summary": "",
        "suggested_next_action": "",
        "owner": "",
        "confidence": "",
        "gate": gate,
        "gate_reason": gate_reason,
        "status": "failed",
        "error": error_text,
    }


def write_csv(rows: list) -> None:
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build_report(rows, failed, elapsed_seconds, total_input_tokens, total_output_tokens) -> str:
    """Build a plain-English markdown summary of the run, for someone who
    is never going to open the CSV."""
    total = len(rows)
    auto_cleared = sum(1 for r in rows if r["gate"] == "auto_cleared")
    needs_review = sum(1 for r in rows if r["gate"] == "needs_review")

    urgency_counts = Counter(r["urgency"] for r in rows if r["status"] == "ok")
    category_counts = Counter(r["category"] for r in rows if r["status"] == "ok")

    lines = []
    lines.append("# Inbox Triage Run Report")
    lines.append("")
    lines.append(f"**Run date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Messages processed:** {total}")
    lines.append(f"**Auto-cleared:** {auto_cleared}")
    lines.append(f"**Needs human review:** {needs_review}")
    lines.append(f"**Failed to process:** {failed}")
    lines.append("")
    lines.append("## What this means")
    lines.append("")
    lines.append(
        f"A message is auto-cleared when the model was confident "
        f"({CONFIDENCE_THRESHOLD:.2f} or higher) and did not flag it as high "
        "urgency. Anything with lower confidence, anything flagged high "
        "urgency, and anything that failed to process is held here for a "
        "person to check before it's treated as handled."
    )
    lines.append("")
    lines.append("## By urgency")
    lines.append("")
    for level in ["high", "medium", "low"]:
        lines.append(f"- {level.capitalize()}: {urgency_counts.get(level, 0)}")
    lines.append("")
    lines.append("## By category")
    lines.append("")
    for cat in [c.value for c in Category]:
        lines.append(f"- {cat.capitalize()}: {category_counts.get(cat, 0)}")
    lines.append("")
    lines.append(f"## Needs human review ({needs_review})")
    lines.append("")
    review_rows = [r for r in rows if r["gate"] == "needs_review"]
    if not review_rows:
        lines.append("None this run.")
    else:
        for r in review_rows:
            lines.append(f"### {r['file']}")
            lines.append(f"- **Why flagged:** {r['gate_reason']}")
            if r["status"] == "ok":
                lines.append(f"- **Summary:** {r['one_line_summary']}")
                lines.append(f"- **Suggested action:** {r['suggested_next_action']}")
                lines.append(f"- **Owner:** {r['owner']}")
                lines.append(f"- **Confidence:** {r['confidence']}")
            else:
                lines.append(f"- **Error:** {r['error']}")
            lines.append("")
    lines.append("## Failures")
    lines.append("")
    failure_rows = [r for r in rows if r["status"] == "failed"]
    if not failure_rows:
        lines.append("None this run.")
    else:
        for r in failure_rows:
            lines.append(f"- **{r['file']}**: {r['error']}")
    lines.append("")
    lines.append("## Run stats")
    lines.append("")
    lines.append(f"- Elapsed time: {elapsed_seconds:.1f}s")
    lines.append(f"- Total input tokens: {total_input_tokens:,}")
    lines.append(f"- Total output tokens: {total_output_tokens:,}")
    lines.append(f"- Total tokens: {total_input_tokens + total_output_tokens:,}")
    lines.append("")

    return "\n".join(lines)


def write_report(rows, failed, elapsed_seconds, total_input_tokens, total_output_tokens) -> None:
    report_text = build_report(rows, failed, elapsed_seconds, total_input_tokens, total_output_tokens)
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write(report_text)


def main() -> None:
    api_key = get_api_key()
    client = anthropic.Anthropic(api_key=api_key)

    message_files = sorted(glob.glob(os.path.join(INBOX_DIR, "*.txt")))
    if not message_files:
        print(f"No .txt files found in {INBOX_DIR}/")
        sys.exit(1)

    rows = []
    succeeded = 0
    failed = 0
    total_input_tokens = 0
    total_output_tokens = 0

    start_time = time.monotonic()

    for i, path in enumerate(message_files, start=1):
        filename = os.path.basename(path)
        print(f"[{i}/{len(message_files)}] Triaging {filename}...")

        try:
            message_text = read_message_safe(path)
        except (OSError, UnicodeDecodeError) as e:
            print(f"    could not read file: {e}")
            rows.append(failure_row(filename, str(e)))
            failed += 1
            continue

        outcome, error = triage_with_retry(client, message_text)

        if error is not None:
            print(f"    FAILED after {MAX_ATTEMPTS} attempts: {error}")
            rows.append(failure_row(filename, str(error)))
            failed += 1
            continue

        result, usage = outcome
        total_input_tokens += usage.input_tokens
        total_output_tokens += usage.output_tokens
        rows.append(success_row(filename, result))
        succeeded += 1
        print(f"    done - urgency={result.urgency.value}, confidence={result.confidence:.2f}")

    elapsed_seconds = time.monotonic() - start_time

    write_csv(rows)
    write_report(rows, failed, elapsed_seconds, total_input_tokens, total_output_tokens)

    auto_cleared = sum(1 for r in rows if r["gate"] == "auto_cleared")
    needs_review = sum(1 for r in rows if r["gate"] == "needs_review")

    print()
    print("--- Summary ---")
    print(f"Succeeded: {succeeded}")
    print(f"Failed: {failed}")
    print(f"Auto-cleared: {auto_cleared}")
    print(f"Needs human review: {needs_review}")
    print(f"Elapsed time: {elapsed_seconds:.1f}s")
    print(f"Total input tokens: {total_input_tokens}")
    print(f"Total output tokens: {total_output_tokens}")
    print(f"Results written to: {RESULTS_CSV}")
    print(f"Report written to: {REPORT_MD}")


if __name__ == "__main__":
    main()
