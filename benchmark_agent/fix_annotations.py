"""Fix malformed CodeDNA annotations on specific files."""
import os
import time
from pathlib import Path

from google import genai
from google.genai import types as gt

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

PROMPT = """You are a Python architect. Generate a CodeDNA v0.7 module docstring.

FILE: {filepath}
FILE CONTENT (first 1500 chars):
{content}

Output ONLY the docstring block, nothing else.
Start with triple-double-quote, end with triple-double-quote.
Use EXACTLY this format:

\"\"\"{filename} — <purpose, max 15 words>.

exports: <main public classes/functions | none>
used_by: <files that import from this | unknown>
rules:   <one hard architectural constraint, max 20 words>
\"\"\""""

TARGETS = [
    ("django__django-13495", "django/db/backends/mysql/operations.py"),
    ("django__django-13495", "django/db/backends/sqlite3/operations.py"),
    ("django__django-11991", "django/db/backends/base/schema.py"),
    ("django__django-11808", "django/db/models/base.py"),
    ("django__django-11808", "django/db/models/constraints.py"),
]

def strip_docstring(content: str) -> str:
    """Remove all leading docstrings and any orphan text before first import/class/def."""
    lines = content.splitlines(keepends=True)
    in_doc = False
    i = 0
    # Skip leading docstrings (possibly multiple broken ones)
    while i < len(lines):
        line = lines[i].strip()
        if not in_doc and (line.startswith('"""') or line.startswith("'''")):
            q = '"""' if line.startswith('"""') else "'''"
            # Check if it closes on same line
            rest = line[3:]
            if q in rest:
                i += 1
                continue
            in_doc = True
            i += 1
            continue
        if in_doc:
            if '"""' in lines[i] or "'''" in lines[i]:
                in_doc = False
            i += 1
            continue
        # Skip blank lines and lines that don't look like Python code
        if line == "" or line.startswith("#"):
            i += 1
            continue
        # Stop at first real Python line
        if (line.startswith("import ") or line.startswith("from ") or
                line.startswith("class ") or line.startswith("def ") or
                line.startswith("@")):
            break
        # Skip other garbage (e.g. "Depends: ...")
        i += 1

    return "".join(lines[i:])


for iid, rel in TARGETS:
    fp = Path(f"projects_swebench/{iid}/codedna/{rel}")
    raw_content = fp.read_text(encoding="utf-8", errors="replace")
    clean_content = strip_docstring(raw_content)

    prompt = PROMPT.format(
        filepath=rel,
        filename=Path(rel).name,
        content=clean_content[:1500],
    )

    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=gt.GenerateContentConfig(temperature=0.0, max_output_tokens=300),
    )
    annotation = resp.text.strip()

    # Strip markdown fences if present
    if annotation.startswith("```"):
        lines = annotation.split("\n")
        inner, in_block = [], False
        for line in lines:
            if line.startswith("```"):
                in_block = not in_block
                continue
            if in_block:
                inner.append(line)
        annotation = "\n".join(inner).strip()

    # Ensure properly closed
    if annotation.startswith('"""') and not annotation.endswith('"""'):
        annotation = annotation.rstrip() + '\n"""'

    fp.write_text(annotation + "\n\n" + clean_content, encoding="utf-8")

    # Verify
    check = fp.read_text(encoding="utf-8", errors="replace")[:500]
    ok = ('exports:' in check and 'rules:' in check
          and check.count('"""') >= 2)
    print(f"  {'✅' if ok else '❌'} {iid}/{rel}")
    time.sleep(0.5)

print("\nDone.")
