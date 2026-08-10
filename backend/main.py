import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from backend.evaluate import evaluate  # noqa: E402
from backend.triage import triage_batch  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
WEB_DIR = os.path.join(ROOT, "web")

app = FastAPI(title="FRONTLINE Triage")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache: dict = {"results": None, "eval": None}

# Free-tier LLM APIs enforce per-minute rate limits; spacing calls out avoids
# hammering into 429s (which cost more wall-clock time via retry/backoff than
# a small fixed delay would). Override via REQUEST_DELAY_S if your tier allows faster.
REQUEST_DELAY_S = float(os.environ.get("REQUEST_DELAY_S", "1.0"))


def _load(name: str):
    with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/messages")
def get_messages():
    return _load("messages.json")


@app.get("/api/ground_truth")
def get_ground_truth():
    return _load("ground_truth.json")


@app.get("/api/meta")
def get_meta():
    provider = os.environ.get("LLM_PROVIDER", "groq").lower()
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile") if provider == "groq" \
        else os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    return {"provider": provider, "model": model, "dataset_size": len(_load("messages.json"))}


@app.post("/api/triage")
def run_triage():
    messages = _load("messages.json")
    results = triage_batch(messages, delay_s=REQUEST_DELAY_S)
    _cache["results"] = [r.model_dump() for r in results]
    return _cache["results"]


@app.get("/api/results")
def get_results():
    return _cache["results"] or []


@app.post("/api/eval")
def run_eval():
    if not _cache["results"]:
        messages = _load("messages.json")
        results = triage_batch(messages, delay_s=REQUEST_DELAY_S)
        _cache["results"] = [r.model_dump() for r in results]
    from backend.schema import TriageResult

    results = [TriageResult(**r) for r in _cache["results"]]
    gt = _load("ground_truth.json")
    report = evaluate(results, gt)
    _cache["eval"] = report
    return report


@app.get("/AI_DECISIONS.md")
def get_ai_decisions():
    path = os.path.join(ROOT, "AI_DECISIONS.md")
    return PlainTextResponse(open(path, encoding="utf-8").read(), media_type="text/markdown")


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
