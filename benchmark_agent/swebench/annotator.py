"""
swebench/annotator.py — Genera annotazioni CodeDNA v0.5 per i file rilevanti.

deps:    google-genai (google.genai), tasks.json, projects_swebench/*/codedna/
exports: annotated Python files with module docstrings in codedna/ dirs
rules:   NEVER include hints about specific bugs in the annotations.
         Annotations describe ARCHITECTURE ONLY (deps, exports, contracts).
         Run this BEFORE knowing which specific task will be tested.
"""

import json
import os
import sys
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

ANNOTATION_PROMPT = """You are an expert Python architect. Given this Python source file from a real open-source project, generate a CodeDNA v0.5 module docstring.

FILE PATH: {filepath}
FILE CONTENT:
```python
{content}
```

OTHER FILES IN THE SAME PACKAGE: {sibling_files}

Generate ONLY the module docstring that should appear as the very first thing in the file.

Format exactly like this:
\"\"\"{filename} — <what this file does, ≤15 words>.

deps:    <file.py → symbol | none>
exports: <function(arg) -> return_type | ClassName>
used_by: <other_file.py → function | unknown>
tables:  <table_name(col1, col2) | none>
rules:   <one hard architectural constraint an agent editing this file must respect>
\"\"\"

RULES:
1. DO NOT include hints about bugs, vulnerabilities, or specific issues.
2. Describe architecture and contracts only.
3. Keep it to 7-10 lines maximum.
4. Output ONLY the docstring block, no other text or markdown.
"""

def get_python_files(directory: Path) -> list[Path]:
    return [f for f in directory.rglob("*.py")
            if "__pycache__" not in str(f) and f.name != "__init__.py"]

def already_annotated(content: str) -> bool:
    return content.strip().startswith('"""') and "deps:" in content[:600]

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
            config=gtypes.GenerateContentConfig(temperature=0.2, max_output_tokens=512),
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
    if not API_KEY:
        print("ERROR: set GEMINI_API_KEY environment variable")
        sys.exit(1)

    client   = genai.Client(api_key=API_KEY)
    model_id = "gemini-2.5-flash-preview-04-17"

    with open(TASKS_FILE) as f:
        tasks = json.load(f)

    for task in tasks:
        iid         = task["instance_id"]
        codedna_dir = PROJECTS_DIR / iid / "codedna"

        if not codedna_dir.exists():
            print(f"⚠️  {iid}: codedna/ not found — run setup_repos.py first.")
            continue

        print(f"\n{'='*60}")
        print(f"Annotating: {iid}")

        # Prioritise files the real fix touches
        priority = [
            codedna_dir / f for f in task.get("files_in_patch", [])
            if (codedna_dir / f).exists() and f.endswith(".py")
        ]

        # Also include top-level Python modules up to 20 files total
        all_py     = get_python_files(codedna_dir)
        top_level  = [f for f in all_py if len(f.relative_to(codedna_dir).parts) <= 2]
        combined   = list({str(f): f for f in priority + top_level}.values())[:20]

        annotated  = 0
        for fp in combined:
            rel = fp.relative_to(codedna_dir)
            ok  = annotate_file(fp, codedna_dir, client, model_id)
            print(f"    {'✅' if ok else '⏭️ '} {rel}")
            if ok:
                annotated += 1

        print(f"  → Annotated {annotated}/{len(combined)} files")

    print("\n✅ Annotation complete.")
    print("Next: python swebench/run_agent.py")

if __name__ == "__main__":
    main()
