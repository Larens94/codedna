"""
swebench/run_agent.py — Runs Gemini agent on Control vs CodeDNA for each task.

deps:    google-genai (google.genai), tasks.json, projects_swebench/*/control and codedna/
exports: results_swebench.json — complete metrics per task/version
rules:   Run control FIRST, then codedna, same process but independent conversations.
         Agent receives ONLY the problem_statement — no knowledge of CodeDNA benchmark.
"""

import json
import os
import re
import sys
import subprocess
from pathlib import Path
from typing import Callable

try:
    from google import genai
    from google.genai import types as gtypes
except ImportError:
    print("ERROR: pip install google-genai")
    sys.exit(1)

TASKS_FILE   = Path(__file__).parent / "tasks.json"
PROJECTS_DIR = Path(__file__).parent.parent / "projects_swebench"
RESULTS_FILE = Path(__file__).parent.parent / "results_swebench.json"
API_KEY      = os.getenv("GEMINI_API_KEY", "")
MODEL_ID     = "gemini-2.5-flash"

# Truncation limits (documented experimental parameters)
READ_FILE_LIMIT = 8000   # characters returned per read_file call
GREP_LIMIT      = 4000   # characters returned per grep call

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

TOOLS_DECL = [
    gtypes.Tool(function_declarations=[
        gtypes.FunctionDeclaration(
            name="list_files",
            description="List files in a directory of the codebase",
            parameters=gtypes.Schema(
                type="OBJECT",
                properties={
                    "directory": gtypes.Schema(type="STRING", description="Relative path, default '.'")
                },
            ),
        ),
        gtypes.FunctionDeclaration(
            name="read_file",
            description="Read the content of a source file",
            parameters=gtypes.Schema(
                type="OBJECT",
                required=["path"],
                properties={
                    "path": gtypes.Schema(type="STRING", description="Relative file path")
                },
            ),
        ),
        gtypes.FunctionDeclaration(
            name="grep",
            description="Search for a pattern across the codebase",
            parameters=gtypes.Schema(
                type="OBJECT",
                required=["pattern"],
                properties={
                    "pattern": gtypes.Schema(type="STRING", description="Text pattern"),
                    "directory": gtypes.Schema(type="STRING", description="Directory, default '.'"),
                },
            ),
        ),
    ])
]


def make_fns(repo_root: Path) -> tuple[dict[str, Callable], dict]:
    log = {"tool_calls": 0, "files_read": [], "greps": [], "total_chars_consumed": 0}

    def list_files(directory: str = ".", **kwargs) -> str:
        log["tool_calls"] += 1
        target = repo_root / directory
        if not target.exists():
            return f"Directory not found: {directory}"
        items = []
        for item in sorted(target.iterdir()):
            if item.name.startswith(".") or item.name == "__pycache__":
                continue
            items.append(f"{'[DIR] ' if item.is_dir() else '      '}{item.name}")
        result = "\n".join(items) or "(empty)"
        log["total_chars_consumed"] += len(result)
        return result

    def read_file(path: str, **kwargs) -> str:
        log["tool_calls"] += 1
        target = repo_root / path
        if not target.exists():
            return f"File not found: {path}"
        log["files_read"].append(path)
        result = target.read_text(encoding="utf-8", errors="replace")[:READ_FILE_LIMIT]
        log["total_chars_consumed"] += len(result)
        return result

    def grep(pattern: str, directory: str = ".", **kwargs) -> str:
        log["tool_calls"] += 1
        log["greps"].append(pattern)
        target = repo_root / directory
        r = subprocess.run(
            ["grep", "-rn", "--include=*.py", pattern, str(target)],
            capture_output=True, text=True
        )
        result = r.stdout[:GREP_LIMIT] or "(no matches)"
        log["total_chars_consumed"] += len(result)
        return result

    fns = {"list_files": list_files, "read_file": read_file, "grep": grep}
    return fns, log


def run_agent(problem: str, repo_root: Path, client, max_turns: int = 15) -> dict:
    fns, log = make_fns(repo_root)
    config   = gtypes.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=TOOLS_DECL,
        temperature=0,
    )

    history = [
        gtypes.Content(
            role="user",
            parts=[gtypes.Part(text=f"Problem:\n\n{problem}\n\nStart by listing the root directory.")]
        )
    ]
    final_text = ""

    for _ in range(max_turns):
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=history,
            config=config,
        )
        candidate = response.candidates[0]
        if not candidate.content:
            print("  [!] Empty response from model (safety filter or max tokens). Early stop.", flush=True)
            break

        history.append(candidate.content)

        tool_calls_this_turn = [
            p for p in candidate.content.parts
            if p.function_call is not None
        ]

        if not tool_calls_this_turn:
            # Text-only response = agent is done
            for p in candidate.content.parts:
                if p.text:
                    final_text = p.text
            break

        # Execute all tool calls and add results
        tool_results = []
        for part in tool_calls_this_turn:
            fc   = part.function_call
            name = fc.name
            args = dict(fc.args)
            res  = fns[name](**args) if name in fns else "unknown function"
            tool_results.append(
                gtypes.Part(function_response=gtypes.FunctionResponse(
                    name=name, response={"result": res}
                ))
            )

        history.append(gtypes.Content(role="tool", parts=tool_results))

    return {
        "tool_calls":          log["tool_calls"],
        "files_read":          log["files_read"],
        "n_files_read":        len(set(log["files_read"])),
        "greps":               log["greps"],
        "total_chars_consumed": log["total_chars_consumed"],
        "final_response":      final_text[:1200],
    }


def extract_proposed_files(final_text: str) -> set[str]:
    """Extract .py file paths mentioned in the agent's final textual response."""
    return set(re.findall(r'[\w/]+\.py', final_text))


def file_metrics(files: set[str], ground_truth: list[str]) -> dict:
    """Compute recall, precision, and F1 using full relative paths.
    
    - recall:    what fraction of ground-truth files did the agent touch?
    - precision: what fraction of files touched were actually relevant?
    - f1:        harmonic mean of recall and precision
    """
    truth = set(ground_truth)
    if not truth:
        return {"recall": 0.0, "precision": 0.0, "f1": 0.0}
    
    hits = files & truth
    recall    = len(hits) / len(truth)       if truth else 0.0
    precision = len(hits) / len(files)       if files else 0.0
    f1        = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.0
    return {"recall": recall, "precision": precision, "f1": f1}


def main():
    if not API_KEY:
        print("ERROR: export GEMINI_API_KEY=<your_key>")
        sys.exit(1)

    client = genai.Client(api_key=API_KEY)

    with open(TASKS_FILE) as f:
        tasks = json.load(f)

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

        print(f"\n{'='*60}")
        print(f"Task: {iid}  ({len(gt)} ground-truth files)")

        # --- CONTROL ---
        print("  → CONTROL ...", flush=True)
        ctrl = run_agent(problem, ctrl_dir, client)
        ctrl_read_set  = set(ctrl["files_read"])
        ctrl_proposed  = extract_proposed_files(ctrl["final_response"])
        ctrl["metrics_read"]     = file_metrics(ctrl_read_set, gt)
        ctrl["metrics_proposed"] = file_metrics(ctrl_proposed, gt)

        # --- CODEDNA ---
        print("  → CODEDNA ...", flush=True)
        cdna = run_agent(problem, cdna_dir, client)
        cdna_read_set  = set(cdna["files_read"])
        cdna_proposed  = extract_proposed_files(cdna["final_response"])
        cdna["metrics_read"]     = file_metrics(cdna_read_set, gt)
        cdna["metrics_proposed"] = file_metrics(cdna_proposed, gt)

        r = {
            "instance_id":       iid,
            "repo":              task["repo"],
            "ground_truth_files": gt,
            "control":           ctrl,
            "codedna":           cdna,
        }

        cr = ctrl["metrics_read"]
        dr = cdna["metrics_read"]
        cp = ctrl["metrics_proposed"]
        dp = cdna["metrics_proposed"]
        print(f"  Control: {ctrl['tool_calls']} calls, {ctrl['total_chars_consumed']} chars | "
              f"read(R={cr['recall']:.0%} P={cr['precision']:.0%} F1={cr['f1']:.0%}) | "
              f"proposed(R={cp['recall']:.0%} P={cp['precision']:.0%} F1={cp['f1']:.0%})")
        print(f"  CodeDNA: {cdna['tool_calls']} calls, {cdna['total_chars_consumed']} chars | "
              f"read(R={dr['recall']:.0%} P={dr['precision']:.0%} F1={dr['f1']:.0%}) | "
              f"proposed(R={dp['recall']:.0%} P={dp['precision']:.0%} F1={dp['f1']:.0%})")
        results.append(r)

    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Results → {RESULTS_FILE}")
    print("Next: python swebench/analyze.py")


if __name__ == "__main__":
    main()
