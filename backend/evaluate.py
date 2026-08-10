from backend.schema import TriageResult


def evaluate(results: list[TriageResult], ground_truth: list[dict]) -> dict:
    gt_by_id = {g["id"]: g for g in ground_truth}
    res_by_id = {r.id: r for r in results}

    rows = []
    category_hits = priority_hits = human_hits = 0
    n = 0

    for gid, gt in gt_by_id.items():
        r = res_by_id.get(gid)
        if r is None:
            continue
        n += 1
        cat_ok = r.category.value == gt["category"]
        pri_ok = r.priority.value == gt["priority"]
        human_ok = r.needs_human == gt["needs_human"]
        category_hits += cat_ok
        priority_hits += pri_ok
        human_hits += human_ok
        rows.append({
            "id": gid,
            "category": {"expected": gt["category"], "got": r.category.value, "match": cat_ok},
            "priority": {"expected": gt["priority"], "got": r.priority.value, "match": pri_ok},
            "needs_human": {"expected": gt["needs_human"], "got": r.needs_human, "match": human_ok},
            "confidence": r.confidence,
            "notes": gt.get("notes", ""),
        })

    latencies = [r.latency_ms for r in results if r.latency_ms is not None]
    in_tokens = [r.input_tokens for r in results if r.input_tokens is not None]
    out_tokens = [r.output_tokens for r in results if r.output_tokens is not None]

    # Gemini 2.0 Flash free-tier pricing reference (approx, as of build time):
    # $0.10 / 1M input tokens, $0.40 / 1M output tokens (paid tier rate used
    # here only as an illustrative cost estimate; free tier itself is $0).
    avg_in = sum(in_tokens) / len(in_tokens) if in_tokens else 0
    avg_out = sum(out_tokens) / len(out_tokens) if out_tokens else 0
    est_cost_per_msg = (avg_in / 1_000_000 * 0.10) + (avg_out / 1_000_000 * 0.40)

    return {
        "n_evaluated": n,
        "category_accuracy": round(category_hits / n, 3) if n else 0,
        "priority_accuracy": round(priority_hits / n, 3) if n else 0,
        "needs_human_accuracy": round(human_hits / n, 3) if n else 0,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "avg_input_tokens": round(avg_in, 1),
        "avg_output_tokens": round(avg_out, 1),
        "est_cost_per_message_usd": round(est_cost_per_msg, 6),
        "rows": rows,
    }
