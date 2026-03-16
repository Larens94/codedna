"""
run_benchmark.py — Runner del benchmark agente reale.

Uso:
    GEMINI_API_KEY=... python run_benchmark.py
"""

import json
from pathlib import Path
from generate_codebase import generate, BASE
from agent import run_agent

def main():
    print("🧬 CodeDNA Annotation Standard — Agent Benchmark")
    print("=" * 60)
    print("Genera codebase su disco...")
    generate("control", BASE)
    generate("codedna", BASE)

    results = {}
    for version in ["control", "codedna"]:
        root = BASE / version
        metrics = run_agent(version, root, verbose=True)
        results[version] = {
            "read_file_calls":  metrics.read_file_calls,
            "list_files_calls": metrics.list_files_calls,
            "grep_calls":       metrics.grep_calls,
            "total_tool_calls": metrics.total_tool_calls,
            "turns":            metrics.turns,
            "files_read":       metrics.files_read,
            "greps_done":       metrics.greps_done,
            "found_correct":    metrics.found_correct,
        }

    # ── Report comparativo ─────────────────────────────────────────────────────
    print("\n")
    print("=" * 60)
    print("  RISULTATI COMPARATIVI")
    print("=" * 60)

    ctrl = results["control"]
    cdna = results["codedna"]

    rows = [
        ("Tool calls totali",   ctrl["total_tool_calls"], cdna["total_tool_calls"]),
        ("read_file chiamate",  ctrl["read_file_calls"],  cdna["read_file_calls"]),
        ("grep chiamate",       ctrl["grep_calls"],       cdna["grep_calls"]),
        ("Turni conversazione", ctrl["turns"],            cdna["turns"]),
        ("Bug trovato?",        ctrl["found_correct"],    cdna["found_correct"]),
    ]

    print(f"{'Metrica':<25} {'CONTROL':>10} {'CODEDNA':>10}  Differenza")
    print("-" * 55)
    for label, c, d in rows:
        if isinstance(c, bool):
            diff = "✅" if (not c and d) else ("❌" if (c and not d) else "~")
            print(f"{label:<25} {str(c):>10} {str(d):>10}  {diff}")
        else:
            diff = c - d
            arrow = "✅ CodeDNA più efficiente" if diff > 0 else ("❌" if diff < 0 else "~")
            print(f"{label:<25} {c:>10} {d:>10}  {'+' if diff > 0 else ''}{diff} {arrow}")

    print("\nFile letti dal Control: ", ctrl["files_read"])
    print("File letti da CodeDNA:  ", cdna["files_read"])
    print("Grep Control: ", ctrl["greps_done"])
    print("Grep CodeDNA: ", cdna["greps_done"])

    # Salva JSON
    out = Path("results_agent.json")
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"\n✅ Risultati salvati in {out}")


if __name__ == "__main__":
    main()
