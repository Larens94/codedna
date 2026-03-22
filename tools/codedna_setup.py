#!/usr/bin/env python3
"""codedna_setup.py — CLI setup tool for CodeDNA Communication Protocol v0.7.

exports: main() -> int, cmd_install(args, target_dir),
         cmd_validate(args, target_dir) -> int, cmd_annotate(args, _), cmd_check(_, target_dir)
used_by: users via CLI, integrations/install.sh
rules:   UNIVERSAL_PROMPT must always reflect current CodeDNA version syntax;
         cmd_validate required fields must match current module docstring fields
agent:   claude-sonnet-4-6 | 2026-03-21 | updated from v0.4 syntax to v0.7

Usage:
    python tools/codedna_setup.py install          # interactive setup
    python tools/codedna_setup.py install cursor   # install for Cursor
    python tools/codedna_setup.py install claude   # install for Claude Code
    python tools/codedna_setup.py install copilot  # install for GitHub Copilot
    python tools/codedna_setup.py install windsurf # install for Windsurf
    python tools/codedna_setup.py install all      # install for all tools
    python tools/codedna_setup.py validate [path]  # validate manifest headers
    python tools/codedna_setup.py annotate <file>  # print annotation prompt for file
    python tools/codedna_setup.py check            # check which tools are installed
"""

import sys
import shutil
from pathlib import Path

# ── Colours ──────────────────────────────────────────────────────────────────
R = "\033[31m"
G = "\033[32m"
Y = "\033[33m"
B = "\033[34m"
C = "\033[36m"
W = "\033[1m"
D = "\033[0m"

REPO_ROOT = Path(__file__).parent.parent
INTEG_DIR = REPO_ROOT / "integrations"

LOGO = f"""
{C}{W}🧬 CodeDNA v0.7{D}  {Y}github.com/Larens94/codedna{D}
{D}Every file carries the complete genome of the project.
"""

# ── Tool configs ──────────────────────────────────────────────────────────────
TOOLS = {
    "cursor": {
        "name": "Cursor",
        "emoji": "🖱️",
        "src": INTEG_DIR / ".cursorrules",
        "dest": ".cursorrules",
        "desc": "Adds CodeDNA rules to .cursorrules at project root",
    },
    "claude": {
        "name": "Claude Code",
        "emoji": "🤖",
        "src": INTEG_DIR / "CLAUDE.md",
        "dest": "CLAUDE.md",
        "desc": "Creates CLAUDE.md at project root",
    },
    "copilot": {
        "name": "GitHub Copilot",
        "emoji": "🐙",
        "src": INTEG_DIR / "copilot-instructions.md",
        "dest": ".github/copilot-instructions.md",
        "desc": "Creates .github/copilot-instructions.md",
    },
    "windsurf": {
        "name": "Windsurf",
        "emoji": "🌊",
        "src": INTEG_DIR / ".cursorrules",  # same format
        "dest": ".windsurfrules",
        "desc": "Adds CodeDNA rules to .windsurfrules at project root",
    },
    "antigravity": {
        "name": "Antigravity",
        "emoji": "🪐",
        "src": None,
        "dest": None,
        "prompt": True,
        "desc": "Prints system prompt to paste in Antigravity settings",
    },
}

UNIVERSAL_PROMPT = """You follow the CodeDNA v0.7 Communication Protocol (github.com/Larens94/codedna).

ON READ: read the module docstring first (first 10-14 lines). Parse exports:, used_by:,
rules:, and agent: before reading any code. Read the Rules: docstring of any function
you plan to edit.

ON WRITE: every new Python file must begin with a CodeDNA module docstring:

  filename.py — <purpose ≤15 words>.

  exports: public_function(arg) -> return_type
  used_by: consumer_file.py → consumer_function
  rules:   <hard architectural constraint agents must never violate>
  agent:   <model-id> | <YYYY-MM-DD> | <what you implemented and what you noticed>

For functions with non-obvious constraints, add a Rules: docstring inside the function.
Use semantic naming: list_dict_users_from_db = get_users().

ON EDIT: re-read rules: and agent: history before writing. After editing, check
used_by: targets. Append a new agent: line (never edit existing ones). Update
rules: if you discover new architectural constraints.

EXPORTS are public contracts — never rename or remove without explicit instruction."""


# ── Helpers ───────────────────────────────────────────────────────────────────


def success(msg):
    print(f"  {G}✓{D} {msg}")


def warn(msg):
    print(f"  {Y}⚠{D}  {msg}")


def error(msg):
    print(f"  {R}✗{D} {msg}")


def info(msg):
    print(f"  {C}·{D} {msg}")


def section(msg):
    print(f"\n{W}{msg}{D}")


def install_tool(tool_key: str, target_dir: Path):
    """Install integration files for one tool into target_dir."""
    cfg = TOOLS[tool_key]

    if cfg.get("prompt"):
        section(f"{cfg['emoji']} {cfg['name']} — System Prompt")
        print(f"\n{Y}Paste this into your Antigravity / LLM system prompt:{D}\n")
        print("─" * 60)
        print(UNIVERSAL_PROMPT)
        print("─" * 60)
        return

    src: Path = cfg["src"]
    dest: Path = target_dir / cfg["dest"]

    if not src or not src.exists():
        error(f"Source file not found: {src}")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        warn(f"{dest.name} already exists — overwriting")

    shutil.copy2(src, dest)
    success(f"{cfg['emoji']} {cfg['name']:15s} → {dest.relative_to(target_dir)}")


def cmd_install(args: list[str], target_dir: Path):
    """Install command."""
    section("🧬 CodeDNA Setup")

    if not args:
        # Interactive
        print("\nWhich AI tools do you use? (space-separated, or 'all')")
        print()
        for k, v in TOOLS.items():
            print(f"  {v['emoji']}  {k:12s}  {v['desc']}")
        print()
        choice = input("→ ").strip().lower()
        keys = list(TOOLS.keys()) if choice == "all" else choice.split()
    else:
        keys = list(TOOLS.keys()) if args[0] == "all" else [args[0]]

    print()
    for key in keys:
        if key not in TOOLS:
            error(f"Unknown tool: '{key}'. Valid: {', '.join(TOOLS)}")
            continue
        install_tool(key, target_dir)

    print()
    info("Done! Now ask your AI to annotate your first file:")
    info(f'{Y}"Annotate this file with the CodeDNA v0.7 protocol"{D}')
    info(f"Spec: {C}github.com/Larens94/codedna/blob/main/SPEC.md{D}")


def cmd_validate(args: list[str], target_dir: Path):
    """Validate manifest headers in Python files."""
    section("🔍 Validating CodeDNA Manifests")

    scan_dir = Path(args[0]) if args else target_dir
    required = ["exports:", "used_by:", "rules:", "agent:"]

    ok = bad = skipped = 0
    problems = []

    for py_file in sorted(scan_dir.rglob("*.py")):
        if any(p in str(py_file) for p in ["__pycache__", ".venv", "venv", "node_modules"]):
            continue

        try:
            lines = py_file.read_text(encoding="utf-8").splitlines()
        except Exception:
            skipped += 1
            continue

        header = "\n".join(lines[:20])
        has_codedna = "exports:" in header and "used_by:" in header

        if not has_codedna:
            skipped += 1
            continue

        missing = [f for f in required if f not in header]
        rel = py_file.relative_to(scan_dir)

        if missing:
            bad += 1
            problems.append((rel, missing))
        else:
            ok += 1

    print()
    if ok:
        success(f"{ok} file(s) with complete manifests")
    if bad:
        error(f"{bad} file(s) with incomplete manifests")
    if skipped:
        info(f"{skipped} file(s) without CodeDNA headers (not annotated yet)")

    if problems:
        print()
        for rel, missing in problems:
            print(f"  {R}{rel}{D}")
            for m in missing:
                print(f"    missing: {Y}{m}{D}")

    return 0 if bad == 0 else 1


def cmd_annotate(args: list[str], _):
    """Print the annotation prompt for a specific file."""
    if not args:
        error("Usage: codedna annotate <file>")
        return 1

    file_path = Path(args[0])
    if not file_path.exists():
        error(f"File not found: {file_path}")
        return 1

    section(f"📝 Annotation Prompt — {file_path.name}")
    print(f"""
Paste this prompt to your AI tool:

─────────────────────────────────────────────────────────────────
Annotate the file `{file_path}` following the CodeDNA v0.7 protocol.

1. Replace or add the module docstring at the top of the file in this format:

   filename.py — <purpose ≤15 words>.

   exports: public_function(arg) -> return_type
   used_by: consumer_file.py → consumer_function
   rules:   <hard architectural constraint agents must never violate>
   agent:   <your-model-id> | <YYYY-MM-DD> | <what you implemented and noticed>

2. For any function with non-obvious domain constraints, add a Rules: docstring:

   def my_function(arg):
       \"\"\"Short description.

       Rules: What the agent MUST or MUST NOT do here.
       \"\"\"

3. Rename ambiguous local variables using the format:
   <type>_<shape>_<domain>_<origin>
   Example: list_dict_orders_from_db = get_orders()

Do NOT change any logic, only add annotations.
─────────────────────────────────────────────────────────────────
""")


def cmd_check(_, target_dir: Path):
    """Check which integrations are installed."""
    section("🔎 Installed integrations")
    print()
    for key, cfg in TOOLS.items():
        if cfg.get("prompt"):
            info(f"{cfg['emoji']}  {cfg['name']:15s}  system prompt (no file needed)")
            continue
        dest = target_dir / cfg["dest"]
        if dest.exists():
            success(f"{cfg['emoji']}  {cfg['name']:15s}  {dest}")
        else:
            warn(f"   {cfg['name']:15s}  not installed (run: codedna install {key})")


# ── Main ──────────────────────────────────────────────────────────────────────

COMMANDS = {
    "install": cmd_install,
    "validate": cmd_validate,
    "annotate": cmd_annotate,
    "check": cmd_check,
}


def main():
    print(LOGO)

    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    cmd = argv[0]
    args = argv[1:]
    target_dir = Path.cwd()

    if cmd not in COMMANDS:
        error(f"Unknown command: '{cmd}'. Run with --help for usage.")
        return 1

    return COMMANDS[cmd](args, target_dir) or 0


if __name__ == "__main__":
    sys.exit(main())
