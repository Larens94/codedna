#!/usr/bin/env python3
"""extract_city_data.py — Extract CodeDNA annotations into JSON for city visualization.

Usage:
    python tools/extract_city_data.py PATH [--root ROOT]

    PATH   Directory to scan for annotated .py files
    ROOT   Base path for relative IDs (default: PATH/..)
           Use ROOT when PATH is a package dir and you want IDs like pkg/sub/file.py

Examples:
    # Django benchmark project
    python tools/extract_city_data.py benchmark_agent/projects_swebench/django__django-13495/codedna/django

    # Any annotated Python project
    python tools/extract_city_data.py /path/to/myapp/src --root /path/to/myapp
"""

import argparse
import ast
import json
import sys
from pathlib import Path


def parse_codedna(source: str) -> dict | None:
    try:
        tree = ast.parse(source)
        ds = ast.get_docstring(tree)
        if not ds or not any(f in ds for f in ("exports:", "used_by:", "rules:")):
            return None
    except Exception:
        return None

    fields: dict[str, str] = {"exports": "", "used_by": "", "rules": "", "agent": ""}
    current = None
    for line in ds.split("\n"):
        s = line.strip()
        if s.startswith("exports:"):
            current = "exports"
            fields[current] = s[8:].strip()
        elif s.startswith("used_by:"):
            current = "used_by"
            fields[current] = s[8:].strip()
        elif s.startswith("rules:"):
            current = "rules"
            fields[current] = s[6:].strip()
        elif s.startswith("agent:"):
            current = "agent"
            fields[current] = s[6:].strip()
        elif (
            current
            and s
            and not any(s.startswith(k + ":") for k in ("exports", "used_by", "rules", "agent", "message"))
        ):
            sep = "\n" if current == "used_by" else " "
            fields[current] += sep + s
    return fields


def count_used_by(ub: str) -> int:
    if not ub or ub.strip() == "none":
        return 0
    return len([l for l in ub.split("\n") if l.strip() and l.strip() != "none"])


def district(rel: str) -> str:
    parts = Path(rel).parts  # ('django', 'db', 'models', ...)
    if len(parts) < 2:
        return "root"
    top = parts[1]
    # contrib and conf get second-level grouping (too large otherwise)
    if top in ("contrib", "conf") and len(parts) >= 3:
        sub = parts[2]
        # collapse locale/* into a single "conf/locale" district
        if top == "conf" and sub == "locale":
            return "conf/locale"
        return f"{top}/{sub}"
    return top


def last_model(agent_text: str) -> str:
    if not agent_text:
        return "unknown"
    lines = [l.strip() for l in agent_text.split("\n") if l.strip()]
    last = lines[-1] if lines else agent_text
    return last.split("|")[0].strip() or "unknown"


def extract(target_dir: Path, root: Path) -> dict:
    buildings = []
    for f in sorted(target_dir.rglob("*.py")):
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        fields = parse_codedna(src)
        if not fields:
            continue

        rel = str(f.relative_to(root))
        ub_count = count_used_by(fields["used_by"])
        agent_lines = [l for l in fields["agent"].split("\n") if l.strip()]

        buildings.append(
            {
                "id": rel,
                "d": district(rel),  # district
                "n": f.name,  # name
                "ub": ub_count,  # used_by count
                "ac": len(agent_lines),  # agent count
                "ex": fields["exports"][:120],
                "ru": fields["rules"][:200],
                "ag": fields["agent"].split("\n")[0][:100],  # first agent line only
                "am": last_model(fields["agent"]),
            }
        )

    max_ub = max((b["ub"] for b in buildings), default=1) or 1
    for b in buildings:
        b["h"] = round(0.3 + (b["ub"] / max_ub) * 5.7, 2)

    districts = sorted({b["d"] for b in buildings})
    models = sorted({b["am"] for b in buildings})

    return {
        "buildings": buildings,
        "stats": {
            "total_files": len(buildings),
            "districts": len(districts),
            "district_list": districts,
            "models": models,
            "total_connections": sum(b["ub"] for b in buildings),
        },
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Extract CodeDNA annotations into JSON for city visualization"
    )
    p.add_argument("path", type=Path, help="Directory to scan for annotated .py files")
    p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Base path for relative IDs (default: PATH/..)",
    )
    args = p.parse_args()

    target = args.path.resolve()
    root = args.root.resolve() if args.root else target.parent

    if not target.exists():
        print(f"Error: {target} does not exist", file=sys.stderr)
        sys.exit(1)

    data = extract(target, root)
    print(
        f"[extract_city_data] {data['stats']['total_files']} buildings · "
        f"{data['stats']['districts']} districts · "
        f"{data['stats']['total_connections']} connections",
        file=sys.stderr,
    )
    print(json.dumps(data, separators=(",", ":")))
