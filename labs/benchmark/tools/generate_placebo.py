"""generate_placebo.py — Create placebo/ variant with shuffled used_by: blocks.

exports: extract_used_by(src) -> (start, end, text) | replace_used_by(src, new_text) -> str | generate_placebo(task_id) -> dict | main()
used_by: none
rules:   PLACEBO = a benchmark condition that keeps the CodeDNA L0 manifest AND
         each file's module header, BUT permutes the `used_by:` block across
         files so every header points to the WRONG callers.
         The `exports:`, `rules:`, and function-level `Rules:` stay as in codedna/.
         The `.codedna` manifest is copied verbatim (same purposes/depends_on).
         If codedna vs placebo F1 is similar, the benefit is NOT from the graph.
         If placebo ≈ control, the benefit IS from the real used_by: graph.
         Deterministic: seed=42 by default so the shuffle is reproducible.
agent:   claude-opus-4-7 | anthropic | 2026-04-17 | s_20260417_placebo | initial placebo generator for causal isolation of used_by: graph effect
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
from pathlib import Path
from typing import Optional

BENCH_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = BENCH_ROOT / "projects"

# Regex: captures the `used_by:` block — starts at line with `used_by:`,
# continues through subsequent lines that begin with whitespace (continuation).
# Ends at the first line whose first non-space char is `rules:`, `agent:`,
# `message:`, or closing `"""`.
_HEADER_END = re.compile(r'^\s*(?:rules:|agent:|message:|""")', re.MULTILINE)


def extract_used_by(src: str) -> Optional[tuple[int, int, str]]:
    """Find the (start_offset, end_offset, text) of the used_by: block.

    Returns None if the file has no used_by: block (e.g. no CodeDNA header).
    """
    # Look only inside the first ~50 lines (module docstring)
    prefix = src[:4000]
    m = re.search(r'^used_by:', prefix, re.MULTILINE)
    if not m:
        return None
    start = m.start()
    # Find end: first line starting with rules:/agent:/message:/""" after start
    m2 = _HEADER_END.search(prefix, m.end())
    if not m2:
        return None
    # Don't include the terminator line itself
    end = m2.start()
    # Trim trailing newline from the block for cleaner swap
    text = src[start:end].rstrip() + "\n"
    return (start, start + len(text), text)


def replace_used_by(src: str, new_used_by_block: str) -> str:
    loc = extract_used_by(src)
    if loc is None:
        return src
    start, end, _ = loc
    return src[:start] + new_used_by_block + src[end:]


def generate_placebo(task_id: str, seed: int = 42, dry_run: bool = False,
                     force: bool = False) -> dict:
    """For a task, create placebo/ by shuffling used_by: blocks across codedna/."""
    if "__" not in task_id:
        task_id = f"django__django-{task_id}"
    task_dir = PROJECTS_DIR / task_id
    cdna = task_dir / "codedna"
    placebo = task_dir / "placebo"

    if not cdna.exists():
        return {"task": task_id, "error": "codedna/ dir missing"}

    if placebo.exists() and not force:
        return {"task": task_id, "error": "placebo/ exists — pass --force to overwrite"}

    # Step 1: collect all .py files with a used_by: block
    py_files = [f for f in cdna.rglob("*.py")
                if "migrations" not in f.parts and "__pycache__" not in f.parts]

    files_with_used_by = []
    original_blocks = {}
    for fp in py_files:
        try:
            src = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        loc = extract_used_by(src)
        if loc is None:
            continue
        rel = str(fp.relative_to(cdna))
        files_with_used_by.append(rel)
        original_blocks[rel] = loc[2]  # the used_by: block text

    # Step 2: build shuffled mapping (deterministic)
    rng = random.Random(seed)
    shuffled_rels = list(files_with_used_by)
    rng.shuffle(shuffled_rels)
    # shuffle_map[src] = src_of_the_block_that_will_replace_it
    shuffle_map = dict(zip(files_with_used_by, shuffled_rels))

    # Fixed-points count (file receives its own block back by chance)
    fixed = sum(1 for k, v in shuffle_map.items() if k == v)
    # If the shuffle left >5% fixed-points, re-shuffle with a derangement-ish pass
    if fixed > max(1, len(shuffle_map) // 20):
        # Manual derangement-like: any self-mapping swapped with next
        items = list(shuffle_map.items())
        for i in range(len(items)):
            k, v = items[i]
            if k == v:
                j = (i + 1) % len(items)
                items[i], items[j] = (items[i][0], items[j][1]), (items[j][0], items[i][1])
        shuffle_map = dict(items)
        fixed = sum(1 for k, v in shuffle_map.items() if k == v)

    if dry_run:
        return {
            "task": task_id,
            "files_with_used_by": len(files_with_used_by),
            "fixed_points": fixed,
            "sample_swaps": list(shuffle_map.items())[:5],
            "dry_run": True,
        }

    # Step 3: copy codedna/ → placebo/, then rewrite used_by: blocks
    if placebo.exists():
        shutil.rmtree(placebo)
    shutil.copytree(cdna, placebo)

    rewritten = 0
    for src_rel, new_rel in shuffle_map.items():
        fp = placebo / src_rel
        try:
            src = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        new_block = original_blocks.get(new_rel)
        if not new_block:
            continue
        patched = replace_used_by(src, new_block)
        if patched != src:
            fp.write_text(patched, encoding="utf-8")
            rewritten += 1

    return {
        "task": task_id,
        "files_with_used_by": len(files_with_used_by),
        "fixed_points": fixed,
        "rewritten": rewritten,
        "placebo_dir": str(placebo),
    }


def main():
    ap = argparse.ArgumentParser(description="Generate placebo/ (shuffled used_by:) for benchmark tasks")
    ap.add_argument("--task-id", nargs="+", required=True,
                    help="Task IDs (bare number or full). One per shuffle.")
    ap.add_argument("--seed", type=int, default=42, help="Shuffle seed (default 42 for reproducibility)")
    ap.add_argument("--dry-run", action="store_true", help="Preview swaps without writing")
    ap.add_argument("--force", action="store_true", help="Overwrite existing placebo/")
    args = ap.parse_args()

    for tid in args.task_id:
        result = generate_placebo(tid, seed=args.seed, dry_run=args.dry_run, force=args.force)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
