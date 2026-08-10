# FRONTLINE — AI Message Triage

Reads raw, messy customer messages and turns each one into a structured triage decision:

```json
{ "category": "...", "priority": "P0-P3", "summary": "...", "suggested_action": "...", "needs_human": true, "confidence": 0.0 }
```

Built for the FRONTLINE One-Day AI Build Challenge. See [AI_DECISIONS.md](AI_DECISIONS.md) for the design write-up.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # then paste your API key
```

Default provider is **Groq** (`llama-3.3-70b-versatile`, free tier, fast, no daily-cap issues). Get a free key at https://console.groq.com/keys and set `GROQ_API_KEY` in `.env`.

A Gemini backend is also implemented — set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY` in `.env` to switch (get a key at https://aistudio.google.com/apikey). Note: some Google Cloud projects' free tier caps `gemini-2.5-flash` at 20 requests/day, which is too low for a 40-message batch — Groq is recommended.

## Run — CLI

```bash
python cli.py --eval
```
Prints a results table, saves `results.json`, and (with `--eval`) scores against the 10 ground-truth messages into `eval_report.json`.

## Run — Web dashboard

```bash
uvicorn backend.main:app --reload
```
Open http://127.0.0.1:8000 — click **Run Triage** to process all 40 messages, **Run Evaluation** to score against ground truth.

## Project layout

```
data/messages.json       40 synthetic customer messages (clear, vague, angry, multi-issue,
                          sarcastic, out-of-scope, non-English, adversarial/injection)
data/ground_truth.json   10 labeled messages for evaluation
backend/schema.py        Pydantic models for the triage output
backend/guardrails.py    Prompt-injection heuristics, confidence gating
backend/triage.py        Gemini call, grounded prompt, fail-safe fallback
backend/evaluate.py      Accuracy / latency / token-cost measurement
backend/main.py          FastAPI app serving the API + dashboard
web/index.html           Single-page dashboard (table, filters, run/eval buttons)
cli.py                   CLI runner with rich table output
```
