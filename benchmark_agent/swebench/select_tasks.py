"""
swebench/select_tasks.py — Scarica SWE-bench e seleziona issue Flask multi-file.

deps:    datasets (HuggingFace), python stdlib
exports: tasks.json (lista curata di issue Flask multi-file)
rules:   Selezionare SOLO issue dove il fix tocca >= 2 file diversi.
         NON leggere il contenuto del patch prima di aver annotato il codebase.
"""

import json
import sys
from pathlib import Path

try:
    from datasets import load_dataset
except ImportError:
    print("ERROR: run `pip install datasets` first")
    sys.exit(1)

OUTPUT = Path(__file__).parent / "tasks.json"

def count_files_in_patch(patch: str) -> int:
    """Count how many distinct files are touched by the patch."""
    return patch.count("diff --git")

def is_good_task(task: dict) -> bool:
    """Return True if task is suitable for CodeDNA benchmark.

    Rules:
    - Repo must be Flask/pallets ecosystem
    - Fix must touch >= 2 files (cross-file navigation required)
    - Problem statement must be non-trivial (> 50 chars)
    - Not a pure documentation fix
    """
    repo = task.get("repo", "").lower()
    if not ("flask" in repo or "werkzeug" in repo or "jinja" in repo or "click" in repo):
        return False
    patch = task.get("patch", "")
    if count_files_in_patch(patch) < 2:
        return False
    problem = task.get("problem_statement", "")
    if len(problem) < 50:
        return False
    # Exclude pure docs/test-only fixes
    non_test_files = [
        line for line in patch.split("\n")
        if line.startswith("diff --git")
        and "test" not in line.lower()
        and ".md" not in line.lower()
        and ".rst" not in line.lower()
        and ".txt" not in line.lower()
    ]
    if len(non_test_files) < 1:
        return False
    return True

def summarize_task(task: dict) -> dict:
    """Extract the fields needed for the benchmark."""
    patch = task.get("patch", "")
    files_in_patch = [
        line.replace("diff --git a/", "").split(" b/")[0]
        for line in patch.split("\n")
        if line.startswith("diff --git")
    ]
    return {
        "instance_id": task["instance_id"],
        "repo": task["repo"],
        "base_commit": task["base_commit"],
        "problem_statement": task["problem_statement"][:300],
        "files_in_patch": files_in_patch,
        "n_files": len(files_in_patch),
        "has_test_patch": bool(task.get("test_patch", "").strip()),
    }

def main():
    print("📥 Loading SWE-bench dataset (this may take a moment)...")
    try:
        ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test", trust_remote_code=True)
        print(f"   Loaded {len(ds)} tasks from SWE-bench_Lite")
    except Exception:
        try:
            ds = load_dataset("princeton-nlp/SWE-bench", split="test", trust_remote_code=True)
            print(f"   Loaded {len(ds)} tasks from SWE-bench")
        except Exception as e:
            print(f"ERROR loading dataset: {e}")
            sys.exit(1)

    print("🔍 Filtering for Flask ecosystem + multi-file patches...")
    good = [t for t in ds if is_good_task(t)]
    print(f"   Found {len(good)} suitable tasks")

    if not good:
        print("⚠️  No tasks found. Trying broader search...")
        # Fallback: just Flask, any number of files
        good = [t for t in ds if "flask" in t.get("repo", "").lower() or
                                   "pallets" in t.get("repo", "").lower()]
        print(f"   Fallback: {len(good)} Flask tasks total")

    summarized = [summarize_task(t) for t in good]
    # Sort by number of files in patch (most cross-file first)
    summarized.sort(key=lambda x: x["n_files"], reverse=True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(summarized, f, indent=2)

    print(f"\n✅ Saved {len(summarized)} tasks to {OUTPUT}")
    print("\n📋 Top 10 candidates (most cross-file):")
    print(f"{'ID':<45} {'Repo':<30} {'Files':>5}")
    print("-" * 85)
    for t in summarized[:10]:
        print(f"{t['instance_id']:<45} {t['repo']:<30} {t['n_files']:>5}")

    print(f"\n🎯 Recommended: pick 5–8 tasks where n_files >= 2 and the files")
    print("   span different modules (not just test files).")
    print(f"\n   Edit {OUTPUT} to keep only your selected tasks,")
    print("   then run: python swebench/setup_repos.py")

if __name__ == "__main__":
    main()
