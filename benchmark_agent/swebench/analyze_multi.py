"""
swebench/analyze_multi.py — Compare CodeDNA results across multiple LLM models.

deps:    results_<model>.json files (output of run_agent_multi.py)
exports: comparative table across all models
rules:   Report results honestly — include ALL tasks and ALL models.

Usage:
  python analyze_multi.py                         # all result files found
  python analyze_multi.py --model gemini-2.5-flash claude-3-7-sonnet
"""

import argparse
import json
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "runs"

def pct(v):
    return f"{v:+.0%}" if v != 0 else "0%"

def load_model_results(model_name: str) -> list | None:
    path = RESULTS_DIR / model_name.replace('/', '-') / "results.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)

def summarize(results: list) -> dict:
    """Compute averages across all tasks for one model."""
    n = len(results)
    if n == 0:
        return {}
    return {
        "n": n,
        "avg_read_calls":   sum(r["codedna"].get("read_calls", r["codedna"]["tool_calls"]) for r in results) / n,
        "avg_unique_files": sum(r["codedna"]["n_files_read"] for r in results) / n,
        "avg_chars":        sum(r["codedna"]["total_chars_consumed"] for r in results) / n,
        "avg_recall":       sum(r["codedna"]["metrics_read"]["recall"] for r in results) / n,
        "avg_precision":    sum(r["codedna"]["metrics_read"]["precision"] for r in results) / n,
        "avg_f1":           sum(r["codedna"]["metrics_read"]["f1"] for r in results) / n,

        "ctrl_avg_recall":  sum(r["control"]["metrics_read"]["recall"] for r in results if r["control"]) / n,
        "ctrl_avg_f1":      sum(r["control"]["metrics_read"]["f1"] for r in results if r["control"]) / n,
        "tasks_better":     sum(1 for r in results
                                if r["codedna"]["metrics_read"]["f1"] > r["control"]["metrics_read"]["f1"]),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", nargs="+", help="Model names to compare")
    args = parser.parse_args()

    # Auto-discover result files
    if args.model:
        model_names = args.model
    else:
        model_names = [p.parent.name
                       for p in RESULTS_DIR.glob("*/results.json")]

    if not model_names:
        print("No result files found. Run run_agent_multi.py first.")
        return

    print("\n" + "="*110)
    print("CodeDNA Multi-Model Comparison")
    print("="*110)

    # ── Per-model summary table ──
    print(f"\n{'Model':<25} {'Ctrl F1':>8} {'DNA F1':>8} {'Δ F1':>7} "
          f"{'DNA Recall':>10} {'UniqueFiles':>12} {'Chars':>10} {'Tasks Won':>10}")
    print("-"*100)

    summaries = {}
    for name in model_names:
        results = load_model_results(name)
        if results is None:
            print(f"  {name:<23} — no results file found")
            continue
        s = summarize(results)
        summaries[name] = s
        delta_f1 = s["avg_f1"] - s["ctrl_avg_f1"]
        print(f"  {name:<23} "
              f"{s['ctrl_avg_f1']:>8.0%} "
              f"{s['avg_f1']:>8.0%} "
              f"{pct(delta_f1):>7} "
              f"{s['avg_recall']:>10.0%} "
              f"{s['avg_unique_files']:>12.1f} "
              f"{s['avg_chars']:>10,.0f} "
              f"  {s['tasks_better']}/{s['n']}")

    if len(summaries) < 2:
        print("\n(Run more models to see cross-model comparison)")
        return

    # ── Per-task breakdown ──
    # Use the first model's tasks as reference
    ref_name = list(summaries.keys())[0]
    ref_results = load_model_results(ref_name)
    tasks = [r["instance_id"] for r in ref_results]

    print(f"\n{'─'*100}")
    print(f"  Per-task DNA F1 by model")
    print(f"{'─'*100}")

    header = f"  {'Task':<35}"
    for name in summaries:
        header += f" {name[:14]:>15}"
    print(header)
    print("-"*100)

    for task_id in tasks:
        row = f"  {task_id[:34]:<35}"
        for name in summaries:
            results = load_model_results(name)
            task_result = next((r for r in results if r["instance_id"] == task_id), None)
            if task_result:
                f1 = task_result["codedna"]["metrics_read"]["f1"]
                row += f" {f1:>15.0%}"
            else:
                row += f" {'—':>15}"
        print(row)

    print("\n📄 Paper-ready summary:")
    best_model = max(summaries, key=lambda n: summaries[n]["avg_f1"])
    bs = summaries[best_model]
    print(f'   Best model: {best_model} — '
          f'CodeDNA F1 {bs["avg_f1"]:.0%} vs Control {bs["ctrl_avg_f1"]:.0%} '
          f'(+{bs["avg_f1"]-bs["ctrl_avg_f1"]:.0%}), '
          f'{bs["tasks_better"]}/{bs["n"]} tasks improved.')

if __name__ == "__main__":
    main()
