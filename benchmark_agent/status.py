#!/usr/bin/env python3
"""One-shot status snapshot for benchmark jobs. No loop, no clear screen."""
import sys
from pathlib import Path

TMPDIR = Path("/private/tmp/claude-501/-Users-fabriziocorpora-Desktop-automation-lab-dynamic-bi-factory-codedna/e90886ea-a00e-4ebd-9c2a-afb5ab1d25e5/tasks")

JOBS = {
    "bzptxufi0": "gemini-2.5-flash",
    "bwkt09hap": "deepseek-chat",
    "bgvjzo9qa": "gemini-2.5-pro",
}

def parse_log(content: str):
    tasks_done, current_task, current_step = 0, None, None
    mean_f1s = []
    for line in content.splitlines():
        s = line.strip()
        if "Task:" in s and "ground-truth" in s:
            current_task = s.split("Task:")[-1].strip()
        if "→ CONTROL" in s or "→ CODEDNA" in s or "→ AGENT" in s:
            current_step = s.lstrip("→ ").strip()
        if "Mean F1" in s:
            tasks_done += 1
            mean_f1s.append(s)
    done   = "✅ Saved →" in content
    error  = "Traceback" in content
    return tasks_done, current_task, current_step, mean_f1s, done, error

def main():
    job_ids = sys.argv[1:] if len(sys.argv) > 1 else list(JOBS.keys())

    for jid in job_ids:
        fpath = TMPDIR / f"{jid}.output"
        model = JOBS.get(jid, jid)
        content = fpath.read_text(errors="replace") if fpath.exists() else ""

        tasks_done, cur_task, cur_step, mean_f1s, done, error = parse_log(content)

        status = "✅ DONE" if done else ("❌ ERROR" if error else "⏳ running")
        print(f"{'─'*65}")
        print(f"  {model:<25} [{jid}]  {status}")
        print(f"  Tasks completati: {tasks_done}/5")
        if cur_task and not done:
            print(f"  Ora su: {cur_task}")
            print(f"  Step:   {cur_step or '?'}")
        if mean_f1s:
            print(f"  Risultati per task:")
            for line in mean_f1s:
                print(f"    {line.strip()}")

    print(f"{'─'*65}")
    all_done = all(
        "✅ Saved →" in (TMPDIR / f"{jid}.output").read_text(errors="replace")
        for jid in job_ids if (TMPDIR / f"{jid}.output").exists()
    )
    if all_done:
        print("  🎉 Tutti i job completati! Lancia: python swebench/analyze_multi.py")

if __name__ == "__main__":
    main()
