"""
swebench/run_agent_multi.py — Runs CodeDNA benchmark on multiple LLM providers.

deps:    google-genai, anthropic, openai — install with: pip install anthropic openai
exports: results_<model>/results.json per model
rules:   Same system prompt, same tools, same tasks for all models.
         Only the LLM client changes — comparison is clean.
         Two conditions: control (no annotations), codedna (curated).

Usage:
  # Test all configured models
  GEMINI_API_KEY=... ANTHROPIC_API_KEY=... OPENAI_API_KEY=... python run_agent_multi.py

  # Test a specific model
  python run_agent_multi.py --model gemini-2.5-flash
  python run_agent_multi.py --model claude-sonnet-4-6

  # Multi-run for statistical significance
  python run_agent_multi.py --model gemini-2.5-flash --runs 3 --temperature 0.1

  # Run only specific condition (faster)
  python run_agent_multi.py --model gemini-2.5-flash --condition codedna
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

TASKS_FILE   = Path(__file__).parent / "tasks.json"
PROJECTS_DIR = Path(__file__).parent.parent / "projects_swebench"
RUNS_DIR     = Path(__file__).parent.parent / "runs"

READ_FILE_LIMIT = 12000
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

CODEDNA_PROMPT = """## CodeDNA v0.7 — READ THIS FIRST

This codebase uses the CodeDNA annotation standard. These rules have the HIGHEST PRIORITY.

### Step 1: Read the `.codedna` manifest at the repo root
It describes the project structure: packages, purposes, dependencies. Read it BEFORE any code file.

### Step 2: Every Python file has a header with 3 fields
```
\"\"\"filename.py — <purpose>.

exports: public_symbol(args) -> type | none
used_by: consumer_file.py → consumer_symbol | none
rules:   <constraints> | none
\"\"\"
```

### Step 3: Efficient reading strategy
For any file you have not fully read yet: read only its first 15 lines (the docstring header).
Then decide based on `exports:`, `used_by:`, and `rules:` whether to read the full file.
This saves tokens and keeps navigation fast.

### Step 4: Follow the `used_by:` graph
`used_by:` tells you which files CONSUME this module. When you read a file and see:
```
used_by: some_module.py → SomeClass
         another_module.py → helper_func
```
Your NEXT ACTIONS should be:
- `read_file("some_module.py")` — read its header to check if it's relevant
- `read_file("another_module.py")` — read its header to check if it's relevant

If a `used_by:` target's purpose relates to the problem, read it in full. Then check ITS `used_by:` too.

### Step 5: Use `rules:` as navigation hints
`rules:` contains hard architectural constraints. If `rules:` mentions other files, components,
or backends, go read those too. Examples:
- `rules: Changes here affect ALL backends; verify mysql, oracle, postgresql, sqlite3.`
  → Action: read the operations file of each backend listed.
- `rules: new connectors need support in sql/where.py and sql/__init__.py`
  → Action: read sql/where.py and sql/__init__.py next.

### Step 6: Before your final answer
Verify: for every file you plan to modify, did you check its `used_by:` targets and `rules:`?
If not, go read them now.

---

You are an expert software engineer debugging a Python codebase.
Your task: read the problem description and find ALL the files that require modification to implement a complete fix.

Tools available:
- list_files(directory): list files in a directory
- read_file(path): read a source file
- grep(pattern, directory): search for a pattern

Do not stop at finding just the first root cause. Use the `used_by:` graph and `rules:` hints to map the full boundary.
"""

# ─────────────────── Tool execution (shared) ───────────────────

def make_fns(repo_root: Path):
    log = {"tool_calls": 0, "read_calls": 0, "grep_calls": 0, "list_calls": 0,
           "files_read": [], "greps": [], "total_chars_consumed": 0}

    def list_files(directory=".", **kw):
        log["tool_calls"] += 1; log["list_calls"] += 1
        target = repo_root / directory
        if not target.exists():
            return f"Directory not found: {directory}"
        items = [f"{'[DIR] ' if i.is_dir() else '      '}{i.name}"
                 for i in sorted(target.iterdir())
                 if (not i.name.startswith(".") or i.name == ".codedna")
                 and i.name != "__pycache__"]
        result = "\n".join(items) or "(empty)"
        log["total_chars_consumed"] += len(result)
        return result

    def read_file(path, **kw):
        log["tool_calls"] += 1; log["read_calls"] += 1
        target = repo_root / path
        if not target.exists():
            return f"File not found: {path}"
        log["files_read"].append(path)
        result = target.read_text(encoding="utf-8", errors="replace")[:READ_FILE_LIMIT]
        log["total_chars_consumed"] += len(result)
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
        return result

    return {"list_files": list_files, "read_file": read_file, "grep": grep}, log


def extract_proposed_files(text: str) -> set:
    """Extract proposed .py file paths from the tail of the agent's response."""
    tail = text[-3000:] if len(text) > 3000 else text
    raw = set(re.findall(r'[\w./]+\.py', tail))
    return {p.lstrip('./') for p in raw if '/' in p.lstrip('./')}


def file_metrics(files: set, ground_truth: list) -> dict:
    truth = set(ground_truth)
    if not truth:
        return {"recall": 0.0, "precision": 0.0, "f1": 0.0}
    hits = files & truth
    R = len(hits) / len(truth)
    P = len(hits) / len(files) if files else 0.0
    F1 = (2 * P * R) / (P + R) if (P + R) else 0.0
    return {"recall": R, "precision": P, "f1": F1}


def build_result(log: dict, final_text: str, ground_truth: list) -> dict:
    read_set = set(log["files_read"])
    proposed = extract_proposed_files(final_text)
    return {
        "tool_calls":           log["tool_calls"],
        "read_calls":           log["read_calls"],
        "grep_calls":           log["grep_calls"],
        "list_calls":           log["list_calls"],
        "files_read":           log["files_read"],
        "files_read_unique":    list(read_set),
        "n_files_read":         len(read_set),
        "greps":                log["greps"],
        "total_chars_consumed": log["total_chars_consumed"],
        "final_response":       final_text,
        "metrics_read":         file_metrics(read_set, ground_truth),
        "metrics_proposed":     file_metrics(proposed, ground_truth),
    }


# ─────────────────── Retry helper ───────────────────

def call_with_retry(fn, *args, max_attempts=5, **kwargs):
    """Generic retry with exponential backoff for API calls."""
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
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

    for _ in range(max_turns):
        resp = call_with_retry(
            client.messages.create,
            model=model_id,
            max_tokens=4096,
            system=prompt,
            tools=tools,
            messages=messages,
            temperature=temperature,
        )
        messages.append({"role": "assistant", "content": resp.content})

        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            final_text = "".join(b.text for b in resp.content if b.type == "text")
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
            system=prompt, messages=messages,
            temperature=temperature,
        )
        final_text = "".join(b.text for b in resp.content if b.type == "text")

    return log, final_text


# ─────────────────── Provider: OpenAI-compatible (GPT, DeepSeek) ───────────────────

def run_openai_compat(problem: str, repo_root: Path, model_id: str,
                      base_url: str = None, max_turns=15, temperature=0, system_prompt=None) -> dict:
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: pip install openai"); sys.exit(1)

    if "deepseek" in model_id.lower():
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        base_url = base_url or "https://api.deepseek.com/v1"
    else:
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = base_url

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
        msg = resp.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            final_text = msg.content or ""
            break

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            res = fns[tc.function.name](**args) if tc.function.name in fns else "unknown"
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": res})

    # Force final summary if agent exhausted max_turns without a text response
    if not final_text:
        messages.append({"role": "user", "content": FORCE_FINAL_PROMPT})
        create_kwargs = dict(model=model_id, messages=messages)
        if not any(x in model_id for x in ("o1", "o3")):
            create_kwargs["temperature"] = temperature
        resp = call_with_retry(client.chat.completions.create, **create_kwargs)
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
            args = json.loads(tc.arguments)
            res = fns[tc.name](**args) if tc.name in fns else "unknown function"
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
        return run_openai_compat(problem, repo_root, m, max_turns=max_turns, temperature=temperature, system_prompt=system_prompt)
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
                        choices=["all", "control", "codedna"],
                        default="all",
                        help="Which condition(s) to run (default: all)")
    args = parser.parse_args()

    if args.temperature is None:
        args.temperature = 0.1 if args.runs > 1 else 0.0

    models_to_run = [args.model] if args.model else list(MODELS.keys())

    with open(TASKS_FILE) as f:
        tasks = json.load(f)

    for model_name in models_to_run:
        cfg = MODELS[model_name]
        print(f"\n{'='*70}")
        print(f"  MODEL: {model_name}  (provider: {cfg['provider']})")
        if args.runs > 1:
            print(f"  RUNS: {args.runs}  |  TEMPERATURE: {args.temperature}")
        print(f"{'='*70}")

        def avg_f1(runs):
            vals = [r["metrics_read"]["f1"] for r in runs]
            m = sum(vals) / len(vals)
            std = (sum((v - m)**2 for v in vals) / (len(vals) - 1)) ** 0.5 if len(vals) > 1 else 0.0
            return {"mean": round(m, 4), "std": round(std, 4), "values": [round(v, 4) for v in vals]}

        run_ctrl = args.condition in ("all", "control")
        run_cdna = args.condition in ("all", "codedna")

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

            ctrl_runs, cdna_runs = [], []

            for run_i in range(args.runs):
                run_label = f" [run {run_i+1}/{args.runs}]" if args.runs > 1 else ""

                if run_ctrl:
                    print(f"  → CONTROL{run_label} ...", flush=True)
                    log, text = dispatch(problem, ctrl_dir, cfg, args.max_turns,
                                         temperature=args.temperature, system_prompt=SYSTEM_PROMPT)
                    r = build_result(log, text, gt)
                    cr = r["metrics_read"]
                    print(f"  Control: {r['tool_calls']} calls "
                          f"({r['read_calls']} reads, {r['grep_calls']} greps) | "
                          f"{r['total_chars_consumed']:,} chars | "
                          f"read(R={cr['recall']:.0%} P={cr['precision']:.0%} F1={cr['f1']:.0%})")
                    ctrl_runs.append(r)

                if run_cdna:
                    print(f"  → CODEDNA{run_label} ...", flush=True)
                    log, text = dispatch(problem, cdna_dir, cfg, args.max_turns,
                                         temperature=args.temperature, system_prompt=CODEDNA_PROMPT)
                    r = build_result(log, text, gt)
                    dr = r["metrics_read"]
                    print(f"  CodeDNA: {r['tool_calls']} calls "
                          f"({r['read_calls']} reads, {r['grep_calls']} greps) | "
                          f"{r['total_chars_consumed']:,} chars | "
                          f"read(R={dr['recall']:.0%} P={dr['precision']:.0%} F1={dr['f1']:.0%})")
                    cdna_runs.append(r)

            # Build result entry (backward-compatible for single run)
            entry = {
                "instance_id":        iid,
                "repo":               task["repo"],
                "ground_truth_files": gt,
            }

            if args.runs == 1:
                entry["control"] = ctrl_runs[0] if ctrl_runs else None
                entry["codedna"] = cdna_runs[0] if cdna_runs else None
            else:
                entry["n_runs"]           = args.runs
                entry["temperature"]      = args.temperature
                entry["control"]          = ctrl_runs[0] if ctrl_runs else None
                entry["control_runs"]     = ctrl_runs    if ctrl_runs else None
                entry["control_f1_stats"] = avg_f1(ctrl_runs) if ctrl_runs else None
                entry["codedna"]          = cdna_runs[0] if cdna_runs else None
                entry["codedna_runs"]     = cdna_runs    if cdna_runs else None
                entry["codedna_f1_stats"] = avg_f1(cdna_runs) if cdna_runs else None

                parts = []
                if ctrl_runs:
                    cf1 = avg_f1(ctrl_runs)
                    parts.append(f"Control: {cf1['mean']:.0%}±{cf1['std']:.0%}")
                if cdna_runs:
                    df1 = avg_f1(cdna_runs)
                    parts.append(f"CodeDNA: {df1['mean']:.0%}±{df1['std']:.0%}")
                print(f"  📊 Mean F1 — {' | '.join(parts)}")

            results.append(entry)

        # Save results — accumulate runs into runs/<model_name>/results.json
        run_dir = RUNS_DIR / model_name.replace('/', '-')
        run_dir.mkdir(parents=True, exist_ok=True)
        out_file = run_dir / "results.json"

        existing = []
        if out_file.exists():
            try:
                existing = json.load(open(out_file))
            except json.JSONDecodeError:
                existing = []

        for new_entry in results:
            iid = new_entry["instance_id"]
            old = next((e for e in existing if e.get("instance_id") == iid), None)
            if old is None:
                existing.append(new_entry)
            else:
                # Merge: accumulate _runs lists and recompute _f1_stats
                for cond in ("control", "codedna"):
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
                    len(old.get("codedna_runs") or []))
                old["temperature"] = new_entry.get("temperature", args.temperature)

        with open(out_file, "w") as f:
            json.dump(existing, f, indent=2)
        print(f"\n✅ Saved → {out_file}")
        print(f"   Next:  python swebench/analyze_multi.py --model {model_name}")


if __name__ == "__main__":
    main()
