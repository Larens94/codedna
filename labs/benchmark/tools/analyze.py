"""analyze.py — Analyse labs/benchmark benchmark results across conditions.

exports: wilcoxon_signed_rank(pairs) -> dict | bootstrap_ci(diffs, n_iter, alpha) -> tuple | permutation_test(pairs, n_iter) -> float | load_results(model_name) -> list | summarize_model(results, conditions) -> None | main()
used_by: none
rules:   Report ALL tasks even when condition missing — mark explicitly with "n/a".
         Wilcoxon one-tailed H1: codedna > baseline (matched, control, placebo).
         Statistical tests: (1) Wilcoxon signed-rank (normal approx, N>=5),
         (2) paired permutation test on means (10k shuffles, no distribution assumption),
         (3) bootstrap 95% CI on paired deltas.
         Primary metric = metrics_read.f1 on unique files read (∩ ground truth).
         Secondary metrics: tool_calls, nav_efficiency, turn_first_hit, tokens_per_gt_file.
         When nav trace contains placebo/matched alongside codedna, compute
         Δ(codedna−placebo) = pure graph effect, Δ(codedna−matched) = pure annotation effect.
agent:   claude-opus-4-7 | anthropic | 2026-04-17 | s_20260417_analyze | initial port of legacy analyze_multi.py — adapted to labs/benchmark runs + multi-condition (control, matched, placebo, codedna). Adds permutation + bootstrap alongside Wilcoxon.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Optional

BENCH_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = BENCH_ROOT / "runs"
PROJECTS_DIR = BENCH_ROOT / "projects"
# Fallback to legacy location for pre-2026-04-17 data
_LEGACY_RUNS = Path(__file__).resolve().parents[3] / "benchmark_agent" / "runs"


# ─────────────────── Statistical tests ───────────────────

def wilcoxon_signed_rank(pairs: list[tuple[float, float]]) -> dict:
    """One-sided Wilcoxon signed-rank: H1: treatment > baseline.

    pairs: list of (baseline, treatment). Returns W+, n, approximate p (normal).
    """
    diffs = [b - a for a, b in pairs]
    nonzero = [(i, d) for i, d in enumerate(diffs) if abs(d) > 1e-9]
    n = len(nonzero)
    if n == 0:
        return {"W_plus": 0, "n": 0, "p_approx": 1.0, "significant_05": False,
                "note": "all differences are zero"}

    abs_sorted = sorted(enumerate(nonzero), key=lambda x: abs(x[1][1]))
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(abs_sorted[j + 1][1][1]) == abs(abs_sorted[i][1][1]):
            j += 1
        avg_rank = (i + 1 + j + 1) / 2
        for k in range(i, j + 1):
            ranks[abs_sorted[k][0]] = avg_rank
        i = j + 1

    w_plus = sum(r for r, (_, d) in zip(ranks, nonzero) if d > 0)

    mu = n * (n + 1) / 4
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z = (w_plus - mu) / sigma if sigma > 0 else 0.0
    p_approx = 0.5 * math.erfc(z / math.sqrt(2)) if z > 0 else 1 - 0.5 * math.erfc(-z / math.sqrt(2))

    return {
        "W_plus": round(w_plus, 2),
        "n": n,
        "z": round(z, 3),
        "p_approx": round(p_approx, 4),
        "significant_05": p_approx < 0.05,
        "note": "normal approximation (reliable n>=5)" if n >= 5 else f"n={n} too small; interpret p with caution",
    }


def permutation_test(pairs: list[tuple[float, float]], n_iter: int = 10000,
                     seed: int = 42) -> dict:
    """Paired permutation test on mean difference (one-tailed, H1: treatment > baseline).

    Under H0 (no effect) signs are exchangeable. Count how often a random
    sign-flip of diffs yields a mean as extreme as the observed one.
    """
    diffs = [b - a for a, b in pairs]
    obs = sum(diffs) / len(diffs) if diffs else 0.0
    rng = random.Random(seed)
    ge = 0
    for _ in range(n_iter):
        flipped = [d if rng.random() > 0.5 else -d for d in diffs]
        if sum(flipped) / len(flipped) >= obs:
            ge += 1
    p = ge / n_iter
    return {"mean_diff": round(obs, 4), "p_permutation": round(p, 4),
            "significant_05": p < 0.05, "n_iter": n_iter}


def bootstrap_ci(diffs: list[float], n_iter: int = 10000, alpha: float = 0.05,
                 seed: int = 42) -> tuple[float, float, float]:
    """Bootstrap CI on mean of diffs. Returns (mean, ci_low, ci_high)."""
    if not diffs:
        return (0.0, 0.0, 0.0)
    rng = random.Random(seed)
    means = []
    n = len(diffs)
    for _ in range(n_iter):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(n_iter * alpha / 2)]
    hi = means[int(n_iter * (1 - alpha / 2))]
    return (round(sum(diffs) / n, 4), round(lo, 4), round(hi, 4))


# ─────────────────── Load & inspect ───────────────────

def _condition_runs(entry: dict, cond: str) -> list:
    """Return per-run results list for a condition, prefer *_runs, fall back to single."""
    runs = entry.get(f"{cond}_runs")
    if runs:
        return runs
    single = entry.get(cond)
    return [single] if single else []


def load_results(model_name: str) -> list:
    """Load results.json for a model, checking labs dir first then legacy."""
    for base in (RUNS_DIR, _LEGACY_RUNS):
        p = base / model_name.replace("/", "-") / "results.json"
        if p.exists():
            return json.loads(p.read_text())
    return []


def _mean_metric(entry: dict, cond: str, metric_path: list[str]) -> Optional[float]:
    """entry[cond_runs] → mean of entry[cond_runs][i][metric_path...]."""
    runs = _condition_runs(entry, cond)
    vals = []
    for r in runs:
        cur = r
        for k in metric_path:
            if not isinstance(cur, dict) or k not in cur:
                cur = None
                break
            cur = cur[k]
        if isinstance(cur, (int, float)) and not isinstance(cur, bool):
            vals.append(cur)
        elif cur is True:
            vals.append(1.0)
        elif cur is False:
            vals.append(0.0)
    return sum(vals) / len(vals) if vals else None


# ─────────────────── Summary report ───────────────────

def summarize_model(results: list, model_name: str,
                    conditions: list[str] = ("control", "matched", "placebo", "codedna")) -> None:
    print(f"\n{'='*90}")
    print(f"  Model: {model_name}")
    print(f"  Tasks: {len(results)}   Conditions present:")
    # Which conditions have at least one run in any task?
    active = [c for c in conditions
              if any(_condition_runs(e, c) for e in results)]
    print(f"    {active}")
    print('='*90)

    # Per-task F1 table (metrics_read.f1)
    print(f"\n{'Task':<26} " + " ".join(f"{c:>9}" for c in active))
    print("-" * (26 + 10 * len(active)))
    for e in results:
        iid = e.get("instance_id", "?").replace("django__django-", "")
        row = f"{iid:<26} "
        for c in active:
            f1 = _mean_metric(e, c, ["metrics_read", "f1"])
            row += f"{f1:>9.3f} " if f1 is not None else f"{'n/a':>9} "
        print(row)

    # Comparisons: codedna vs each baseline
    if "codedna" in active:
        for baseline in [b for b in ("control", "matched", "placebo") if b in active]:
            pairs = []
            for e in results:
                bl = _mean_metric(e, baseline, ["metrics_read", "f1"])
                tr = _mean_metric(e, "codedna", ["metrics_read", "f1"])
                if bl is not None and tr is not None:
                    pairs.append((bl, tr))
            if len(pairs) < 3:
                print(f"\n  codedna vs {baseline}: only {len(pairs)} paired tasks — skipping stats")
                continue
            print(f"\n  Δ(codedna − {baseline}) on F1_read:")
            diffs = [b - a for a, b in pairs]
            mean, lo, hi = bootstrap_ci(diffs)
            w = wilcoxon_signed_rank(pairs)
            perm = permutation_test(pairs)
            print(f"    mean Δ = {mean:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]  (N={len(pairs)})")
            print(f"    Wilcoxon W+ = {w['W_plus']}  z = {w['z']}  p ≈ {w['p_approx']}  {'✅ sig' if w['significant_05'] else '❌'}")
            print(f"    Permutation p = {perm['p_permutation']}  {'✅ sig' if perm['significant_05'] else '❌'}")

    # Secondary metrics (tool_calls, nav_efficiency)
    print(f"\n  Secondary (means across tasks):")
    print(f"    {'cond':<10} {'tool_calls':>11} {'nav_eff':>8} {'1st_hit_turn':>13} {'tokens/GT':>10}")
    for c in active:
        tc_vals = [v for e in results if (v := _mean_metric(e, c, ["tool_calls"])) is not None]
        ne_vals = [v for e in results if (v := _mean_metric(e, c, ["nav_efficiency"])) is not None]
        th_vals = [v for e in results if (v := _mean_metric(e, c, ["turn_first_hit"])) is not None]
        tg_vals = [v for e in results if (v := _mean_metric(e, c, ["tokens_per_gt_file"])) is not None]
        def m(vs): return sum(vs)/len(vs) if vs else float("nan")
        print(f"    {c:<10} {m(tc_vals):>11.1f} {m(ne_vals):>8.3f} {m(th_vals):>13.2f} {m(tg_vals):>10.0f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="Model name (dir under runs/). Default: all found.")
    ap.add_argument("--conditions", nargs="+",
                    default=["control", "matched", "placebo", "codedna"],
                    help="Conditions to include (default: all 4)")
    ap.add_argument("--json", action="store_true", help="Emit JSON summary")
    args = ap.parse_args()

    if args.model:
        models = [args.model]
    else:
        models = []
        for base in (RUNS_DIR, _LEGACY_RUNS):
            if base.exists():
                models.extend(p.name for p in base.iterdir() if p.is_dir() and (p / "results.json").exists())
        models = sorted(set(models))

    if not models:
        print("No results found in", RUNS_DIR, "or", _LEGACY_RUNS)
        return

    for m in models:
        results = load_results(m)
        if not results:
            print(f"skip {m} (no results)")
            continue
        summarize_model(results, m, args.conditions)


if __name__ == "__main__":
    main()
