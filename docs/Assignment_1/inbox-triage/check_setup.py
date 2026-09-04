"""
check_setup.py

Plain-English purpose: a quick sanity check that your Claude setup actually
works before you rely on it for anything else. It reads your API key and
model name from the .env file, sends Claude one tiny message, and prints
what came back.

How to run it:
    python docs/Assignment_1/inbox-triage/check_setup.py
"""

import os
import sys

from dotenv import find_dotenv, load_dotenv

import anthropic

# Short and cheap on purpose - this script only needs to prove the
# connection works, not do real work.
MAX_TOKENS = 300

# Common placeholder text people leave in .env files by mistake. If the key
# or model is set to one of these, treat it the same as "not set yet".
PLACEHOLDER_VALUES = {
    "your-key-here",
    "your_api_key_here",
    "insert-your-key-here",
    "replace-me",
    "changeme",
    "change-me",
    "xxx",
    "todo",
    "your-model-here",
    "model-name-here",
}


def is_placeholder(value: str) -> bool:
    """True if the value is missing, blank, or looks like leftover
    placeholder text rather than a real value someone actually set."""
    if not value:
        return True
    return value.strip().lower() in PLACEHOLDER_VALUES


def load_setup_values() -> tuple[str, str]:
    """Load ANTHROPIC_API_KEY and ANTHROPIC_MODEL from the .env file.
    Stops with a plain-English fix instead of letting the rest of the
    script fail confusingly later if either one is missing or a
    placeholder."""
    load_dotenv(find_dotenv(usecwd=True))

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if is_placeholder(api_key):
        print("ANTHROPIC_API_KEY is missing, empty, or still placeholder text.")
        print("To fix it:")
        print("  1. Open the .env file in the project root.")
        print("  2. Set: ANTHROPIC_API_KEY=your-real-key-from-the-Anthropic-console")
        print("  3. Run this script again.")
        sys.exit(1)

    model = os.environ.get("ANTHROPIC_MODEL", "")
    if is_placeholder(model):
        print("ANTHROPIC_MODEL is missing, empty, or still placeholder text.")
        print("To fix it:")
        print("  1. Open the .env file in the project root.")
        print("  2. Set: ANTHROPIC_MODEL=claude-opus-5 (or whichever model you want to use)")
        print("  3. Run this script again.")
        sys.exit(1)

    return api_key, model


def main() -> None:
    api_key, model = load_setup_values()
    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            output_config={"effort": "low"},  # this is just a connectivity check
            messages=[{
                "role": "user",
                "content": "Reply with a single sentence confirming the connection works.",
            }],
        )
    except anthropic.AuthenticationError:
        print("Claude rejected the API key - it's set, but not valid.")
        print("To fix it:")
        print("  1. Double-check the ANTHROPIC_API_KEY value in your .env file for typos.")
        print("  2. Make sure the key hasn't been revoked or expired in your Anthropic account.")
        print("  3. Run this script again.")
        sys.exit(1)

    # Only collect text blocks - a response can also include a thinking
    # block, which has no .text and would crash a plain response.content[0].text.
    reply_text = "\n".join(block.text for block in response.content if block.type == "text")

    print(f"Model that answered: {response.model}")
    print(f"Reply: {reply_text}")
    print(f"Input tokens: {response.usage.input_tokens}")
    print(f"Output tokens: {response.usage.output_tokens}")


if __name__ == "__main__":
    main()
