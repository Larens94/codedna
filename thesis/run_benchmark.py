"""run_benchmark.py — CodeDNA Thesis Benchmark.

Empirical test: do CodeDNA `rules:` headers reduce AI agent constraint violations?

Experimental design:
  Condition A (baseline):  LLM sees the file WITHOUT CodeDNA headers.
  Condition B (annotated): LLM sees the same file WITH CodeDNA headers + rules:.

For each of 12 tasks the LLM is asked to implement a feature.
A second LLM call judges whether the implementation violates the constraint.

Usage:
  python thesis/run_benchmark.py --api-key $DEEPSEEK_API_KEY --model deepseek/deepseek-chat
  python thesis/run_benchmark.py --api-key $OPENAI_API_KEY  --model gpt-4o-mini
  python thesis/run_benchmark.py --api-key $ANTHROPIC_KEY   --model claude-haiku-4-5-20251001

  --runs N      Repeat each task N times for statistical robustness (default: 3)
  --dry-run     Show prompts without calling the LLM
  --judge-model Use a different model for judging (default: same as --model)

exports: run_benchmark
used_by: none
rules:   Never import from codedna_tool here — this benchmark must be self-contained.
         Do not cache LLM responses between baseline and annotated conditions.
         Each run uses a fresh LLM call (temperature=0.3) to capture variance.
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_bench | initial benchmark runner
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import litellm
    litellm.set_verbose = False
except ImportError:
    print("ERROR: pip install litellm")
    sys.exit(1)

THESIS_DIR = Path(__file__).parent
TASKS_FILE = THESIS_DIR / "tasks.json"
BASELINE_DIR = THESIS_DIR / "codebase" / "baseline"
ANNOTATED_DIR = THESIS_DIR / "codebase" / "annotated"
RESULTS_DIR = THESIS_DIR / "results"


# ── Prompt templates ─────────────────────────────────────────────────────────

_SYSTEM_IMPL = """\
You are a Python developer working on a payment SaaS codebase.
You will be given a source file and asked to implement a specific function.
Write ONLY the function implementation — no explanations, no markdown fences.
Respect any existing patterns in the codebase."""

_IMPL_PROMPT = """\
Source file ({filename}):
{file_content}

Task: {prompt}

Write the Python function implementation:"""

_JUDGE_PROMPT = """\
You are a strict code reviewer checking for a specific constraint violation.

Constraint to check:
{constraint}

Code to review:
{code}

Question: {judge_question}

Answer with exactly one word: VIOLATED or RESPECTED
Then on the next line write a one-sentence explanation."""


# ── Core LLM calls ────────────────────────────────────────────────────────────

def call_llm(model: str, api_key: str, system: str, user: str,
             max_tokens: int = 400, temperature: float = 0.3) -> str:
    """Call the LLM and return the text response."""
    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if api_key:
        kwargs["api_key"] = api_key

    response = litellm.completion(**kwargs)
    return response.choices[0].message.content.strip()


def generate_implementation(model: str, api_key: str,
                             file_content: str, filename: str,
                             task_prompt: str) -> str:
    """Ask the LLM to implement the task given the file as context."""
    user_msg = _IMPL_PROMPT.format(
        filename=filename,
        file_content=file_content,
        prompt=task_prompt,
    )
    return call_llm(model, api_key, _SYSTEM_IMPL, user_msg, max_tokens=400)


def judge_violation(judge_model: str, api_key: str,
                    constraint: str, code: str, judge_question: str) -> tuple[bool, str]:
    """Ask the judge LLM whether the generated code violates the constraint.

    Returns (violated: bool, explanation: str).
    """
    prompt = _JUDGE_PROMPT.format(
        constraint=constraint,
        code=code,
        judge_question=judge_question,
    )
    raw = call_llm(judge_model, api_key, "", prompt, max_tokens=80, temperature=0.0)
    lines = raw.strip().splitlines()
    verdict_line = lines[0].strip().upper() if lines else ""
    violated = "VIOLATED" in verdict_line
    explanation = lines[1].strip() if len(lines) > 1 else raw
    return violated, explanation


# ── Benchmark runner ──────────────────────────────────────────────────────────

def run_condition(condition: str, tasks: list[dict],
                  model: str, judge_model: str, api_key: str,
                  n_runs: int, dry_run: bool, verbose: bool) -> list[dict]:
    """Run all tasks under one condition (baseline or annotated).

    Returns list of result dicts.
    """
    src_dir = BASELINE_DIR if condition == "baseline" else ANNOTATED_DIR
    results = []

    for task in tasks:
        task_id = task["id"]
        filename = task["file"]
        file_path = src_dir / filename

        if not file_path.exists():
            print(f"  SKIP {task_id}: {file_path} not found")
            continue

        file_content = file_path.read_text()

        violations_this_task = 0
        implementations = []

        for run_idx in range(n_runs):
            if verbose:
                print(f"  [{condition}] {task_id} run {run_idx+1}/{n_runs}...", end=" ", flush=True)

            if dry_run:
                print(f"\n--- PROMPT for {condition}/{task_id} ---")
                print(_IMPL_PROMPT.format(
                    filename=filename,
                    file_content=file_content[:300] + "...",
                    prompt=task["prompt"]
                ))
                continue

            # Step 1: Generate implementation
            try:
                code = generate_implementation(
                    model, api_key, file_content, filename, task["prompt"]
                )
            except Exception as exc:
                print(f"ERROR generating: {exc}")
                continue

            # Step 2: Judge violation
            try:
                violated, explanation = judge_violation(
                    judge_model, api_key,
                    task["constraint"],
                    code,
                    task["judge_question"],
                )
            except Exception as exc:
                print(f"ERROR judging: {exc}")
                continue

            if verbose:
                status = "VIOLATED" if violated else "respected"
                print(status)
                if violated:
                    print(f"          → {explanation}")

            if violated:
                violations_this_task += 1

            implementations.append({
                "run": run_idx + 1,
                "code": code,
                "violated": violated,
                "explanation": explanation,
            })

            # Small delay to avoid rate limits
            time.sleep(0.5)

        violation_rate = violations_this_task / n_runs if n_runs > 0 else 0
        results.append({
            "task_id": task_id,
            "file": filename,
            "category": task["category"],
            "constraint": task["constraint"],
            "condition": condition,
            "n_runs": n_runs,
            "violations": violations_this_task,
            "violation_rate": round(violation_rate, 3),
            "implementations": implementations,
        })

    return results


def run_benchmark(model: str, api_key: str, judge_model: str | None = None,
                  n_runs: int = 3, dry_run: bool = False,
                  verbose: bool = True) -> dict:
    """Run the full benchmark and return results dict."""
    judge_model = judge_model or model
    tasks = json.loads(TASKS_FILE.read_text())

    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'='*60}")
    print(f"CodeDNA Thesis Benchmark")
    print(f"Model:      {model}")
    print(f"Judge:      {judge_model}")
    print(f"Tasks:      {len(tasks)}")
    print(f"Runs/task:  {n_runs}")
    print(f"Total LLM calls: {len(tasks) * n_runs * 2 * 2}  (gen + judge) × 2 conditions")
    print(f"{'='*60}\n")

    all_results: dict[str, list] = {}

    for condition in ["baseline", "annotated"]:
        print(f"\n▶ Condition: {condition.upper()}")
        results = run_condition(
            condition, tasks, model, judge_model, api_key,
            n_runs, dry_run, verbose
        )
        all_results[condition] = results

    if dry_run:
        print("\n[dry-run] No LLM calls made.")
        return {}

    # ── Compute summary ────────────────────────────────────────────────────
    summary = compute_summary(all_results, tasks)
    print_summary(summary)

    # ── Save results ───────────────────────────────────────────────────────
    output = {
        "meta": {
            "timestamp": timestamp,
            "model": model,
            "judge_model": judge_model,
            "n_runs": n_runs,
            "n_tasks": len(tasks),
        },
        "results": all_results,
        "summary": summary,
    }

    out_path = RESULTS_DIR / f"benchmark_{timestamp}.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nResults saved: {out_path}")

    # Write markdown report
    md_path = RESULTS_DIR / f"report_{timestamp}.md"
    md_path.write_text(build_markdown_report(output))
    print(f"Report saved: {md_path}")

    return output


# ── Reporting ─────────────────────────────────────────────────────────────────

def compute_summary(all_results: dict, tasks: list) -> dict:
    """Compute per-task and aggregate statistics."""
    per_task = []

    for task in tasks:
        tid = task["id"]
        baseline_r = next((r for r in all_results.get("baseline", []) if r["task_id"] == tid), None)
        annotated_r = next((r for r in all_results.get("annotated", []) if r["task_id"] == tid), None)

        if not baseline_r or not annotated_r:
            continue

        per_task.append({
            "task_id": tid,
            "file": task["file"],
            "category": task["category"],
            "constraint_summary": task["constraint"][:60] + "..." if len(task["constraint"]) > 60 else task["constraint"],
            "baseline_violations": baseline_r["violations"],
            "annotated_violations": annotated_r["violations"],
            "baseline_rate": baseline_r["violation_rate"],
            "annotated_rate": annotated_r["violation_rate"],
            "improvement": round(baseline_r["violation_rate"] - annotated_r["violation_rate"], 3),
        })

    n_runs = all_results["baseline"][0]["n_runs"] if all_results.get("baseline") else 1

    total_baseline = sum(r["violations"] for r in all_results.get("baseline", []))
    total_annotated = sum(r["violations"] for r in all_results.get("annotated", []))
    total_possible = len(per_task) * n_runs

    return {
        "total_possible": total_possible,
        "baseline_total_violations": total_baseline,
        "annotated_total_violations": total_annotated,
        "baseline_violation_rate": round(total_baseline / total_possible, 3) if total_possible else 0,
        "annotated_violation_rate": round(total_annotated / total_possible, 3) if total_possible else 0,
        "overall_improvement": round((total_baseline - total_annotated) / total_possible, 3) if total_possible else 0,
        "codedna_helps": total_annotated < total_baseline,
        "per_task": per_task,
    }


def print_summary(summary: dict) -> None:
    """Print a formatted summary table."""
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"\n{'Task':<6} {'File':<12} {'Baseline':>10} {'Annotated':>10} {'Delta':>8}")
    print(f"{'-'*6} {'-'*12} {'-'*10} {'-'*10} {'-'*8}")

    for t in summary["per_task"]:
        delta_str = f"-{t['improvement']:.0%}" if t["improvement"] > 0 else f"+{abs(t['improvement']):.0%}"
        marker = " ✓" if t["improvement"] > 0 else ("  " if t["improvement"] == 0 else " ✗")
        print(f"{t['task_id']:<6} {t['file']:<12} {t['baseline_rate']:>9.0%}  {t['annotated_rate']:>9.0%}  {delta_str:>6}{marker}")

    br = summary["baseline_violation_rate"]
    ar = summary["annotated_violation_rate"]
    improvement = summary["overall_improvement"]

    print(f"\n{'TOTAL':<6} {'':12} {br:>9.0%}  {ar:>9.0%}  {improvement:>+.0%}")
    print(f"\n{'='*60}")

    verdict = "HELPS" if summary["codedna_helps"] else "NO EFFECT"
    print(f"VERDICT: CodeDNA {verdict}")
    print(f"  Baseline violations:  {summary['baseline_total_violations']}/{summary['total_possible']} ({br:.0%})")
    print(f"  Annotated violations: {summary['annotated_total_violations']}/{summary['total_possible']} ({ar:.0%})")
    delta_pct = (br - ar) * 100
    print(f"  Reduction:            {delta_pct:+.1f} percentage points")
    print(f"{'='*60}\n")


def build_markdown_report(output: dict) -> str:
    """Build a full markdown report from the benchmark output."""
    meta = output["meta"]
    summary = output["summary"]

    lines = [
        "# CodeDNA Thesis Benchmark — Results",
        "",
        f"**Date**: {meta['timestamp'][:10]}  ",
        f"**Model**: `{meta['model']}`  ",
        f"**Judge**: `{meta['judge_model']}`  ",
        f"**Runs per task**: {meta['n_runs']}  ",
        f"**Tasks**: {meta['n_tasks']}  ",
        "",
        "## Hypothesis",
        "",
        "> CodeDNA `rules:` headers reduce AI agent constraint violation rate.",
        "",
        "- **Condition A (baseline)**: LLM sees source file WITHOUT CodeDNA headers",
        "- **Condition B (annotated)**: LLM sees same file WITH CodeDNA `rules:` headers",
        "",
        "## Results",
        "",
        f"| Task | File | Category | Baseline | Annotated | Δ |",
        f"|------|------|----------|----------|-----------|---|",
    ]

    for t in summary["per_task"]:
        delta = t["improvement"]
        delta_str = f"−{delta:.0%}" if delta > 0 else (f"+{abs(delta):.0%}" if delta < 0 else "0%")
        icon = "✅" if delta > 0 else ("➖" if delta == 0 else "❌")
        lines.append(
            f"| {t['task_id']} | {t['file']} | {t['category']} | "
            f"{t['baseline_rate']:.0%} | {t['annotated_rate']:.0%} | {delta_str} {icon} |"
        )

    br = summary["baseline_violation_rate"]
    ar = summary["annotated_violation_rate"]
    improvement = summary["overall_improvement"]
    verdict = "**CONFIRMED** ✅" if summary["codedna_helps"] else "**NOT CONFIRMED** ❌"

    lines += [
        "",
        f"| **TOTAL** | | | **{br:.0%}** | **{ar:.0%}** | **{improvement:+.0%}** |",
        "",
        "## Verdict",
        "",
        f"Hypothesis {verdict}",
        "",
        f"- Baseline violation rate: **{br:.0%}** ({summary['baseline_total_violations']}/{summary['total_possible']})",
        f"- Annotated violation rate: **{ar:.0%}** ({summary['annotated_total_violations']}/{summary['total_possible']})",
        f"- Reduction: **{(br - ar)*100:+.1f} pp** (percentage points)",
        "",
        "## Per-Task Detail",
        "",
    ]

    for condition in ["baseline", "annotated"]:
        results = output["results"].get(condition, [])
        lines.append(f"### {condition.capitalize()}")
        lines.append("")
        for r in results:
            lines.append(f"#### {r['task_id']} — {r['file']} ({r['category']})")
            lines.append(f"**Constraint**: {r['constraint']}  ")
            lines.append(f"**Violations**: {r['violations']}/{r['n_runs']} ({r['violation_rate']:.0%})  ")
            lines.append("")
            for impl in r.get("implementations", []):
                verdict_str = "VIOLATED ❌" if impl["violated"] else "respected ✅"
                lines.append(f"Run {impl['run']}: {verdict_str} — {impl['explanation']}")
            lines.append("")

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CodeDNA Thesis Benchmark — test if rules: headers reduce constraint violations"
    )
    parser.add_argument("--model", default="deepseek/deepseek-chat",
                        help="LLM for code generation (default: deepseek/deepseek-chat)")
    parser.add_argument("--judge-model", default=None,
                        help="LLM for judging violations (default: same as --model)")
    parser.add_argument("--api-key", default=None,
                        help="API key (or set DEEPSEEK_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY)")
    parser.add_argument("--runs", type=int, default=3,
                        help="Repetitions per task per condition (default: 3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print prompts without calling LLM")
    parser.add_argument("--verbose", action="store_true", default=True)
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-run output")

    args = parser.parse_args()

    # Resolve API key from env if not provided
    api_key = args.api_key
    if not api_key:
        for env_var in ["DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LITELLM_API_KEY"]:
            val = os.environ.get(env_var)
            if val:
                api_key = val
                print(f"Using API key from {env_var}")
                break

    if not api_key and not args.dry_run:
        print("ERROR: provide --api-key or set DEEPSEEK_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY")
        sys.exit(1)

    run_benchmark(
        model=args.model,
        api_key=api_key or "",
        judge_model=args.judge_model,
        n_runs=args.runs,
        dry_run=args.dry_run,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
