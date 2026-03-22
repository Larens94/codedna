"""
tools/agent_history.py — Reads AI agent session history from git trailers.

exports: main() → prints agent timeline, messages, file maps
used_by: none — standalone CLI tool
rules:   reads git log only — never modifies repo state.
         reasoning is NOT available in git trailers (not captured at v0.7/v0.8).
         AI-Visited: lists files read, not the reasoning behind navigation choices.
agent:   claude-sonnet-4-6 | anthropic | 2026-03-20 | s_20260320_002 | created
         message: "reasoning data missing — see --missing-data flag for full picture
                  of what would make this tool more useful for model training"

Usage:
    python tools/agent_history.py                   # full timeline
    python tools/agent_history.py --sessions        # one line per session
    python tools/agent_history.py --messages        # only sessions with AI-Message:
    python tools/agent_history.py --file README.md  # sessions that touched a file
    python tools/agent_history.py --model claude    # filter by model
    python tools/agent_history.py --missing-data    # show what data is NOT captured
"""

import subprocess
import sys
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

# ── Colours ──────────────────────────────────────────────────────────────────
R = "\033[31m"
G = "\033[32m"
Y = "\033[33m"
B = "\033[34m"
M = "\033[35m"
C = "\033[36m"
W = "\033[1m"
DIM = "\033[2m"
D = "\033[0m"

PROVIDER_COLOURS = {
    "anthropic": C,
    "google": G,
    "openai": B,
    "deepseek": M,
    "mistral": Y,
}


@dataclass
class AgentSession:
    commit_hash: str
    commit_date: str
    commit_title: str
    agent: Optional[str] = None
    provider: Optional[str] = None
    session_id: Optional[str] = None
    visited: list[str] = field(default_factory=list)
    message: Optional[str] = None
    changed: list[str] = field(default_factory=list)  # from git diff


def _run_git(args: list[str]) -> str:
    result = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=_repo_root())
    return result.stdout.strip()


def _repo_root() -> str:
    return subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()


def _parse_commits() -> list[AgentSession]:
    """Rules: parse only commits with at least one AI-* trailer."""
    raw = _run_git(
        [
            "log",
            "--format=%H%n%ai%n%s%n%b%n<<<END>>>",
        ]
    )

    list_session_parsed = []
    for str_block_commit in raw.split("<<<END>>>"):
        str_block_commit = str_block_commit.strip()
        if not str_block_commit or "AI-Agent:" not in str_block_commit:
            continue

        list_line_block = str_block_commit.splitlines()
        str_hash = list_line_block[0].strip() if len(list_line_block) > 0 else ""
        str_date = list_line_block[1].strip()[:10] if len(list_line_block) > 1 else ""
        str_title = list_line_block[2].strip() if len(list_line_block) > 2 else ""
        str_body = "\n".join(list_line_block[3:])

        session = AgentSession(
            commit_hash=str_hash,
            commit_date=str_date,
            commit_title=str_title,
        )

        for str_line in str_body.splitlines():
            str_line = str_line.strip()
            if str_line.startswith("AI-Agent:"):
                session.agent = str_line.split(":", 1)[1].strip()
            elif str_line.startswith("AI-Provider:"):
                session.provider = str_line.split(":", 1)[1].strip()
            elif str_line.startswith("AI-Session:"):
                session.session_id = str_line.split(":", 1)[1].strip()
            elif str_line.startswith("AI-Visited:"):
                str_visited = str_line.split(":", 1)[1].strip()
                session.visited = [f.strip() for f in str_visited.split(",") if f.strip()]
            elif str_line.startswith("AI-Message:"):
                session.message = str_line.split(":", 1)[1].strip()

        # files changed — from git diff-tree
        str_diff = _run_git(["diff-tree", "--no-commit-id", "-r", "--name-only", str_hash])
        session.changed = [f.strip() for f in str_diff.splitlines() if f.strip()]

        list_session_parsed.append(session)

    return list_session_parsed


def _colour_for(str_provider: Optional[str]) -> str:
    if not str_provider:
        return DIM
    return PROVIDER_COLOURS.get(str_provider.lower(), DIM)


def _bar(int_n: int, int_max: int, int_width: int = 20) -> str:
    int_filled = int(int_width * int_n / int_max) if int_max else 0
    return "█" * int_filled + "░" * (int_width - int_filled)


# ── Views ─────────────────────────────────────────────────────────────────────


def view_timeline(list_session: list[AgentSession]) -> None:
    print(f"\n{W}{'─'*70}{D}")
    print(f"{W}  🧬 CodeDNA — Agent Session Timeline{D}")
    print(f"{W}{'─'*70}{D}\n")

    for session in reversed(list_session):
        str_col = _colour_for(session.provider)
        str_provider_label = f"[{session.provider}]" if session.provider else ""
        print(
            f"  {DIM}{session.commit_date}{D}  "
            f"{str_col}{W}{session.agent or '?'}{D}  "
            f"{DIM}{str_provider_label}{D}  "
            f"{DIM}{session.session_id or ''}{D}"
        )
        print(f"  {DIM}{'─'*2}{D} {session.commit_title}")

        if session.visited:
            str_visited_label = ", ".join(session.visited[:4])
            str_more = f" +{len(session.visited)-4} more" if len(session.visited) > 4 else ""
            print(f"     {DIM}read:    {str_visited_label}{str_more}{D}")

        if session.changed:
            str_changed_label = ", ".join(session.changed[:4])
            str_more = f" +{len(session.changed)-4} more" if len(session.changed) > 4 else ""
            print(f"     {Y}changed: {str_changed_label}{str_more}{D}")

        if session.message:
            print(f"     {C}message: {session.message}{D}")

        print()


def view_messages(list_session: list[AgentSession]) -> None:
    list_with_message = [s for s in list_session if s.message]
    if not list_with_message:
        print(f"{DIM}No AI-Message: entries found.{D}")
        return

    print(f"\n{W}  🗨  Agent Messages{D}\n")
    for session in reversed(list_with_message):
        str_col = _colour_for(session.provider)
        print(f"  {DIM}{session.commit_date}{D}  {str_col}{W}{session.agent}{D}")
        print(f"  {C}→ {session.message}{D}")
        print()


def view_file_map(list_session: list[AgentSession]) -> None:
    dict_file_visited: dict[str, list[str]] = defaultdict(list)
    dict_file_changed: dict[str, list[str]] = defaultdict(list)

    for session in list_session:
        str_label = f"{session.agent} ({session.commit_date})"
        for str_file in session.visited:
            dict_file_visited[str_file].append(str_label)
        for str_file in session.changed:
            dict_file_changed[str_file].append(str_label)

    set_all_files = set(dict_file_visited.keys()) | set(dict_file_changed.keys())
    int_max_visits = max((len(v) for v in dict_file_visited.values()), default=1)

    print(f"\n{W}  📁 File Map — visits / changes per file{D}\n")
    for str_file in sorted(set_all_files):
        int_visits = len(dict_file_visited.get(str_file, []))
        int_changes = len(dict_file_changed.get(str_file, []))
        str_bar = _bar(int_visits, int_max_visits, 16)
        print(f"  {str_bar}  {W}{str_file}{D}" f"  {DIM}read:{int_visits}  changed:{int_changes}{D}")
    print()


def view_model_stats(list_session: list[AgentSession]) -> None:
    dict_model_count: dict[str, int] = defaultdict(int)
    dict_model_changed: dict[str, int] = defaultdict(int)
    dict_model_visited: dict[str, int] = defaultdict(int)

    for session in list_session:
        str_key = f"{session.agent} ({session.provider})"
        dict_model_count[str_key] += 1
        dict_model_changed[str_key] += len(session.changed)
        dict_model_visited[str_key] += len(session.visited)

    int_max = max(dict_model_count.values(), default=1)
    print(f"\n{W}  📊 Model Distribution{D}\n")
    for str_model, int_count in sorted(dict_model_count.items(), key=lambda x: -x[1]):
        str_bar = _bar(int_count, int_max, 20)
        int_v = dict_model_visited[str_model]
        int_c = dict_model_changed[str_model]
        float_eff = round(int_c / int_v, 2) if int_v else 0
        print(
            f"  {str_bar}  {int_count} sessions  {W}{str_model}{D}"
            f"  {DIM}efficiency: {float_eff} (changed/visited){D}"
        )
    print()


def view_missing_data() -> None:
    print(f"""
{W}  ⚠  Data NOT captured in git trailers — what's missing{D}

  {R}NOT AVAILABLE{D}
  ├─ Agent reasoning / chain-of-thought
  │    Why did the agent navigate to file X instead of Y?
  │    What hypothesis did it form before reading a file?
  │    What did it consider and reject?
  │
  ├─ Tool call sequence (intra-session)
  │    Order in which files were read within the session.
  │    AI-Visited: is a flat list — no sequence, no timestamps.
  │
  ├─ Confidence signals
  │    Did the agent hesitate? Did it read a file multiple times?
  │    Were there backtracking patterns?
  │
  └─ Errors and self-corrections
       Did the agent start in the wrong direction and correct itself?
       These failure traces are the most valuable for training.

  {G}AVAILABLE{D}
  ├─ AI-Agent, AI-Provider, AI-Session, AI-Date    → who and when
  ├─ AI-Visited                                    → navigation trace (unordered)
  ├─ git diff                                      → exactly what changed
  ├─ AI-Message                                    → agent's own summary and open questions
  └─ Commit title + body                           → task description

  {Y}TRAINING DATA POTENTIAL{D}
  ├─ (available now)  correct navigation pairs: task description + visited files + changed files
  ├─ (available now)  message: lifecycle: observation → rules: promotion or dismissal
  ├─ (needs capture)  reasoning traces from models that expose chain-of-thought
  └─ (needs capture)  per-tool-call log with timestamps (requires agent instrumentation)

  To capture reasoning: instrument the agent runner (run_agent_multi.py) to log
  the full tool call sequence + model thinking per session → store as session_id.json
  alongside git commit. The session_id trailer is the link.
""")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="CodeDNA — AI agent session history reader")
    parser.add_argument("--sessions", action="store_true", help="one line per session")
    parser.add_argument("--messages", action="store_true", help="only sessions with AI-Message:")
    parser.add_argument("--file-map", action="store_true", help="file visit/change heatmap")
    parser.add_argument("--stats", action="store_true", help="model distribution stats")
    parser.add_argument("--missing-data", action="store_true", help="show what data is NOT captured")
    parser.add_argument("--file", type=str, help="filter: sessions touching FILE")
    parser.add_argument("--model", type=str, help="filter: sessions by MODEL substring")
    args = parser.parse_args()

    if args.missing_data:
        view_missing_data()
        return

    list_session_all = _parse_commits()

    if args.file:
        list_session_all = [s for s in list_session_all if any(args.file in f for f in s.visited + s.changed)]

    if args.model:
        list_session_all = [s for s in list_session_all if s.agent and args.model.lower() in s.agent.lower()]

    if not list_session_all:
        print(f"{DIM}No AI agent sessions found matching your filters.{D}")
        return

    if args.messages:
        view_messages(list_session_all)
    elif args.file_map:
        view_file_map(list_session_all)
    elif args.stats:
        view_model_stats(list_session_all)
    else:
        # default: full timeline + stats
        view_timeline(list_session_all)
        view_model_stats(list_session_all)
        view_file_map(list_session_all)


if __name__ == "__main__":
    main()
