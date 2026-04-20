"""setup_benchmark.py — Download and prepare SWE-bench tasks for CodeDNA benchmark.

exports: PROJECTS_DIR | REPO_CACHE | TASKS_FILE | load_swebench_tasks(repo_filter, n_tasks, multi_file_first, dataset) | clone_repo(repo) | checkout_task(task, bare_repo, force) | annotate_task(task, model, no_llm) | update_tasks_json(tasks) | main()
used_by: none
rules:   Never modify existing control/ or codedna/ directories unless --force is passed.
Each task must have: control/ (vanilla repo at base_commit) + codedna/ (annotated).
Annotation uses codedna CLI (codedna init) — not the Gemini annotator.
Repo clones use --filter=blob:none (blobless) — blobs fetched on demand by git archive.
clone_repo() returns None on failure — main() must check and skip the repo.
agent:   claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_004 | moved to labs/benchmark/, updated paths
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_bench | fix annotate_task: remove partial codedna/ on timeout/CalledProcessError; switch clone to --filter=blob:none + broken-cache detection; clone_repo now returns None on failure
claude-opus-4-7 | anthropic | 2026-04-17 | s_20260417_opus47 | added --task-id flag to filter specific SWE-bench instance_ids (bare number or full id); enables targeted download of our 5 benchmark tasks
claude-opus-4-6 | anthropic | 2026-04-21 | s_20260421_unused | remove unused os import (CodeQL #1671)
USAGE:
# Step 1: List available tasks
python setup_benchmark.py --list --repo django/django
# Step 2: Download and prepare 50 Django tasks
python setup_benchmark.py --repo django/django --n-tasks 50
# Step 3: Prepare all 500 SWE-bench Verified tasks (all 12 repos)
python setup_benchmark.py --all
# Step 4: Annotate with CodeDNA (requires LLM or --no-llm)
python setup_benchmark.py --annotate --no-llm
python setup_benchmark.py --annotate --model ollama/llama3
# Resume interrupted setup (skips already-prepared tasks)
python setup_benchmark.py --repo django/django --n-tasks 50
# Force re-download and re-annotate
python setup_benchmark.py --repo django/django --n-tasks 50 --force
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECTS_DIR = Path(__file__).parent / "projects"
REPO_CACHE   = Path(__file__).parent / "_repo_cache"
TASKS_FILE   = Path(__file__).parent / "tasks.json"


def load_swebench_tasks(repo_filter=None, n_tasks=None, multi_file_first=False,
                         dataset="verified"):
    """Load tasks from SWE-bench dataset.

    Rules:   Requires 'datasets' package (pip install datasets).
             Returns tasks sorted by n_files descending if multi_file_first=True.
             dataset="verified" (500 tasks, default) or "full" (2294 tasks).
    """
    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: pip install datasets")
        sys.exit(1)

    if dataset == "full":
        print("Loading SWE-bench (full, 2294 tasks) from HuggingFace...")
        ds = load_dataset("princeton-nlp/SWE-bench", split="test")
    else:
        print("Loading SWE-bench Verified from HuggingFace...")
        ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")

    tasks = []
    for row in ds:
        if repo_filter and row["repo"] != repo_filter:
            continue

        n_files = row["patch"].count("diff --git")

        # Extract files from patch
        files_in_patch = []
        for line in row["patch"].split("\n"):
            if line.startswith("diff --git a/"):
                fpath = line.split(" b/")[-1]
                if fpath not in files_in_patch:
                    files_in_patch.append(fpath)

        tasks.append({
            "instance_id": row["instance_id"],
            "repo": row["repo"],
            "base_commit": row["base_commit"],
            "problem_statement": row["problem_statement"],
            "files_in_patch": files_in_patch,
            "n_files": n_files,
        })

    if multi_file_first:
        tasks.sort(key=lambda t: t["n_files"], reverse=True)

    if n_tasks and n_tasks < len(tasks):
        tasks = tasks[:n_tasks]

    return tasks


def clone_repo(repo: str):
    """Clone a repo to _repo_cache/ if not already cached.

    Rules:   Uses --filter=blob:none (partial clone) for speed — still supports
             git archive on any commit without downloading all blobs upfront.
             Never delete the cache during runs.
    """
    repo_dir = REPO_CACHE / repo.replace("/", "__")
    if repo_dir.exists():
        # Verify it's a valid git repo (not a broken partial clone)
        result = subprocess.run(
            ["git", "--git-dir", str(repo_dir), "rev-list", "--count", "--all"],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and int(result.stdout.strip() or "0") > 0:
            print(f"  Repo cached: {repo_dir}")
            return repo_dir
        else:
            print(f"  Broken cache detected — re-cloning {repo_dir.name}")
            shutil.rmtree(repo_dir)

    REPO_CACHE.mkdir(parents=True, exist_ok=True)
    url = f"https://github.com/{repo}.git"
    print(f"  Cloning {url} (partial, no blobs) ...")
    try:
        subprocess.run(
            ["git", "clone", "--bare", "--filter=blob:none", url, str(repo_dir)],
            check=True, text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: git clone failed for {repo} (exit {e.returncode})")
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        return None
    print(f"  Cloned: {repo_dir}")
    return repo_dir


def checkout_task(task: dict, bare_repo: Path, force: bool = False):
    """Create control/ directory for a task by checking out base_commit.

    Rules:   Skips if control/ already exists (unless --force).
             Uses git archive to extract files without .git directory.
    """
    iid = task["instance_id"]
    task_dir = PROJECTS_DIR / iid
    ctrl_dir = task_dir / "control"

    if ctrl_dir.exists() and not force:
        print(f"  control/ exists — skipping")
        return True

    if ctrl_dir.exists():
        shutil.rmtree(ctrl_dir)

    task_dir.mkdir(parents=True, exist_ok=True)

    commit = task["base_commit"]

    # Use git archive to extract snapshot at commit
    try:
        ctrl_dir.mkdir()
        result = subprocess.run(
            ["git", "archive", "--format=tar", commit],
            cwd=str(bare_repo),
            capture_output=True, check=True,
        )
        subprocess.run(
            ["tar", "xf", "-"],
            cwd=str(ctrl_dir),
            input=result.stdout, check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: git archive failed for {commit}: {e.stderr[:200] if e.stderr else e}")
        if ctrl_dir.exists():
            shutil.rmtree(ctrl_dir)
        return False

    # Save metadata
    (task_dir / "problem_statement.txt").write_text(task["problem_statement"])
    (task_dir / "files_in_patch.json").write_text(json.dumps(task["files_in_patch"], indent=2))

    return True


def annotate_task(task: dict, model: str = None, no_llm: bool = False):
    """Create codedna/ directory by copying control/ and running codedna init.

    Rules:   Skips if codedna/ already exists.
             Uses codedna CLI — must be installed (pip install codedna).
    """
    iid = task["instance_id"]
    task_dir = PROJECTS_DIR / iid
    ctrl_dir = task_dir / "control"
    cdna_dir = task_dir / "codedna"

    if cdna_dir.exists():
        print(f"  codedna/ exists — skipping")
        return True

    if not ctrl_dir.exists():
        print(f"  ERROR: control/ not found for {iid}")
        return False

    print(f"  Copying control/ → codedna/ ...")
    shutil.copytree(ctrl_dir, cdna_dir)

    # Run codedna init
    cmd = ["codedna", "init", str(cdna_dir)]
    if no_llm:
        cmd.append("--no-llm")
    elif model:
        cmd.extend(["--model", model])

    print(f"  Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
        print(f"  Annotated")
        return True
    except FileNotFoundError:
        print("  ERROR: 'codedna' CLI not found. Run: pip install git+https://github.com/Larens94/codedna.git")
        return False
    except subprocess.TimeoutExpired:
        print(f"  ERROR: annotation timed out after 300s — removing incomplete codedna/")
        shutil.rmtree(cdna_dir, ignore_errors=True)
        return False
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: codedna init failed — removing incomplete codedna/")
        print(f"  {e.stderr[:300] if e.stderr else ''}")
        shutil.rmtree(cdna_dir, ignore_errors=True)
        return False


def update_tasks_json(tasks: list):
    """Write/merge tasks into tasks.json.

    Rules:   Never overwrite existing entries — merge by instance_id.
    """
    existing = []
    if TASKS_FILE.exists():
        existing = json.loads(TASKS_FILE.read_text())

    existing_ids = {t["instance_id"] for t in existing}
    new_tasks = [t for t in tasks if t["instance_id"] not in existing_ids]

    # Clean tasks for JSON (remove n_files, keep what run_agent_multi.py expects)
    for t in new_tasks:
        existing.append({
            "instance_id": t["instance_id"],
            "repo": t["repo"],
            "base_commit": t["base_commit"],
            "problem_statement": t["problem_statement"],
            "files_in_patch": t["files_in_patch"],
            "n_files": t["n_files"],
        })

    TASKS_FILE.write_text(json.dumps(existing, indent=2))
    print(f"\ntasks.json: {len(existing)} total ({len(new_tasks)} new)")


def main():
    parser = argparse.ArgumentParser(
        description="Download and prepare SWE-bench tasks for CodeDNA benchmark"
    )
    parser.add_argument("--list", action="store_true",
                        help="List available tasks without downloading")
    parser.add_argument("--repo",
                        help="Filter by repo (e.g. django/django, sympy/sympy)")
    parser.add_argument("--n-tasks", type=int,
                        help="Number of tasks to prepare (default: all matching)")
    parser.add_argument("--multi-file-first", action="store_true",
                        help="Prioritize multi-file tasks (2+ files in patch)")
    parser.add_argument("--all", action="store_true",
                        help="Prepare all 500 SWE-bench Verified tasks")
    parser.add_argument("--annotate", action="store_true",
                        help="Also create codedna/ with annotations")
    parser.add_argument("--no-llm", action="store_true",
                        help="Annotate without LLM (structural only)")
    parser.add_argument("--model",
                        help="LLM model for annotation (e.g. ollama/llama3, claude-haiku-4-5-20251001)")
    parser.add_argument("--force", action="store_true",
                        help="Re-download and re-annotate even if directories exist")
    parser.add_argument("--task-id", nargs="+", default=None,
                        help="Filter to specific task IDs, e.g. --task-id 14480 13495 "
                             "(accepts bare numbers or full instance_ids like django__django-14480)")
    parser.add_argument("--dataset", choices=["verified", "full"], default="verified",
                        help="Which SWE-bench split to load (default: verified=500, full=2294)")
    args = parser.parse_args()

    repo_filter = None if args.all else args.repo
    if not args.all and not args.repo and not args.list and not args.task_id:
        parser.error("Specify --repo <owner/repo>, --all, or --task-id <id...>")

    tasks = load_swebench_tasks(
        repo_filter=repo_filter,
        n_tasks=None if args.task_id else args.n_tasks,
        multi_file_first=args.multi_file_first,
        dataset=args.dataset,
    )

    if args.task_id:
        wanted = set()
        for t in args.task_id:
            t = t.strip()
            if "__" in t:
                wanted.add(t)
            else:
                wanted.add(f"django__django-{t}")
        tasks = [t for t in tasks if t["instance_id"] in wanted]
        if not tasks:
            print(f"No tasks matched --task-id {args.task_id}")
            return
        print(f"Filtered to {len(tasks)} task(s) via --task-id")

    if not tasks:
        print("No tasks found.")
        return

    # ── List mode ──
    if args.list:
        from collections import Counter
        repos = Counter(t["repo"] for t in tasks)
        print(f"\n{len(tasks)} tasks across {len(repos)} repo(s):\n")
        for repo, count in repos.most_common():
            multi = sum(1 for t in tasks if t["repo"] == repo and t["n_files"] >= 2)
            print(f"  {repo:45s} {count:4d} tasks ({multi} multi-file)")
        print()
        if args.repo:
            print(f"{'Instance ID':50s} {'Files':>5s}  Status")
            print("-" * 70)
            for t in tasks:
                task_dir = PROJECTS_DIR / t["instance_id"]
                has_ctrl = (task_dir / "control").exists()
                has_cdna = (task_dir / "codedna").exists()
                status = ""
                if has_ctrl:
                    status += "control/"
                if has_cdna:
                    status += " + codedna/"
                if not status:
                    status = "not downloaded"
                print(f"  {t['instance_id']:48s} {t['n_files']:5d}  {status}")
        return

    # ── Download mode ──
    print(f"\nPreparing {len(tasks)} tasks...")
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    # Group by repo for efficient cloning
    from collections import defaultdict
    by_repo = defaultdict(list)
    for t in tasks:
        by_repo[t["repo"]].append(t)

    ok_count = 0
    fail_count = 0
    t0 = time.time()

    for repo, repo_tasks in by_repo.items():
        print(f"\n{'='*60}")
        print(f"Repo: {repo} ({len(repo_tasks)} tasks)")
        print(f"{'='*60}")

        bare_repo = clone_repo(repo)
        if bare_repo is None:
            print(f"  Skipping {repo} — clone failed")
            fail_count += len(repo_tasks)
            continue

        for i, task in enumerate(repo_tasks, 1):
            iid = task["instance_id"]
            print(f"\n[{i}/{len(repo_tasks)}] {iid} ({task['n_files']} files in patch)")

            success = checkout_task(task, bare_repo, force=args.force)
            if not success:
                fail_count += 1
                continue

            if args.annotate:
                annotate_task(task, model=args.model, no_llm=args.no_llm)

            ok_count += 1

    elapsed = time.time() - t0

    # Update tasks.json
    update_tasks_json(tasks)

    # Summary
    print(f"\n{'='*60}")
    print(f"Done in {elapsed:.0f}s")
    print(f"  Prepared: {ok_count}/{len(tasks)} tasks")
    if fail_count:
        print(f"  Failed: {fail_count} tasks")
    print(f"  Location: {PROJECTS_DIR}")
    print(f"  Tasks file: {TASKS_FILE}")

    if not args.annotate:
        print(f"\nNext step — annotate with CodeDNA:")
        print(f"  python setup_benchmark.py --repo {args.repo or 'django/django'} --annotate --no-llm")
    else:
        print(f"\nNext step — run the benchmark:")
        print(f"  python run_agent_multi.py --model deepseek-chat --runs 3")


if __name__ == "__main__":
    main()
