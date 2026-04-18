"""rescore_traces.py — Re-score existing benchmark traces with a stronger parser.

exports: extract_proposed_robust(text, repo_files) -> set | rescore_session(trace_path, repo_root, gt) -> dict | main()
used_by: none
rules:   Zero LLM cost — pure post-hoc analysis on existing session_traces/*.json.
         Never modifies original trace files — writes rescored results separately.
         repo_files is a list of real file paths; used to expand globs and
         match suffix-only mentions (e.g. 'sql/where.py' → 'django/db/models/sql/where.py').
         Strips markdown formatting (bold **, italic *, backticks, inline code fences)
         BEFORE regex extraction to catch paths hidden inside formatting.
agent:   claude-opus-4-7 | anthropic | 2026-04-17 | s_20260417_blade | initial re-scoring tool for Haiku+Opus traces
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = BENCH_ROOT / "projects"
# Default: labs/benchmark/runs (new location). Fallback to legacy
# benchmark_agent/runs if labs runs dir is empty (for rescoring old data).
_LABS_RUNS = BENCH_ROOT / "runs"
_LEGACY_RUNS = Path(__file__).resolve().parents[3] / "benchmark_agent" / "runs"
RUNS_ROOT = _LABS_RUNS if _LABS_RUNS.exists() and any(_LABS_RUNS.iterdir()) else _LEGACY_RUNS

# Match any path-like token ending in .py.
# Allows wildcard (*) and dot chars in path segments.
_PY_PATH_RE = re.compile(r"[A-Za-z_][\w\-/*.]*\.py\b")

# Markdown formatting to strip before extraction
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC_RE = re.compile(r"\*(.+?)\*")
_MD_CODE_RE = re.compile(r"`([^`\n]+)`")
_MD_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```")


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting so path tokens inside ** ** or ` ` are visible."""
    text = _MD_CODE_FENCE_RE.sub(lambda m: m.group(0).replace("```", " "), text)
    text = _MD_BOLD_RE.sub(r"\1", text)
    text = _MD_ITALIC_RE.sub(r"\1", text)
    text = _MD_CODE_RE.sub(r"\1", text)
    return text


def _expand_glob_against_repo(token: str, repo_files: list[str]) -> list[str]:
    """If token contains a glob (*), expand against repo_files using fnmatch.

    If token has no glob, returns [token] unchanged.
    """
    if "*" not in token:
        return [token]
    return [f for f in repo_files if fnmatch.fnmatch(f, token)]


def _match_suffix_against_repo(token: str, repo_files: list[str]) -> list[str]:
    """If token is a partial path (no exact repo match), match by suffix.

    Example: 'sql/where.py' matches 'django/db/models/sql/where.py'.
    Only matches if suffix is unique in the repo — otherwise returns empty
    (ambiguous mentions are discarded).
    """
    if token in repo_files:
        return [token]
    candidates = [f for f in repo_files if f.endswith("/" + token) or f == token]
    # Only accept if unique match
    return candidates if len(candidates) == 1 else []


def extract_proposed_robust(text: str, repo_files: list[str] | None = None) -> set[str]:
    """Extract proposed file paths from agent final response — robust edition.

    Rules:   1. Strip markdown (bold/italic/backtick/code-fence) so embedded paths
                are visible.
             2. Search the FULL text, not a 4000-char tail — avoids mid-path
                truncation ('dj|ango/...').
             3. Expand glob tokens (*, **, [abc]) against repo_files when provided.
             4. Resolve partial paths by unique suffix match against repo_files.
             5. Drop single-segment names (no '/') — too ambiguous.

    Returns the set of repo-relative .py paths the agent proposed.
    """
    stripped = _strip_markdown(text)

    raw_tokens = _PY_PATH_RE.findall(stripped)
    # Normalize: strip leading './' and leading '/'
    tokens = []
    for t in raw_tokens:
        t = t.lstrip("/").lstrip(".").lstrip("/")
        if "/" not in t:
            continue
        tokens.append(t)

    proposed: set[str] = set()
    for t in tokens:
        if repo_files is not None:
            # First expand glob
            expanded = _expand_glob_against_repo(t, repo_files)
            if expanded and "*" in t:
                proposed.update(expanded)
                continue
            # Then try exact or suffix match
            if t in repo_files:
                proposed.add(t)
                continue
            matched = _match_suffix_against_repo(t, repo_files)
            if matched:
                proposed.update(matched)
                continue
            # No repo match — keep as-is if it looks like a plausible django path
            if t.startswith("django/") or t.startswith("tests/"):
                proposed.add(t)
        else:
            proposed.add(t)
    return proposed


def _f1(files: set, ground_truth: list) -> dict:
    truth = set(ground_truth)
    if not truth:
        return {"recall": 0.0, "precision": 0.0, "f1": 0.0}
    hits = files & truth
    R = len(hits) / len(truth)
    P = len(hits) / len(files) if files else 0.0
    F1 = (2 * P * R) / (P + R) if (P + R) else 0.0
    return {"recall": round(R, 3), "precision": round(P, 3), "f1": round(F1, 3),
            "hits": sorted(hits), "missed": sorted(truth - files),
            "spurious": sorted(files - truth), "n_proposed": len(files)}


def _list_repo_py_files(repo_root: Path) -> list[str]:
    skip = {"__pycache__", ".git", "vendor", "node_modules", "migrations"}
    out: list[str] = []
    for f in repo_root.rglob("*.py"):
        parts = f.relative_to(repo_root).parts
        if any(p in skip for p in parts):
            continue
        out.append(str(f.relative_to(repo_root)))
    return out


def rescore_session(trace_path: Path) -> dict:
    """Re-score a single session trace file using the robust parser.

    Returns dict with original vs rescored metrics for comparison.
    """
    trace = json.loads(trace_path.read_text())
    task_id = trace["task"]
    condition = trace["condition"]
    gt = trace["ground_truth"]

    # Find the final_response from results.json (traces don't store it separately)
    model = trace["model"]
    results_path = RUNS_ROOT / model.replace("/", "-") / "results.json"
    results = json.loads(results_path.read_text())
    task_entry = next((e for e in results if e["instance_id"] == task_id), None)
    if not task_entry:
        return {"error": "no task entry in results.json"}

    # Look in the single-run field and in _runs list (multi-run mode)
    final_response = None
    cond_data = task_entry.get(condition)
    if cond_data and cond_data.get("session_id") == trace["session_id"]:
        final_response = cond_data.get("final_response")
    if final_response is None:
        for r in task_entry.get(f"{condition}_runs") or []:
            if r.get("session_id") == trace["session_id"]:
                final_response = r.get("final_response")
                break
    if not final_response:
        return {"error": "no final_response found"}

    # Build repo_files list from the task's repo
    project_dir = PROJECTS_DIR / task_id
    repo_dir = project_dir / condition
    repo_files = _list_repo_py_files(repo_dir) if repo_dir.exists() else None

    original = cond_data.get("metrics_proposed") if cond_data else {}
    rescored_files = extract_proposed_robust(final_response, repo_files)
    rescored_metrics = _f1(rescored_files, gt)

    return {
        "session_id": trace["session_id"],
        "task": task_id,
        "condition": condition,
        "model": model,
        "gt_count": len(gt),
        "original_metrics": original,
        "rescored_metrics": rescored_metrics,
    }


def main():
    parser = argparse.ArgumentParser(description="Re-score benchmark traces with robust parser")
    parser.add_argument("--model", help="Model dir to re-score (e.g. claude-opus-4-7). Default: all.")
    parser.add_argument("--out", default=None, help="JSON output file (default: print to stdout)")
    args = parser.parse_args()

    glob = f"{args.model.replace('/','-') if args.model else '*'}/session_traces/*.json"
    trace_paths = sorted(RUNS_ROOT.glob(glob))
    if not trace_paths:
        print(f"No traces found under {RUNS_ROOT}/{glob}")
        return

    out_rows = []
    for tp in trace_paths:
        result = rescore_session(tp)
        if "error" in result:
            continue
        out_rows.append(result)

    for row in out_rows:
        orig = row["original_metrics"] or {}
        new = row["rescored_metrics"]
        delta_f1 = new["f1"] - (orig.get("f1", 0) or 0)
        marker = " ⬆" if delta_f1 > 0.05 else (" ⬇" if delta_f1 < -0.05 else "")
        print(f"{row['model']:28s} {row['task']:22s} {row['condition']:7s} "
              f"orig F1={orig.get('f1',0):.2f}  new F1={new['f1']:.2f} "
              f"Δ={delta_f1:+.2f} R={new['recall']:.2f} P={new['precision']:.2f}{marker}")

    if args.out:
        Path(args.out).write_text(json.dumps(out_rows, indent=2))
        print(f"\nFull JSON → {args.out}")


if __name__ == "__main__":
    main()
