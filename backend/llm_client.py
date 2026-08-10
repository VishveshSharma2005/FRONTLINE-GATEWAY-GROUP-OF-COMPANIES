"""Thin provider abstraction so triage.py doesn't care whether we're calling
Gemini or Groq. Both are OpenAI-JSON-mode-ish; we normalize to
(raw_text, input_tokens, output_tokens)."""
import os

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

PROVIDER = os.environ.get("LLM_PROVIDER", "groq").lower()


class LLMResponse:
    def __init__(self, text: str, input_tokens: int | None, output_tokens: int | None):
        self.text = text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


def _groq_generate(system_prompt: str, user_prompt: str) -> LLMResponse:
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    usage = completion.usage
    return LLMResponse(
        text=completion.choices[0].message.content or "",
        input_tokens=getattr(usage, "prompt_tokens", None),
        output_tokens=getattr(usage, "completion_tokens", None),
    )


def _gemini_generate(system_prompt: str, user_prompt: str) -> LLMResponse:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    usage = getattr(response, "usage_metadata", None)
    return LLMResponse(
        text=response.text or "",
        input_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
        output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
    )


def generate_json(system_prompt: str, user_prompt: str) -> LLMResponse:
    if PROVIDER == "gemini":
        return _gemini_generate(system_prompt, user_prompt)
    return _groq_generate(system_prompt, user_prompt)


def groq_generate_with_tools(system_prompt: str, user_prompt: str, tools_spec: list, tool_impls: dict) -> LLMResponse:
    """Groq-only: lets the model call a function (e.g. ticket lookup) before
    producing its final JSON triage. One tool round-trip max, then a final
    JSON-mode call to lock the output schema."""
    import json as _json

    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    client = Groq(api_key=api_key)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    first = client.chat.completions.create(
        model=model, messages=messages, tools=tools_spec, tool_choice="auto", temperature=0.1
    )
    msg = first.choices[0].message
    total_in = first.usage.prompt_tokens
    total_out = first.usage.completion_tokens

    if msg.tool_calls:
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls})
        for call in msg.tool_calls:
            fn = tool_impls.get(call.function.name)
            args = _json.loads(call.function.arguments or "{}")
            result = fn(**args) if fn else {"error": "unknown_tool"}
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": _json.dumps(result)}
            )

        final = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        total_in += final.usage.prompt_tokens
        total_out += final.usage.completion_tokens
        return LLMResponse(final.choices[0].message.content or "", total_in, total_out)

    # No tool needed -> the first response should already be JSON-shaped text;
    # force a clean JSON-mode call to be safe.
    final = client.chat.completions.create(
        model=model, messages=messages, response_format={"type": "json_object"}, temperature=0.1
    )
    total_in += final.usage.prompt_tokens
    total_out += final.usage.completion_tokens
    return LLMResponse(final.choices[0].message.content or "", total_in, total_out)
