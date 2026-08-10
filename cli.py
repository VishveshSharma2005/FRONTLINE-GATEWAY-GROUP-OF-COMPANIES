import argparse
import json
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()

from backend.evaluate import evaluate
from backend.triage import triage_batch

console = Console()


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def print_table(results):
    table = Table(title="Triage Results")
    for col in ["id", "category", "priority", "needs_human", "confidence", "summary"]:
        table.add_column(col)
    for r in results:
        table.add_row(
            r.id,
            r.category.value,
            r.priority.value,
            "YES" if r.needs_human else "",
            f"{r.confidence:.2f}",
            r.summary[:60],
        )
    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="FRONTLINE message triage CLI")
    parser.add_argument("--messages", default="data/messages.json")
    parser.add_argument("--ground-truth", default="data/ground_truth.json")
    parser.add_argument("--out", default="results.json")
    parser.add_argument("--eval", action="store_true", help="run evaluation against ground truth")
    parser.add_argument("--delay", type=float, default=4.0, help="seconds between API calls (rate-limit safety)")
    args = parser.parse_args()

    messages = load_json(args.messages)
    console.print(f"[bold]Triaging {len(messages)} messages...[/bold]")

    results = triage_batch(messages, delay_s=args.delay)
    print_table(results)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump([r.model_dump() for r in results], f, indent=2)
    console.print(f"[green]Saved results to {args.out}[/green]")

    if args.eval:
        gt = load_json(args.ground_truth)
        report = evaluate(results, gt)
        console.print("\n[bold]Evaluation[/bold]")
        console.print(f"Evaluated: {report['n_evaluated']} messages")
        console.print(f"Category accuracy: {report['category_accuracy']*100:.1f}%")
        console.print(f"Priority accuracy: {report['priority_accuracy']*100:.1f}%")
        console.print(f"needs_human accuracy: {report['needs_human_accuracy']*100:.1f}%")
        console.print(f"Avg latency: {report['avg_latency_ms']} ms")
        console.print(f"Avg tokens in/out: {report['avg_input_tokens']}/{report['avg_output_tokens']}")
        console.print(f"Est. cost/message: ${report['est_cost_per_message_usd']}")

        with open("eval_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        console.print("[green]Saved eval_report.json[/green]")


if __name__ == "__main__":
    sys.exit(main() or 0)
