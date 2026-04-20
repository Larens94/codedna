#!/usr/bin/env python3
"""Analyze existing benchmark_agent/runs results and generate paper-ready summaries.

Produces:
- research_support/analysis/model_summary.csv
- research_support/analysis/task_summary.csv
- research_support/analysis/REPORT_IT.md
"""

from __future__ import annotations

import csv
import itertools
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "benchmark_agent" / "runs"
OUT_DIR = ROOT / "research_support" / "analysis"


def _safe_mean(values: List[float]) -> float:
    return mean(values) if values else float("nan")


def _safe_std(values: List[float]) -> float:
    if len(values) <= 1:
        return 0.0
    return pstdev(values)


def _metric_f1(run: dict) -> float:
    return float(run.get("metrics_read", {}).get("f1", 0.0))


def _metric(run: dict, key: str) -> float | None:
    val = run.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _extract_runs(task_entry: dict, side: str) -> List[dict]:
    runs_key = f"{side}_runs"
    if runs_key in task_entry and task_entry[runs_key]:
        return list(task_entry[runs_key])
    single = task_entry.get(side)
    return [single] if isinstance(single, dict) else []


def _rank_abs(values: List[float]) -> List[float]:
    """Average ranks for ties on absolute values."""
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def wilcoxon_one_tailed_greater(diffs: List[float]) -> Tuple[float, float, int]:
    """Exact one-tailed Wilcoxon signed-rank p-value for H1: median(diffs) > 0."""
    nonzero = [d for d in diffs if d != 0]
    n = len(nonzero)
    if n == 0:
        return 0.0, 1.0, 0
    abs_vals = [abs(d) for d in nonzero]
    ranks = _rank_abs(abs_vals)
    w_plus_obs = sum(r for d, r in zip(nonzero, ranks) if d > 0)

    # Exact null distribution by enumerating all sign assignments.
    # Works well for small n (here n is usually <= 6).
    total = 0
    ge = 0
    for signs in itertools.product((0, 1), repeat=n):
        total += 1
        w_plus = sum(r for s, r in zip(signs, ranks) if s == 1)
        if w_plus >= w_plus_obs - 1e-12:
            ge += 1
    p_one_tailed = ge / total
    return w_plus_obs, p_one_tailed, n


def wilcoxon_one_tailed_greater_normal_approx(diffs: List[float]) -> Tuple[float, float, int, float]:
    """Project-consistent Wilcoxon one-tailed p-value via normal approximation.

    Mirrors benchmark_agent/swebench/analyze_multi.py behavior.
    Returns: (W_plus, p_approx, n_nonzero, z)
    """
    nonzero = [d for d in diffs if abs(d) > 1e-9]
    n = len(nonzero)
    if n == 0:
        return 0.0, 1.0, 0, 0.0

    abs_vals = [abs(d) for d in nonzero]
    ranks = _rank_abs(abs_vals)
    w_plus = sum(r for d, r in zip(nonzero, ranks) if d > 0)

    mu = n * (n + 1) / 4
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z = (w_plus - mu) / sigma if sigma > 0 else 0.0

    # Same A&S polynomial approximation used in analyze_multi.py
    def norm_cdf(x: float) -> float:
        t = 1 / (1 + 0.2316419 * abs(x))
        poly = t * (
            0.319381530
            + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429)))
        )
        p = 1 - (1 / math.sqrt(2 * math.pi)) * math.exp(-x * x / 2) * poly
        return p if x >= 0 else 1 - p

    p_approx = 1 - norm_cdf(z)  # one-tailed H1: greater
    return w_plus, p_approx, n, z


def sign_test_one_tailed_greater(diffs: List[float]) -> Tuple[int, int, float]:
    nonzero = [d for d in diffs if d != 0]
    n = len(nonzero)
    pos = sum(1 for d in nonzero if d > 0)
    if n == 0:
        return 0, 0, 1.0
    # P(X >= pos), X ~ Binomial(n, 0.5)
    p = 0.0
    for k in range(pos, n + 1):
        p += math.comb(n, k) * (0.5**n)
    return pos, n, p


def bootstrap_ci_mean(values: List[float], n_boot: int = 20000, seed: int = 42) -> Tuple[float, float]:
    if not values:
        return float("nan"), float("nan")
    rng = random.Random(seed)
    n = len(values)
    sims = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        sims.append(mean(sample))
    sims.sort()
    lo = sims[int(0.025 * n_boot)]
    hi = sims[int(0.975 * n_boot)]
    return lo, hi


@dataclass
class TaskRow:
    model: str
    instance_id: str
    repo: str
    n_runs_control: int
    n_runs_codedna: int
    f1_control_mean: float
    f1_codedna_mean: float
    f1_delta: float
    f1_control_std: float
    f1_codedna_std: float


def analyze_model(model_dir: Path) -> Tuple[List[TaskRow], dict]:
    model = model_dir.name
    data = json.loads((model_dir / "results.json").read_text(encoding="utf-8"))
    task_rows: List[TaskRow] = []

    deltas = []
    ctrl_means = []
    dna_means = []
    wins = 0
    losses = 0
    ties = 0

    # Optional metrics where available.
    opt_metric_keys = [
        "read_calls",
        "tool_calls",
        "n_files_read",
        "grep_calls",
        "total_chars_consumed",
        "input_tokens",
        "output_tokens",
        "nav_efficiency",
        "redundant_reads",
        "tokens_per_gt_file",
    ]
    opt_sums: Dict[str, List[float]] = {k: [] for k in opt_metric_keys}

    for t in data:
        control_runs = _extract_runs(t, "control")
        codedna_runs = _extract_runs(t, "codedna")

        c_f1 = [_metric_f1(r) for r in control_runs]
        d_f1 = [_metric_f1(r) for r in codedna_runs]
        c_mean = _safe_mean(c_f1)
        d_mean = _safe_mean(d_f1)
        delta = d_mean - c_mean

        ctrl_means.append(c_mean)
        dna_means.append(d_mean)
        deltas.append(delta)

        if delta > 0:
            wins += 1
        elif delta < 0:
            losses += 1
        else:
            ties += 1

        task_rows.append(
            TaskRow(
                model=model,
                instance_id=t.get("instance_id", ""),
                repo=t.get("repo", ""),
                n_runs_control=len(control_runs),
                n_runs_codedna=len(codedna_runs),
                f1_control_mean=c_mean,
                f1_codedna_mean=d_mean,
                f1_delta=delta,
                f1_control_std=_safe_std(c_f1),
                f1_codedna_std=_safe_std(d_f1),
            )
        )

        # Optional metrics: delta = codedna - control using per-task run means.
        for key in opt_metric_keys:
            c_vals = [v for v in (_metric(r, key) for r in control_runs) if v is not None]
            d_vals = [v for v in (_metric(r, key) for r in codedna_runs) if v is not None]
            if c_vals and d_vals:
                opt_sums[key].append(_safe_mean(d_vals) - _safe_mean(c_vals))

    w_plus, p_wilcoxon, n_w = wilcoxon_one_tailed_greater(deltas)
    w_plus_approx, p_wilcoxon_approx, n_w_approx, z_w_approx = wilcoxon_one_tailed_greater_normal_approx(deltas)
    sign_pos, sign_n, p_sign = sign_test_one_tailed_greater(deltas)
    ci_lo, ci_hi = bootstrap_ci_mean(deltas)

    summary = {
        "model": model,
        "n_tasks": len(task_rows),
        "control_f1_mean": _safe_mean(ctrl_means),
        "codedna_f1_mean": _safe_mean(dna_means),
        "delta_f1_mean": _safe_mean(deltas),
        "delta_f1_ci95_lo": ci_lo,
        "delta_f1_ci95_hi": ci_hi,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "wilcoxon_w_plus": w_plus,
        "wilcoxon_n": n_w,
        "wilcoxon_p_one_tailed_exact": p_wilcoxon,
        "wilcoxon_w_plus_approx": w_plus_approx,
        "wilcoxon_n_approx": n_w_approx,
        "wilcoxon_z_approx": z_w_approx,
        "wilcoxon_p_one_tailed_approx": p_wilcoxon_approx,
        "sign_pos": sign_pos,
        "sign_n": sign_n,
        "sign_p_one_tailed": p_sign,
    }

    for key in opt_metric_keys:
        vals = opt_sums[key]
        summary[f"delta_{key}_mean"] = _safe_mean(vals) if vals else float("nan")

    return task_rows, summary


def write_csv(path: Path, rows: Iterable[dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def generate_markdown(model_summaries: List[dict], task_rows: List[TaskRow]) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append("# Report Analisi Benchmark (Auto-generato)")
    lines.append("")
    lines.append(f"Generato: {ts}")
    lines.append("")
    lines.append("## Sintesi Modello")
    lines.append("")
    lines.append("| Model | Tasks | Ctrl F1 | DNA F1 | Delta | 95% CI Delta | Wins/Losses/Ties | Wilcoxon p exact | Wilcoxon p approx* |")
    lines.append("|---|---:|---:|---:|---:|---|---:|---:|")
    for s in model_summaries:
        lines.append(
            "| {model} | {n_tasks} | {c:.3f} | {d:.3f} | {delta:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {w}/{l}/{t} | {p_exact:.3f} | {p_approx:.3f} |".format(
                model=s["model"],
                n_tasks=s["n_tasks"],
                c=s["control_f1_mean"],
                d=s["codedna_f1_mean"],
                delta=s["delta_f1_mean"],
                lo=s["delta_f1_ci95_lo"],
                hi=s["delta_f1_ci95_hi"],
                w=s["wins"],
                l=s["losses"],
                t=s["ties"],
                p_exact=s["wilcoxon_p_one_tailed_exact"],
                p_approx=s["wilcoxon_p_one_tailed_approx"],
            )
        )

    lines.append("")
    lines.append("## Insight Operativi")
    lines.append("")
    lines.append("- `delta_f1_mean > 0` indica vantaggio medio CodeDNA.")
    lines.append("- `wins/losses` misura robustezza per-task (non solo media).")
    lines.append("- CI bootstrap aiuta a comunicare incertezza su campioni piccoli.")
    lines.append("- Wilcoxon one-tailed segue ipotesi H1: CodeDNA > Control.")
    lines.append("- `p approx` e calcolato con normal approximation (allineato allo script benchmark del repo).")
    lines.append("- `p exact` e il valore combinatorio esatto (piu conservativo con N piccoli).")
    lines.append("- Per modelli/task con N molto piccolo (es. n=1), il p-value va interpretato solo come indicazione preliminare.")
    lines.append("")

    # Add top 10 task deltas across all models.
    sorted_rows = sorted(task_rows, key=lambda x: x.f1_delta, reverse=True)
    lines.append("## Top Task Delta (positivi)")
    lines.append("")
    lines.append("| Model | Task | Delta F1 | Ctrl | DNA |")
    lines.append("|---|---|---:|---:|---:|")
    for r in sorted_rows[:10]:
        lines.append(
            f"| {r.model} | {r.instance_id} | {r.f1_delta:+.3f} | {r.f1_control_mean:.3f} | {r.f1_codedna_mean:.3f} |"
        )

    lines.append("")
    lines.append("## Task con regressione")
    lines.append("")
    lines.append("| Model | Task | Delta F1 | Ctrl | DNA |")
    lines.append("|---|---|---:|---:|---:|")
    for r in sorted(task_rows, key=lambda x: x.f1_delta):
        if r.f1_delta < 0:
            lines.append(
                f"| {r.model} | {r.instance_id} | {r.f1_delta:+.3f} | {r.f1_control_mean:.3f} | {r.f1_codedna_mean:.3f} |"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model_dirs = sorted([p for p in RUNS_DIR.iterdir() if p.is_dir() and (p / "results.json").exists()])
    all_task_rows: List[TaskRow] = []
    model_summaries: List[dict] = []

    for d in model_dirs:
        task_rows, summary = analyze_model(d)
        all_task_rows.extend(task_rows)
        model_summaries.append(summary)

    model_fields = list(model_summaries[0].keys()) if model_summaries else []
    write_csv(OUT_DIR / "model_summary.csv", model_summaries, model_fields)

    task_dict_rows = [
        {
            "model": r.model,
            "instance_id": r.instance_id,
            "repo": r.repo,
            "n_runs_control": r.n_runs_control,
            "n_runs_codedna": r.n_runs_codedna,
            "f1_control_mean": f"{r.f1_control_mean:.6f}",
            "f1_codedna_mean": f"{r.f1_codedna_mean:.6f}",
            "f1_delta": f"{r.f1_delta:.6f}",
            "f1_control_std": f"{r.f1_control_std:.6f}",
            "f1_codedna_std": f"{r.f1_codedna_std:.6f}",
        }
        for r in all_task_rows
    ]
    write_csv(
        OUT_DIR / "task_summary.csv",
        task_dict_rows,
        [
            "model",
            "instance_id",
            "repo",
            "n_runs_control",
            "n_runs_codedna",
            "f1_control_mean",
            "f1_codedna_mean",
            "f1_delta",
            "f1_control_std",
            "f1_codedna_std",
        ],
    )

    report = generate_markdown(model_summaries, all_task_rows)
    (OUT_DIR / "REPORT_IT.md").write_text(report, encoding="utf-8")

    print("Generated:")
    print(f"- {OUT_DIR / 'model_summary.csv'}")
    print(f"- {OUT_DIR / 'task_summary.csv'}")
    print(f"- {OUT_DIR / 'REPORT_IT.md'}")


if __name__ == "__main__":
    main()
