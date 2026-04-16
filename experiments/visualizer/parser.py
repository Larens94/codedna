"""parser.py — Extract CodeDNA annotations and session events from live run directories.

exports: class AgentEntry | class FunctionAnnotation | class FileAnnotation | class SessionEvent | class ConditionSnapshot | class RunSnapshot | _RE_EXPORTS | _RE_USED_BY | _RE_RULES | _RE_AGENT | _RE_MESSAGE_INLINE | _RE_FUNC_DEF | _RE_FN_RULES | _RE_FN_MESSAGE | parse_file(path, base_dir) | _CONDITION_LABELS | scan_condition(condition_dir, condition) | scan_run(run_dir) | find_latest_run(runs_root)
used_by: none
rules:   read-only — never writes or modifies any file;
parse only the first 40 lines of each Python file for the module header;
full file body is scanned only for function-level Rules:/message: docstrings;
polling interval is the caller's responsibility
agent:   claude-sonnet-4-6 | anthropic | 2026-03-29 | s_20260329_002 | Initial design
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AgentEntry:
    """One agent: line from a module docstring."""
    name: str
    date: str
    note: str
    message: Optional[str] = None   # inline message: sub-field if present


@dataclass
class FunctionAnnotation:
    """Rules:/message: extracted from a function docstring."""
    function_name: str
    rules: Optional[str] = None
    message: Optional[str] = None


@dataclass
class FileAnnotation:
    """All CodeDNA fields extracted from a single Python file."""
    path: Path
    relative_path: str
    exports: Optional[str] = None
    used_by: Optional[str] = None
    rules: Optional[str] = None
    agent_entries: list[AgentEntry] = field(default_factory=list)
    function_annotations: list[FunctionAnnotation] = field(default_factory=list)
    has_annotation_header: bool = False
    line_count: int = 0
    mtime: float = 0.0


@dataclass
class SessionEvent:
    """One entry from a session interactions.json or decisions.json log."""
    timestamp: str
    agent: str
    event_type: str
    summary: str


@dataclass
class ConditionSnapshot:
    """Full snapshot of one condition directory at a point in time."""
    condition: str           # "a" or "b"
    label: str               # "Annotation Protocol" or "Standard Practices"
    root: Path
    files: list[FileAnnotation] = field(default_factory=list)
    events: list[SessionEvent] = field(default_factory=list)
    scanned_at: float = field(default_factory=time.time)

    # Derived stats
    @property
    def py_file_count(self) -> int:
        return len(self.files)

    @property
    def total_loc(self) -> int:
        return sum(f.line_count for f in self.files)

    @property
    def annotated_count(self) -> int:
        return sum(1 for f in self.files if f.has_annotation_header)

    @property
    def coverage_pct(self) -> float:
        n = self.py_file_count
        return round(100 * self.annotated_count / n, 1) if n else 0.0

    @property
    def all_agent_entries(self) -> list[AgentEntry]:
        entries: list[AgentEntry] = []
        for f in self.files:
            entries.extend(f.agent_entries)
        return entries

    @property
    def all_messages(self) -> list[tuple[str, AgentEntry]]:
        """Return (file_relative_path, AgentEntry) for every entry that has a message."""
        out = []
        for f in self.files:
            for ae in f.agent_entries:
                if ae.message:
                    out.append((f.relative_path, ae))
            for fa in f.function_annotations:
                if fa.message:
                    out.append((f"{f.relative_path}::{fa.function_name}", AgentEntry(
                        name="(fn)", date="", note=fa.function_name, message=fa.message
                    )))
        return out

    @property
    def unique_agents(self) -> list[str]:
        seen: set[str] = set()
        return [
            ae.name for ae in self.all_agent_entries
            if ae.name not in seen and not seen.add(ae.name)  # type: ignore[func-returns-value]
        ]


@dataclass
class RunSnapshot:
    """Snapshot of an entire run (both conditions)."""
    run_id: str
    run_dir: Path
    conditions: dict[str, ConditionSnapshot] = field(default_factory=dict)
    scanned_at: float = field(default_factory=time.time)


# ─────────────────────────────────────────────────────────────────────────────
# REGEX PATTERNS
# ─────────────────────────────────────────────────────────────────────────────

_RE_EXPORTS  = re.compile(r"^\s*exports:\s*(.+)", re.MULTILINE)
_RE_USED_BY  = re.compile(r"^\s*used_by:\s*(.+)", re.MULTILINE)
_RE_RULES    = re.compile(r"^\s*rules:\s*(.+)", re.MULTILINE)
_RE_AGENT    = re.compile(
    r"^\s*agent:\s*([^\|]+?)\s*\|\s*([^\|]+?)\s*\|\s*(.+)",
    re.MULTILINE,
)
_RE_MESSAGE_INLINE = re.compile(
    r"message:\s*[\"']?(.+?)[\"']?\s*$",
    re.MULTILINE,
)
_RE_FUNC_DEF   = re.compile(r"^def\s+(\w+)\s*\(", re.MULTILINE)
_RE_FN_RULES   = re.compile(r"Rules:\s*(.+?)(?=\n\s*\w|\Z)", re.DOTALL)
_RE_FN_MESSAGE = re.compile(r"message:\s*(.+?)(?=\n\s*\w|\Z)", re.DOTALL)


# ─────────────────────────────────────────────────────────────────────────────
# FILE PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_file(path: Path, base_dir: Path | None = None) -> FileAnnotation:
    """Parse a Python file and extract all CodeDNA annotations.

    Rules:   read-only; silently returns empty FileAnnotation on any IO error.
    """
    rel = str(path.relative_to(base_dir)) if base_dir and path.is_relative_to(base_dir) else path.name

    ann = FileAnnotation(path=path, relative_path=rel)
    try:
        ann.mtime = path.stat().st_mtime
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ann

    lines = text.splitlines()
    ann.line_count = len(lines)

    # ── Module-level header (first 40 lines) ─────────────────────────────────
    header = "\n".join(lines[:40])

    m = _RE_EXPORTS.search(header)
    if m:
        ann.exports = m.group(1).strip()
        ann.has_annotation_header = True

    m = _RE_USED_BY.search(header)
    if m:
        ann.used_by = m.group(1).strip()

    m = _RE_RULES.search(header)
    if m:
        ann.rules = m.group(1).strip()

    for m in _RE_AGENT.finditer(header):
        agent_name = m.group(1).strip()
        agent_date = m.group(2).strip()
        agent_note = m.group(3).strip()

        # Check next line for message: sub-field
        end_pos = m.end()
        rest = header[end_pos:end_pos + 200]
        msg_m = _RE_MESSAGE_INLINE.match(rest.lstrip("\n"))
        agent_msg = msg_m.group(1).strip() if msg_m else None

        ann.agent_entries.append(AgentEntry(
            name=agent_name,
            date=agent_date,
            note=agent_note,
            message=agent_msg,
        ))

    # ── Function-level Rules:/message: ───────────────────────────────────────
    for fn_m in _RE_FUNC_DEF.finditer(text):
        fn_name = fn_m.group(1)
        # Grab the next 300 chars after the def line for the docstring
        snippet = text[fn_m.end(): fn_m.end() + 400]
        fa = FunctionAnnotation(function_name=fn_name)
        r = _RE_FN_RULES.search(snippet)
        if r:
            fa.rules = r.group(1).strip()
        msg = _RE_FN_MESSAGE.search(snippet)
        if msg:
            fa.message = msg.group(1).strip()
        if fa.rules or fa.message:
            ann.function_annotations.append(fa)

    return ann


# ─────────────────────────────────────────────────────────────────────────────
# SESSION LOG READER
# ─────────────────────────────────────────────────────────────────────────────

def _load_session_events(condition_dir: Path) -> list[SessionEvent]:
    """Read interactions.json / decisions.json from session_logs/ subdirs."""
    events: list[SessionEvent] = []
    session_root = condition_dir / "session_logs"
    if not session_root.exists():
        return events

    for log_file in sorted(session_root.rglob("interactions.json")) + \
                    sorted(session_root.rglob("decisions.json")):
        try:
            data = json.loads(log_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if not isinstance(data, list):
            continue

        for entry in data:
            agent  = entry.get("agent", entry.get("type", "?"))
            etype  = entry.get("type", entry.get("decision_type", ""))
            ts     = entry.get("timestamp", "")
            content = entry.get("content", entry.get("details", {}))

            if isinstance(content, dict):
                summary = (
                    content.get("description")
                    or content.get("result")
                    or content.get("error")
                    or str(content)[:120]
                )
            else:
                summary = str(content)[:120]

            events.append(SessionEvent(
                timestamp=ts,
                agent=agent,
                event_type=etype,
                summary=str(summary)[:120],
            ))

    return events


# ─────────────────────────────────────────────────────────────────────────────
# CONDITION SCANNER
# ─────────────────────────────────────────────────────────────────────────────

_CONDITION_LABELS = {"a": "Annotation Protocol", "b": "Standard Practices"}


def scan_condition(condition_dir: Path, condition: str) -> ConditionSnapshot:
    """Scan one condition directory and return a full snapshot."""
    label = _CONDITION_LABELS.get(condition, condition)
    snap = ConditionSnapshot(condition=condition, label=label, root=condition_dir)

    if not condition_dir.exists():
        return snap

    for py_file in sorted(condition_dir.rglob("*.py")):
        snap.files.append(parse_file(py_file, base_dir=condition_dir))

    snap.events = _load_session_events(condition_dir)
    snap.scanned_at = time.time()
    return snap


# ─────────────────────────────────────────────────────────────────────────────
# RUN SCANNER
# ─────────────────────────────────────────────────────────────────────────────

def scan_run(run_dir: Path) -> RunSnapshot:
    """Scan a full run directory (both conditions) and return a RunSnapshot."""
    snap = RunSnapshot(run_id=run_dir.name, run_dir=run_dir)

    for condition in ("a", "b"):
        cond_dir = run_dir / condition
        snap.conditions[condition] = scan_condition(cond_dir, condition)

    snap.scanned_at = time.time()
    return snap


def find_latest_run(runs_root: Path) -> Path | None:
    """Return the most recently created run directory, or None."""
    if not runs_root.exists():
        return None
    dirs = sorted(
        (d for d in runs_root.iterdir() if d.is_dir()),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    return dirs[0] if dirs else None
