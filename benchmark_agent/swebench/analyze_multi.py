"""
swebench/analyze_multi.py — Compare CodeDNA benchmark results across models and conditions.

deps:    runs/*/results.json (output of run_agent_multi.py)
exports: comparative table, Wilcoxon signed-rank test, annotation cost, qualitative rules report
rules:   Report results honestly — include ALL tasks and ALL models.
         Wilcoxon requires N≥3 non-zero differences; flag when sample is too small.

Usage:
  python analyze_multi.py                          # all result files found
  python analyze_multi.py --model gemini-2.5-flash
  python analyze_multi.py --qualitative            # show which rules the agent read
  python analyze_multi.py --annotation-cost        # show auto-annotation cost
"""

import argparse
import json
import math
from pathlib import Path

RESULTS_DIR  = Path(__file__).parent.parent / "runs"
PROJECTS_DIR = Path(__file__).parent.parent / "projects_swebench"


# ─────────────────── Wilcoxon signed-rank (manual, no scipy) ───────────────────

def wilcoxon_signed_rank(pairs: list[tuple[float, float]]) -> dict:
    """
    One-sided Wilcoxon signed-rank test: H1: codedna > control.
    Returns: {W_plus, n, p_approx, significant_05, note}
    p_approx uses normal approximation (valid for n >= 5).
    """
    diffs = [b - a for a, b in pairs]
    nonzero = [(i, d) for i, d in enumerate(diffs) if abs(d) > 1e-9]
    n = len(nonzero)

    if n == 0:
        return {"W_plus": 0, "n": 0, "p_approx": 1.0, "significant_05": False,
                "note": "all differences are zero"}

    # Rank by absolute value
    ranked = sorted(nonzero, key=lambda x: abs(x[1]))
    ranks  = list(range(1, n + 1))

    # Handle ties: average ranks
    i = 0
    while i < n:
        j = i + 1
        while j < n and abs(abs(ranked[j][1]) - abs(ranked[i][1])) < 1e-9:
            j += 1
        if j > i + 1:
            avg = sum(ranks[i:j]) / (j - i)
            ranks[i:j] = [avg] * (j - i)
        i = j

    W_plus  = sum(r for (_, d), r in zip(ranked, ranks) if d > 0)
    W_minus = sum(r for (_, d), r in zip(ranked, ranks) if d < 0)

    # Normal approximation: z = (W+ - mu) / sigma
    mu    = n * (n + 1) / 4
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z     = (W_plus - mu) / sigma if sigma > 0 else 0.0

    # One-tailed p-value from z (approximation using Abramowitz & Stegun)
    def norm_cdf(x):
        t = 1 / (1 + 0.2316419 * abs(x))
        poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937
               + t * (-1.821255978 + t * 1.330274429))))
        p = 1 - (1 / math.sqrt(2 * math.pi)) * math.exp(-x * x / 2) * poly
        return p if x >= 0 else 1 - p

    p_approx = 1 - norm_cdf(z)  # one-tailed

    note = ""
    if n < 5:
        note = f"n={n} is small; p-value approximation unreliable — report W+={W_plus} directly"

    return {
        "W_plus":         round(W_plus, 2),
        "W_minus":        round(W_minus, 2),
        "n":              n,
        "z":              round(z, 3),
        "p_approx":       round(p_approx, 4),
        "significant_05": p_approx < 0.05,
        "note":           note,
    }


# ─────────────────── Qualitative rules analysis ───────────────────

def extract_rules_from_file(filepath: Path) -> list[str]:
    """Extract rules: lines from a CodeDNA-annotated Python file."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    rules = []
    in_docstring = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith(('"""', "'''")):
            in_docstring = not in_docstring
            if not in_docstring:
                break
            continue
        if in_docstring and stripped.startswith("rules:"):
            rule_text = stripped[len("rules:"):].strip()
            if rule_text:
                rules.append(rule_text)
    return rules


def qualitative_rules_report(results: list, condition: str = "codedna") -> str:
    """
    For each task: list rules: encountered by the agent (files it read),
    and mark which rules came from ground-truth files.
    """
    lines = [f"\n{'='*80}", "Qualitative Rules Analysis",
             f"Condition: {condition}", "="*80]

    for entry in results:
        iid   = entry["instance_id"]
        cond  = entry.get(condition)
        if cond is None:
            continue

        gt_set       = set(entry.get("ground_truth_files", []))
        files_read   = cond.get("files_read_unique", cond.get("files_read", []))
        variant_dir  = PROJECTS_DIR / iid / condition.replace("-", "_")

        lines.append(f"\n  Task: {iid}")
        lines.append(f"  Files read: {len(files_read)}  GT files: {len(gt_set)}")

        rules_seen = []
        for rel_path in files_read:
            fp = variant_dir / rel_path
            rules = extract_rules_from_file(fp)
            for rule in rules:
                is_gt = rel_path in gt_set
                rules_seen.append((rel_path, rule, is_gt))

        if rules_seen:
            lines.append("  Rules encountered:")
            for path, rule, is_gt in rules_seen:
                tag = " [GT]" if is_gt else ""
                lines.append(f"    [{path}]{tag}")
                lines.append(f"      → {rule}")
        else:
            lines.append("  (no rules: fields encountered or variant not annotated)")

    return "\n".join(lines)


# ─────────────────── Annotation cost report ───────────────────

def annotation_cost_report(results: list) -> str:
    lines = [f"\n{'='*80}", "Annotation Cost (agent_annotated condition)", "="*80]
    total_chars, total_files, total_time = 0, 0, 0.0
    found = False
    for entry in results:
        cost = entry.get("annotation_cost")
        if not cost:
            continue
        found = True
        lines.append(
            f"  {entry['instance_id']:<35}  "
            f"{cost['files_annotated']:>3}/{cost['files_considered']:<3} files  "
            f"{cost['chars_generated']:>8,} chars  "
            f"{cost['elapsed_seconds']:>6.1f}s  "
            f"model: {cost.get('model_id','?')}"
        )
        total_chars += cost["chars_generated"]
        total_files += cost["files_annotated"]
        total_time  += cost["elapsed_seconds"]
    if not found:
        lines.append("  (no annotation cost data — run setup_agent_annotated.py first)")
    else:
        lines.append(f"  {'TOTAL':<35}  {total_files:>7} files  "
                     f"{total_chars:>8,} chars  {total_time:>6.1f}s")
    return "\n".join(lines)


# ─────────────────── Summarize one model's results ───────────────────

def _has_metrics(entry: dict, condition: str) -> bool:
    c = entry.get(condition)
    return c is not None and c.get("metrics_read") is not None


def summarize(results: list) -> dict:
    conditions = ["control", "codedna", "agent_annotated"]
    out = {}
    for cond in conditions:
        valid = [r for r in results if _has_metrics(r, cond)]
        n = len(valid)
        if n == 0:
            continue
        out[cond] = {
            "n":             n,
            "avg_f1":        sum(r[cond]["metrics_read"]["f1"]       for r in valid) / n,
            "avg_recall":    sum(r[cond]["metrics_read"]["recall"]    for r in valid) / n,
            "avg_precision": sum(r[cond]["metrics_read"]["precision"] for r in valid) / n,
            "avg_chars":     sum(r[cond]["total_chars_consumed"]      for r in valid) / n,
            "avg_files":     sum(r[cond]["n_files_read"]              for r in valid) / n,
        }
    return out


def load_model_results(model_name: str) -> list | None:
    path = RESULTS_DIR / model_name.replace("/", "-") / "results.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def pct(v: float) -> str:
    return f"{v:+.0%}" if v != 0 else " 0%"


# ─────────────────── Main ───────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",         nargs="+", help="Model names to compare")
    parser.add_argument("--qualitative",   action="store_true",
                        help="Show qualitative rules analysis per task")
    parser.add_argument("--annotation-cost", action="store_true",
                        help="Show auto-annotation cost table")
    args = parser.parse_args()

    model_names = args.model or [
        p.parent.name for p in RESULTS_DIR.glob("*/results.json")
    ]
    if not model_names:
        print("No result files found. Run run_agent_multi.py first.")
        return

    print("\n" + "="*110)
    print("CodeDNA Benchmark — Multi-Model Comparison")
    print("="*110)

    # ── Per-model summary table ──
    print(f"\n{'Model':<25} {'Ctrl F1':>8} {'DNA F1':>8} {'Ann F1':>8} "
          f"{'Δ(DNA)':>7} {'Δ(Ann)':>7} {'DNA Chars':>10} {'Tasks↑(DNA)':>12}")
    print("-"*95)

    all_summaries: dict[str, dict] = {}
    all_results:   dict[str, list] = {}

    for name in model_names:
        results = load_model_results(name)
        if results is None:
            print(f"  {name:<23} — no results file found")
            continue
        s = summarize(results)
        if not s:
            print(f"  {name:<23} — no valid results")
            continue
        all_summaries[name] = s
        all_results[name]   = results

        ctrl_f1 = s.get("control",        {}).get("avg_f1")
        dna_f1  = s.get("codedna",        {}).get("avg_f1")
        ann_f1  = s.get("agent_annotated",{}).get("avg_f1")

        ctrl_str = f"{ctrl_f1:.0%}" if ctrl_f1 is not None else "—"
        dna_str  = f"{dna_f1:.0%}"  if dna_f1  is not None else "—"
        ann_str  = f"{ann_f1:.0%}"  if ann_f1  is not None else "—"

        delta_dna = pct(dna_f1 - ctrl_f1) if (dna_f1 and ctrl_f1) else "—"
        delta_ann = pct(ann_f1 - ctrl_f1) if (ann_f1 and ctrl_f1) else "—"
        dna_chars = s.get("codedna", {}).get("avg_chars", 0)

        # tasks improved: codedna vs control
        comparable = [r for r in results if _has_metrics(r, "codedna") and _has_metrics(r, "control")]
        tasks_up   = sum(1 for r in comparable
                         if r["codedna"]["metrics_read"]["f1"] > r["control"]["metrics_read"]["f1"])
        n_comp     = len(comparable)

        print(f"  {name:<23} {ctrl_str:>8} {dna_str:>8} {ann_str:>8} "
              f"{delta_dna:>7} {delta_ann:>7} {dna_chars:>10,.0f} "
              f"  {tasks_up}/{n_comp}")

    # ── Wilcoxon signed-rank test ──
    print(f"\n{'─'*95}")
    print("  Wilcoxon Signed-Rank Test  (H1: condition > control, one-tailed)")
    print(f"{'─'*95}")
    print(f"  {'Model':<25} {'Condition':<18} {'W+':>6} {'n':>4} {'z':>7} {'p':>8}  {'sig?':>6}  Note")
    print(f"  {'-'*85}")

    for name, results in all_results.items():
        for cond_key, cond_label in [("codedna", "CodeDNA"), ("agent_annotated", "AgentAnnotated")]:
            pairs = [
                (r["control"]["metrics_read"]["f1"], r[cond_key]["metrics_read"]["f1"])
                for r in results
                if _has_metrics(r, "control") and _has_metrics(r, cond_key)
            ]
            if not pairs:
                continue
            w = wilcoxon_signed_rank(pairs)
            sig_str = "✓ p<0.05" if w["significant_05"] else "✗"
            note    = w["note"] or ""
            print(f"  {name:<25} {cond_label:<18} {w['W_plus']:>6} {w['n']:>4} "
                  f"{w['z']:>7.3f} {w['p_approx']:>8.4f}  {sig_str:<8}  {note}")

    # ── Per-task breakdown ──
    if all_summaries:
        ref_name    = list(all_summaries.keys())[0]
        ref_results = all_results[ref_name]
        task_ids    = [r["instance_id"] for r in ref_results]

        print(f"\n{'─'*95}")
        print("  Per-task F1 — CodeDNA condition")
        header = f"  {'Task':<35}"
        for name in all_summaries:
            header += f" {name[:14]:>15}"
        print(header)
        print("  " + "-"*85)
        for tid in task_ids:
            row = f"  {tid[:34]:<35}"
            for name in all_summaries:
                r = next((x for x in all_results[name] if x["instance_id"] == tid), None)
                if r and _has_metrics(r, "codedna"):
                    row += f" {r['codedna']['metrics_read']['f1']:>15.0%}"
                else:
                    row += f" {'—':>15}"
            print(row)

    # ── Qualitative rules analysis ──
    if args.qualitative and all_results:
        ref_name = list(all_results.keys())[0]
        print(qualitative_rules_report(all_results[ref_name], "codedna"))
        if any(_has_metrics(r, "agent_annotated") for r in all_results[ref_name]):
            print(qualitative_rules_report(all_results[ref_name], "agent_annotated"))

    # ── Annotation cost ──
    if args.annotation_cost and all_results:
        ref_name = list(all_results.keys())[0]
        print(annotation_cost_report(all_results[ref_name]))

    # ── Paper-ready summary ──
    print(f"\n{'─'*95}")
    print("  Paper-ready summary:")
    if all_summaries:
        best = max(all_summaries,
                   key=lambda n: all_summaries[n].get("codedna", {}).get("avg_f1", 0))
        bs = all_summaries[best]
        cf = bs.get("control", {}).get("avg_f1", 0)
        df = bs.get("codedna", {}).get("avg_f1", 0)
        af = bs.get("agent_annotated", {}).get("avg_f1")
        n  = bs.get("codedna", {}).get("n", 0)
        print(f"  Best model: {best}")
        print(f"    CodeDNA F1:     {df:.0%}  vs Control: {cf:.0%}  (Δ={df-cf:+.0%}) over {n} task(s)")
        if af is not None:
            print(f"    AgentAnn F1:    {af:.0%}  vs Control: {cf:.0%}  (Δ={af-cf:+.0%})")
        print(f"\n  ⚠️  Statistical note: Wilcoxon p-values are approximate (normal approx).")
        print(f"     For N<5, report W+ directly and note exact p requires lookup table.")


if __name__ == "__main__":
    main()
