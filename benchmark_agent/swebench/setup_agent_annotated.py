"""
swebench/setup_agent_annotated.py — Creates agent_annotated/ dirs for all tasks.

deps:    annotator.py, tasks.json, projects_swebench/*/control/
exports: projects_swebench/*/agent_annotated/ with auto-generated CodeDNA headers
         projects_swebench/*/agent_annotated/.annotation_cost.json
rules:   agent_annotated/ is a copy of control/ + LLM-generated annotations only.
         No human knowledge is injected. This tests the protocol end-to-end.

Usage:
  GEMINI_API_KEY=... python setup_agent_annotated.py
  GEMINI_API_KEY=... python setup_agent_annotated.py --task django__django-14480
  GEMINI_API_KEY=... python setup_agent_annotated.py --model gemini-2.5-flash
"""

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

try:
    from google import genai
    from google.genai import types as gtypes
except ImportError:
    print("ERROR: pip install google-genai")
    sys.exit(1)

TASKS_FILE   = Path(__file__).parent / "tasks.json"
PROJECTS_DIR = Path(__file__).parent.parent / "projects_swebench"
API_KEY      = os.getenv("GEMINI_API_KEY", "")

ANNOTATION_PROMPT = """You are an expert Python architect analysing a real open-source codebase.
Given this Python source file, generate a CodeDNA v0.7 module docstring.

FILE PATH: {filepath}
FILE CONTENT:
```python
{content}
```

OTHER FILES IN THE SAME PACKAGE: {sibling_files}

Generate ONLY the module docstring that should appear as the very first thing in the file.

Format exactly like this (keep to 7-10 lines):
\"\"\"{filename} — <what this file does, ≤15 words>.

exports: <function(arg) -> return_type | ClassName | none>
used_by: <other_file.py → symbol | unknown>
rules:   <one hard architectural constraint an agent editing this file must respect>
\"\"\"

RULES:
1. DO NOT include hints about bugs, vulnerabilities, or specific tasks.
2. Describe architecture and contracts only.
3. Output ONLY the docstring block — no markdown fences, no other text.
"""


def get_python_files(directory: Path) -> list[Path]:
    return [f for f in directory.rglob("*.py")
            if "__pycache__" not in str(f)]


def already_annotated(content: str) -> bool:
    first = content.lstrip()
    return first.startswith(('"""', "'''")) and (
        "exports:" in first[:600] or "rules:" in first[:600]
    )


def annotate_file(filepath: Path, repo_root: Path, client, model_id: str) -> tuple[bool, int]:
    """Returns (was_annotated, chars_generated)."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    if already_annotated(content):
        return False, 0
    if len(content.strip()) < 30:
        return False, 0

    siblings = [f.name for f in filepath.parent.glob("*.py") if f != filepath][:5]
    rel_path = filepath.relative_to(repo_root)

    prompt = ANNOTATION_PROMPT.format(
        filepath=str(rel_path),
        filename=filepath.name,
        content=content[:3000],
        sibling_files=", ".join(siblings) or "none",
    )

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=gtypes.GenerateContentConfig(temperature=0.0, max_output_tokens=512),
        )
        raw = response.text.strip()

        # Strip markdown fences if model wraps in ```
        if raw.startswith("```"):
            lines = raw.split("\n")
            inner, in_block = [], False
            for line in lines:
                if line.startswith("```"):
                    in_block = not in_block
                    continue
                if in_block:
                    inner.append(line)
            raw = "\n".join(inner).strip()

        # Remove existing module docstring if present
        new_content = content
        stripped = content.lstrip()
        if stripped.startswith(('"""', "'''")):
            q = '"""' if stripped.startswith('"""') else "'''"
            end = stripped.find(q, 3)
            if end != -1:
                new_content = stripped[end + 3:].lstrip()

        filepath.write_text(raw + "\n\n" + new_content, encoding="utf-8")
        return True, len(raw)

    except Exception as e:
        print(f"    ⚠️  {rel_path}: {e}")
        return False, 0


def setup_task(task: dict, model_id: str, client, force: bool = False) -> dict:
    iid         = task["instance_id"]
    ctrl_dir    = PROJECTS_DIR / iid / "control"
    ann_dir     = PROJECTS_DIR / iid / "agent_annotated"
    cost_file   = ann_dir / ".annotation_cost.json"

    if not ctrl_dir.exists():
        print(f"⚠️  {iid}: control/ not found — skipping.")
        return {}

    # Copy control → agent_annotated
    if ann_dir.exists() and not force:
        print(f"  ℹ️  {iid}: agent_annotated/ exists (use --force to redo)")
    else:
        if ann_dir.exists():
            shutil.rmtree(ann_dir)
        print(f"  Copying control/ → agent_annotated/ ...")
        shutil.copytree(ctrl_dir, ann_dir)

    # Annotate: prioritise ground-truth files, then top-level Python files
    priority = [
        ann_dir / f for f in task.get("files_in_patch", [])
        if (ann_dir / f).exists() and f.endswith(".py")
    ]
    all_py    = get_python_files(ann_dir)
    top_level = [f for f in all_py if len(f.relative_to(ann_dir).parts) <= 3]
    combined  = list({str(f): f for f in priority + top_level}.values())[:30]

    total_annotated  = 0
    total_chars_gen  = 0
    total_files      = len(combined)
    t0               = time.time()

    for fp in combined:
        rel = fp.relative_to(ann_dir)
        ok, chars = annotate_file(fp, ann_dir, client, model_id)
        if ok:
            total_annotated += 1
            total_chars_gen += chars
            print(f"    ✅ {rel}")
        else:
            print(f"    ⏭️  {rel}")
        time.sleep(0.3)  # avoid rate limits

    elapsed = round(time.time() - t0, 1)
    cost = {
        "instance_id":     iid,
        "model_id":        model_id,
        "files_considered": total_files,
        "files_annotated": total_annotated,
        "chars_generated": total_chars_gen,
        "elapsed_seconds": elapsed,
    }
    cost_file.write_text(json.dumps(cost, indent=2))
    print(f"  → Annotated {total_annotated}/{total_files} files "
          f"| {total_chars_gen:,} chars generated | {elapsed}s")
    return cost


def main():
    parser = argparse.ArgumentParser(
        description="Set up agent_annotated/ variants for benchmark tasks"
    )
    parser.add_argument("--task",  help="Run for a specific instance_id only")
    parser.add_argument("--model", default="gemini-2.5-flash",
                        help="Gemini model for annotation (default: gemini-2.5-flash)")
    parser.add_argument("--force", action="store_true",
                        help="Re-create agent_annotated/ even if it already exists")
    args = parser.parse_args()

    if not API_KEY:
        print("ERROR: set GEMINI_API_KEY environment variable")
        sys.exit(1)

    client = genai.Client(api_key=API_KEY)

    with open(TASKS_FILE) as f:
        tasks = json.load(f)

    if args.task:
        tasks = [t for t in tasks if t["instance_id"] == args.task]
        if not tasks:
            print(f"ERROR: task '{args.task}' not found in tasks.json")
            sys.exit(1)

    all_costs = []
    for task in tasks:
        print(f"\n{'='*60}")
        print(f"Task: {task['instance_id']}")
        cost = setup_task(task, args.model, client, force=args.force)
        if cost:
            all_costs.append(cost)

    if all_costs:
        total_chars = sum(c["chars_generated"] for c in all_costs)
        total_time  = sum(c["elapsed_seconds"] for c in all_costs)
        print(f"\n{'='*60}")
        print(f"Done. Total: {total_chars:,} chars generated | {total_time:.0f}s across {len(all_costs)} tasks.")
        print(f"Next: python swebench/run_agent_multi.py --condition agent-annotated")


if __name__ == "__main__":
    main()
