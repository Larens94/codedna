"""
benchmark_server.py — Live benchmark runner with SSE streaming.

Imports ALL logic directly from run_agent_multi.py to guarantee identical behavior.
Only adds: Flask server + SSE event streaming + reasoning capture.

Usage:
  GEMINI_API_KEY=... python benchmark_server.py
  Open http://localhost:5001
"""

import json
import os
import re
import sys
import threading
import time
import traceback
from pathlib import Path
from queue import Queue, Empty

# Add swebench dir to path so we can import run_agent_multi
SWEBENCH_DIR = Path(__file__).parent / "swebench"
sys.path.insert(0, str(SWEBENCH_DIR))

# Import EVERYTHING from the real benchmark script — guarantees identical logic
import run_agent_multi as ram

try:
    from flask import Flask, Response, request, jsonify, send_file
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "-q"])
    from flask import Flask, Response, request, jsonify, send_file


# ─── Paths ───
BASE_DIR     = Path(__file__).parent
TASKS_FILE   = SWEBENCH_DIR / "tasks.json"
PROJECTS_DIR = BASE_DIR / "projects_swebench"
RUNS_DIR     = BASE_DIR / "runs"
UI_FILE      = BASE_DIR / "benchmark_ui.html"


# ─── Streaming wrappers around the REAL provider functions ───
# These intercept events (reasoning, tool calls) mid-flight and push to SSE queue.

def _wrap_fns(fns_dict, log, side, queue):
    """Wrap the real make_fns() tools to emit SSE events on each call."""
    wrapped = {}
    for name, fn in fns_dict.items():
        def make_wrapper(fn_name, fn_impl):
            def wrapper(**kwargs):
                # Emit tool_call event
                queue.put({"type": "tool_call", "side": side, "name": fn_name, "args": kwargs})
                result = fn_impl(**kwargs)
                # Emit tool_result preview
                preview = result[:300] if isinstance(result, str) else str(result)[:300]
                queue.put({"type": "tool_result", "side": side, "name": fn_name, "preview": preview})
                return result
            return wrapper
        wrapped[name] = make_wrapper(name, fn)
    return wrapped


def run_with_streaming(problem, repo_root, provider, model_id, side, queue,
                       temperature=0, max_turns=30, system_prompt=None):
    """Run a benchmark using the REAL provider functions, with SSE event interception."""
    try:
        fns_raw, log = ram.make_fns(repo_root)
        fns = _wrap_fns(fns_raw, log, side, queue)

        queue.put({"type": "start", "side": side, "model": model_id})
        reasoning_texts = []  # collect all reasoning for saving
        prompt = system_prompt or ram.SYSTEM_PROMPT

        if provider == "gemini":
            final_text = _run_gemini(problem, model_id, fns, log, side, queue,
                                     temperature, max_turns, reasoning_texts, prompt)
        elif provider == "anthropic":
            final_text = _run_anthropic(problem, model_id, fns, log, side, queue,
                                        temperature, max_turns, reasoning_texts, prompt)
        elif provider == "openai":
            final_text = _run_openai(problem, model_id, fns, log, side, queue,
                                      temperature, max_turns, reasoning_texts, prompt)
        elif provider == "codex":
            final_text = _run_codex(problem, model_id, fns, log, side, queue,
                                     temperature, max_turns, reasoning_texts, prompt)
        else:
            queue.put({"type": "error", "side": side, "error": f"Unknown provider: {provider}"})
            return

        queue.put({"type": "final_response", "side": side, "text": (final_text or "")[:3000]})

        # Emit done with full log
        read_set = set(log["files_read"])
        queue.put({
            "type": "done", "side": side,
            "log": {
                "tool_calls": log["tool_calls"],
                "read_calls": log["read_calls"],
                "grep_calls": log["grep_calls"],
                "list_calls": log["list_calls"],
                "files_read": log["files_read"],
                "files_read_unique": list(read_set),
                "n_files_read": len(read_set),
                "greps": log["greps"],
                "total_chars_consumed": log["total_chars_consumed"],
                "final_response": final_text or "",
                "reasoning_log": reasoning_texts,
            }
        })
    except Exception as e:
        queue.put({"type": "error", "side": side, "error": f"{type(e).__name__}: {str(e)}"})
        traceback.print_exc()


# ─── Provider implementations (mirrors run_agent_multi.py exactly, + event emission) ───

def _run_gemini(problem, model_id, fns, log, side, queue, temperature, max_turns, reasoning_texts, system_prompt):
    from google import genai
    from google.genai import types as gt

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    tools_decl = [gt.Tool(function_declarations=[
        gt.FunctionDeclaration(name="list_files", description="List files in a directory",
            parameters=gt.Schema(type="OBJECT", properties={"directory": gt.Schema(type="STRING")})),
        gt.FunctionDeclaration(name="read_file", description="Read a source file",
            parameters=gt.Schema(type="OBJECT", required=["path"],
                                 properties={"path": gt.Schema(type="STRING")})),
        gt.FunctionDeclaration(name="grep", description="Search for a pattern",
            parameters=gt.Schema(type="OBJECT", required=["pattern"],
                                 properties={"pattern": gt.Schema(type="STRING"),
                                             "directory": gt.Schema(type="STRING")})),
    ])]

    config = gt.GenerateContentConfig(system_instruction=system_prompt,
                                      tools=tools_decl, temperature=temperature)
    history = [gt.Content(role="user",
        parts=[gt.Part(text=f"Problem:\n\n{problem}\n\nStart by listing the root directory.")])]
    final_text = ""

    for turn in range(max_turns):
        queue.put({"type": "turn_start", "side": side, "turn": turn + 1})
        resp = ram.call_with_retry(client.models.generate_content,
                               model=model_id, contents=history, config=config)
        cand = resp.candidates[0]
        if not cand.content:
            break
        history.append(cand.content)

        text_parts = [p.text for p in cand.content.parts if p.text]
        if text_parts:
            reasoning = "\n".join(text_parts)
            reasoning_texts.append(reasoning)
            queue.put({"type": "reasoning", "side": side, "text": reasoning[:2000]})

        tool_parts = [p for p in cand.content.parts if p.function_call is not None]
        if not tool_parts:
            final_text = "\n".join(text_parts)
            break

        results = []
        for p in tool_parts:
            fc = p.function_call
            args = dict(fc.args)
            res = fns[fc.name](**args) if fc.name in fns else "unknown"
            results.append(gt.Part(function_response=gt.FunctionResponse(
                name=fc.name, response={"result": res})))
        history.append(gt.Content(role="tool", parts=results))

    if not final_text:
        history.append(gt.Content(role="user", parts=[gt.Part(text=ram.FORCE_FINAL_PROMPT)]))
        config_no_tools = gt.GenerateContentConfig(system_instruction=system_prompt, temperature=temperature)
        resp = ram.call_with_retry(client.models.generate_content,
                               model=model_id, contents=history, config=config_no_tools)
        cand = resp.candidates[0]
        if cand.content:
            final_text = "".join(p.text for p in cand.content.parts if p.text)

    return final_text


def _run_anthropic(problem, model_id, fns, log, side, queue, temperature, max_turns, reasoning_texts, system_prompt):
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    tools = [
        {"name": "list_files", "description": "List files in a directory",
         "input_schema": {"type": "object", "properties": {"directory": {"type": "string", "default": "."}}}},
        {"name": "read_file", "description": "Read a source file",
         "input_schema": {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}}},
        {"name": "grep", "description": "Search for a pattern",
         "input_schema": {"type": "object", "required": ["pattern"],
                          "properties": {"pattern": {"type": "string"}, "directory": {"type": "string", "default": "."}}}},
    ]
    messages = [{"role": "user", "content": f"Problem:\n\n{problem}\n\nStart by listing the root directory."}]
    final_text = ""

    for turn in range(max_turns):
        queue.put({"type": "turn_start", "side": side, "turn": turn + 1})
        resp = ram.call_with_retry(client.messages.create, model=model_id, max_tokens=4096,
                               system=system_prompt, tools=tools, messages=messages, temperature=temperature)
        messages.append({"role": "assistant", "content": resp.content})

        text_blocks = [b.text for b in resp.content if b.type == "text"]
        if text_blocks:
            reasoning = "\n".join(text_blocks)
            reasoning_texts.append(reasoning)
            queue.put({"type": "reasoning", "side": side, "text": reasoning[:2000]})

        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            final_text = "\n".join(text_blocks)
            break

        tool_results = []
        for tu in tool_uses:
            res = fns[tu.name](**tu.input) if tu.name in fns else "unknown"
            tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": res})
        messages.append({"role": "user", "content": tool_results})

    if not final_text:
        messages.append({"role": "user", "content": ram.FORCE_FINAL_PROMPT})
        resp = ram.call_with_retry(client.messages.create, model=model_id, max_tokens=4096,
                               system=system_prompt, messages=messages, temperature=temperature)
        final_text = "".join(b.text for b in resp.content if b.type == "text")

    return final_text


def _run_openai(problem, model_id, fns, log, side, queue, temperature, max_turns, reasoning_texts, system_prompt):
    from openai import OpenAI
    if "deepseek" in model_id.lower():
        client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY", ""), base_url="https://api.deepseek.com/v1")
    else:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

    tools = [
        {"type": "function", "function": {"name": "list_files", "description": "List files in a directory",
            "parameters": {"type": "object", "properties": {"directory": {"type": "string", "default": "."}}}}},
        {"type": "function", "function": {"name": "read_file", "description": "Read a source file",
            "parameters": {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}}}},
        {"type": "function", "function": {"name": "grep", "description": "Search for a pattern",
            "parameters": {"type": "object", "required": ["pattern"],
                           "properties": {"pattern": {"type": "string"}, "directory": {"type": "string", "default": "."}}}}},
    ]
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Problem:\n\n{problem}\n\nStart by listing the root directory."}
    ]
    final_text = ""

    for turn in range(max_turns):
        queue.put({"type": "turn_start", "side": side, "turn": turn + 1})
        is_reasoning = any(x in model_id for x in ("o1", "o3"))
        create_kwargs = dict(model=model_id, messages=messages, tools=tools)
        if not is_reasoning:
            create_kwargs["temperature"] = temperature

        resp = ram.call_with_retry(client.chat.completions.create, **create_kwargs)
        msg = resp.choices[0].message
        messages.append(msg)

        if msg.content:
            reasoning_texts.append(msg.content)
            queue.put({"type": "reasoning", "side": side, "text": msg.content[:2000]})

        if not msg.tool_calls:
            final_text = msg.content or ""
            break

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            res = fns[tc.function.name](**args) if tc.function.name in fns else "unknown"
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": res})

    if not final_text:
        messages.append({"role": "user", "content": ram.FORCE_FINAL_PROMPT})
        create_kwargs = dict(model=model_id, messages=messages)
        if not any(x in model_id for x in ("o1", "o3")):
            create_kwargs["temperature"] = temperature
        resp = ram.call_with_retry(client.chat.completions.create, **create_kwargs)
        final_text = resp.choices[0].message.content or ""

    return final_text


def _run_codex(problem, model_id, fns, log, side, queue, temperature, max_turns, reasoning_texts, system_prompt):
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    tools = [
        {"type": "function", "name": "list_files", "description": "List files in a directory",
         "parameters": {"type": "object", "properties": {"directory": {"type": "string", "default": "."}}}},
        {"type": "function", "name": "read_file", "description": "Read a source file",
         "parameters": {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}}},
        {"type": "function", "name": "grep", "description": "Search for a pattern",
         "parameters": {"type": "object", "required": ["pattern"],
                        "properties": {"pattern": {"type": "string"}, "directory": {"type": "string", "default": "."}}}},
    ]

    initial_input = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Problem:\n\n{problem}\n\nStart by listing the root directory."},
    ]
    final_text = ""
    previous_response_id = None
    next_input = initial_input

    for turn in range(max_turns):
        queue.put({"type": "turn_start", "side": side, "turn": turn + 1})
        create_kwargs = dict(model=model_id, input=next_input, tools=tools, temperature=temperature)
        if previous_response_id:
            create_kwargs["previous_response_id"] = previous_response_id

        resp = ram.call_with_retry(client.responses.create, **create_kwargs)
        previous_response_id = resp.id

        tool_calls_found = []
        for item in resp.output:
            if item.type == "function_call":
                tool_calls_found.append(item)
            elif item.type == "message":
                for block in item.content:
                    if hasattr(block, "text"):
                        final_text = block.text
                        reasoning_texts.append(block.text)
                        queue.put({"type": "reasoning", "side": side, "text": block.text[:2000]})

        if not tool_calls_found:
            break

        tool_results = []
        for tc in tool_calls_found:
            args = json.loads(tc.arguments)
            res = fns[tc.name](**args) if tc.name in fns else "unknown"
            tool_results.append({"type": "function_call_output", "call_id": tc.call_id, "output": res})
        next_input = tool_results

    if not final_text:
        next_input = [{"role": "user", "content": ram.FORCE_FINAL_PROMPT}]
        create_kwargs = dict(model=model_id, input=next_input, temperature=temperature)
        if previous_response_id:
            create_kwargs["previous_response_id"] = previous_response_id
        resp = ram.call_with_retry(client.responses.create, **create_kwargs)
        for item in resp.output:
            if item.type == "message":
                for block in item.content:
                    if hasattr(block, "text"):
                        final_text = block.text

    return final_text or ""


# ═══════════════════════════════════════════
#  FLASK APP
# ═══════════════════════════════════════════

app = Flask(__name__)

# Global state for SSE
active_queue = None
active_gt = None
active_run_meta = None
active_final_texts = {}
active_reasoning = {}


@app.route("/")
def index():
    return send_file(str(UI_FILE))


@app.route("/api/models")
def api_models():
    available = {}
    for name, cfg in ram.MODELS.items():
        p = cfg["provider"]
        has_key = False
        if p == "gemini":      has_key = bool(os.getenv("GEMINI_API_KEY"))
        elif p == "anthropic": has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
        elif p in ("openai", "codex"): has_key = bool(os.getenv("OPENAI_API_KEY"))
        if "deepseek" in name: has_key = bool(os.getenv("DEEPSEEK_API_KEY"))
        available[name] = {"provider": p, "available": has_key}
    return jsonify(available)


@app.route("/api/tasks")
def api_tasks():
    with open(TASKS_FILE) as f:
        tasks = json.load(f)
    return jsonify([{
        "id": t["instance_id"].replace("django__django-", ""),
        "instance_id": t["instance_id"],
        "name": t["problem_statement"][:100],
        "n_files": t["n_files"],
        "gt": t["files_in_patch"]
    } for t in tasks])


@app.route("/api/run", methods=["POST"])
def api_run():
    global active_queue, active_gt, active_run_meta, active_final_texts, active_reasoning

    data = request.json
    model_name = data.get("model")
    task_id = data.get("task_id")

    if model_name not in ram.MODELS:
        return jsonify({"error": f"Unknown model: {model_name}"}), 400

    cfg = ram.MODELS[model_name]
    instance_id = f"django__django-{task_id}"

    with open(TASKS_FILE) as f:
        tasks = json.load(f)
    task = next((t for t in tasks if t["instance_id"] == instance_id), None)
    if not task:
        return jsonify({"error": f"Task not found: {instance_id}"}), 400

    ctrl_dir = PROJECTS_DIR / instance_id / "control"
    cdna_dir = PROJECTS_DIR / instance_id / "codedna"

    if not ctrl_dir.exists() or not cdna_dir.exists():
        return jsonify({"error": f"Repos not set up for {instance_id}"}), 400

    active_queue = Queue()
    active_gt = task["files_in_patch"]
    active_run_meta = {"model": model_name, "task_id": task_id,
                       "instance_id": instance_id, "repo": task["repo"]}
    active_final_texts.clear()
    active_reasoning.clear()

    problem = task["problem_statement"]
    active_queue.put({"type": "task_info", "task_id": task_id, "gt": active_gt,
                      "n_gt": len(active_gt), "model": model_name})

    # Run sequentially (control first, then codedna) to avoid rate limits
    def run_sequential():
        run_with_streaming(problem, ctrl_dir, cfg["provider"], cfg["model_id"],
                           "control", active_queue, temperature=0, max_turns=30,
                           system_prompt=ram.SYSTEM_PROMPT)
        time.sleep(2)  # brief pause between runs
        run_with_streaming(problem, cdna_dir, cfg["provider"], cfg["model_id"],
                           "codedna", active_queue, temperature=0, max_turns=30,
                           system_prompt=ram.CODEDNA_PROMPT)

    threading.Thread(target=run_sequential, daemon=True).start()

    return jsonify({"status": "started", "task_id": task_id, "model": model_name})


@app.route("/api/stream")
def api_stream():
    def gen():
        global active_queue, active_gt, active_run_meta, active_final_texts
        if not active_queue:
            yield f"data: {json.dumps({'type': 'error', 'error': 'No active run'})}\n\n"
            return

        done_sides = set()
        side_results = {}

        while len(done_sides) < 2:
            try:
                event = active_queue.get(timeout=120)
            except Empty:
                yield f"data: {json.dumps({'type': 'timeout'})}\n\n"
                break

            if event.get("type") == "final_response":
                active_final_texts[event["side"]] = event.get("text", "")
                proposed = ram.extract_proposed_files(event.get("text", ""))
                if active_gt:
                    event["metrics_proposed"] = ram.file_metrics(proposed, active_gt)

            if event.get("type") == "done" and active_gt:
                side = event["side"]
                log_data = event["log"]
                files_read = set(log_data["files_read"])
                event["metrics_read"] = ram.file_metrics(files_read, active_gt)
                final_text = log_data.get("final_response", "")
                proposed = ram.extract_proposed_files(final_text)
                event["metrics_proposed"] = ram.file_metrics(proposed, active_gt)
                done_sides.add(side)
                side_results[side] = {**log_data, "metrics_read": event["metrics_read"],
                                      "metrics_proposed": event["metrics_proposed"]}

            if event.get("type") == "error":
                done_sides.add(event.get("side", "both"))

            yield f"data: {json.dumps(event)}\n\n"

        # Save results
        if active_run_meta and side_results:
            _save_run_results(active_run_meta, side_results, active_gt)

        yield f"data: {json.dumps({'type': 'all_done'})}\n\n"

    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _save_run_results(meta, side_results, gt):
    """Save to runs/<model>/results.json in same format as run_agent_multi.py."""
    run_dir = RUNS_DIR / meta["model"].replace('/', '-')
    run_dir.mkdir(parents=True, exist_ok=True)
    out_file = run_dir / "results.json"

    existing = []
    if out_file.exists():
        try:
            existing = json.load(open(out_file))
        except json.JSONDecodeError:
            existing = []

    new_entry = {
        "instance_id": meta["instance_id"],
        "repo": meta["repo"],
        "ground_truth_files": gt,
        "control": side_results.get("control"),
        "codedna": side_results.get("codedna"),
    }

    replaced = False
    for i, entry in enumerate(existing):
        if entry.get("instance_id") == meta["instance_id"]:
            existing[i] = new_entry
            replaced = True
            break
    if not replaced:
        existing.append(new_entry)

    with open(out_file, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"💾 Saved → {out_file}  ({meta['instance_id']})")


if __name__ == "__main__":
    print(f"🧬 CodeDNA Benchmark Server")
    print(f"   Tasks: {TASKS_FILE}")
    print(f"   Projects: {PROJECTS_DIR}")
    print(f"   UI: {UI_FILE}")

    keys = {
        "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY")),
        "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "DEEPSEEK_API_KEY": bool(os.getenv("DEEPSEEK_API_KEY")),
    }
    for k, v in keys.items():
        print(f"   {k}: {'✅' if v else '❌'}")

    print(f"\n   Open http://localhost:5001\n")
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)
