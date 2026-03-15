"""
Beacon Benchmark Suite
======================
Confronta Beacon (file con manifest embedded) vs. Control (file senza manifest)
su tre metriche: token usage, velocità, qualità delle edit.

Usage:
    pip install tiktoken google-genai
    GEMINI_API_KEY=... python beacon_benchmark.py
"""

import os, time, json, textwrap
import tiktoken
from google import genai
from dataclasses import dataclass, field, asdict
from typing import Literal

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = "gemini-2.0-flash-lite"
RUNS_PER_SCENARIO = 3  # quante volte ripetere ogni test per media

# ─────────────────────────────────────────────────────────────
# FIXTURE: file di codice base (senza manifest)
# ─────────────────────────────────────────────────────────────
CODE_MAIN_NO_MANIFEST = """
from .utils import calcola_kpi, format_currency

def render(execute_query_func):
    rows = execute_query_func("SELECT mese, fatturato, costo FROM ordini ORDER BY mese")
    kpi = calcola_kpi(rows)

    rows_html = ""
    for r in rows:
        margine = r['fatturato'] - r['costo']
        rows_html += f\"\"\"
        <tr class="even:bg-gray-50">
            <td class="px-4 py-2">{r['mese']}</td>
            <td class="px-4 py-2 text-right">{format_currency(r['fatturato'])}</td>
            <td class="px-4 py-2 text-right">{format_currency(r['costo'])}</td>
            <td class="px-4 py-2 text-right">{format_currency(margine)}</td>
        </tr>\"\"\"

    return f\"\"\"
    <div class="p-6">
        <h1 class="text-xl font-bold text-gray-800 mb-4">Report Mensile</h1>
        <div class="grid grid-cols-3 gap-4 mb-6">
            <div class="bg-blue-50 rounded-lg p-4">
                <p class="text-sm text-gray-500">Fatturato Totale</p>
                <p class="text-2xl font-bold">{kpi['totale']}</p>
            </div>
            <div class="bg-green-50 rounded-lg p-4">
                <p class="text-sm text-gray-500">Media Mensile</p>
                <p class="text-2xl font-bold">{kpi['media']}</p>
            </div>
            <div class="bg-purple-50 rounded-lg p-4">
                <p class="text-sm text-gray-500">Margine %</p>
                <p class="text-2xl font-bold">{kpi['margine_pct']}%</p>
            </div>
        </div>
        <table class="w-full text-sm">
            <thead>
                <tr class="bg-gray-100">
                    <th class="px-4 py-2 text-left">Mese</th>
                    <th class="px-4 py-2 text-right">Fatturato</th>
                    <th class="px-4 py-2 text-right">Costo</th>
                    <th class="px-4 py-2 text-right">Margine</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>\"\"\"
""".strip()

CODE_UTILS_NO_MANIFEST = """
def calcola_kpi(rows: list) -> dict:
    if not rows:
        return {'totale': '€0', 'media': '€0', 'margine_pct': '0.0'}
    totale = sum(r['fatturato'] for r in rows)
    costi = sum(r['costo'] for r in rows)
    media = totale / len(rows)
    margine_pct = round((totale - costi) / totale * 100, 1) if totale else 0
    return {
        'totale': format_currency(totale),
        'media': format_currency(media),
        'margine_pct': margine_pct
    }

def format_currency(n: float) -> str:
    return f'€{n:,.0f}'.replace(',', '.')
""".strip()

# Versioni CON manifest Beacon
PYLENS_MANIFEST_MAIN = """# ============================================================
# FILE: main.py
# PURPOSE: Report mensile fatturato/costo/margine con KPI card e tabella
# DEPENDS_ON: utils.py → calcola_kpi(), format_currency()
# EXPORTS: render(execute_query_func) → HTML string
# STYLE: tailwind, nessun grafico
# DB_TABLES: ordini (colonne: mese, fatturato, costo)
# LAST_MODIFIED: prima generazione report mensile
# ============================================================
"""

PYLENS_MANIFEST_UTILS = """# ============================================================
# FILE: utils.py
# PURPOSE: Funzioni helper per aggregazioni KPI e formattazione valute
# DEPENDS_ON: nessuno
# EXPORTS: calcola_kpi(rows) → dict, format_currency(n) → str
# STYLE: nessuno (logica pura)
# DB_TABLES: nessuna
# LAST_MODIFIED: prima generazione helper KPI
# REQUIRED_BY: main.py → blocco KPI card + tabella
# ============================================================
"""

CODE_MAIN_WITH_MANIFEST = PYLENS_MANIFEST_MAIN + "\n" + CODE_MAIN_NO_MANIFEST
CODE_UTILS_WITH_MANIFEST = PYLENS_MANIFEST_UTILS + "\n" + CODE_UTILS_NO_MANIFEST

# Contesto aggiuntivo che il sistema Control deve iniettare nel prompt
# per "compensare" la mancanza di manifest (simula CLAUDE.md approach)
CONTROL_CONTEXT_INJECTION = """CONTEXT (iniettato dal sistema esterno):
- Questo progetto usa Tailwind CSS
- La funzione calcola_kpi è definita in utils.py e ritorna dict con: totale, media, margine_pct
- format_currency è in utils.py e accetta float, ritorna stringa €
- Le query usano la tabella 'ordini' con colonne: mese, fatturato, costo
- L'ultima modifica fatta è stata: prima generazione report mensile
"""

# ─────────────────────────────────────────────────────────────
# SCENARI DI TEST
# ─────────────────────────────────────────────────────────────
SCENARIOS = [
    {
        "id": "S1",
        "name": "Aggiunta colonna semplice",
        "request": "aggiungi la colonna 'nr_ordini' alla tabella. I dati vengono dalla stessa query esistente",
        "files": {"main.py": None, "utils.py": None},  # None = popolato al runtime
        "expected_contains": ["nr_ordini"],
        "must_not_break": ["calcola_kpi", "format_currency"],
    },
    {
        "id": "S2",
        "name": "Modifica cross-file (KPI)",
        "request": "aggiungi una quarta KPI card che mostra il numero totale di mesi nel report",
        "files": {"main.py": None, "utils.py": None},
        "expected_contains": ["n_mesi"],
        "must_not_break": ["calcola_kpi", "format_currency", "render"],
    },
    {
        "id": "S3",
        "name": "Cambio stile (colore header)",
        "request": "cambia il colore dell'header della tabella da bg-gray-100 a bg-blue-100",
        "files": {"main.py": None},
        "expected_contains": ["bg-blue-100"],
        "must_not_break": ["calcola_kpi", "render"],
    },
]


# ─────────────────────────────────────────────────────────────
# MISURATORI
# ─────────────────────────────────────────────────────────────
enc = tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    return len(enc.encode(text))

def build_control_prompt(scenario: dict) -> str:
    files_str = ""
    for fname, code in scenario["files"].items():
        if code:
            files_str += f"\n--- {fname} ---\n```python\n{code}\n```\n"

    return f"""Sei un code editor. Modifica il file main.py apportando SOLO la modifica richiesta.

RICHIESTA: {scenario['request']}

{CONTROL_CONTEXT_INJECTION}

FILE CORRENTI:
{files_str}

Rispondi con blocchi SEARCH/REPLACE nel formato:
<<<<<<< SEARCH
[codice da cercare]
=======
[codice sostitutivo]
>>>>>>> REPLACE"""

def build_beacon_prompt(scenario: dict) -> str:
    files_str = ""
    for fname, code in scenario["files"].items():
        if code:
            files_str += f"\n--- {fname} ---\n```python\n{code}\n```\n"

    return f"""Sei un code editor. Modifica il file main.py apportando SOLO la modifica richiesta.
Leggi il manifest all'inizio di ogni file per capire subito il contesto.

RICHIESTA: {scenario['request']}

FILE CORRENTI (con manifest Beacon embedded):
{files_str}

Rispondi con blocchi SEARCH/REPLACE nel formato:
<<<<<<< SEARCH
[codice da cercare]
=======
[codice sostitutivo]
>>>>>>> REPLACE"""

def judge_quality(scenario: dict, ai_response: str) -> dict:
    """Usa l'AI come giudice per valutare la qualità della risposta."""
    judge_prompt = f"""Sei un valutatore di qualità per sistemi di AI code editing.

RICHIESTA ORIGINALE: {scenario['request']}

RISPOSTA DELL'AI (blocchi SEARCH/REPLACE):
{ai_response}

Valuta la risposta su questi criteri (0-10 ciascuno):
1. CORRETTEZZA: la modifica è corretta e soddisfa la richiesta?
2. SICUREZZA: non rompe funzioni esistenti? (deve mantenere: {scenario['must_not_break']})
3. PRECISIONE: modifica SOLO quello che serve, senza toccare il resto?

Rispondi SOLO con JSON:
{{"correttezza": 0-10, "sicurezza": 0-10, "precisione": 0-10, "note": "breve commento"}}"""

    genai_client = genai.Client(api_key=GEMINI_API_KEY)
    r = genai_client.models.generate_content(model=MODEL, contents=judge_prompt)
    raw = r.text.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = "\n".join(raw.split("\n")[:-1])
    try:
        return json.loads(raw.strip())
    except:
        return {"correttezza": 0, "sicurezza": 0, "precisione": 0, "note": f"parse error: {raw[:100]}"}


# ─────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────
@dataclass
class RunResult:
    scenario_id: str
    approach: Literal["control", "beacon"]
    run: int
    prompt_tokens: int
    response_tokens: int
    total_tokens: int
    time_ms: float
    quality_correttezza: float
    quality_sicurezza: float
    quality_precisione: float
    quality_score: float
    note: str = ""

def run_single(approach: str, prompt: str, scenario: dict, run_idx: int) -> RunResult:
    genai_client = genai.Client(api_key=GEMINI_API_KEY)

    prompt_tokens = count_tokens(prompt)
    t0 = time.perf_counter()
    r = genai_client.models.generate_content(model=MODEL, contents=prompt)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    response_text = r.text or ""
    response_tokens = count_tokens(response_text)

    quality = judge_quality(scenario, response_text)
    quality_score = round((quality["correttezza"] + quality["sicurezza"] + quality["precisione"]) / 3, 2)

    return RunResult(
        scenario_id=scenario["id"],
        approach=approach,
        run=run_idx,
        prompt_tokens=prompt_tokens,
        response_tokens=response_tokens,
        total_tokens=prompt_tokens + response_tokens,
        time_ms=round(elapsed_ms, 1),
        quality_correttezza=quality["correttezza"],
        quality_sicurezza=quality["sicurezza"],
        quality_precisione=quality["precisione"],
        quality_score=quality_score,
        note=quality.get("note", "")
    )


def run_benchmarks():
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY non impostata. Esporta: export GEMINI_API_KEY=...")
        return

    # api_key is passed directly to genai.Client() in each call
    results: list[RunResult] = []

    # Popola i file nei scenari
    for s in SCENARIOS:
        s["files"]["main.py"] = CODE_MAIN_NO_MANIFEST
        if "utils.py" in s["files"]:
            s["files"]["utils.py"] = CODE_UTILS_NO_MANIFEST

    for s in SCENARIOS:
        print(f"\n{'='*60}")
        print(f"SCENARIO {s['id']}: {s['name']}")
        print(f"{'='*60}")

        for run_i in range(1, RUNS_PER_SCENARIO + 1):
            print(f"\n  [Run {run_i}/{RUNS_PER_SCENARIO}]")

            # --- CONTROL ---
            control_files = dict(s["files"])
            control_scenario = {**s, "files": control_files}
            control_prompt = build_control_prompt(control_scenario)

            print(f"    Control: ", end="", flush=True)
            r_control = run_single("control", control_prompt, s, run_i)
            results.append(r_control)
            print(f"tokens={r_control.total_tokens}, time={r_control.time_ms}ms, quality={r_control.quality_score}/10")

            time.sleep(1)  # Rate limit

            # --- PYLENS ---
            beacon_files = {
                "main.py": CODE_MAIN_WITH_MANIFEST,
            }
            if "utils.py" in s["files"]:
                beacon_files["utils.py"] = CODE_UTILS_WITH_MANIFEST
            beacon_scenario = {**s, "files": beacon_files}
            beacon_prompt = build_beacon_prompt(beacon_scenario)

            print(f"    Beacon: ", end="", flush=True)
            r_beacon = run_single("beacon", beacon_prompt, s, run_i)
            results.append(r_beacon)
            print(f"tokens={r_beacon.total_tokens}, time={r_beacon.time_ms}ms, quality={r_beacon.quality_score}/10")

            time.sleep(1)

    # ─── REPORT ──────────────────────────────────────────────
    print(f"\n\n{'='*70}")
    print("RISULTATI BENCHMARK PYLENS")
    print(f"{'='*70}")
    print(f"{'Scenario':<12} {'Approach':<10} {'PromptTok':>10} {'RespTok':>8} {'TotTok':>8} {'TimeMs':>8} {'Quality':>8}")
    print("-"*70)
    for r in results:
        print(f"{r.scenario_id:<12} {r.approach:<10} {r.prompt_tokens:>10} {r.response_tokens:>8} {r.total_tokens:>8} {r.time_ms:>8.0f} {r.quality_score:>8.1f}")

    # Aggregati per approach
    print(f"\n{'='*50}")
    print("MEDIA AGGREGATA")
    print(f"{'='*50}")
    for approach in ["control", "beacon"]:
        subset = [r for r in results if r.approach == approach]
        if subset:
            avg_prompt = round(sum(r.prompt_tokens for r in subset) / len(subset))
            avg_total  = round(sum(r.total_tokens for r in subset) / len(subset))
            avg_time   = round(sum(r.time_ms for r in subset) / len(subset))
            avg_q      = round(sum(r.quality_score for r in subset) / len(subset), 2)
            print(f"\n{approach.upper()}:")
            print(f"  Prompt tokens (avg):  {avg_prompt}")
            print(f"  Total tokens (avg):   {avg_total}")
            print(f"  Time ms (avg):        {avg_time}")
            print(f"  Quality score (avg):  {avg_q}/10")

    # Salva JSON per analisi
    out_path = os.path.join(os.path.dirname(__file__), "results.json")
    with open(out_path, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    print(f"\n✅ Risultati salvati in: {out_path}")


if __name__ == "__main__":
    run_benchmarks()
