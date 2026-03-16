"""
swebench/setup_repos.py — Checkout dei repo alla commit base per ogni task SWE-bench.

deps:    tasks.json (output di select_tasks.py), git
exports: projects_swebench/<instance_id>/control/ — repo originale senza annotazioni
         projects_swebench/<instance_id>/codedna/  — copia identica, pronta per annotazione
rules:   NEVER apply the ground-truth patch before running the agent.
         Uses a shared _repo_cache/ to avoid cloning the same repo multiple times.
"""

import json
import subprocess
import shutil
from pathlib import Path

TASKS_FILE  = Path(__file__).parent / "tasks.json"
PROJECTS_DIR = Path(__file__).parent.parent / "projects_swebench"
CACHE_DIR    = Path(__file__).parent.parent / "_repo_cache"

REPO_URLS = {
    "pallets/flask":    "https://github.com/pallets/flask.git",
    "pallets/werkzeug": "https://github.com/pallets/werkzeug.git",
    "django/django":    "https://github.com/django/django.git",
    "psf/requests":     "https://github.com/psf/requests.git",
}


def run(cmd: list, cwd=None, check=True):
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)
    if result.returncode != 0 and check:
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result


def get_or_clone_cache(repo: str) -> Path:
    """Full-depth clone to local cache, reused across tasks of the same repo."""
    key = repo.replace("/", "__")
    cache_path = CACHE_DIR / key
    if not cache_path.exists():
        url = REPO_URLS.get(repo, f"https://github.com/{repo}.git")
        print(f"\n📥 Cloning {repo} (full, may take ~2 min)...")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", url, str(cache_path)])
        print(f"  ✅ Cached → {cache_path}")
    else:
        print(f"  ✅ Cache hit: {repo}")
    return cache_path


def setup_task(task: dict):
    iid         = task["instance_id"]
    repo        = task["repo"]
    base_commit = task["base_commit"]

    task_dir    = PROJECTS_DIR / iid
    control_dir = task_dir / "control"
    codedna_dir = task_dir / "codedna"

    print(f"\n{'='*60}")
    print(f"Task: {iid}")
    print(f"Repo: {repo}   Commit: {base_commit[:12]}...")

    if control_dir.exists() and codedna_dir.exists():
        print("  ✅ Already done, skipping.")
        return

    cache = get_or_clone_cache(repo)

    # control/ = full copy of cache checked out at base_commit
    if not control_dir.exists():
        task_dir.mkdir(parents=True, exist_ok=True)
        print("  Copying cache → control/ ...")
        shutil.copytree(str(cache), str(control_dir))
        try:
            run(["git", "checkout", base_commit], cwd=control_dir)
        except subprocess.CalledProcessError:
            print("  Fetching full history (shallow cache)...")
            run(["git", "fetch", "--unshallow"], cwd=control_dir, check=False)
            run(["git", "checkout", base_commit], cwd=control_dir)
        print(f"  ✅ control/ @ {base_commit[:12]}")

    # codedna/ = identical copy, .git excluded — annotator fills in docstrings
    if not codedna_dir.exists():
        print("  Copying control/ → codedna/ ...")
        shutil.copytree(
            str(control_dir), str(codedna_dir),
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        print("  ✅ codedna/ ready for annotation")

    # Save metadata
    (task_dir / "problem_statement.txt").write_text(task["problem_statement"])
    (task_dir / "files_in_patch.json").write_text(
        json.dumps(task["files_in_patch"], indent=2)
    )
    print(f"  Ground-truth files: {task['files_in_patch'][:3]} ...")


def main():
    if not TASKS_FILE.exists():
        print(f"ERROR: {TASKS_FILE} not found — run select_tasks.py first.")
        return

    with open(TASKS_FILE) as f:
        tasks = json.load(f)

    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Setting up {len(tasks)} tasks → {PROJECTS_DIR}")

    for task in tasks:
        try:
            setup_task(task)
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "")[:300]
            print(f"  ❌ Failed: {stderr}")

    print(f"\n✅ Done. Projects in {PROJECTS_DIR}")
    print("Next: python swebench/annotator.py")


if __name__ == "__main__":
    main()
