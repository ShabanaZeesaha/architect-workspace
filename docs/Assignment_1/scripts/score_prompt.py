"""
score_prompt.py

Plain-English purpose: this script takes a prompt file and a set of test
cases (eval.jsonl), asks Claude to answer each test case using that prompt,
and checks how many answers matched what we expected.

How to run it from the terminal:
    python scripts/score_prompt.py <path-to-prompt-file> <path-to-eval.jsonl>

Example:
    python scripts/score_prompt.py prompts/triage-report-request/prompt.md prompts/triage-report-request/eval.jsonl
"""

import sys
import os
import json

from dotenv import load_dotenv, find_dotenv
import anthropic


# ---------------------------------------------------------------------------
# Settings you might want to change
# ---------------------------------------------------------------------------

# Which Claude model to test the prompt against.
MODEL_NAME = "claude-sonnet-5"

# How many tokens (roughly, chunks of words) Claude is allowed to reply with.
MAX_TOKENS = 1024

# For number fields, how far off the answer can be and still count as
# "close enough". 0.01 means half a cent off on a dollar amount still counts.
NUMBER_TOLERANCE = 0.01


# ---------------------------------------------------------------------------
# Step 1: Read the prompt file and fill in each test case's values
# ---------------------------------------------------------------------------

def fill_prompt(prompt_template: str, input_values: dict) -> str:
    """
    Takes the prompt text and swaps placeholders like {{message}} for the
    real value from that test case's "input" object.

    Example: if the prompt contains "{{message}}" and the test case's input
    is {"message": "hello"}, the result will have "hello" in that spot.
    """
    filled = prompt_template
    for field_name, value in input_values.items():
        placeholder = "{{" + field_name + "}}"
        filled = filled.replace(placeholder, str(value))
    return filled


# ---------------------------------------------------------------------------
# Step 2: Send the filled-in prompt to Claude and get back an answer
# ---------------------------------------------------------------------------

def ask_claude(client: "anthropic.Anthropic", filled_prompt: str) -> str:
    """
    Sends one message to Claude and returns the plain text it replied with.
    """
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": filled_prompt}],
    )
    text_blocks = [block.text for block in response.content if block.type == "text"]
    return "\n".join(text_blocks)


def parse_claude_reply_as_json(reply_text: str):
    """
    We expect Claude's reply to be a JSON object (e.g. {"priority": "high"}).
    Sometimes a model adds a sentence before or after the JSON, so if a
    straight parse fails, we try again using just the part between the
    first "{" and the last "}".

    Returns a dict, or None if we genuinely couldn't find valid JSON.
    """
    reply_text = reply_text.strip()

    try:
        return json.loads(reply_text)
    except json.JSONDecodeError:
        pass

    start = reply_text.find("{")
    end = reply_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(reply_text[start:end + 1])
        except json.JSONDecodeError:
            return None

    return None


# ---------------------------------------------------------------------------
# Step 3: Compare Claude's answer to what we expected
# ---------------------------------------------------------------------------

def values_match(expected_value, actual_value) -> bool:
    """
    Compares one field's expected value to what Claude actually returned.

    - Text is compared ignoring uppercase/lowercase and extra spaces.
    - Numbers are allowed to be off by a tiny amount (NUMBER_TOLERANCE).
    - Anything else (lists, true/false, etc.) has to match exactly.
    """
    if isinstance(expected_value, str):
        actual_text = actual_value if isinstance(actual_value, str) else str(actual_value)
        return expected_value.strip().lower() == actual_text.strip().lower()

    if isinstance(expected_value, (int, float)) and not isinstance(expected_value, bool):
        try:
            actual_number = float(actual_value)
        except (TypeError, ValueError):
            return False
        return abs(float(expected_value) - actual_number) <= NUMBER_TOLERANCE

    return expected_value == actual_value


def case_matches(expected: dict, actual) -> bool:
    """
    A test case only counts as a pass if EVERY field named in "expected"
    matches. Fields Claude adds that we didn't ask about are ignored.
    """
    if not isinstance(actual, dict):
        return False
    for field_name, expected_value in expected.items():
        if field_name not in actual:
            return False
        if not values_match(expected_value, actual[field_name]):
            return False
    return True


# ---------------------------------------------------------------------------
# Step 4: Set up the Claude API key from the .env file
# ---------------------------------------------------------------------------

def get_api_key():
    """
    Loads the .env file and reads ANTHROPIC_API_KEY from it.
    Returns the key as text, or None if it isn't set.
    """
    load_dotenv(find_dotenv(usecwd=True))
    return os.environ.get("ANTHROPIC_API_KEY")


# ---------------------------------------------------------------------------
# Main program
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 3:
        print("How to use this script:")
        print("  python scripts/score_prompt.py <prompt-file> <eval-jsonl-file>")
        sys.exit(1)

    prompt_file_path = sys.argv[1]
    eval_file_path = sys.argv[2]

    # --- Check the two input files exist before doing anything else ---
    if not os.path.isfile(prompt_file_path):
        print(f"Can't find a prompt file at: {prompt_file_path}")
        print("Nothing to test yet - write the prompt file first, then run this again.")
        sys.exit(1)

    if not os.path.isfile(eval_file_path):
        print(f"Can't find an eval file at: {eval_file_path}")
        sys.exit(1)

    # --- Check the API key before doing anything else ---
    api_key = get_api_key()
    if not api_key:
        print("Your Anthropic API key is missing.")
        print("Fix: create a file named .env in your project folder and add this line:")
        print("  ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    prompt_template = open(prompt_file_path, "r", encoding="utf-8").read()

    cases = []
    with open(eval_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))

    # --- Run each test case ---
    scored_count = 0
    matched_count = 0
    skipped_count = 0
    failures = []  # list of (case_number, expected, actual)

    for case_number, case in enumerate(cases, start=1):
        expected = case.get("expected", {})
        input_values = case.get("input", {})

        # If nobody has filled in an expected answer for this case yet,
        # there's nothing to score it against, so we skip it.
        if not expected:
            skipped_count += 1
            continue

        filled_prompt = fill_prompt(prompt_template, input_values)

        try:
            reply_text = ask_claude(client, filled_prompt)
        except anthropic.AuthenticationError:
            print("Your Anthropic API key was rejected by the server (it looks wrong or expired).")
            print("Fix: check the ANTHROPIC_API_KEY value in your .env file and try again.")
            sys.exit(1)
        except anthropic.APIConnectionError:
            print("Couldn't reach the Anthropic API - check your internet connection and try again.")
            sys.exit(1)
        except anthropic.AnthropicError as e:
            print(f"Case {case_number}: Claude API returned an error ({e}). Skipping this case.")
            continue

        actual = parse_claude_reply_as_json(reply_text)

        scored_count += 1
        if actual is not None and case_matches(expected, actual):
            matched_count += 1
        else:
            failures.append((case_number, expected, actual if actual is not None else reply_text))

    # --- Print the report ---
    print()
    if scored_count == 0:
        print("Score: N/A - none of the cases have an expected answer filled in yet.")
    else:
        score = matched_count / scored_count
        print(f"Score: {score:.2f} ({matched_count}/{scored_count} cases matched)")

    for case_number, expected, actual in failures:
        print(f"  Case {case_number} FAILED - expected: {expected} | got: {actual}")

    print()
    print(f"Model used: {MODEL_NAME}")
    print(f"Cases in file: {len(cases)} | Scored: {scored_count} | Skipped (no expected answer yet): {skipped_count}")


if __name__ == "__main__":
    main()
