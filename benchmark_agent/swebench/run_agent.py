"""
swebench/run_agent.py — Esegue l'agente Gemini su Control vs CodeDNA per ogni task.

deps:    google-genai (google.genai), tasks.json, projects_swebench/*/control and codedna/
exports: results_swebench.json — metriche complete per task/versione
rules:   Run control FIRST, then codedna, same session.
         Agent receives ONLY the problem_statement — no knowledge of CodeDNA benchmark.
"""

import json
import os
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
MODEL_ID     = "gemini-2.5-flash-preview-04-17"

SYSTEM_PROMPT = """You are an expert software engineer debugging a Python codebase.
Your task: read the problem description and find the root cause by navigating the codebase.

Tools available:
- list_files(directory): list files in a directory
- read_file(path): read a source file
- grep(pattern, directory): search for a pattern

Strategy:
1. Start by listing the root directory to understand the structure
2. Identify which modules are most likely related to the problem
3. Read the relevant files and trace the issue
4. Report: which file(s) contain the root cause and what the fix should be

Be efficient. Read only what you need. Stop when you have identified the root cause.
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
    log = {"tool_calls": 0, "files_read": [], "greps": []}

    def list_files(directory: str = ".") -> str:
        log["tool_calls"] += 1
        target = repo_root / directory
        if not target.exists():
            return f"Directory not found: {directory}"
        items = []
        for item in sorted(target.iterdir()):
            if item.name.startswith(".") or item.name == "__pycache__":
                continue
            items.append(f"{'[DIR] ' if item.is_dir() else '      '}{item.name}")
        return "\n".join(items) or "(empty)"

    def read_file(path: str) -> str:
        log["tool_calls"] += 1
        target = repo_root / path
        if not target.exists():
            return f"File not found: {path}"
        log["files_read"].append(path)
        return target.read_text(encoding="utf-8", errors="replace")[:4000]

    def grep(pattern: str, directory: str = ".") -> str:
        log["tool_calls"] += 1
        log["greps"].append(pattern)
        target = repo_root / directory
        r = subprocess.run(
            ["grep", "-rn", "--include=*.py", pattern, str(target)],
            capture_output=True, text=True
        )
        return r.stdout[:2000] or "(no matches)"

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
        "tool_calls":  log["tool_calls"],
        "files_read":  log["files_read"],
        "n_files_read": len(set(log["files_read"])),
        "greps":        log["greps"],
        "final_response": final_text[:600],
    }


def file_accuracy(files_read: list[str], ground_truth: list[str]) -> float:
    if not ground_truth:
        return 0.0
    read  = {Path(f).name for f in files_read}
    truth = {Path(f).name for f in ground_truth}
    return len(read & truth) / len(truth)


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

        print("  → CONTROL ...")
        ctrl = run_agent(problem, ctrl_dir, client)
        ctrl["file_accuracy"] = file_accuracy(ctrl["files_read"], gt)

        print("  → CODEDNA ...")
        cdna = run_agent(problem, cdna_dir, client)
        cdna["file_accuracy"] = file_accuracy(cdna["files_read"], gt)

        r = {
            "instance_id":       iid,
            "repo":              task["repo"],
            "ground_truth_files": gt,
            "control":           ctrl,
            "codedna":           cdna,
            "delta_tool_calls":  ctrl["tool_calls"] - cdna["tool_calls"],
            "delta_file_accuracy": cdna["file_accuracy"] - ctrl["file_accuracy"],
        }

        print(f"  Control: {ctrl['tool_calls']} calls, acc={ctrl['file_accuracy']:.0%}")
        print(f"  CodeDNA: {cdna['tool_calls']} calls, acc={cdna['file_accuracy']:.0%}")
        results.append(r)

    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Results → {RESULTS_FILE}")
    print("Next: python swebench/analyze.py")


if __name__ == "__main__":
    main()
