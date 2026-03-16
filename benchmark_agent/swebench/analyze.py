"""
swebench/analyze.py — Analyze results and generate table + statistics.

deps:    results_swebench.json (output of run_agent.py)
exports: prints results table + aggregated statistics
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

    n = len(results)

    # Helper to safely get a key with fallback (for backward compat)
    def g(d, key, fallback=0):
        return d.get(key, fallback)

    # ── Table 1: Tool Calls & Chars ──
    print("\n" + "="*100)
    print("CodeDNA vs Control — SWE-bench File Localization Benchmark")
    print("="*100)

    print(f"\n{'Task':<40} {'Ctrl Read':<10} {'DNA Read':<10} "
          f"{'Ctrl Grep':<10} {'DNA Grep':<10} "
          f"{'Ctrl Uniq':<10} {'DNA Uniq':<10} "
          f"{'Ctrl Chars':>11} {'DNA Chars':>10}")
    print("-"*120)

    for r in results:
        ctrl = r["control"]
        cdna = r["codedna"]
        print(f"{r['instance_id'][:39]:<40} "
              f"{g(ctrl,'read_calls', ctrl['tool_calls']):<10} "
              f"{g(cdna,'read_calls', cdna['tool_calls']):<10} "
              f"{g(ctrl,'grep_calls'):<10} "
              f"{g(cdna,'grep_calls'):<10} "
              f"{ctrl['n_files_read']:<10} "
              f"{cdna['n_files_read']:<10} "
              f"{ctrl['total_chars_consumed']:>11,} "
              f"{cdna['total_chars_consumed']:>10,}")

    # Aggregates for table 1
    avg_ctrl_reads = sum(g(r["control"],"read_calls", r["control"]["tool_calls"]) for r in results) / n
    avg_cdna_reads = sum(g(r["codedna"],"read_calls", r["codedna"]["tool_calls"]) for r in results) / n
    avg_ctrl_unique = sum(r["control"]["n_files_read"] for r in results) / n
    avg_cdna_unique = sum(r["codedna"]["n_files_read"] for r in results) / n
    avg_ctrl_chars = sum(r["control"]["total_chars_consumed"] for r in results) / n
    avg_cdna_chars = sum(r["codedna"]["total_chars_consumed"] for r in results) / n
    print("-"*120)
    print(f"{'AVERAGE':<40} "
          f"{avg_ctrl_reads:<10.1f} {avg_cdna_reads:<10.1f} "
          f"{'':10} {'':10} "
          f"{avg_ctrl_unique:<10.1f} {avg_cdna_unique:<10.1f} "
          f"{avg_ctrl_chars:>11,.0f} {avg_cdna_chars:>10,.0f}")

    # ── Table 2: File Metrics (Read-based) ──
    print(f"\n{'─'*90}")
    print(f"  FILE METRICS (based on unique files read via read_file tool)")
    print(f"{'─'*90}")
    print(f"\n{'Task':<40} {'Ctrl R':>7} {'DNA R':>7} {'Δ R':>6} "
          f"{'Ctrl P':>7} {'DNA P':>7} "
          f"{'Ctrl F1':>8} {'DNA F1':>8}")
    print("-"*90)

    for r in results:
        cr = r["control"]["metrics_read"]
        dr = r["codedna"]["metrics_read"]
        print(f"{r['instance_id'][:39]:<40} "
              f"{cr['recall']:>7.0%} {dr['recall']:>7.0%} {pct(dr['recall']-cr['recall']):>6} "
              f"{cr['precision']:>7.0%} {dr['precision']:>7.0%} "
              f"{cr['f1']:>8.0%} {dr['f1']:>8.0%}")

    avg_cr = sum(r["control"]["metrics_read"]["recall"] for r in results) / n
    avg_dr = sum(r["codedna"]["metrics_read"]["recall"] for r in results) / n
    avg_cp = sum(r["control"]["metrics_read"]["precision"] for r in results) / n
    avg_dp = sum(r["codedna"]["metrics_read"]["precision"] for r in results) / n
    avg_cf1 = sum(r["control"]["metrics_read"]["f1"] for r in results) / n
    avg_df1 = sum(r["codedna"]["metrics_read"]["f1"] for r in results) / n
    print("-"*90)
    print(f"{'AVERAGE':<40} "
          f"{avg_cr:>7.0%} {avg_dr:>7.0%} {pct(avg_dr-avg_cr):>6} "
          f"{avg_cp:>7.0%} {avg_dp:>7.0%} "
          f"{avg_cf1:>8.0%} {avg_df1:>8.0%}")

    # ── Table 3: File Metrics (Proposed in final response) ──
    print(f"\n{'─'*90}")
    print(f"  FILE METRICS (based on files proposed in final text response)")
    print(f"{'─'*90}")
    print(f"\n{'Task':<40} {'Ctrl R':>7} {'DNA R':>7} {'Δ R':>6} "
          f"{'Ctrl P':>7} {'DNA P':>7} "
          f"{'Ctrl F1':>8} {'DNA F1':>8}")
    print("-"*90)

    for r in results:
        cr = r["control"]["metrics_proposed"]
        dr = r["codedna"]["metrics_proposed"]
        print(f"{r['instance_id'][:39]:<40} "
              f"{cr['recall']:>7.0%} {dr['recall']:>7.0%} {pct(dr['recall']-cr['recall']):>6} "
              f"{cr['precision']:>7.0%} {dr['precision']:>7.0%} "
              f"{cr['f1']:>8.0%} {dr['f1']:>8.0%}")

    avg_cr_p = sum(r["control"]["metrics_proposed"]["recall"] for r in results) / n
    avg_dr_p = sum(r["codedna"]["metrics_proposed"]["recall"] for r in results) / n
    avg_cp_p = sum(r["control"]["metrics_proposed"]["precision"] for r in results) / n
    avg_dp_p = sum(r["codedna"]["metrics_proposed"]["precision"] for r in results) / n
    avg_cf1_p = sum(r["control"]["metrics_proposed"]["f1"] for r in results) / n
    avg_df1_p = sum(r["codedna"]["metrics_proposed"]["f1"] for r in results) / n
    print("-"*90)
    print(f"{'AVERAGE':<40} "
          f"{avg_cr_p:>7.0%} {avg_dr_p:>7.0%} {pct(avg_dr_p-avg_cr_p):>6} "
          f"{avg_cp_p:>7.0%} {avg_dp_p:>7.0%} "
          f"{avg_cf1_p:>8.0%} {avg_df1_p:>8.0%}")

    # ── Summary ──
    codedna_better_f1 = sum(1 for r in results
                           if r["codedna"]["metrics_read"]["f1"] > r["control"]["metrics_read"]["f1"])

    print(f"\n📊 Summary ({n} tasks):")
    print(f"   Read calls:     Control avg {avg_ctrl_reads:.1f} → CodeDNA avg {avg_cdna_reads:.1f}")
    print(f"   Unique files:   Control avg {avg_ctrl_unique:.1f} → CodeDNA avg {avg_cdna_unique:.1f}")
    print(f"   Chars consumed: Control avg {avg_ctrl_chars:,.0f} → CodeDNA avg {avg_cdna_chars:,.0f}")
    print(f"   Read Recall:    Control avg {avg_cr:.0%} → CodeDNA avg {avg_dr:.0%}")
    print(f"   Read F1:        Control avg {avg_cf1:.0%} → CodeDNA avg {avg_df1:.0%}")
    print(f"   CodeDNA better F1: {codedna_better_f1}/{n} tasks")

    print(f"\n📄 Paper-ready sentence:")
    print(f'   "On {n} real SWE-bench tasks from the Django ecosystem, CodeDNA '
          f'improved file localization recall from {avg_cr:.0%} to {avg_dr:.0%} '
          f'and F1 from {avg_cf1:.0%} to {avg_df1:.0%} '
          f'(CodeDNA better on {codedna_better_f1}/{n} tasks)."')

if __name__ == "__main__":
    main()

