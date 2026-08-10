"""Demonstrates optional tool/function-calling: when a message references an
existing ticket number, the model calls lookup_ticket_status() to ground its
suggested_action in real data instead of guessing what happened to it.

Run: python tool_demo.py
"""
import json

from dotenv import load_dotenv

load_dotenv()

from backend.guardrails import sanitize_for_prompt  # noqa: E402
from backend.llm_client import groq_generate_with_tools  # noqa: E402
from backend.tools import TOOL_IMPLS, TOOLS_SPEC  # noqa: E402
from backend.triage import SYSTEM_PROMPT  # noqa: E402

TOOL_AWARE_SYSTEM_PROMPT = SYSTEM_PROMPT + (
    "\nYou have access to a lookup_ticket_status tool. If the message references "
    "an existing ticket number, call it to get the real status before writing "
    "your summary and suggested_action, instead of guessing."
)


def main():
    message = "just checking in on ticket #48213 from last week, any update?"
    safe_text = sanitize_for_prompt(message)
    user_prompt = f"<<<MESSAGE>>>\n{safe_text}\n<<<END_MESSAGE>>>"

    print(f"Message: {message}\n")
    response = groq_generate_with_tools(TOOL_AWARE_SYSTEM_PROMPT, user_prompt, TOOLS_SPEC, TOOL_IMPLS)
    result = json.loads(response.text)
    print("Triage result (grounded via tool call, not guessed):")
    print(json.dumps(result, indent=2))
    print(f"\ntokens in/out: {response.input_tokens}/{response.output_tokens}")


if __name__ == "__main__":
    main()
