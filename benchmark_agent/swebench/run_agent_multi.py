"""
swebench/run_agent_multi.py — Runs CodeDNA benchmark on multiple LLM providers.

deps:    google-genai, anthropic, openai — install with: pip install anthropic openai
exports: results_multi_<model>.json per model
rules:   Same system prompt, same tools, same tasks for all models.
         Only the LLM client changes — comparison is clean.

Usage:
  # Test all configured models
  GEMINI_API_KEY=... ANTHROPIC_API_KEY=... OPENAI_API_KEY=... python run_agent_multi.py

  # Test a specific model
  python run_agent_multi.py --model gemini-2.5-pro
  python run_agent_multi.py --model claude-3-7-sonnet
  python run_agent_multi.py --model gpt-4o
  python run_agent_multi.py --model deepseek-chat
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
                 if not i.name.startswith(".") and i.name != "__pycache__"]
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

def call_with_retry(fn, *args, max_attempts=3, **kwargs):
    """Generic retry with exponential backoff for API calls."""
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt < max_attempts - 1:
                wait = 2 ** attempt
                print(f"    ⚠️  API error ({type(e).__name__}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


FORCE_FINAL_PROMPT = (
    "You have used all available tool calls. Based on everything you have read so far, "
    "provide your final analysis: list ALL files that need modification and explain the fix."
)


# ─────────────────── Provider: Gemini ───────────────────

def run_gemini(problem: str, repo_root: Path, model_id: str, max_turns=15) -> dict:
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

    config = gt.GenerateContentConfig(system_instruction=SYSTEM_PROMPT,
                                      tools=tools_decl, temperature=0)
    history = [gt.Content(role="user",
        parts=[gt.Part(text=f"Problem:\n\n{problem}\n\nStart by listing the root directory.")])]
    final_text = ""

    for _ in range(max_turns):
        resp = call_with_retry(client.models.generate_content,
                               model=model_id, contents=history, config=config)
        cand = resp.candidates[0]
        if not cand.content:
            break
        history.append(cand.content)
        tool_parts = [p for p in cand.content.parts if p.function_call is not None]
        if not tool_parts:
            final_text = "".join(p.text for p in cand.content.parts if p.text)
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
        config_no_tools = gt.GenerateContentConfig(system_instruction=SYSTEM_PROMPT,
                                                    temperature=0)
        resp = call_with_retry(client.models.generate_content,
                               model=model_id, contents=history, config=config_no_tools)
        cand = resp.candidates[0]
        if cand.content:
            final_text = "".join(p.text for p in cand.content.parts if p.text)

    return log, final_text


# ─────────────────── Provider: Anthropic (Claude) ───────────────────

def run_anthropic(problem: str, repo_root: Path, model_id: str, max_turns=15) -> dict:
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
                 "content": f"Problem:\n\n{problem}\n\nStart by listing the root directory."}]
    final_text = ""

    for _ in range(max_turns):
        resp = call_with_retry(
            client.messages.create,
            model=model_id,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
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
            system=SYSTEM_PROMPT, messages=messages,
        )
        final_text = "".join(b.text for b in resp.content if b.type == "text")

    return log, final_text


# ─────────────────── Provider: OpenAI-compatible (GPT, DeepSeek) ───────────────────

def run_openai_compat(problem: str, repo_root: Path, model_id: str,
                      base_url: str = None, max_turns=15) -> dict:
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

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Problem:\n\n{problem}\n\nStart by listing the root directory."}
    ]
    final_text = ""

    for _ in range(max_turns):
        # Reasoning models (o1, o3) don't support temperature
        is_reasoning = any(x in model_id for x in ("o1", "o3"))
        create_kwargs = dict(model=model_id, messages=messages, tools=tools)
        if not is_reasoning:
            create_kwargs["temperature"] = 0

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
            create_kwargs["temperature"] = 0
        resp = call_with_retry(client.chat.completions.create, **create_kwargs)
        final_text = resp.choices[0].message.content or ""

    return log, final_text


# ─────────────────── Provider: OpenAI Responses API (Codex) ───────────────────

def run_openai_responses(problem: str, repo_root: Path, model_id: str, max_turns=15):
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
    initial_input = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",
         "content": f"Problem:\n\n{problem}\n\nStart by listing the root directory."},
    ]
    final_text = ""
    previous_response_id = None
    next_input = initial_input

    for _ in range(max_turns):
        create_kwargs = dict(model=model_id, input=next_input, tools=tools)
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
        create_kwargs = dict(model=model_id, input=next_input)
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
    "claude-sonnet-4":   {"provider": "anthropic", "model_id": "claude-sonnet-4-20250514"},
    "claude-opus-4":     {"provider": "anthropic", "model_id": "claude-opus-4-20250514"},
    "claude-sonnet-4-5": {"provider": "anthropic", "model_id": "claude-sonnet-4-5-20250929"},
    "claude-opus-4-5":   {"provider": "anthropic", "model_id": "claude-opus-4-5-20251101"},
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


def dispatch(problem, repo_root, cfg, max_turns=15):
    p = cfg["provider"]
    m = cfg["model_id"]
    if p == "gemini":
        return run_gemini(problem, repo_root, m, max_turns)
    elif p == "anthropic":
        return run_anthropic(problem, repo_root, m, max_turns)
    elif p == "openai":
        return run_openai_compat(problem, repo_root, m, max_turns=max_turns)
    elif p == "codex":
        return run_openai_responses(problem, repo_root, m, max_turns)
    else:
        raise ValueError(f"Unknown provider: {p}")


# ─────────────────── Main ───────────────────

def main():
    parser = argparse.ArgumentParser(description="Multi-model CodeDNA benchmark")
    parser.add_argument("--model", choices=list(MODELS.keys()),
                        help="Model to test (default: all configured)")
    parser.add_argument("--max-turns", type=int, default=15,
                        help="Max agent turns per task (default: 15)")
    parser.add_argument("--codedna-only", action="store_true",
                        help="Skip control, run CodeDNA only (faster)")
    args = parser.parse_args()

    models_to_run = [args.model] if args.model else list(MODELS.keys())

    with open(TASKS_FILE) as f:
        tasks = json.load(f)

    for model_name in models_to_run:
        cfg = MODELS[model_name]
        print(f"\n{'='*70}")
        print(f"  MODEL: {model_name}  (provider: {cfg['provider']})")
        print(f"{'='*70}")

        results = []
        for task in tasks:
            iid     = task["instance_id"]
            problem = task["problem_statement"]
            gt      = task["files_in_patch"]
            ctrl_dir = PROJECTS_DIR / iid / "control"
            cdna_dir = PROJECTS_DIR / iid / "codedna"

            if not ctrl_dir.exists():
                print(f"⚠️  {iid}: not set up — run setup_repos.py first.")
                continue

            print(f"\n{'─'*60}")
            print(f"Task: {iid}  ({len(gt)} ground-truth files)")

            ctrl_result = None
            if not args.codedna_only:
                print("  → CONTROL ...", flush=True)
                log, text = dispatch(problem, ctrl_dir, cfg, args.max_turns)
                ctrl_result = build_result(log, text, gt)
                cr = ctrl_result["metrics_read"]
                print(f"  Control: {ctrl_result['tool_calls']} calls "
                      f"({ctrl_result['read_calls']} reads, {ctrl_result['grep_calls']} greps) | "
                      f"{ctrl_result['total_chars_consumed']:,} chars | "
                      f"read(R={cr['recall']:.0%} P={cr['precision']:.0%} F1={cr['f1']:.0%})")

            print("  → CODEDNA ...", flush=True)
            log, text = dispatch(problem, cdna_dir, cfg, args.max_turns)
            cdna_result = build_result(log, text, gt)
            dr = cdna_result["metrics_read"]
            print(f"  CodeDNA: {cdna_result['tool_calls']} calls "
                  f"({cdna_result['read_calls']} reads, {cdna_result['grep_calls']} greps) | "
                  f"{cdna_result['total_chars_consumed']:,} chars | "
                  f"read(R={dr['recall']:.0%} P={dr['precision']:.0%} F1={dr['f1']:.0%})")

            results.append({
                "instance_id":        iid,
                "repo":               task["repo"],
                "ground_truth_files": gt,
                "control":            ctrl_result,
                "codedna":            cdna_result,
            })

        # Save results in runs/<model_name>/results.json
        run_dir = RUNS_DIR / model_name.replace('/', '-')
        run_dir.mkdir(parents=True, exist_ok=True)
        out_file = run_dir / "results.json"
        with open(out_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Saved → {out_file}")
        print(f"   Next:  python swebench/analyze_multi.py --model {model_name}")


if __name__ == "__main__":
    main()
