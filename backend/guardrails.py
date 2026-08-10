import re

# Heuristics that flag a message as a likely prompt-injection / manipulation
# attempt. These never change the triage output on their own -- they only
# add a signal that forces needs_human=True and caps confidence.
_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"system prompt",
    r"you are now in .*mode",
    r"disregard (the|your) (task|instructions)",
    r"developer mode",
    r"override (safety|system)",
    r"act as (if|though)",
    r"reveal (your|the) (prompt|instructions)",
    r"needs_human\s*=\s*false",
    r"confidence\s*=\s*1\.0",
    r"<script",
    r"DROP TABLE",
]

_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

CONFIDENCE_HUMAN_THRESHOLD = 0.6
MAX_INJECTED_CONFIDENCE = 0.3


def detect_injection(text: str) -> bool:
    """Cheap heuristic pre-check; the LLM prompt also defends against this
    independently, this is a belt-and-suspenders signal used for gating."""
    return bool(_INJECTION_RE.search(text))


def sanitize_for_prompt(text: str) -> str:
    """Message text is never executed as instructions -- it's always
    embedded as clearly delimited, labeled data. This just strips characters
    that could be used to break out of the delimiter fence."""
    return text.replace("```", "'''").strip()


def apply_guardrails(result: dict, raw_text: str) -> dict:
    """Post-processing safety net applied after every model call, so that
    even if the model is fooled, the system output stays safe."""
    flags = []

    if detect_injection(raw_text):
        flags.append("possible_prompt_injection")
        result["needs_human"] = True
        result["confidence"] = min(result.get("confidence", 0), MAX_INJECTED_CONFIDENCE)
        if result.get("category") not in ("abuse",):
            result["category"] = "abuse"

    if not raw_text.strip():
        flags.append("empty_message")
        result["needs_human"] = True
        result["confidence"] = min(result.get("confidence", 0), 0.2)

    if result.get("confidence", 1.0) < CONFIDENCE_HUMAN_THRESHOLD:
        flags.append("low_confidence")
        result["needs_human"] = True

    result["flags"] = flags
    return result
