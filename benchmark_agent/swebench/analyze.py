"""
swebench/analyze.py — Analizza i risultati e genera tabella e statistiche.

deps:    results_swebench.json (output di run_agent.py)
exports: stampa tabella risultati + statistiche aggregate
rules:   Report results honestly — include ALL tasks, even negative ones.
"""

import json
from pathlib import Path

RESULTS_FILE = Path(__file__).parent.parent / "results_swebench.json"

def pct(v):
    return f"{v:+.0%}" if v != 0 else "0%"

def main():
    if not RESULTS_FILE.exists():
        print(f"ERROR: {RESULTS_FILE} not found. Run run_agent.py first.")
        return

    with open(RESULTS_FILE) as f:
        results = json.load(f)

    if not results:
        print("No results to analyze.")
        return

    print("\n" + "="*90)
    print("CodeDNA vs Control — SWE-bench Benchmark Results")
    print("="*90)
    print(f"\n{'Task':<40} {'Ctrl Calls':>10} {'DNA Calls':>10} {'Δ Calls':>8} "
          f"{'Ctrl Acc':>9} {'DNA Acc':>8} {'Δ Acc':>7}")
    print("-"*90)

    for r in results:
        ctrl = r["control"]
        cdna = r["codedna"]
        delta_calls = cdna["tool_calls"] - ctrl["tool_calls"]
        delta_acc = cdna["file_accuracy"] - ctrl["file_accuracy"]
        print(f"{r['instance_id'][:39]:<40} "
              f"{ctrl['tool_calls']:>10} {cdna['tool_calls']:>10} "
              f"{delta_calls:>+8} "
              f"{ctrl['file_accuracy']:>9.0%} {cdna['file_accuracy']:>8.0%} "
              f"{pct(delta_acc):>7}")

    print("-"*90)

    # Aggregates
    n = len(results)
    avg_ctrl_calls = sum(r["control"]["tool_calls"] for r in results) / n
    avg_cdna_calls = sum(r["codedna"]["tool_calls"] for r in results) / n
    avg_ctrl_acc = sum(r["control"]["file_accuracy"] for r in results) / n
    avg_cdna_acc = sum(r["codedna"]["file_accuracy"] for r in results) / n
    pct_reduction_calls = (avg_ctrl_calls - avg_cdna_calls) / avg_ctrl_calls if avg_ctrl_calls else 0

    print(f"{'AVERAGE':<40} {avg_ctrl_calls:>10.1f} {avg_cdna_calls:>10.1f} "
          f"{avg_cdna_calls-avg_ctrl_calls:>+8.1f} "
          f"{avg_ctrl_acc:>9.0%} {avg_cdna_acc:>8.0%} "
          f"{pct(avg_cdna_acc - avg_ctrl_acc):>7}")

    print(f"\n📊 Summary ({n} tasks):")
    print(f"   Tool calls:     Control avg {avg_ctrl_calls:.1f} → CodeDNA avg {avg_cdna_calls:.1f} "
          f"({pct_reduction_calls:.0%} reduction)")
    print(f"   File accuracy:  Control avg {avg_ctrl_acc:.0%} → CodeDNA avg {avg_cdna_acc:.0%}")

    # Tasks where CodeDNA won
    codedna_better_calls = sum(1 for r in results if r["codedna"]["tool_calls"] < r["control"]["tool_calls"])
    codedna_better_acc = sum(1 for r in results if r["codedna"]["file_accuracy"] > r["control"]["file_accuracy"])
    print(f"   CodeDNA fewer calls: {codedna_better_calls}/{n} tasks")
    print(f"   CodeDNA better accuracy: {codedna_better_acc}/{n} tasks")

    # Paper-ready numbers
    print(f"\n📄 Paper-ready sentence:")
    print(f'   "On {n} real SWE-bench tasks from the Flask ecosystem, CodeDNA reduced '
          f'agent tool calls by {pct_reduction_calls:.0%} '
          f'(from {avg_ctrl_calls:.1f} to {avg_cdna_calls:.1f} per task) and improved '
          f'cross-file navigation accuracy from {avg_ctrl_acc:.0%} to {avg_cdna_acc:.0%}."')

if __name__ == "__main__":
    main()
