#!/usr/bin/env python3
"""analyze_claude_code_test.py — Compares control vs CodeDNA Claude Code sessions."""

import json
from pathlib import Path
from collections import Counter

LOGS = {
    "control": Path("/tmp/codedna_test_control.jsonl"),
    "codedna":  Path("/tmp/codedna_test_codedna.jsonl"),
}

GT_FILES = [
    "django/db/backends/base/features.py",
    "django/db/backends/mysql/features.py",
    "django/db/models/expressions.py",
    "django/db/models/query.py",
    "django/db/models/query_utils.py",
    "django/db/models/sql/__init__.py",
    "django/db/models/sql/where.py",
]

def load(path):
    if not path.exists():
        print(f"  [!] Log not found: {path}")
        return []
    entries = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries

def analyze(name, entries):
    print(f"\n{'='*50}")
    print(f"  {name.upper()}")
    print(f"{'='*50}")

    if not entries:
        print("  No data.")
        return

    tools = Counter(e["tool"] for e in entries)
    print(f"\n  Total tool calls : {len(entries)}")
    print(f"  Breakdown:")
    for tool, count in tools.most_common():
        print(f"    {tool:<30} {count}")

    # Files read
    files_read = []
    for e in entries:
        inp = e.get("input", "")
        if e["tool"] in ("Read", "read_file", "str_replace_based_edit_tool"):
            # extract file path from input string
            for segment in inp.replace("'", '"').split('"'):
                if "/" in segment and "." in segment:
                    files_read.append(segment.strip())
                    break

    files_unique = list(dict.fromkeys(files_read))
    print(f"\n  Files read (unique): {len(files_unique)}")
    for f in files_unique:
        gt = "✅ GT" if any(gt in f for gt in GT_FILES) else "   "
        print(f"    {gt}  {f}")

    # F1
    gt_found = sum(1 for f in files_unique if any(gt in f for gt in GT_FILES))
    precision = gt_found / len(files_unique) if files_unique else 0
    recall    = gt_found / len(GT_FILES)
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
    print(f"\n  GT files found   : {gt_found}/{len(GT_FILES)}")
    print(f"  Precision        : {precision:.2f}")
    print(f"  Recall           : {recall:.2f}")
    print(f"  F1               : {f1:.2f}")

    duration = None
    if len(entries) >= 2:
        from datetime import datetime
        t0 = datetime.fromisoformat(entries[0]["ts"])
        t1 = datetime.fromisoformat(entries[-1]["ts"])
        duration = (t1 - t0).total_seconds()
        print(f"\n  Session duration : {duration:.0f}s")

if __name__ == "__main__":
    print("\nCodeDNA Claude Code Test — Analysis")
    print("Task: django__django-14480 (XOR support for Q() and QuerySet())")
    print(f"Ground truth files: {len(GT_FILES)}")

    for name, path in LOGS.items():
        entries = load(path)
        analyze(name, entries)

    print("\n\nNOTE: add /cost output manually from each session for token comparison.")
