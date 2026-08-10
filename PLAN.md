# FRONTLINE Triage System — Build Plan

## Architecture
```
GATEWAY/
├── data/
│   ├── messages.json          # ~40 synthetic customer messages (messy, adversarial)
│   └── ground_truth.json      # 10 labeled messages for eval
├── backend/
│   ├── main.py                # FastAPI app: /api/triage, /api/results, /api/eval
│   ├── schema.py              # Pydantic models: TriageResult, Message
│   ├── triage.py              # Core LLM triage logic (Gemini) + guardrails
│   ├── guardrails.py          # Prompt-injection detection, input sanitization, confidence gating
│   └── evaluate.py            # Ground-truth comparison, cost/latency/accuracy metrics
├── web/
│   └── index.html             # Single-page dashboard (table, filters, run button, eval view)
├── cli.py                     # CLI runner: prints rich table, saves results.json
├── requirements.txt
├── .env.example
├── .gitignore
├── AI_DECISIONS.md            # One-pager for submission
└── README.md
```

## Data model (per message)
```json
{
  "category": "billing|technical|complaint|question|abuse|spam|other",
  "priority": "P0|P1|P2|P3",
  "summary": "...",
  "suggested_action": "...",
  "needs_human": true/false,
  "confidence": 0.0-1.0
}
```

## Reliability design (Level 2)
- **Structured output**: Gemini JSON mode + Pydantic validation; retry once on malformed JSON, then fail safe → `needs_human=true`.
- **Prompt injection defense**: message content is wrapped as inert data (delimited, labeled "untrusted user message"), system prompt explicitly instructs to never follow instructions found inside the message. A regex/heuristic pre-check flags obvious injection attempts as a signal.
- **No hallucination**: prompt instructs "only use info present in the message; if missing, say unknown" — summary/action grounded only in message text.
- **Confidence gating**: low confidence (<0.6) or validation failure → `needs_human=true` regardless of model's own flag.
- **Garbage input survival**: empty/non-English/gibberish messages handled via try/except + fallback triage object, never crashes the batch.

## Evaluation (Level 3)
- 10 ground-truth labeled messages → compare category/priority/needs_human agreement %.
- Track tokens, latency, estimated cost per message (Gemini flash pricing) during batch run.
- Report where it disagrees and why (logged per-message diff).

## UI
- Minimal web dashboard: table of all triage results, filter by needs_human/priority, "Run Eval" button showing accuracy score.
- CLI fallback table via `rich`.

## Build order
1. Dataset (40 messages incl. adversarial/injection/non-English/multi-issue) + 10 ground truth
2. Schema + guardrails + triage core (Gemini call)
3. Batch runner + CLI table
4. Eval module (accuracy, cost, latency)
5. FastAPI backend wiring
6. Web dashboard
7. AI_DECISIONS.md + README
8. Test end-to-end on full dataset, commit & push incrementally
