"""
run_enterprise.py — Benchmark su codebase enterprise (57 file, 5 bug).

Esegue l'agente Gemini su 3 bug diversi in entrambe le versioni
(enterprise_control e enterprise_codedna) e produce un report comparativo.
"""

import os, json
from pathlib import Path
from agent import run_agent, AgentMetrics, TASK, SYSTEM_PROMPT, TOOLS, MODEL, GEMINI_API_KEY
from google.genai import types
from google import genai

BASE = Path(__file__).parent / "projects"
CTRL = BASE / "enterprise_control"
CDNA = BASE / "enterprise_codedna"

# ── Task definitions per ogni bug ──────────────────────────────────────────────

TASKS = {
    "B1_suspended_revenue": {
        "task": """\
BUG REPORT: Il report mensile delle entrate (revenue) mostra cifre gonfiate.
Dopo analisi, sospettiamo che i tenant SOSPESI vengano inclusi nel totale.
Naviga il codebase per trovare: quale file/funzione calcola il revenue mensile?
Dove viene costruita la query che aggrega le fatture? Il filtro tenant suspension è applicato?
Indica: FILE_DA_MODIFICARE, MOTIVO, FIX.""",
        "correct_files": {"analytics/revenue.py"},
    },
    "B3_admin_permission": {
        "task": """\
BUG REPORT: La creazione di prodotti tramite API è accessibile anche a utenti non-admin.
Il check di permesso non funziona correttamente.
Naviga il codebase per trovare: come viene verificato il ruolo admin nell'API?
Qual è il campo corretto nel token JWT per il ruolo utente?
Indica: FILE_DA_MODIFICARE, MOTIVO, FIX.""",
        "correct_files": {"api/products.py"},
    },
    "B4_fulfillment_inventory": {
        "task": """\
BUG REPORT: Dopo il fulfillment degli ordini, l'inventario non viene decrementato.
I prodotti mostrano stock errato: non vengono scalate le unità vendute.
Naviga il codebase per trovare: dove avviene il fulfillment degli ordini?
L'inventario viene decrementato? Dove dovrebbe avvenire?
Indica: FILE_DA_MODIFICARE, MOTIVO, FIX.""",
        "correct_files": {"orders/fulfillment.py"},
    },
}


def run_single(version: str, root: Path, task_def: dict, verbose: bool = True) -> AgentMetrics:
    """Runs the agent on a specific task and codebase version."""
    client = genai.Client(api_key=GEMINI_API_KEY)

    # Import tool implementations from agent.py
    from agent import _read_file, _list_files, _grep

    metrics = AgentMetrics()
    messages = [types.Content(role="user", parts=[types.Part(text=task_def["task"])])]
    correct_files = task_def["correct_files"]

    if verbose:
        print(f"\n{'='*60}")
        print(f"  AGENTE — {version.upper()}")
        print(f"{'='*60}")

    for turn in range(20):
        metrics.turns = turn + 1
        response = client.models.generate_content(
            model=MODEL,
            contents=messages,
            config=types.GenerateContentConfig(
                tools=TOOLS,
                temperature=0,
                system_instruction=SYSTEM_PROMPT,
            ),
        )
        candidate = response.candidates[0]
        messages.append(types.Content(role="model", parts=candidate.content.parts))

        tool_calls = [p for p in candidate.content.parts if p.function_call]
        text_parts = [p.text for p in candidate.content.parts if p.text]

        if not tool_calls:
            metrics.final_answer = "\n".join(text_parts)
            answer_lower = metrics.final_answer.lower()
            metrics.found_correct = all(f.lower() in answer_lower for f in correct_files)
            if verbose:
                print(f"\n📋 RISPOSTA FINALE:\n{metrics.final_answer[:600]}...")
                print(f"\n✅ File corretti trovati: {metrics.found_correct}")
            break

        tool_results = []
        for part in tool_calls:
            fc = part.function_call
            args = dict(fc.args)
            metrics.total_tool_calls += 1

            if fc.name == "read_file":
                metrics.read_file_calls += 1
                path = args.get("path", "")
                metrics.files_read.append(path)
                result = _read_file(path, root)
                if verbose: print(f"  📖 read_file({path})")
            elif fc.name == "list_files":
                metrics.list_files_calls += 1
                d = args.get("directory", "")
                result = _list_files(d, root)
                if verbose: print(f"  📂 list_files({d or 'root'})")
            elif fc.name == "grep":
                metrics.grep_calls += 1
                pat = args.get("pattern", "")
                d = args.get("directory", "")
                metrics.greps_done.append(pat)
                result = _grep(pat, d, root)
                if verbose: print(f"  🔍 grep('{pat}')")
            else:
                result = "Tool non riconosciuto"

            tool_results.append(types.Part(
                function_response=types.FunctionResponse(name=fc.name, response={"result": result})
            ))

        messages.append(types.Content(role="user", parts=tool_results))

    return metrics


def print_row(label, ctrl, cdna):
    diff = ctrl - cdna
    arrow = f"+{diff} ✅ CodeDNA vince" if diff > 0 else ("~" if diff == 0 else f"{diff} ⚠️ Control vince")
    print(f"{label:<30} {ctrl:^8} {cdna:^8}   {arrow}")


def main():
    print("🧬 CodeDNA Annotation Standard — Enterprise Benchmark")
    print("=" * 66)
    print(f"Codebase: {CTRL.name} vs {CDNA.name}")
    print(f"File per versione: {len(list(CTRL.rglob('*.py')))} (control) / {len(list(CDNA.rglob('*.py')))} (codedna)")
    print("=" * 66)

    all_results = {}

    for bug_id, task_def in TASKS.items():
        print(f"\n\n{'─'*66}")
        print(f"  BUG: {bug_id}")
        print(f"{'─'*66}")

        ctrl_m = run_single("CONTROL", CTRL, task_def, verbose=True)
        cdna_m = run_single("CODEDNA", CDNA, task_def, verbose=True)
        all_results[bug_id] = (ctrl_m, cdna_m)

    # ── Report finale ──────────────────────────────────────────────────────────
    print("\n\n" + "═" * 66)
    print("  RISULTATI COMPARATIVI — ENTERPRISE BENCHMARK")
    print("═" * 66)
    print(f"{'Bug':<20} {'Version':<10} {'Tools':>6} {'Reads':>6} {'Greps':>6} {'Turni':>6} {'Trovato':>8}")
    print("─" * 66)

    total_ctrl_tools = 0
    total_cdna_tools = 0

    for bug_id, (ctrl, cdna) in all_results.items():
        short = bug_id[:18]
        print(f"{short:<20} control    {ctrl.total_tool_calls:>6} {ctrl.read_file_calls:>6} {ctrl.grep_calls:>6} {ctrl.turns:>6} {'✅' if ctrl.found_correct else '❌':>8}")
        print(f"{'':20} codedna    {cdna.total_tool_calls:>6} {cdna.read_file_calls:>6} {cdna.grep_calls:>6} {cdna.turns:>6} {'✅' if cdna.found_correct else '❌':>8}")
        print()
        total_ctrl_tools += ctrl.total_tool_calls
        total_cdna_tools += cdna.total_tool_calls

    print("─" * 66)
    savings = total_ctrl_tools - total_cdna_tools
    pct = round(savings / total_ctrl_tools * 100) if total_ctrl_tools > 0 else 0
    print(f"{'TOTALE TOOL CALLS':<30} {total_ctrl_tools:^8} {total_cdna_tools:^8}   -{savings} ({pct}% meno con CodeDNA)")
    print("═" * 66)

    # salva JSON
    out = {}
    for bug_id, (ctrl, cdna) in all_results.items():
        out[bug_id] = {
            "control": {"tools": ctrl.total_tool_calls, "reads": ctrl.read_file_calls, "greps": ctrl.grep_calls, "found": ctrl.found_correct},
            "codedna": {"tools": cdna.total_tool_calls, "reads": cdna.read_file_calls, "greps": cdna.grep_calls, "found": cdna.found_correct},
        }
    out_file = Path(__file__).parent / "results_enterprise.json"
    out_file.write_text(json.dumps(out, indent=2))
    print(f"\n✅ Risultati salvati in {out_file.name}")


if __name__ == "__main__":
    main()
