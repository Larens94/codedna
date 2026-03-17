#!/usr/bin/env python3
"""
watch_jobs.py — Live monitor for benchmark background jobs.
Usage: python watch_jobs.py job1 job2 job3 ...
       python watch_jobs.py  # auto-detects running run_agent_multi.py processes
"""
import os
import sys
import time
import subprocess
from pathlib import Path

TMPDIR = Path("/private/tmp/claude-501/-Users-fabriziocorpora-Desktop-automation-lab-dynamic-bi-factory-codedna/e90886ea-a00e-4ebd-9c2a-afb5ab1d25e5/tasks")

TAIL_LINES = 6
REFRESH    = 3  # seconds

def get_running_jobs():
    """Find active run_agent_multi.py processes and their output files."""
    r = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    jobs = []
    for line in r.stdout.splitlines():
        if "run_agent_multi.py" in line and "grep" not in line:
            # Extract model name from --model flag
            model = "unknown"
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "--model" and i + 1 < len(parts):
                    model = parts[i + 1]
            jobs.append(model)
    return jobs

def read_tail(filepath: Path, n: int) -> list[str]:
    try:
        lines = filepath.read_text(errors="replace").splitlines()
        return lines[-n:] if len(lines) >= n else lines
    except Exception:
        return ["(no output yet)"]

def clear():
    os.system("clear")

def color(text, code):
    return f"\033[{code}m{text}\033[0m"

def main():
    job_ids = sys.argv[1:]

    # If job IDs given, use them; otherwise scan for output files newer than 2h
    if job_ids:
        files = {jid: TMPDIR / f"{jid}.output" for jid in job_ids}
    else:
        files = {f.stem: f for f in sorted(TMPDIR.glob("*.output"),
                                            key=lambda x: x.stat().st_mtime,
                                            reverse=True)[:6]}

    if not files:
        print("No job files found. Pass job IDs as arguments or check the tmp dir.")
        sys.exit(1)

    print(color(f"Watching {len(files)} job(s) — refresh every {REFRESH}s — Ctrl+C to quit", "1;36"))
    time.sleep(1)

    try:
        while True:
            clear()
            running = get_running_jobs()
            print(color(f"  CodeDNA Benchmark Monitor — {time.strftime('%H:%M:%S')}  |  Active processes: {len(running)}", "1;36"))
            print()

            for jid, fpath in files.items():
                # Determine status
                exists = fpath.exists()
                lines  = read_tail(fpath, TAIL_LINES) if exists else ["(waiting...)"]

                # Guess model name from content
                model = jid
                if exists:
                    for l in fpath.read_text(errors="replace").splitlines()[:10]:
                        if "MODEL:" in l:
                            model = l.split("MODEL:")[-1].strip().rstrip("(provider:").strip()
                            break

                # Detect if done or failed
                content = fpath.read_text(errors="replace") if exists else ""
                done    = "✅ Saved →" in content
                failed  = "Traceback" in content or "ERROR" in content

                if done:
                    status = color("✅ DONE", "1;32")
                elif failed:
                    status = color("❌ ERROR", "1;31")
                else:
                    status = color("⏳ running", "1;33")

                print(color(f"  ┌─ {model:<25} [{jid}]  {status}", "1;37"))
                for line in lines:
                    # Colorize F1 lines
                    if "Mean F1" in line:
                        print(color(f"  │  {line.strip()}", "1;35"))
                    elif "F1=" in line and "%" in line:
                        print(color(f"  │  {line.strip()}", "36"))
                    elif "RateLimitError" in line or "Traceback" in line:
                        print(color(f"  │  {line.strip()}", "31"))
                    elif "Saved →" in line:
                        print(color(f"  │  {line.strip()}", "32"))
                    else:
                        print(f"  │  {line.strip()}")
                print("  └" + "─"*60)
                print()

            all_done = all("✅ Saved →" in (fpath.read_text(errors="replace") if fpath.exists() else "") for fpath in files.values())
            if all_done:
                print(color("  🎉 All jobs completed!", "1;32"))
                print(color("  Run: python swebench/analyze_multi.py", "1;36"))
                break

            time.sleep(REFRESH)

    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
