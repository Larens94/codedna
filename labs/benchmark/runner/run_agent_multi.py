"""run_agent_multi.py — Runs CodeDNA benchmark on multiple LLM providers.

exports: TASKS_FILE | PROJECTS_DIR | RUNS_DIR | READ_FILE_LIMIT | GREP_LIMIT | SYSTEM_PROMPT | CODEDNA_PROMPT | make_fns(repo_root) | extract_proposed_files(text) | file_metrics(files, ground_truth) | build_result(log, final_text, ground_truth, session_id, model, provider, task, condition) | call_with_retry(fn) | FORCE_FINAL_PROMPT | build_initial_message(problem, repo_root) | run_gemini(problem, repo_root, model_id, max_turns, temperature, system_prompt) | _ANTHROPIC_COSTS | _ANTHROPIC_HISTORY_WINDOW | run_anthropic(problem, repo_root, model_id, max_turns, temperature, system_prompt) | run_openai_compat(problem, repo_root, model_id, base_url, max_turns, temperature, system_prompt) | run_openai_responses(problem, repo_root, model_id, max_turns, temperature, system_prompt) | (+3 more)
used_by: none
rules:   Same system prompt, same tools, same tasks for all models.
Only the LLM client changes — comparison is clean.
Two conditions: control (no annotations), codedna (curated).
trace: is ordered and timestamped — DO NOT sort or reorder entries.
session_id format: bench_<model>_<task_short>_<condition>_<YYYYMMDD_HHMMSS>
agent:   claude-opus-4-6 | anthropic | 2026-04-15 | s_20260415_001 | added --local-model and --base-url for Ollama/vLLM support
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_bench | fix token tracking in run_openai_compat (DeepSeek/GPT); smarter extract_proposed_files with proposal markers; add redundant_reads/nav_efficiency/tokens_per_gt_file/first_hit metrics to build_result; add --projects-dir and --tasks-file CLI args so labs/benchmark/projects can be used directly
claude-opus-4-7 | anthropic | 2026-04-17 | s_20260417_001 | register claude-opus-4-7 in _ANTHROPIC_COSTS and MODELS dict; same pricing as opus-4-6 pending official announcement
claude-opus-4-7 | anthropic | 2026-04-17 | s_20260417_opus47 | Opus 4.7 deprecates temperature param — wrap in _NO_TEMPERATURE_MODELS gate; build extra_kwargs dynamically
claude-opus-4-7 | anthropic | 2026-04-17 | s_20260417_infra | forked from benchmark_agent/swebench — labs-dedicated runner. Raised READ_FILE_LIMIT 12000→40000 per validator (2026-unrealistic at 1M ctx). Upgraded CODEDNA_PROMPT to v0.8 with L2 Rules guidance. Plan: port robust path parser inline, add matched_control + shuffled_placebo conditions, capture run_manifest.json per run.
message: "reasoning still not captured — trace has tool sequence + timestamps but not
model chain-of-thought. Worth capturing in a future pass."
Usage:
# Test a specific model (API)
python3 run_agent_multi.py --model gemini-2.5-flash
python3 run_agent_multi.py --model deepseek-chat --runs 3 --temperature 0.1
# Test a local model via Ollama
python3 run_agent_multi.py --local-model qwen2.5:32b
# Local model with custom URL (vLLM)
python3 run_agent_multi.py --local-model my-model --base-url http://localhost:8000/v1
# Run only specific condition
python3 run_agent_multi.py --model gemini-2.5-flash --condition codedna
# Use labs/benchmark tasks (22 Django tasks already prepared)
python3 run_agent_multi.py --model deepseek-chat --runs 3 --projects-dir ../../labs/benchmark/projects --tasks-file ../../labs/benchmark/tasks.json
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# Rules: __file__ = labs/benchmark/runner/run_agent_multi.py
#   parent        = labs/benchmark/runner/
#   parent.parent = labs/benchmark/
# Defaults are for labs/benchmark/ layout; override via --tasks-file / --projects-dir / RUNS_DIR env.
TASKS_FILE   = Path(__file__).parent.parent / "tasks.json"
PROJECTS_DIR = Path(__file__).parent.parent / "projects"
RUNS_DIR     = Path(__file__).parent.parent / "runs"

READ_FILE_LIMIT = 40000   # Rules: was 12000 (2026-unrealistic given 1M-context models); raised per validator recommendation
GREP_LIMIT      = 4000

SYSTEM_PROMPT = """You are an expert software engineer debugging a Python codebase.
Your task: read the problem description and find ALL the files that require modification to implement a complete fix.

Tools available:
- list_files(directory): list files in a directory
- read_file(path): read a source file
- grep(pattern, directory): search for a pattern

Strategy:
1. Start by listing the root directory to understand the structure
2. Identify the core files related to the problem
3. Trace the execution path: read the relevant files to understand how they work
4. Crucially: If a file defines dependencies or lists where it is used, EXPLORE those related files to ensure your fix is complete. A complete fix often requires changing test files, backend-specific files, or related utilities alongside the root cause.
5. Report: provide a comprehensive list of EVERY file you think needs modification, and what the fix should be.

Do not stop at finding just the first root cause. Make sure you map the full architectural boundary of the problem.
"""

CODEDNA_PROMPT = """## CodeDNA v0.8 — READ THIS FIRST

This codebase uses the CodeDNA annotation standard. These rules have the HIGHEST PRIORITY.
CodeDNA encodes architectural truth at 3 levels. Use them in order.

### Level 0 — `.codedna` manifest (provided in first message)
Already included above. Its `packages:` section gives each package's `purpose:` and `depends_on:`.
Use this to pick the correct package before reading any file. Do NOT re-read `.codedna` — you have it.

### Level 1 — module header (top of every `.py` file)
```
\"\"\"filename.py — <purpose>.

exports: public_symbol(args) -> type | none
used_by: consumer_file.py → consumer_symbol | none
rules:   <architectural constraints this file must obey>
agent:   <session narrative — skip this line, it's history>
\"\"\"
```

Read ONLY the first 20 lines of any file first. The header tells you whether to read the rest.
- `exports:` — public API symbols. If none match your task, STOP and move on.
- `used_by:` — who consumes this file. Tells you where the change cascades.
- `rules:` — hard constraints. If rules mention other files or backends, read those next.

### Level 2 — function `Rules:` docstring (inside functions)
```python
def my_function(arg: type) -> return_type:
    \"\"\"Short description.

    Rules:   What the agent MUST or MUST NOT do when modifying this function.
    message: <optional: open observations from previous agents>
    \"\"\"
```

When you read a file FULLY, scan every function docstring for a `Rules:` line. These are
per-function constraints that tell you:
- What invariants must hold when editing the function
- Which callers assume specific behaviour
- Edge cases and workarounds that must NOT be removed

**Respect `Rules:` in functions exactly like you respect `rules:` in module headers.**

---

## Navigation strategy

1. Start with the `.codedna` manifest to locate the RIGHT package.
2. Read the header of 1–3 candidate files (first 20 lines). Filter by `exports:` and `purpose:`.
3. If a file looks relevant: read fully, then check its `used_by:` graph.
   IMPORTANT: `used_by:` tells you WHO depends on this file — NOT that all of them need changes.
   For each caller, ask: "does this caller's domain intersect with the bug?" If not, skip it.
   Think: "which of these callers could be affected by THIS SPECIFIC change?"
4. If `related:` is present, check those files too — they share the same logic without importing
   each other (cross-cutting pattern). Same filter applies: is it relevant to THIS bug?
5. If `rules:` mentions a file/backend/package, read that immediately.
6. When inside a function, read its `Rules:` docstring BEFORE deciding what to change.
7. Before your final answer: verify every file you propose has had its `used_by:` and `rules:`
   checked, and every function you'd edit has its `Rules:` read.

---

You are an expert software engineer debugging a Python codebase.
Your task: read the problem description and find ALL the files that require modification for a COMPLETE fix.

Tools available:
- list_files(directory): list files in a directory
- read_file(path): read a source file
- grep(pattern, directory): search for a pattern

Do not stop at the first root cause. Use the 3 CodeDNA levels to map the full architectural boundary.
"""

# Matched-control prompt: same length, same directive style, same strategy
# checklist as CODEDNA_PROMPT — but ZERO reliance on annotations. Purpose is
# to isolate the causal effect of CodeDNA annotations from the confounding
# effect of a longer/more-prescriptive prompt. Δ(codedna − matched_control) is
# the clean annotation effect.
MATCHED_CONTROL_PROMPT = """## Multi-file bug-localisation — READ THIS FIRST

You are navigating a Python codebase to find ALL files that must change for a complete
bug fix. These rules have the HIGHEST PRIORITY and must be followed in order.

### Level 0 — project root structure
Start by listing the root directory (`list_files(".")`) to understand the top-level layout.
The project organises code into packages (directories with `__init__.py`). Pick the package
whose name most closely matches the problem domain BEFORE reading any file.

### Level 1 — file header as filter
For any Python file you have not fully read: read only the first ~20 lines first.
- Find the class/function definitions declared near the top — these are the "exports".
- Decide whether the file's API surface intersects the problem. If not, STOP and move on.
- Only read a file fully when its top-of-file symbols match the problem domain.

### Level 2 — function signatures & existing docstrings
When reading a file fully, focus on:
- Public function/class signatures — do any change for the fix?
- Existing docstrings — they document invariants, edge cases, and constraints.
- Comments that describe WHY, not WHAT.
- Workarounds and edge-case branches (often the site of the bug).

Respect existing constraints. Don't propose changes that violate behavior other code relies on.

---

## Navigation strategy

1. Start with `list_files(".")` to locate the RIGHT package/directory for the problem.
2. Read the header of 1–3 candidate files (first 20 lines). Filter by declared symbols.
3. If a file looks relevant: read fully, then use `grep` to find its callers — every caller
   is a candidate for modification (especially cross-cutting fixes).
4. If the file mentions other files/backends/packages in docs or comments, read those next.
5. When inside a function, read its signature and docstring BEFORE deciding what to change.
6. Before your final answer: verify every file you propose has had its callers and
   constraints checked, and every function you'd edit has its signature read.

---

You are an expert software engineer debugging a Python codebase.
Your task: read the problem description and find ALL the files that require modification for a COMPLETE fix.

Tools available:
- list_files(directory): list files in a directory
- read_file(path): read a source file
- grep(pattern, directory): search for a pattern

Do not stop at the first root cause. Systematically map the full architectural boundary.
"""

# ─────────────────── Tool execution (shared) ───────────────────

def make_fns(repo_root: Path):
    float_t0 = time.time()
    log = {"tool_calls": 0, "read_calls": 0, "grep_calls": 0, "list_calls": 0,
           "files_read": [], "greps": [], "total_chars_consumed": 0,
           "input_tokens": 0, "output_tokens": 0,
           "trace": []}   # ordered sequence of tool calls with relative timestamps

    def _record(tool: str, args: dict, result_len: int):
        log["trace"].append({
            "t":          round(time.time() - float_t0, 2),
            "tool":       tool,
            "args":       args,
            "result_len": result_len,
        })

    def list_files(directory=".", **kw):
        log["tool_calls"] += 1; log["list_calls"] += 1
        target = repo_root / directory
        if not target.exists():
            return f"Directory not found: {directory}"
        if not target.is_dir():
            return f"Not a directory: {directory}"
        items = [f"{'[DIR] ' if i.is_dir() else '      '}{i.name}"
                 for i in sorted(target.iterdir())
                 if (not i.name.startswith(".") or i.name == ".codedna")
                 and i.name != "__pycache__"]
        result = "\n".join(items) or "(empty)"
        log["total_chars_consumed"] += len(result)
        _record("list_files", {"directory": directory}, len(result))
        return result

    def read_file(path, **kw):
        log["tool_calls"] += 1; log["read_calls"] += 1
        target = repo_root / path
        if not target.exists():
            return f"File not found: {path}"
        if target.is_dir():
            return f"Is a directory, use list_files() instead: {path}"
        log["files_read"].append(path)
        result = target.read_text(encoding="utf-8", errors="replace")[:READ_FILE_LIMIT]
        log["total_chars_consumed"] += len(result)
        _record("read_file", {"path": path}, len(result))
        return result

    def grep(pattern, directory=".", **kw):
        log["tool_calls"] += 1; log["grep_calls"] += 1
        log["greps"].append(pattern)
        target = repo_root / directory
        try:
            r = subprocess.run(["grep", "-rn", "--include=*.py", pattern, str(target)],
                               capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired:
            r = type('R', (), {'stdout': '(grep timed out)'})()
        result = r.stdout[:GREP_LIMIT] or "(no matches)"
        log["total_chars_consumed"] += len(result)
        _record("grep", {"pattern": pattern, "directory": directory}, len(result))
        return result

    return {"list_files": list_files, "read_file": read_file, "grep": grep}, log


# ── Robust path extraction (markdown-aware + glob expansion + suffix match) ──
# Previously: regex failed on markdown bold/glob/backtick, truncated at 4000 chars
# mid-path ("dj|ango/..."), dropped paths without repo prefix. Rescore tool added
# post-hoc; now merged inline so live results.json and rescored agree.

_PY_PATH_RE = re.compile(r"[A-Za-z_][\w\-/*.]*\.py\b")
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC_RE = re.compile(r"\*(.+?)\*")
_MD_CODE_RE = re.compile(r"`([^`\n]+)`")
_MD_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```")


def _strip_markdown(text: str) -> str:
    """Remove markdown bold/italic/code/code-fence so paths inside are visible."""
    text = _MD_CODE_FENCE_RE.sub(lambda m: m.group(0).replace("```", " "), text)
    text = _MD_BOLD_RE.sub(r"\1", text)
    text = _MD_ITALIC_RE.sub(r"\1", text)
    text = _MD_CODE_RE.sub(r"\1", text)
    return text


def _expand_glob_against_repo(token: str, repo_files: list) -> list:
    if "*" not in token:
        return [token]
    import fnmatch as _fn
    return [f for f in repo_files if _fn.fnmatch(f, token)]


def _match_suffix_against_repo(token: str, repo_files: list) -> list:
    if token in repo_files:
        return [token]
    candidates = [f for f in repo_files if f.endswith("/" + token)]
    return candidates if len(candidates) == 1 else []


def extract_proposed_files(text: str, repo_files: list = None) -> set:
    """Extract proposed .py file paths from the agent's final response.

    Rules:   Search FULL text (no 4000-char tail — avoids mid-path truncation).
             Strip markdown formatting (**bold**, *italic*, `code`, ```fenced```)
             before regex so paths inside formatting are captured.
             Expand glob tokens (*) against repo_files when provided.
             Resolve partial paths by unique suffix match against repo_files
             ('sql/where.py' → 'django/db/models/sql/where.py' if unique).
             Drop single-segment names (no '/') as too ambiguous.
    """
    stripped = _strip_markdown(text)
    raw_tokens = _PY_PATH_RE.findall(stripped)
    tokens = []
    for t in raw_tokens:
        t = t.lstrip("/").lstrip(".").lstrip("/")
        if "/" not in t:
            continue
        tokens.append(t)

    proposed: set = set()
    for t in tokens:
        if repo_files is not None:
            if "*" in t:
                expanded = _expand_glob_against_repo(t, repo_files)
                if expanded:
                    proposed.update(expanded)
                    continue
            if t in repo_files:
                proposed.add(t)
                continue
            matched = _match_suffix_against_repo(t, repo_files)
            if matched:
                proposed.update(matched)
                continue
            if t.startswith("django/") or t.startswith("tests/"):
                proposed.add(t)
        else:
            proposed.add(t)
    return proposed


def file_metrics(files: set, ground_truth: list) -> dict:
    truth = set(ground_truth)
    if not truth:
        return {"recall": 0.0, "precision": 0.0, "f1": 0.0}
    hits = files & truth
    R = len(hits) / len(truth)
    P = len(hits) / len(files) if files else 0.0
    F1 = (2 * P * R) / (P + R) if (P + R) else 0.0
    return {"recall": R, "precision": P, "f1": F1}


def _list_repo_py_files(repo_root: Path) -> list:
    """List all .py files under repo_root (relative), skipping noise dirs.

    Rules:   Used by extract_proposed_files to resolve glob and partial paths
             against the actual repo content. Keep in sync with the skip set
             in codedna_tool/cli.py collect_files().
    """
    skip = {"__pycache__", ".git", "vendor", "node_modules", "migrations", ".tox"}
    out = []
    try:
        for f in repo_root.rglob("*.py"):
            parts = f.relative_to(repo_root).parts
            if any(p in skip for p in parts):
                continue
            out.append(str(f.relative_to(repo_root)))
    except (OSError, ValueError):
        pass
    return out


def build_result(log: dict, final_text: str, ground_truth: list,
                 session_id: str = "", model: str = "", provider: str = "",
                 task: str = "", condition: str = "",
                 repo_root: Path = None) -> dict:
    read_set = set(log["files_read"])
    # Build repo_files list for glob/suffix resolution. Zero cost when no repo_root.
    repo_files = _list_repo_py_files(repo_root) if repo_root else None
    proposed = extract_proposed_files(final_text, repo_files=repo_files)
    truth = set(ground_truth)
    total_tokens = log["input_tokens"] + log["output_tokens"]

    # ── Efficiency metrics ────────────────────────────────────────────────
    # Redundant reads: total reads minus unique reads (re-reads of same file)
    redundant_reads = len(log["files_read"]) - len(read_set)

    # Navigation efficiency: fraction of files read that were ground-truth
    nav_efficiency = round(len(read_set & truth) / len(read_set), 3) if read_set else 0.0

    # Token cost per ground-truth file correctly identified in read set
    gt_found = len(read_set & truth)
    tokens_per_gt_file = round(total_tokens / max(1, gt_found), 1) if total_tokens > 0 else None

    # First-hit rate: was a ground-truth file among the first 3 read_file calls?
    first_reads = [
        e["args"].get("path", "") for e in log["trace"]
        if e.get("tool") == "read_file"
    ][:3]
    first_hit = any(p in truth for p in first_reads)

    # Turn-at-first-hit: trace index of the first read_file that hit a GT file.
    # None if no GT file was ever read.
    turn_first_hit = None
    read_idx = 0
    for e in log["trace"]:
        if e.get("tool") == "read_file":
            read_idx += 1
            if e.get("args", {}).get("path", "") in truth:
                turn_first_hit = read_idx
                break

    return {
        "session_id":           session_id,
        "model":                model,
        "provider":             provider,
        "task":                 task,
        "condition":            condition,
        "tool_calls":           log["tool_calls"],
        "read_calls":           log["read_calls"],
        "grep_calls":           log["grep_calls"],
        "list_calls":           log["list_calls"],
        "files_read":           log["files_read"],
        "files_read_unique":    list(read_set),
        "n_files_read":         len(read_set),
        "redundant_reads":      redundant_reads,
        "nav_efficiency":       nav_efficiency,
        "tokens_per_gt_file":   tokens_per_gt_file,
        "first_hit":            first_hit,
        "turn_first_hit":       turn_first_hit,
        "proposed_files":       sorted(proposed),
        "greps":                log["greps"],
        "total_chars_consumed": log["total_chars_consumed"],
        "input_tokens":         log["input_tokens"],
        "output_tokens":        log["output_tokens"],
        "final_response":       final_text,
        "metrics_read":         file_metrics(read_set, ground_truth),
        "metrics_proposed":     file_metrics(proposed, ground_truth),
        "trace":                log["trace"],
    }


# ─────────────────── Retry helper ───────────────────

def call_with_retry(fn, *args, max_attempts=5, **kwargs):
    """Generic retry with exponential backoff for API calls.
    BadRequestError (400) is never retried — it indicates a malformed request."""
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            # Don't retry client errors (400) — they won't succeed on retry
            if "BadRequestError" in type(e).__name__ or "400" in str(e)[:50]:
                raise
            if attempt < max_attempts - 1:
                wait = 5 * (2 ** attempt)  # 5s, 10s, 20s, 40s
                print(f"    ⚠️  API error ({type(e).__name__}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


FORCE_FINAL_PROMPT = (
    "You have used all available tool calls. Based on everything you have read so far, "
    "provide your final analysis: list ALL files that need modification and explain the fix."
)


def build_initial_message(problem: str, repo_root: Path) -> str:
    """Build the initial user message, injecting .codedna content if present."""
    codedna_path = repo_root / ".codedna"
    if codedna_path.exists():
        codedna_content = codedna_path.read_text(encoding="utf-8", errors="replace").strip()
        return (
            f"Problem:\n\n{problem}\n\n"
            f"## Project manifest (.codedna)\n\n{codedna_content}\n\n"
            "Read the `.codedna` manifest above first — it maps packages, purposes, and dependencies. "
            "Then start exploring the repository."
        )
    return f"Problem:\n\n{problem}\n\nStart by listing the root directory."


# ─────────────────── Provider: Gemini ───────────────────

def run_gemini(problem: str, repo_root: Path, model_id: str, max_turns=15, temperature=0, system_prompt=None) -> dict:
    try:
        from google import genai
        from google.genai import types as gt
    except ImportError:
        print("ERROR: pip install google-genai"); sys.exit(1)

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: set GEMINI_API_KEY"); sys.exit(1)

    client = genai.Client(api_key=api_key)
    fns, log = make_fns(repo_root)

    tools_decl = [gt.Tool(function_declarations=[
        gt.FunctionDeclaration(name="list_files",
            description="List files in a directory",
            parameters=gt.Schema(type="OBJECT", properties={"directory": gt.Schema(type="STRING")})),
        gt.FunctionDeclaration(name="read_file",
            description="Read a source file",
            parameters=gt.Schema(type="OBJECT", required=["path"],
                                 properties={"path": gt.Schema(type="STRING")})),
        gt.FunctionDeclaration(name="grep",
            description="Search for a pattern",
            parameters=gt.Schema(type="OBJECT", required=["pattern"],
                                 properties={"pattern": gt.Schema(type="STRING"),
                                             "directory": gt.Schema(type="STRING")})),
    ])]

    prompt = system_prompt or SYSTEM_PROMPT
    config = gt.GenerateContentConfig(system_instruction=prompt,
                                      tools=tools_decl, temperature=temperature)
    history = [gt.Content(role="user",
        parts=[gt.Part(text=build_initial_message(problem, repo_root))])]
    final_text = ""

    for _ in range(max_turns):
        resp = call_with_retry(client.models.generate_content,
                               model=model_id, contents=history, config=config)
        cand = resp.candidates[0]
        if not cand.content:
            break
        history.append(cand.content)
        parts = cand.content.parts or []
        tool_parts = [p for p in parts if p.function_call is not None]
        if not tool_parts:
            final_text = "".join(p.text for p in parts if p.text)
            break
        results = []
        for p in tool_parts:
            fc = p.function_call
            res = fns[fc.name](**dict(fc.args)) if fc.name in fns else "unknown"
            results.append(gt.Part(function_response=gt.FunctionResponse(
                name=fc.name, response={"result": res})))
        history.append(gt.Content(role="tool", parts=results))

    # Force final summary if agent exhausted max_turns without a text response
    if not final_text:
        history.append(gt.Content(role="user",
            parts=[gt.Part(text=FORCE_FINAL_PROMPT)]))
        config_no_tools = gt.GenerateContentConfig(system_instruction=prompt,
                                                    temperature=temperature)
        resp = call_with_retry(client.models.generate_content,
                               model=model_id, contents=history, config=config_no_tools)
        cand = resp.candidates[0]
        if cand.content:
            final_text = "".join(p.text for p in cand.content.parts if p.text)

    return log, final_text


# ─────────────────── Provider: Anthropic (Claude) ───────────────────

# Cost per million tokens (input, output) — update if pricing changes
_ANTHROPIC_COSTS = {
    "claude-haiku-4-5-20251001": (0.80, 4.00),
    "claude-sonnet-4-6":         (3.00, 15.00),
    "claude-opus-4-6":           (15.00, 75.00),
    "claude-opus-4-7":           (15.00, 75.00),
}
_ANTHROPIC_HISTORY_WINDOW = 8  # keep first msg + last N assistant/user pairs

def _trim_anthropic_messages(messages: list, window: int) -> list:
    """Keep first message (problem) + last `window` turn pairs to limit input growth.

    The suffix must always start with an assistant message to avoid orphaned
    tool_result blocks. If the raw slice starts with a user(tool_results) message,
    the Anthropic API would merge it with messages[0], producing
    messages.0.content.1 = tool_result → BadRequestError.
    """
    max_msgs = 1 + window * 2
    if len(messages) <= max_msgs:
        return messages

    suffix = list(messages[-(window * 2):])
    # Drop leading user messages so the suffix always begins with an assistant turn
    while suffix and suffix[0].get("role") != "assistant":
        suffix = suffix[1:]

    if not suffix:
        # Extreme edge case: all trimmed messages were user messages
        return [messages[0]]

    return [messages[0]] + suffix

def run_anthropic(problem: str, repo_root: Path, model_id: str, max_turns=15, temperature=0, system_prompt=None) -> dict:
    try:
        import anthropic
    except ImportError:
        print("ERROR: pip install anthropic"); sys.exit(1)

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: set ANTHROPIC_API_KEY"); sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    fns, log = make_fns(repo_root)

    tools = [
        {"name": "list_files", "description": "List files in a directory",
         "input_schema": {"type": "object", "properties": {
             "directory": {"type": "string", "default": "."}}}},
        {"name": "read_file", "description": "Read a source file",
         "input_schema": {"type": "object", "required": ["path"],
                          "properties": {"path": {"type": "string"}}}},
        {"name": "grep", "description": "Search for a pattern",
         "input_schema": {"type": "object", "required": ["pattern"],
                          "properties": {"pattern": {"type": "string"},
                                         "directory": {"type": "string", "default": "."}}}},
    ]

    messages = [{"role": "user",
                 "content": build_initial_message(problem, repo_root)}]
    prompt = system_prompt or SYSTEM_PROMPT
    final_text = ""

    # Rules: Opus 4.7+ and other frontier Anthropic models deprecate temperature
    # (they use thinking/sampling internally). Build kwargs dynamically.
    _NO_TEMPERATURE_MODELS = {"claude-opus-4-7"}
    extra_kwargs = {} if model_id in _NO_TEMPERATURE_MODELS else {"temperature": temperature}

    for _ in range(max_turns):
        resp = call_with_retry(
            client.messages.create,
            model=model_id,
            max_tokens=4096,
            system=prompt,
            tools=tools,
            messages=_trim_anthropic_messages(messages, _ANTHROPIC_HISTORY_WINDOW),
            **extra_kwargs,
        )
        # Track token usage
        if hasattr(resp, "usage") and resp.usage:
            log["input_tokens"]  += resp.usage.input_tokens
            log["output_tokens"] += resp.usage.output_tokens
        messages.append({"role": "assistant", "content": resp.content})

        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            text_out = "".join(b.text for b in resp.content if b.type == "text")
            if log["tool_calls"] == 0 and len(text_out) < 500:
                messages.append({"role": "user", "content": [{"type": "text",
                    "text": "You haven't explored the codebase yet. "
                            "Start by calling list_files('.') to see the project structure."}]})
                continue
            final_text = text_out
            break

        tool_results = []
        for tu in tool_uses:
            res = fns[tu.name](**tu.input) if tu.name in fns else "unknown"
            tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": res})
        messages.append({"role": "user", "content": tool_results})

    # Force final summary if agent exhausted max_turns without a text response
    if not final_text:
        messages.append({"role": "user", "content": FORCE_FINAL_PROMPT})
        resp = call_with_retry(
            client.messages.create,
            model=model_id, max_tokens=4096,
            system=prompt,
            messages=_trim_anthropic_messages(messages, _ANTHROPIC_HISTORY_WINDOW),
            **extra_kwargs,
        )
        if hasattr(resp, "usage") and resp.usage:
            log["input_tokens"]  += resp.usage.input_tokens
            log["output_tokens"] += resp.usage.output_tokens
        final_text = "".join(b.text for b in resp.content if b.type == "text")

    # Print token usage + estimated cost
    costs = _ANTHROPIC_COSTS.get(model_id, (3.00, 15.00))
    cost_usd = (log["input_tokens"] / 1_000_000 * costs[0]
                + log["output_tokens"] / 1_000_000 * costs[1])
    print(f"    💰 tokens in={log['input_tokens']:,} out={log['output_tokens']:,} "
          f"≈ ${cost_usd:.4f}")

    return log, final_text


# ─────────────────── Provider: OpenAI-compatible (GPT, DeepSeek) ───────────────────

def run_openai_compat(problem: str, repo_root: Path, model_id: str,
                      base_url: str = None, max_turns=15, temperature=0, system_prompt=None) -> dict:
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: pip install openai"); sys.exit(1)

    if base_url and ("localhost" in base_url or "127.0.0.1" in base_url):
        api_key = "local"  # local models don't need a real key
    elif "deepseek" in model_id.lower():
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        base_url = base_url or "https://api.deepseek.com/v1"
    else:
        api_key = os.getenv("OPENAI_API_KEY", "")

    if not api_key:
        print(f"ERROR: set API key for {model_id}"); sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=base_url)
    fns, log = make_fns(repo_root)

    tools = [
        {"type": "function", "function": {
            "name": "list_files", "description": "List files in a directory",
            "parameters": {"type": "object", "properties": {
                "directory": {"type": "string", "default": "."}}}}},
        {"type": "function", "function": {
            "name": "read_file", "description": "Read a source file",
            "parameters": {"type": "object", "required": ["path"],
                           "properties": {"path": {"type": "string"}}}}},
        {"type": "function", "function": {
            "name": "grep", "description": "Search for a pattern",
            "parameters": {"type": "object", "required": ["pattern"],
                           "properties": {"pattern": {"type": "string"},
                                          "directory": {"type": "string", "default": "."}}}}}
    ]

    prompt = system_prompt or SYSTEM_PROMPT
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": build_initial_message(problem, repo_root)},
    ]
    final_text = ""

    for _ in range(max_turns):
        # Reasoning models (o1, o3) don't support temperature
        is_reasoning = any(x in model_id for x in ("o1", "o3"))
        create_kwargs = dict(model=model_id, messages=messages, tools=tools)
        if not is_reasoning:
            create_kwargs["temperature"] = temperature

        resp = call_with_retry(client.chat.completions.create, **create_kwargs)
        # Track tokens — usage is always present in non-streaming OpenAI responses
        if resp.usage:
            log["input_tokens"]  += resp.usage.prompt_tokens
            log["output_tokens"] += resp.usage.completion_tokens
        msg = resp.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            # Guard: if model bails on turn 1 with a very short response, nudge it to explore
            if log["tool_calls"] == 0 and len(msg.content or "") < 500:
                messages.append({"role": "user",
                                  "content": "You haven't explored the codebase yet. "
                                             "Start by calling list_files('.') to see the project structure."})
                continue
            final_text = msg.content or ""
            break

        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            try:
                res = fns[tc.function.name](**args) if tc.function.name in fns else "unknown"
            except TypeError:
                res = f"(error: invalid arguments for {tc.function.name})"
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": res})

    # Force final summary if agent exhausted max_turns without a text response
    if not final_text:
        messages.append({"role": "user", "content": FORCE_FINAL_PROMPT})
        create_kwargs = dict(model=model_id, messages=messages)
        if not any(x in model_id for x in ("o1", "o3")):
            create_kwargs["temperature"] = temperature
        resp = call_with_retry(client.chat.completions.create, **create_kwargs)
        if resp.usage:
            log["input_tokens"]  += resp.usage.prompt_tokens
            log["output_tokens"] += resp.usage.completion_tokens
        final_text = resp.choices[0].message.content or ""

    return log, final_text


# ─────────────────── Provider: OpenAI Responses API (Codex) ───────────────────

def run_openai_responses(problem: str, repo_root: Path, model_id: str, max_turns=15, temperature=0, system_prompt=None):
    """Use the OpenAI Responses API for gpt-5-codex base models."""
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: pip install openai"); sys.exit(1)

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: set OPENAI_API_KEY"); sys.exit(1)

    client = OpenAI(api_key=api_key)
    fns, log = make_fns(repo_root)

    tools = [
        {"type": "function", "name": "list_files",
         "description": "List files in a directory",
         "parameters": {"type": "object", "properties": {
             "directory": {"type": "string", "default": "."}}}},
        {"type": "function", "name": "read_file",
         "description": "Read a source file",
         "parameters": {"type": "object", "required": ["path"],
                        "properties": {"path": {"type": "string"}}}},
        {"type": "function", "name": "grep",
         "description": "Search for a pattern",
         "parameters": {"type": "object", "required": ["pattern"],
                        "properties": {"pattern": {"type": "string"},
                                       "directory": {"type": "string", "default": "."}}}},
    ]

    # Responses API: first call sends full input, subsequent calls send only new tool results
    prompt = system_prompt or SYSTEM_PROMPT
    initial_input = [
        {"role": "system", "content": prompt},
        {"role": "user",
         "content": build_initial_message(problem, repo_root)},
    ]
    final_text = ""
    previous_response_id = None
    next_input = initial_input

    for _ in range(max_turns):
        create_kwargs = dict(model=model_id, input=next_input, tools=tools, temperature=temperature)
        if previous_response_id:
            create_kwargs["previous_response_id"] = previous_response_id

        resp = call_with_retry(client.responses.create, **create_kwargs)
        previous_response_id = resp.id

        # Collect tool calls and text from output
        tool_calls_found = []
        for item in resp.output:
            if item.type == "function_call":
                tool_calls_found.append(item)
            elif item.type == "message":
                for block in item.content:
                    if hasattr(block, "text"):
                        final_text = block.text

        if not tool_calls_found:
            break

        # Execute tools and build results
        tool_results = []
        for tc in tool_calls_found:
            try:
                args = json.loads(tc.arguments)
            except json.JSONDecodeError:
                args = {}
            try:
                res = fns[tc.name](**args) if tc.name in fns else "unknown function"
            except TypeError:
                res = f"(error: invalid arguments for {tc.name})"
            tool_results.append({
                "type": "function_call_output",
                "call_id": tc.call_id,
                "output": res,
            })

        # Next turn: only send the new tool results (API tracks history via previous_response_id)
        next_input = tool_results

    # Force final summary if agent exhausted max_turns without a text response
    if not final_text:
        next_input = [{"role": "user", "content": FORCE_FINAL_PROMPT}]
        create_kwargs = dict(model=model_id, input=next_input, temperature=temperature)
        if previous_response_id:
            create_kwargs["previous_response_id"] = previous_response_id
        resp = call_with_retry(client.responses.create, **create_kwargs)
        for item in resp.output:
            if item.type == "message":
                for block in item.content:
                    if hasattr(block, "text"):
                        final_text = block.text

    return log, final_text


# ─────────────────── Model registry ───────────────────

MODELS = {
    # Google
    "gemini-2.5-flash": {"provider": "gemini",    "model_id": "gemini-2.5-flash"},
    "gemini-2.5-pro":   {"provider": "gemini",    "model_id": "gemini-2.5-pro"},
    # Anthropic Claude 4 (latest, March 2026)
    "claude-sonnet-4-6": {"provider": "anthropic", "model_id": "claude-sonnet-4-6"},
    "claude-opus-4-6":   {"provider": "anthropic", "model_id": "claude-opus-4-6"},
    "claude-opus-4-7":   {"provider": "anthropic", "model_id": "claude-opus-4-7"},
    "claude-haiku-4-5":  {"provider": "anthropic", "model_id": "claude-haiku-4-5-20251001"},
    # OpenAI chat models (function calling via Chat Completions API)
    "gpt-4.1":           {"provider": "openai",    "model_id": "gpt-4.1"},
    "gpt-4o":            {"provider": "openai",    "model_id": "gpt-4o"},
    "gpt-4o-mini":       {"provider": "openai",    "model_id": "gpt-4o-mini"},
    # OpenAI reasoning (no temperature)
    "o3":                {"provider": "openai",    "model_id": "o3"},
    "o3-mini":           {"provider": "openai",    "model_id": "o3-mini"},
    "o1-pro":            {"provider": "openai",    "model_id": "o1-pro"},
    # OpenAI Codex (Responses API — base models, function calling via responses.create)
    "gpt-5-codex":       {"provider": "codex",     "model_id": "gpt-5-codex"},
    "gpt-5.1-codex":     {"provider": "codex",     "model_id": "gpt-5.1-codex"},
    "gpt-5.2-codex":     {"provider": "codex",     "model_id": "gpt-5.2-codex"},
    "gpt-5.3-codex":     {"provider": "codex",     "model_id": "gpt-5.3-codex"},
    "gpt-5.1-codex-mini":{"provider": "codex",     "model_id": "gpt-5.1-codex-mini"},
    # DeepSeek (OpenAI-compatible)
    "deepseek-chat":     {"provider": "openai",    "model_id": "deepseek-chat"},
}


def dispatch(problem, repo_root, cfg, max_turns=15, temperature=0, system_prompt=None):
    p = cfg["provider"]
    m = cfg["model_id"]
    if p == "gemini":
        return run_gemini(problem, repo_root, m, max_turns, temperature=temperature, system_prompt=system_prompt)
    elif p == "anthropic":
        return run_anthropic(problem, repo_root, m, max_turns, temperature=temperature, system_prompt=system_prompt)
    elif p == "openai":
        return run_openai_compat(problem, repo_root, m, base_url=cfg.get("base_url"), max_turns=max_turns, temperature=temperature, system_prompt=system_prompt)
    elif p == "codex":
        return run_openai_responses(problem, repo_root, m, max_turns, temperature=temperature, system_prompt=system_prompt)
    else:
        raise ValueError(f"Unknown provider: {p}")


# ─────────────────── Main ───────────────────

def main():
    parser = argparse.ArgumentParser(description="Multi-model CodeDNA benchmark")
    parser.add_argument("--model", choices=list(MODELS.keys()),
                        help="Model to test (default: all configured)")
    parser.add_argument("--max-turns", type=int, default=30,
                        help="Max agent turns per task (default: 30)")
    parser.add_argument("--runs", type=int, default=1,
                        help="Number of runs per task for statistical averaging (default: 1)")
    parser.add_argument("--temperature", type=float, default=None,
                        help="Temperature for LLM sampling (default: 0.0 single run, 0.1 multi-run)")
    parser.add_argument("--condition",
                        choices=["all", "control", "codedna", "matched", "matched_control",
                                 "placebo", "control+codedna", "control+matched+codedna",
                                 "control+matched+placebo+codedna"],
                        default="all",
                        help="Which condition(s) to run. 'matched' = matched-prompt baseline "
                             "(same style/length as codedna prompt, no annotation reliance). "
                             "'placebo' = same CODEDNA_PROMPT on a repo where used_by: blocks are "
                             "shuffled (graph is broken). Δ(codedna−matched) = prompt-effect-free. "
                             "Δ(codedna−placebo) = pure used_by: graph effect. "
                             "'all' runs control+matched+codedna (placebo opt-in).")
    parser.add_argument("--task", nargs="+",
                        help="Run only specific task IDs, e.g. --task 14480 13495")
    parser.add_argument("--local-model",
                        help="Local model via Ollama/vLLM (e.g. qwen2.5:32b, llama3.1:70b)")
    parser.add_argument("--base-url", default=None,
                        help="Base URL for local models (default: http://localhost:11434/v1 for Ollama)")
    parser.add_argument("--projects-dir", default=None,
                        help="Path to projects directory (default: ../projects_swebench)")
    parser.add_argument("--tasks-file", default=None,
                        help="Path to tasks.json (default: ./tasks.json)")
    args = parser.parse_args()

    # Allow overriding module-level paths via CLI
    global TASKS_FILE, PROJECTS_DIR
    if args.tasks_file:
        TASKS_FILE = Path(args.tasks_file).resolve()
    if args.projects_dir:
        PROJECTS_DIR = Path(args.projects_dir).resolve()

    if args.temperature is None:
        args.temperature = 0.1 if args.runs > 1 else 0.0

    # Register local model on-the-fly
    if args.local_model:
        local_name = f"local-{args.local_model.replace(':', '-').replace('/', '-')}"
        MODELS[local_name] = {
            "provider": "openai",
            "model_id": args.local_model,
            "base_url": args.base_url or "http://localhost:11434/v1",
        }
        args.model = local_name

    models_to_run = [args.model] if args.model else list(MODELS.keys())

    with open(TASKS_FILE) as f:
        tasks = json.load(f)

    if args.task:
        filter_ids = {f"django__django-{t}" if not t.startswith("django") else t
                      for t in args.task}
        tasks = [t for t in tasks if t["instance_id"] in filter_ids]
        if not tasks:
            print(f"No tasks found for: {args.task}")
            return

    for model_name in models_to_run:
        cfg = MODELS[model_name]
        print(f"\n{'='*70}")
        print(f"  MODEL: {model_name}  (provider: {cfg['provider']})")
        if args.runs > 1:
            print(f"  RUNS: {args.runs}  |  TEMPERATURE: {args.temperature}")
        print(f"{'='*70}")

        def avg_f1(runs):
            vals = [r["metrics_proposed"]["f1"] for r in runs]
            m = sum(vals) / len(vals)
            std = (sum((v - m)**2 for v in vals) / (len(vals) - 1)) ** 0.5 if len(vals) > 1 else 0.0
            return {"mean": round(m, 4), "std": round(std, 4), "values": [round(v, 4) for v in vals]}

        # Rules: "matched" is a control condition using the MATCHED_CONTROL_PROMPT
        # on the SAME repo as "control" (no annotations, just a richer prompt).
        # Δ(codedna − matched) isolates the annotation effect from the prompt effect.
        run_ctrl = args.condition in ("all", "control", "control+codedna",
                                       "control+matched+codedna", "control+matched+placebo+codedna")
        run_matched = args.condition in ("all", "matched", "matched_control",
                                          "control+matched+codedna", "control+matched+placebo+codedna")
        run_placebo = args.condition in ("placebo", "control+matched+placebo+codedna")
        run_cdna = args.condition in ("all", "codedna", "control+codedna",
                                       "control+matched+codedna", "control+matched+placebo+codedna")

        run_dir = RUNS_DIR / model_name.replace('/', '-')
        run_dir.mkdir(parents=True, exist_ok=True)
        out_file = run_dir / "results.json"
        traces_dir = run_dir / "session_traces"
        traces_dir.mkdir(exist_ok=True)

        # ── Run manifest (reproducibility anchor, written BEFORE any run) ──
        # Rules: this file MUST exist alongside results.json. If any field is
        # missing at publication time, results are non-reproducible.
        import hashlib as _hashlib
        import subprocess as _subprocess
        def _sha256_str(s: str) -> str:
            return _hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]
        def _sha256_file(p: Path) -> str:
            if not p.exists():
                return "NOEXIST"
            h = _hashlib.sha256()
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()[:16]
        def _git_sha() -> str:
            try:
                r = _subprocess.run(["git", "rev-parse", "HEAD"],
                                    capture_output=True, text=True, timeout=5)
                return r.stdout.strip()[:12] if r.returncode == 0 else "UNKNOWN"
            except Exception:
                return "UNKNOWN"
        def _git_dirty() -> bool:
            try:
                r = _subprocess.run(["git", "status", "--porcelain"],
                                    capture_output=True, text=True, timeout=5)
                return bool(r.stdout.strip())
            except Exception:
                return False

        manifest = {
            "timestamp_utc":    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model_name":       model_name,
            "model_id":         cfg["model_id"],
            "provider":         cfg["provider"],
            "cli_args": {
                "runs":         args.runs,
                "temperature":  args.temperature,
                "max_turns":    args.max_turns,
                "condition":    args.condition,
                "task":         args.task,
            },
            "git": {
                "commit":       _git_sha(),
                "dirty":        _git_dirty(),
            },
            "file_sha256": {
                "runner":       _sha256_file(Path(__file__)),
                "tasks_json":   _sha256_file(TASKS_FILE),
            },
            "prompt_sha256": {
                "system":          _sha256_str(SYSTEM_PROMPT),
                "matched_control": _sha256_str(MATCHED_CONTROL_PROMPT),
                "codedna":         _sha256_str(CODEDNA_PROMPT),
            },
            "limits": {
                "read_file_limit":  READ_FILE_LIMIT,
                "grep_limit":       GREP_LIMIT,
                "history_window":   _ANTHROPIC_HISTORY_WINDOW,
            },
            "python_version":   sys.version.split()[0],
        }
        try:
            import anthropic as _ant
            manifest["sdk_versions"] = {"anthropic": _ant.__version__}
        except ImportError:
            pass
        manifest_path = run_dir / "run_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        print(f"  📜 manifest → {manifest_path}  (git={manifest['git']['commit']}, dirty={manifest['git']['dirty']})")

        def _save_results(run_dir, out_file, new_entries, avg_f1, args):
            existing = []
            if out_file.exists():
                try:
                    existing = json.load(open(out_file))
                except json.JSONDecodeError:
                    existing = []
            for new_entry in new_entries:
                iid = new_entry["instance_id"]
                old = next((e for e in existing if e.get("instance_id") == iid), None)
                if old is None:
                    existing.append(new_entry)
                else:
                    for cond in ("control", "matched", "placebo", "codedna"):
                        new_runs = new_entry.get(f"{cond}_runs") or (
                            [new_entry[cond]] if new_entry.get(cond) else [])
                        old_runs = old.get(f"{cond}_runs") or (
                            [old[cond]] if old.get(cond) else [])
                        merged = old_runs + new_runs
                        if merged:
                            old[cond] = merged[0]
                            old[f"{cond}_runs"] = merged
                            old[f"{cond}_f1_stats"] = avg_f1(merged)
                    old["n_runs"] = max(
                        len(old.get("control_runs") or []),
                        len(old.get("matched_runs") or []),
                        len(old.get("placebo_runs") or []),
                        len(old.get("codedna_runs") or []))
                    old["temperature"] = new_entry.get("temperature", args.temperature)
            with open(out_file, "w") as f:
                json.dump(existing, f, indent=2)

        results = []
        for task in tasks:
            iid      = task["instance_id"]
            problem  = task["problem_statement"]
            gt       = task["files_in_patch"]
            ctrl_dir = PROJECTS_DIR / iid / "control"
            cdna_dir = PROJECTS_DIR / iid / "codedna"

            if not ctrl_dir.exists():
                print(f"⚠️  {iid}: not set up — run setup_repos.py first.")
                continue

            print(f"\n{'─'*60}")
            print(f"Task: {iid}  ({len(gt)} ground-truth files)")

            ctrl_runs, cdna_runs, matched_runs, placebo_runs = [], [], [], []
            placebo_dir = PROJECTS_DIR / iid / "placebo"

            for run_i in range(args.runs):
                run_label = f" [run {run_i+1}/{args.runs}]" if args.runs > 1 else ""

                def _make_session_id(mdl, task_id, cond, run_idx):
                    str_ts = time.strftime("%Y%m%d_%H%M%S")
                    str_task_short = task_id.split("-")[-1]
                    return f"bench_{mdl}_{str_task_short}_{cond}_{str_ts}_r{run_idx}"

                def _save_trace(traces_dir, session_id, result, ground_truth):
                    """Rules: save trace independently of results.json — do not inline."""
                    dict_trace_doc = {
                        "session_id":    session_id,
                        "model":         result["model"],
                        "provider":      result["provider"],
                        "task":          result["task"],
                        "condition":     result["condition"],
                        "ground_truth":  ground_truth,
                        "metrics_read":  result["metrics_read"],
                        "trace":         result["trace"],
                        "note_missing":  (
                            "reasoning/chain-of-thought not captured — "
                            "trace contains tool sequence + timestamps only"
                        ),
                    }
                    path_trace = traces_dir / f"{session_id}.json"
                    path_trace.write_text(json.dumps(dict_trace_doc, indent=2))
                    return path_trace

                if run_ctrl:
                    print(f"  → CONTROL{run_label} ...", flush=True)
                    log, text = dispatch(problem, ctrl_dir, cfg, args.max_turns,
                                         temperature=args.temperature, system_prompt=SYSTEM_PROMPT)
                    str_sid = _make_session_id(model_name, iid, "control", run_i)
                    r = build_result(log, text, gt,
                                     session_id=str_sid, model=model_name,
                                     provider=cfg["provider"], task=iid, condition="control",
                                     repo_root=ctrl_dir)
                    cr = r["metrics_proposed"]
                    path_trace = _save_trace(traces_dir, str_sid, r, gt)
                    print(f"  Control: {r['tool_calls']} calls "
                          f"({r['read_calls']} reads, {r['grep_calls']} greps) | "
                          f"{r['total_chars_consumed']:,} chars | "
                          f"read(R={cr['recall']:.0%} P={cr['precision']:.0%} F1={cr['f1']:.0%})")
                    print(f"  📋 trace → {path_trace.name}  ({len(r['trace'])} steps)")
                    ctrl_runs.append(r)

                if run_matched:
                    print(f"  → MATCHED{run_label} ...", flush=True)
                    log, text = dispatch(problem, ctrl_dir, cfg, args.max_turns,
                                         temperature=args.temperature, system_prompt=MATCHED_CONTROL_PROMPT)
                    str_sid = _make_session_id(model_name, iid, "matched", run_i)
                    r = build_result(log, text, gt,
                                     session_id=str_sid, model=model_name,
                                     provider=cfg["provider"], task=iid, condition="matched",
                                     repo_root=ctrl_dir)
                    mr = r["metrics_proposed"]
                    path_trace = _save_trace(traces_dir, str_sid, r, gt)
                    print(f"  Matched: {r['tool_calls']} calls "
                          f"({r['read_calls']} reads, {r['grep_calls']} greps) | "
                          f"{r['total_chars_consumed']:,} chars | "
                          f"read(R={mr['recall']:.0%} P={mr['precision']:.0%} F1={mr['f1']:.0%})")
                    print(f"  📋 trace → {path_trace.name}  ({len(r['trace'])} steps)")
                    matched_runs.append(r)

                if run_placebo:
                    if not placebo_dir.exists():
                        print(f"  ⚠️  PLACEBO skipped (no placebo/ dir — run generate_placebo.py first)")
                    else:
                        print(f"  → PLACEBO{run_label} ...", flush=True)
                        log, text = dispatch(problem, placebo_dir, cfg, args.max_turns,
                                             temperature=args.temperature, system_prompt=CODEDNA_PROMPT)
                        str_sid = _make_session_id(model_name, iid, "placebo", run_i)
                        r = build_result(log, text, gt,
                                         session_id=str_sid, model=model_name,
                                         provider=cfg["provider"], task=iid, condition="placebo",
                                         repo_root=placebo_dir)
                        pr = r["metrics_proposed"]
                        path_trace = _save_trace(traces_dir, str_sid, r, gt)
                        print(f"  Placebo: {r['tool_calls']} calls "
                              f"({r['read_calls']} reads, {r['grep_calls']} greps) | "
                              f"{r['total_chars_consumed']:,} chars | "
                              f"read(R={pr['recall']:.0%} P={pr['precision']:.0%} F1={pr['f1']:.0%})")
                        print(f"  📋 trace → {path_trace.name}  ({len(r['trace'])} steps)")
                        placebo_runs.append(r)

                if run_cdna:
                    print(f"  → CODEDNA{run_label} ...", flush=True)
                    log, text = dispatch(problem, cdna_dir, cfg, args.max_turns,
                                         temperature=args.temperature, system_prompt=CODEDNA_PROMPT)
                    str_sid = _make_session_id(model_name, iid, "codedna", run_i)
                    r = build_result(log, text, gt,
                                     session_id=str_sid, model=model_name,
                                     provider=cfg["provider"], task=iid, condition="codedna",
                                     repo_root=cdna_dir)
                    dr = r["metrics_proposed"]
                    path_trace = _save_trace(traces_dir, str_sid, r, gt)
                    print(f"  CodeDNA: {r['tool_calls']} calls "
                          f"({r['read_calls']} reads, {r['grep_calls']} greps) | "
                          f"{r['total_chars_consumed']:,} chars | "
                          f"read(R={dr['recall']:.0%} P={dr['precision']:.0%} F1={dr['f1']:.0%})")
                    print(f"  📋 trace → {path_trace.name}  ({len(r['trace'])} steps)")
                    cdna_runs.append(r)

            # Build result entry (backward-compatible for single run)
            entry = {
                "instance_id":        iid,
                "repo":               task["repo"],
                "ground_truth_files": gt,
            }

            if args.runs == 1:
                entry["control"] = ctrl_runs[0] if ctrl_runs else None
                entry["matched"] = matched_runs[0] if matched_runs else None
                entry["placebo"] = placebo_runs[0] if placebo_runs else None
                entry["codedna"] = cdna_runs[0] if cdna_runs else None
            else:
                entry["n_runs"]           = args.runs
                entry["temperature"]      = args.temperature
                entry["control"]          = ctrl_runs[0] if ctrl_runs else None
                entry["control_runs"]     = ctrl_runs    if ctrl_runs else None
                entry["control_f1_stats"] = avg_f1(ctrl_runs) if ctrl_runs else None
                entry["matched"]          = matched_runs[0] if matched_runs else None
                entry["matched_runs"]     = matched_runs    if matched_runs else None
                entry["matched_f1_stats"] = avg_f1(matched_runs) if matched_runs else None
                entry["placebo"]          = placebo_runs[0] if placebo_runs else None
                entry["placebo_runs"]     = placebo_runs    if placebo_runs else None
                entry["placebo_f1_stats"] = avg_f1(placebo_runs) if placebo_runs else None
                entry["codedna"]          = cdna_runs[0] if cdna_runs else None
                entry["codedna_runs"]     = cdna_runs    if cdna_runs else None
                entry["codedna_f1_stats"] = avg_f1(cdna_runs) if cdna_runs else None

                parts = []
                if ctrl_runs:
                    cf1 = avg_f1(ctrl_runs)
                    parts.append(f"Control: {cf1['mean']:.0%}±{cf1['std']:.0%}")
                if matched_runs:
                    mf1 = avg_f1(matched_runs)
                    parts.append(f"Matched: {mf1['mean']:.0%}±{mf1['std']:.0%}")
                if placebo_runs:
                    pf1 = avg_f1(placebo_runs)
                    parts.append(f"Placebo: {pf1['mean']:.0%}±{pf1['std']:.0%}")
                if cdna_runs:
                    df1 = avg_f1(cdna_runs)
                    parts.append(f"CodeDNA: {df1['mean']:.0%}±{df1['std']:.0%}")
                print(f"  📊 Mean F1 — {' | '.join(parts)}")

            results.append(entry)

            # Save incrementally after each task
            _save_results(run_dir, out_file, [entry], avg_f1, args)
            print(f"  💾 Saved → {out_file}")

        print(f"\n✅ All tasks done → {out_file}")
        print(f"   Next:  python swebench/analyze_multi.py --model {model_name}")


if __name__ == "__main__":
    main()
