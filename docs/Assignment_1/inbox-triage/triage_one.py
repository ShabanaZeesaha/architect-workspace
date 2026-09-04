"""
triage_one.py

Plain-English purpose: read one inbox message and ask Claude to triage it -
how urgent it is, what kind of message it is, a one-line summary, what to do
next, who should own it, and how confident Claude is in that judgment.

The result comes back as a guaranteed structured object (via the Anthropic
SDK's structured output support), not as prose we have to parse ourselves.

How to run it:
    python triage_one.py inbox/msg01.txt
"""

import os
import sys
from enum import Enum

import anthropic
from dotenv import find_dotenv, load_dotenv
from pydantic import BaseModel, Field

MODEL = "claude-opus-5"
MAX_TOKENS = 1024


class Urgency(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Category(str, Enum):
    outage = "outage"
    billing = "billing"
    sales = "sales"
    internal = "internal"
    vendor = "vendor"
    spam = "spam"
    unclear = "unclear"


class TriageResult(BaseModel):
    """The exact shape Claude's answer is forced into - every field is
    guaranteed to be present and of the right type, every time."""

    urgency: Urgency
    category: Category
    one_line_summary: str
    suggested_next_action: str
    owner: str = Field(description="Which team should pick this up")
    confidence: float = Field(ge=0, le=1, description="How sure the model is, 0 to 1")


def get_api_key() -> str:
    """Load ANTHROPIC_API_KEY from the .env file. Stops with a plain-English
    fix instead of a stack trace if it's missing."""
    load_dotenv(find_dotenv(usecwd=True))
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key.strip():
        print("ANTHROPIC_API_KEY is missing or empty.")
        print("To fix it: open the .env file in the project root and set")
        print("  ANTHROPIC_API_KEY=your-real-key-from-the-Anthropic-console")
        sys.exit(1)
    return api_key


def read_message(path: str) -> str:
    """Read the message file we were asked to triage."""
    if not os.path.isfile(path):
        print(f"Can't find a message file at: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def triage(client: anthropic.Anthropic, message_text: str) -> TriageResult:
    """Send the message to Claude and get back a validated TriageResult.
    output_format=TriageResult is what guarantees the shape - Claude cannot
    return anything that doesn't fit this exact schema."""
    try:
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
    except anthropic.AuthenticationError:
        print("Claude rejected the API key - it's set, but not valid.")
        print("Check ANTHROPIC_API_KEY in your .env file and try again.")
        sys.exit(1)

    return response.parsed_output


def print_result(path: str, result: TriageResult) -> None:
    """Print the result as a readable block, not raw JSON."""
    print(f"Message: {path}")
    print(f"Urgency: {result.urgency.value}")
    print(f"Category: {result.category.value}")
    print(f"Summary: {result.one_line_summary}")
    print(f"Suggested next action: {result.suggested_next_action}")
    print(f"Owner: {result.owner}")
    print(f"Confidence: {result.confidence:.2f}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python triage_one.py <path-to-message-file>")
        print("Example: python triage_one.py inbox/msg01.txt")
        sys.exit(1)

    path = sys.argv[1]
    api_key = get_api_key()
    client = anthropic.Anthropic(api_key=api_key)

    message_text = read_message(path)
    result = triage(client, message_text)
    print_result(path, result)


if __name__ == "__main__":
    main()
