"""manifest_store.py — Concurrent, lossless persistence for the .codedna manifest.

exports: DEFAULT_MAX_AGENT_SESSIONS | _TOP_LEVEL_KEY_RE | _SESSION_START_RE | manifest_lock(path) | read_max_agent_sessions(content) | parse_agent_sessions(content) | replace_agent_sessions(content, sessions, limit) | replace_top_level_section(content, generated, key) | atomic_write_text(path, content) | mutate_manifest(path, transform) | append_session(path, session) | prune_sessions(path, limit)
used_by: codedna_tool/cli.py → append_session, atomic_write_text, mutate_manifest, parse_agent_sessions, prune_sessions, replace_agent_sessions, replace_top_level_section
         tests/test_manifest_store.py → append_session, atomic_write_text, parse_agent_sessions, prune_sessions, read_max_agent_sessions, replace_agent_sessions, replace_top_level_section
related: codedna_tool/cli.py — generates structural manifest sections
rules:   Every .codedna mutation MUST hold the sibling .codedna.lock exclusively.
Writes MUST use a same-directory temporary file, fsync, os.replace, and preserve mode bits.
Session retention defaults to five and keeps the newest entries exactly.
agent:   gpt-5 | openai | 2026-08-20 | s_20260820_sessions | added lossless locked manifest storage and canonical session writer
message: "The text-preserving strategy intentionally rewrites only agent_sessions."
gpt-5 | openai | 2026-08-20 | s_20260820_hardening | expose atomic writer for source rewrites and install-time manifest creation
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

try:  # POSIX
    import fcntl
except ImportError:  # Windows
    fcntl = None
    import msvcrt

DEFAULT_MAX_AGENT_SESSIONS = 5
_TOP_LEVEL_KEY_RE = re.compile(r"^[A-Za-z_][\w-]*\s*:", re.MULTILINE)
_SESSION_START_RE = re.compile(r"^  -\s+agent\s*:", re.MULTILINE)


@contextmanager
def manifest_lock(path: Path) -> Iterator[None]:
    """Hold the manifest's inter-process exclusive lock.

    Rules:   The lock file is persistent and MUST NOT be deleted after release; unlinking
             it permits two processes to lock different inodes. All writers share this lock.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    with lock_path.open("a+b") as lock_file:
        if fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        else:
            # Rules: msvcrt.locking locks a byte range, so the persistent lock
            # file must contain at least one byte on Windows.
            if lock_file.tell() == 0:
                lock_file.write(b"\0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            else:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)


def read_max_agent_sessions(content: str) -> int:
    """Return configured retention, falling back to five.

    Rules:   Invalid, zero, and negative legacy values use the safe default of five.
    """
    match = re.search(r"^max_agent_sessions:\s*([^#\n]+)", content, re.MULTILINE)
    if not match:
        return DEFAULT_MAX_AGENT_SESSIONS
    try:
        value = int(match.group(1).strip().strip('"\''))
    except ValueError:
        return DEFAULT_MAX_AGENT_SESSIONS
    return value if value > 0 else DEFAULT_MAX_AGENT_SESSIONS


def _session_bounds(content: str) -> tuple[int, int] | None:
    match = re.search(r"^agent_sessions\s*:[^\n]*(?:\n|$)", content, re.MULTILINE)
    if not match:
        return None
    end = len(content)
    next_key = _TOP_LEVEL_KEY_RE.search(content, match.end())
    if next_key:
        end = next_key.start()
    return match.start(), end


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        if value[0] == '"':
            try:
                return str(json.loads(value))
            except (ValueError, TypeError):
                pass
        return value[1:-1].replace("''", "'")
    return value


def parse_agent_sessions(content: str) -> list[dict[str, object]]:
    """Parse legacy and canonical session entries without requiring a YAML package.

    Rules:   Accept quoted scalars, flow/block arrays, and multiline message blocks.
             Unknown per-session fields are retained as strings or string lists.
    """
    bounds = _session_bounds(content)
    if not bounds:
        return []
    block = content[bounds[0]:bounds[1]]
    starts = list(_SESSION_START_RE.finditer(block))
    sessions: list[dict[str, object]] = []
    for index, start in enumerate(starts):
        raw = block[start.start(): starts[index + 1].start() if index + 1 < len(starts) else len(block)]
        session: dict[str, object] = {}
        current_key = ""
        block_style = False
        for line in raw.splitlines():
            # Rules: field indentation is exact. Block-scalar prose may itself
            # contain text such as `first: ...` at six spaces and must remain
            # part of message rather than becoming an accidental YAML field.
            field = re.match(r"^(?:  - |    )([\w-]+):\s*(.*)$", line)
            if field:
                current_key, value = field.group(1), field.group(2).strip()
                block_style = value in ("|", ">", "|-", ">-")
                if block_style:
                    session[current_key] = ""
                elif value.startswith("[") and value.endswith("]"):
                    try:
                        parsed = json.loads(value)
                    except ValueError:
                        parsed = [_unquote(item) for item in value[1:-1].split(",") if item.strip()]
                    session[current_key] = parsed
                else:
                    session[current_key] = _unquote(value)
                continue
            # A block-list marker requires whitespace after `-`; prose lines
            # beginning with CLI flags such as `--extensions` are not arrays.
            item = re.match(r"^      -\s+(.*)$", line)
            if item and current_key:
                existing = session.get(current_key)
                if not isinstance(existing, list):
                    existing = []
                    session[current_key] = existing
                existing.append(_unquote(item.group(1)))
            elif block_style and current_key and re.match(r"^      ", line):
                text = line[6:]
                previous = str(session[current_key])
                session[current_key] = (previous + ("\n" if previous else "") + text)
        if session.get("agent"):
            sessions.append(session)
    return sessions


def _dump_session(session: dict[str, object]) -> list[str]:
    preferred = ("agent", "provider", "date", "session_id", "task", "changed", "visited", "message")
    keys = [key for key in preferred if key in session]
    keys.extend(key for key in session if key not in keys)
    lines: list[str] = []
    for index, key in enumerate(keys):
        prefix = "  - " if index == 0 else "    "
        value = session[key]
        # JSON strings and arrays are valid YAML and safely preserve quotes/backslashes/newlines.
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        lines.append(f"{prefix}{key}: {encoded}")
    return lines


def replace_agent_sessions(content: str, sessions: list[dict[str, object]], limit: int | None = None) -> str:
    """Replace only agent_sessions while preserving every other byte-range.

    Rules:   Retention keeps exactly the newest N entries. A missing key is appended;
             top-level keys and comments after an existing session block remain in place.
    """
    effective_limit = limit if limit is not None else read_max_agent_sessions(content)
    effective_limit = effective_limit if effective_limit > 0 else DEFAULT_MAX_AGENT_SESSIONS
    kept = sessions[-effective_limit:]
    lines = ["agent_sessions:"]
    if kept:
        for session in kept:
            lines.extend(_dump_session(session))
    else:
        lines[0] = "agent_sessions: []"
    replacement = "\n".join(lines) + "\n"
    bounds = _session_bounds(content)
    if bounds:
        before, after = content[:bounds[0]], content[bounds[1]:]
        return before + replacement + after.lstrip("\n")
    separator = "" if not content or content.endswith("\n\n") else ("\n" if content.endswith("\n") else "\n\n")
    return content + separator + replacement


def replace_top_level_section(content: str, generated: str, key: str) -> str:
    """Replace one top-level YAML section from generated content.

    Rules:   Only the named section may change; comments, custom metadata, ordering,
             and keys before or after it must remain byte-for-byte unchanged.
    """
    pattern = re.compile(rf"^{re.escape(key)}\s*:[^\n]*(?:\n|$)", re.MULTILINE)

    def bounds(text: str) -> tuple[int, int] | None:
        start = pattern.search(text)
        if not start:
            return None
        following = _TOP_LEVEL_KEY_RE.search(text, start.end())
        return start.start(), following.start() if following else len(text)

    generated_bounds = bounds(generated)
    if not generated_bounds:
        return content
    section = generated[generated_bounds[0]:generated_bounds[1]].rstrip() + "\n\n"
    current_bounds = bounds(content)
    if current_bounds:
        return content[:current_bounds[0]] + section + content[current_bounds[1]:].lstrip("\n")
    separator = "" if not content or content.endswith("\n\n") else ("\n" if content.endswith("\n") else "\n\n")
    return content + separator + section


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace a text file while preserving its permission bits.

    Rules:   The temporary file MUST live beside the destination so os.replace is
             atomic. On failure, the original remains intact and the temp is removed.
    """
    mode = path.stat().st_mode & 0o7777 if path.exists() else 0o644
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as temp_file:
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            # Windows does not allow opening directories this way; the file was
            # already fsynced before replace, which is the strongest portable guarantee.
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def mutate_manifest(path: Path, transform: Callable[[str], str]) -> str:
    """Apply a lossless manifest mutation under lock and atomically persist it.

    Rules:   Read MUST happen after acquiring the lock to prevent lost updates.
             The transform must be deterministic and side-effect free.
    """
    with manifest_lock(path):
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        updated = transform(current)
        atomic_write_text(path, updated)
        return updated


def append_session(path: Path, session: dict[str, object]) -> str:
    """Append one session and enforce configured retention atomically.

    Rules:   agent, provider, date, session_id, task, changed, visited, and message
             are canonical fields; callers may include additional metadata.
    """
    return mutate_manifest(
        path,
        lambda content: replace_agent_sessions(content, parse_agent_sessions(content) + [session]),
    )


def prune_sessions(path: Path, limit: int | None = None) -> str:
    """Prune sessions to an explicit limit or max_agent_sessions.

    Rules:   Pruning never changes Git history; .codedna is only the recent-session cache.
    """
    return mutate_manifest(
        path,
        lambda content: replace_agent_sessions(content, parse_agent_sessions(content), limit),
    )
