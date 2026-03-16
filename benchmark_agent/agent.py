"""
agent.py — Agente Gemini con function calling che naviga il filesystem.

Strumenti disponibili all'agente:
  read_file(path)        → legge un file
  list_files(directory)  → lista file ricorsivamente
  grep(pattern, directory) → cerca un pattern nei file

L'agente naviga il codebase per trovare i file da modificare per un bug.
Misuriamo: n° chiamate per ogni tool prima della risposta finale.
"""

import os, json
from pathlib import Path
from google import genai
from google.genai import types

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = "gemini-2.5-flash"

# ── Tool implementations ───────────────────────────────────────────────────────

def _read_file(path: str, root: Path) -> str:
    full = root / path
    if not full.exists():
        return f"ERROR: {path} non trovato"
    if not full.is_file():
        return f"ERROR: {path} non è un file"
    return full.read_text(encoding="utf-8")

def _list_files(directory: str, root: Path) -> str:
    target = root / directory if directory else root
    if not target.exists():
        return f"ERROR: directory {directory} non trovata"
    files = sorted([
        str(f.relative_to(root))
        for f in target.rglob("*")
        if f.is_file() and not f.name.startswith("__")
    ])
    return "\n".join(files) if files else "(nessun file)"

def _grep(pattern: str, directory: str, root: Path) -> str:
    target = root / directory if directory else root
    results = []
    for f in sorted(target.rglob("*.py")):
        try:
            content = f.read_text(encoding="utf-8")
            for i, line in enumerate(content.splitlines(), 1):
                if pattern.lower() in line.lower():
                    results.append(f"{f.relative_to(root)}:{i}: {line.strip()}")
        except Exception:
            pass
    if not results:
        return f"(nessun risultato per '{pattern}')"
    return "\n".join(results[:40])  # max 40 risultati


# ── Tool schemas per Gemini ─────────────────────────────────────────────────────

TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="read_file",
            description="Legge il contenuto completo di un file Python nel codebase.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "path": types.Schema(type=types.Type.STRING,
                                        description="Percorso relativo al file (es: 'orders/orders.py')")
                },
                required=["path"]
            )
        ),
        types.FunctionDeclaration(
            name="list_files",
            description="Elenca tutti i file Python in una directory (ricorsivamente).",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "directory": types.Schema(type=types.Type.STRING,
                                              description="Directory relativa ('' per root)")
                },
                required=["directory"]
            )
        ),
        types.FunctionDeclaration(
            name="grep",
            description="Cerca un pattern testuale in tutti i file Python della directory.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "pattern": types.Schema(type=types.Type.STRING,
                                            description="Testo da cercare (case insensitive)"),
                    "directory": types.Schema(type=types.Type.STRING,
                                              description="Directory dove cercare ('' per root)")
                },
                required=["pattern", "directory"]
            )
        ),
    ])
]

SYSTEM_PROMPT = """\
Sei un AI code navigator. Hai accesso a tool per leggere file e navigare un codebase Python.
Il tuo obiettivo è trovare ESATTAMENTE quali file modificare per risolvere il bug descritto.
Usa i tool per navigare il codebase prima di rispondere.
Quando hai trovato la risposta, rispondi con:
  FILE_DA_MODIFICARE: <lista di file>
  MOTIVO: <spiegazione breve per ognuno>
  FIX: <pseudocode della fix>
"""

TASK = """\
Bug critico: gli ordini degli utenti ELIMINATI continuano ad apparire nella revenue dashboard,
gonfiando le entrate mensili. Un utente eliminato 2 mesi fa genera ancora fatturato nel report.

Naviga il codebase per trovare:
1. Quali file sono coinvolti nel bug?
2. Perché ognuno è coinvolto?
3. Qual è la fix?
"""

# Risposta ground truth
CORRECT_FILES = {"orders/orders.py"}  # file root cause


# ── Agent loop ─────────────────────────────────────────────────────────────────

class AgentMetrics:
    def __init__(self):
        self.read_file_calls = 0
        self.list_files_calls = 0
        self.grep_calls = 0
        self.total_tool_calls = 0
        self.files_read: list[str] = []
        self.greps_done: list[str] = []
        self.final_answer: str = ""
        self.found_correct: bool = False
        self.turns: int = 0


def run_agent(version: str, root: Path, verbose: bool = True) -> AgentMetrics:
    """Esegue l'agente su una versione del codebase e ritorna le metriche."""
    client = genai.Client(api_key=GEMINI_API_KEY)
    metrics = AgentMetrics()

    messages = [
        types.Content(role="user", parts=[types.Part(text=TASK)])
    ]

    if verbose:
        print(f"\n{'='*60}")
        print(f"  AGENTE — versione: {version.upper()}")
        print(f"{'='*60}")

    # Agent loop con max 20 turni
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

        # Raccoglie function calls
        tool_calls = [p for p in candidate.content.parts if p.function_call]
        text_parts = [p.text for p in candidate.content.parts if p.text]

        if not tool_calls:
            # L'agente ha finito — risposta finale
            metrics.final_answer = "\n".join(text_parts)
            # Verifica se ha trovato i file corretti
            answer_lower = metrics.final_answer.lower()
            metrics.found_correct = all(
                f.lower() in answer_lower for f in CORRECT_FILES
            )
            if verbose:
                print(f"\n📋 RISPOSTA FINALE:\n{metrics.final_answer}")
                print(f"\n✅ File corretti trovati: {metrics.found_correct}")
            break

        # Esegui i tool calls
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
                if verbose:
                    print(f"  📖 read_file({path})")

            elif fc.name == "list_files":
                metrics.list_files_calls += 1
                d = args.get("directory", "")
                result = _list_files(d, root)
                if verbose:
                    print(f"  📂 list_files({d or 'root'})")

            elif fc.name == "grep":
                metrics.grep_calls += 1
                pat = args.get("pattern", "")
                d = args.get("directory", "")
                metrics.greps_done.append(pat)
                result = _grep(pat, d, root)
                if verbose:
                    print(f"  🔍 grep('{pat}')")

            else:
                result = "Tool non riconosciuto"

            tool_results.append(types.Part(
                function_response=types.FunctionResponse(
                    name=fc.name,
                    response={"result": result}
                )
            ))

        messages.append(types.Content(role="user", parts=tool_results))

    return metrics
