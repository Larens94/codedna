"""wiki.py — Scaffold semantic wiki assets for CodeDNA projects.

exports: class WikiScaffoldResult | render_create_wiki_skill(project_name) -> str | render_wiki_keeper_agent(project_name) -> str | render_codedna_wiki(project_root, project_name) -> str | ensure_wiki_scaffold(project_root, dry_run) -> WikiScaffoldResult
used_by: codedna_tool/cli.py → ensure_wiki_scaffold
rules:   Never overwrite existing wiki assets; scaffold only missing files.
         `codedna-wiki.md` must present `.codedna` as Level 0 structural truth.
         Repo-local Codex skill must live at `.agents/skills/create-wiki/SKILL.md`.
         Claude Code agent must live at `.claude/agents/codedna-wiki-keeper.md` (model: haiku).
agent:   gpt-5.4 | openai | 2026-04-17 | s_20260417_001 | scaffolded repo-local create-wiki skill and codedna-wiki baseline for init
         message: "Template is intentionally compact; future pass can enrich it from .planning/codebase automatically when present."
         claude-opus-4-7 | anthropic | 2026-04-19 | s_20260419_001 | add wiki-keeper Claude Code sub-agent scaffold; skill updated to instruct spawn in CC context
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re


_SKILL_PATH = Path(".agents/skills/create-wiki/SKILL.md")
_WIKI_PATH = Path("codedna-wiki.md")
_AGENT_PATH = Path(".claude/agents/codedna-wiki-keeper.md")
_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}


@dataclass
class WikiScaffoldResult:
    """Track which wiki assets were created or already existed.

    Rules:   `created` and `existing` store repo-relative POSIX paths for stable CLI output.
    """

    created: list[str] = field(default_factory=list)
    existing: list[str] = field(default_factory=list)


def _read_project_name(project_root: Path) -> str:
    """Return project name from `.codedna` when available, else directory name."""
    path_codedna = project_root / ".codedna"
    if path_codedna.exists():
        str_content = path_codedna.read_text(encoding="utf-8", errors="replace")
        obj_match = re.search(r"^project:\s*\"?(.+?)\"?\s*$", str_content, re.MULTILINE)
        if obj_match:
            return obj_match.group(1).strip()
    return project_root.name


def _list_top_level_dirs(project_root: Path) -> list[str]:
    """List stable top-level directories for the starter wiki map."""
    list_str_dirs: list[str] = []
    for path_child in sorted(project_root.iterdir()):
        if not path_child.is_dir():
            continue
        if path_child.name in _SKIP_DIRS:
            continue
        list_str_dirs.append(path_child.name)
    return list_str_dirs[:8]


def render_wiki_keeper_agent(project_name: str) -> str:
    """Render the Claude Code sub-agent definition for isolated wiki maintenance.

    Rules:   model must be haiku for token efficiency.
             Agent scope is read-only except for codedna-wiki.md.
             Description must include spawn trigger conditions for auto-dispatch.
    """
    return f"""---
name: codedna-wiki-keeper
description: "Dedicated wiki maintenance agent for `{project_name}`. Spawn this agent when any of the following occur: (1) user asks to read, summarize, refresh, or update codedna-wiki.md; (2) codedna init or codedna wiki just ran; (3) a major refactor or architecture change landed; (4) .planning/codebase/ was regenerated. This agent reads .codedna and relevant files then updates codedna-wiki.md in isolation — keeping wiki maintenance out of the main agent context window."
model: haiku
color: green
---

You are the **CodeDNA Wiki Keeper** for `{project_name}` — a focused, low-token specialist that reads and maintains `codedna-wiki.md` as the semantic companion to `.codedna` (Level 0).

You are NOT a general coding assistant. You do exactly one thing: keep the semantic wiki accurate, compact, and useful for agents that come after you.

---

## Your Scope

You touch exactly **one file per task**:

- `codedna-wiki.md` — read it, update it, or summarize it

You may **read** (never write) these files to gather context:

- `.codedna` — Level 0 structural truth (always read this first)
- `.planning/codebase/*.md` — intermediate codebase map (read when available)
- `README.md`, `SPEC.md`, `QUICKSTART.md`, `AGENTS.md` — when directly relevant
- Module docstrings (first 10–15 lines only) of files mentioned in `.codedna`

You do **not** modify source files, annotations, or any file other than `codedna-wiki.md`.

---

## Read workflow (when asked to summarize or explain the codebase)

1. Read `.codedna` — extract project identity, packages, last 2–3 session entries
2. Read `codedna-wiki.md` — this is your primary answer source
3. If the wiki is missing or stale, run the refresh workflow first
4. Return a compact, structured summary (≤400 words unless asked for more)

---

## Refresh workflow (when asked to update the wiki)

1. Read `.codedna`
2. Read `.planning/codebase/*.md` if the directory exists — skim for structural changes
3. Read only the module docstrings of files that changed since the last wiki update
4. Update `codedna-wiki.md`:
   - Keep the existing structure; patch only the sections that are stale
   - Do not rewrite sections that are still accurate
   - Update `Last refreshed:` date at the top
   - Add or update the hotspot and drift sections if new issues were found
5. Report back: what changed, what sections were updated, what you left untouched

---

## Wiki structure to preserve

The wiki must always contain these sections (add if missing):

- **Identity** — what this project is and does
- **How this wiki relates to L0** — `.codedna` is authoritative; wiki is semantic
- **Semantic topology** — subsystems, boundaries, key files
- **Operational workflows** — setup, annotation, maintenance, release
- **Testing and validation model** — what is covered, what is not
- **Hotspots and likely drift** — monolithic files, fragile integrations, research noise
- **Refresh protocol** — when and how to update this file

---

## Output rules

- Keep `codedna-wiki.md` compact (under 250 lines)
- Semantic synthesis over file inventories — explain WHY, not just WHAT
- If you find drift between `.codedna` and the wiki, note it explicitly in Hotspots
- If `.codedna` and the wiki disagree on structure, trust `.codedna` and update the wiki
- End your response to the caller with a one-paragraph summary of what changed

---

## Token discipline

You run as a lightweight model. Apply these constraints:

- Read module docstrings only (first 10–15 lines) unless a full read is strictly necessary
- Prefer targeted reads (offset + limit) over full file reads
- Do not load the entire codebase — load what `.codedna` tells you is relevant
- If `.planning/codebase/` docs exist, prefer reading them over re-reading source files
"""


def render_create_wiki_skill(project_name: str) -> str:
    """Render repo-local skill instructions for semantic wiki upkeep across runtimes.

    Rules:   Output must stay markdown-only and reference `.codedna` as L0.
             Claude Code section must instruct sub-agent spawn (codedna-wiki-keeper).
             Direct workflow section must cover Codex/OpenCode fallback.
    """
    return f"""---
name: create-wiki
description: Maintain `codedna-wiki.md` as the semantic companion to `.codedna` (L0) for `{project_name}`.
model: haiku
preferred-model: haiku
model-hint: "Use the smallest available model. This task is read-heavy markdown synthesis — Haiku or equivalent (GPT-4o-mini, Gemini Flash, Qwen-turbo). Never use Opus/o3/Pro for wiki-only tasks."
---

# Create Wiki

Use this skill when the user asks to create, refresh, repair, or extend the project wiki, or when the codebase changed enough that the semantic map is stale.

## Model preference

This skill runs on a **lightweight model**. Match to your runtime:

| Runtime | Preferred model |
|---------|----------------|
| Claude Code | `haiku` (enforced via `.claude/agents/codedna-wiki-keeper.md`) |
| Codex | `o4-mini` or smallest available |
| OpenCode | smallest configured model |
| Gemini | `gemini-flash` |
| Other | any fast/cheap tier |

Wiki maintenance is read-heavy markdown synthesis — no code generation, no reasoning-intensive tasks. Saving tokens here is free performance.

## Core idea

This skill follows the `llm-wiki` pattern from Karpathy's note:

- persistent compiled knowledge beats rebuilding the same understanding every session
- the wiki is not a dump of files; it is the semantic model of the codebase

For CodeDNA projects:

- `.codedna` is Level 0 structural truth
- source file docstrings are local truth
- `codedna-wiki.md` is the semantic synthesis layer

---

## Sub-agent dispatch (Claude Code)

**In Claude Code: do not perform wiki work inline.** Spawn the dedicated wiki-keeper sub-agent to isolate all wiki reads from your context window:

Use the Agent tool with `subagent_type="codedna-wiki-keeper"` and pass the task as a clear prompt, for example:

- `"Refresh codedna-wiki.md — a major refactor just landed"`
- `"Read codedna-wiki.md and summarize the architecture for onboarding"`
- `"Update the hotspots section — we just added a new subsystem"`

The wiki-keeper runs on Haiku, keeps wiki context isolated, and returns a compact summary.

If `.claude/agents/codedna-wiki-keeper.md` is missing, run `codedna wiki` first to scaffold it.

---

## Direct workflow (Codex, OpenCode, other runtimes)

When sub-agent spawning is not available, perform wiki work directly.

### Inputs

Read in this order:

1. `.codedna`
2. `.planning/codebase/*.md` when available
3. `README.md`, `SPEC.md`, `QUICKSTART.md`, `AGENTS.md` when relevant
4. only the module docstrings or focused files needed for the current refresh

### Output

Update exactly one semantic artifact:

- `codedna-wiki.md`

### Rules

- Treat `.codedna` as authoritative for package structure and recent sessions
- Do not invent structural relationships that contradict `.codedna`
- Prefer semantic synthesis over raw inventories
- Preserve architecture, hotspots, contradictions, and refresh guidance
- If `.planning/codebase/` exists, use it as support context but keep `codedna-wiki.md` shorter and more decisive
- Call out drift explicitly when the wiki and L0 no longer match

### Recommended structure

- Project identity
- Relationship to L0 (`.codedna`)
- Semantic topology
- Operational workflows
- Testing and validation model
- Hotspots and likely drift
- Refresh protocol

### Refresh workflow

1. Re-read `.codedna`
2. Re-read `.planning/codebase/*.md` if present
3. Inspect only the files needed for the affected semantic sections
4. Update `codedna-wiki.md`
5. Keep the wiki compact and high-signal
"""


def render_codedna_wiki(project_root: Path, project_name: str) -> str:
    """Render the starter semantic wiki that complements `.codedna`.

    Rules:   Keep the wiki generic enough for any project root while making L0 explicit.
    """
    list_str_dirs = _list_top_level_dirs(project_root)
    list_str_topology = "\n".join(f"- `{name}/`" for name in list_str_dirs) or "- Add major subsystem directories here"

    return f"""# CodeDNA Wiki

Last refreshed: 2026-04-19
Primary structural source: `.codedna`
Repo-local wiki skill: `.agents/skills/create-wiki/SKILL.md`
Wiki keeper agent: `.claude/agents/codedna-wiki-keeper.md`

## Identity

`{project_name}` uses CodeDNA as its in-source coordination protocol.

This file is the semantic companion to `.codedna`:

- `.codedna` is Level 0 structural truth
- `codedna-wiki.md` is the semantic map agents use to preserve architectural understanding over time

## Semantic topology

Starter top-level view:

{list_str_topology}

Use this section to explain what each subsystem is for, how the boundaries work, and where agents should start reading.

## How this complements L0

Use `.codedna` for:

- project/package structure
- key files
- recent session log

Use this wiki for:

- architecture mental model
- workflows
- hotspots and drift
- contradictions or open questions

If this file disagrees with `.codedna`, refresh this file and trust `.codedna` first.

## Operational workflows

Track the workflows that matter most to the project:

- setup and install
- main runtime path
- test path
- release or validation path

## Hotspots and likely drift

Document:

- monolithic files
- fragile integrations
- generated areas to avoid
- places where structure and intent often diverge

## Refresh protocol

Refresh this file when:

- `.codedna` changes meaningfully
- `.planning/codebase/` is generated or refreshed
- major refactors land
- new subsystems or workflows appear

When refreshing (Claude Code):

1. spawn `codedna-wiki-keeper` sub-agent via Agent tool
2. pass task prompt describing what changed
3. keeper returns summary of updates

When refreshing (other runtimes):

1. read `.codedna`
2. read `.planning/codebase/*.md` if present
3. inspect only the focused files needed for the semantic update
4. keep this file shorter and more explanatory than the codebase map
"""


def ensure_wiki_scaffold(project_root: Path, dry_run: bool = False) -> WikiScaffoldResult:
    """Create repo-local wiki assets if they do not already exist.

    Rules:   `project_root` is the repository root for the target project.
             Dry-run mode must report missing files without writing them.
             _AGENT_PATH is Claude Code specific but harmless on other runtimes.
    """
    obj_result = WikiScaffoldResult()
    str_project_name = _read_project_name(project_root)
    dict_path_content = {
        _SKILL_PATH: render_create_wiki_skill(str_project_name),
        _WIKI_PATH: render_codedna_wiki(project_root, str_project_name),
        _AGENT_PATH: render_wiki_keeper_agent(str_project_name),
    }

    for path_rel, str_content in dict_path_content.items():
        path_abs = project_root / path_rel
        str_rel = path_rel.as_posix()
        if path_abs.exists():
            obj_result.existing.append(str_rel)
            continue
        obj_result.created.append(str_rel)
        if dry_run:
            continue
        path_abs.parent.mkdir(parents=True, exist_ok=True)
        path_abs.write_text(str_content, encoding="utf-8")

    return obj_result
