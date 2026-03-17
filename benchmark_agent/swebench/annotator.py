"""
swebench/annotator.py — Genera annotazioni CodeDNA v0.5 per i file rilevanti.

deps:    google-genai (google.genai), tasks.json, projects_swebench/*/codedna/
exports: annotated Python files with module docstrings in codedna/ dirs
rules:   NEVER include hints about specific bugs in the annotations.
         Annotations describe ARCHITECTURE ONLY (deps, exports, contracts).
         Run this BEFORE knowing which specific task will be tested.
"""

import argparse
import json
import os
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

ANNOTATION_PROMPT = """You are an expert Python architect. Given this Python source file from a real open-source project, generate a CodeDNA v0.7 module docstring.

FILE PATH: {filepath}
FILE CONTENT:
```python
{content}
```

OTHER FILES IN THE SAME PACKAGE: {sibling_files}

Generate ONLY the module docstring. It must be the very first thing in the file.

Output EXACTLY this format (no extra fields, no markdown fences):
\"\"\"{filename} — <what this file does, max 15 words>.

exports: <ClassName | function(args) -> type | none>
used_by: <other_file.py → symbol | none>
rules:   <one architectural constraint an agent editing this file MUST respect>
\"\"\"

STRICT RULES:
1. Output ONLY the docstring — starting with \"\"\" and ending with \"\"\".
2. Exactly 4 lines inside: summary, blank, exports:, used_by:, rules:
3. NO deps:, NO tables:, NO other fields.
4. DO NOT mention bugs or specific task details — architecture only.
5. Keep rules: to one sentence, max 20 words.
"""

def get_python_files(directory: Path) -> list[Path]:
    return [f for f in directory.rglob("*.py")
            if "__pycache__" not in str(f) and f.name != "__init__.py"]

def already_annotated(content: str) -> bool:
    first = content.strip()
    return first.startswith(('"""', "'''")) and (
        "exports:" in first[:600] and "rules:" in first[:600]
    )

def annotate_file(filepath: Path, repo_root: Path, client, model_id: str) -> bool:
    content = filepath.read_text(encoding="utf-8", errors="replace")
    if already_annotated(content):
        return False
    if len(content.strip()) < 30:
        return False

    siblings = [f.name for f in filepath.parent.glob("*.py") if f != filepath][:5]
    rel_path  = filepath.relative_to(repo_root)

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
            config=gtypes.GenerateContentConfig(temperature=0.2, max_output_tokens=1024),
        )
        raw = response.text.strip()

        # Strip markdown fences if model wraps in ```
        if raw.startswith("```"):
            lines = raw.split("\n")
            inner = []
            in_block = False
            for line in lines:
                if line.startswith("```"):
                    in_block = not in_block
                    continue
                if in_block:
                    inner.append(line)
            raw = "\n".join(inner).strip()

        # Ensure docstring is properly closed
        if raw.startswith('"""') and not raw.endswith('"""'):
            raw = raw.rstrip() + '\n"""'
        elif raw.startswith("'''") and not raw.endswith("'''"):
            raw = raw.rstrip() + "\n'''"

        # Remove existing module docstring if present
        new_content = content
        if content.strip().startswith(('"""', "'''")):
            q = '"""' if content.strip().startswith('"""') else "'''"
            end = content.find(q, 3)
            if end != -1:
                new_content = content[end + 3:].lstrip()

        filepath.write_text(raw + "\n\n" + new_content, encoding="utf-8")
        return True

    except Exception as e:
        print(f"    ⚠️  {rel_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Annotate codedna/ dirs with CodeDNA v0.7 headers (exports + used_by + rules)"
    )
    parser.add_argument("--task",  help="Annotate a specific instance_id only")
    parser.add_argument("--force", action="store_true",
                        help="Re-annotate even files that already have full annotations")
    parser.add_argument("--model", default="gemini-2.5-flash",
                        help="Gemini model to use (default: gemini-2.5-flash)")
    args = parser.parse_args()

    if not API_KEY:
        print("ERROR: set GEMINI_API_KEY environment variable")
        sys.exit(1)

    client   = genai.Client(api_key=API_KEY)
    model_id = args.model

    with open(TASKS_FILE) as f:
        tasks = json.load(f)

    if args.task:
        tasks = [t for t in tasks if t["instance_id"] == args.task]
        if not tasks:
            print(f"ERROR: task '{args.task}' not found in tasks.json")
            sys.exit(1)

    for task in tasks:
        iid         = task["instance_id"]
        codedna_dir = PROJECTS_DIR / iid / "codedna"

        if not codedna_dir.exists():
            print(f"⚠️  {iid}: codedna/ not found — skipping.")
            continue

        print(f"\n{'='*60}")
        print(f"Annotating: {iid}  (force={args.force})")

        # Prioritise files the real fix touches
        priority = [
            codedna_dir / f for f in task.get("files_in_patch", [])
            if (codedna_dir / f).exists() and f.endswith(".py")
        ]

        # Also include top-level Python modules up to 30 files total
        all_py    = get_python_files(codedna_dir)
        top_level = [f for f in all_py if len(f.relative_to(codedna_dir).parts) <= 3]
        combined  = list({str(f): f for f in priority + top_level}.values())[:30]

        # If --force, strip existing docstrings so already_annotated() returns False
        if args.force:
            for fp in combined:
                content = fp.read_text(encoding="utf-8", errors="replace")
                stripped = content.lstrip()
                if stripped.startswith(('"""', "'''")):
                    q = '"""' if stripped.startswith('"""') else "'''"
                    end = stripped.find(q, 3)
                    if end != -1:
                        fp.write_text(stripped[end + 3:].lstrip(), encoding="utf-8")

        annotated = 0
        for fp in combined:
            rel = fp.relative_to(codedna_dir)
            ok  = annotate_file(fp, codedna_dir, client, model_id)
            print(f"    {'✅' if ok else '⏭️ '} {rel}")
            if ok:
                annotated += 1
            time.sleep(0.3)

        print(f"  → Annotated {annotated}/{len(combined)} files")

    print("\n✅ Annotation complete.")
    print("Next: python swebench/run_agent_multi.py")

if __name__ == "__main__":
    main()
