# CodeDNA Research Support Kit (No-Code)

Questo kit e pensato per contribuire alla ricerca senza modificare il codice di CodeDNA.
Usa solo benchmark, raccolta risultati e documentazione sperimentale.

## Obiettivo

Aiutare il team a produrre evidenza robusta per un paper:
- piu task
- piu run
- confronto control vs codedna
- tracciamento chiaro dei risultati

## Percorso semplice (3 ruoli)

1. Operatore benchmark
- prepara task
- lancia run
- salva output JSON e log

2. Curatore risultati
- consolida CSV
- controlla qualita dati (task, model, seed, run_id)
- calcola medie/F1 delta per task e modello

3. Supporto paper
- aggiorna Methods/Limitations
- prepara tabella risultati e note di replicabilita

## Regole di sicurezza (per non toccare il progetto)

- Non editare `codedna_tool/`, `codedna-plugin/`, `integrations/`.
- Lavora solo su:
  - `labs/benchmark/`
  - `benchmark_agent/runs/`
  - `research_support/`
- Non fare commit sul branch main del progetto originale.
- Se possibile, lavora su fork personale o branch `research/<nome>`.

## Setup minimo

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -e .[dev]
pip install datasets
```

## Flusso operativo consigliato

### Opzione guidata (consigliata, Windows PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File research_support\run_benchmark_team.ps1 -Tasks 50 -PrepareOnly
# poi, quando sei pronto:
powershell -ExecutionPolicy Bypass -File research_support\run_benchmark_team.ps1 -Tasks 50 -Model deepseek-chat -Runs 3
```

Nota: se imposti `HF_TOKEN` (HuggingFace), eviti warning e ottieni rate limit migliori.

1. Preparazione task (es. 50 Django, multi-file first)

```bash
python labs/benchmark/setup_benchmark.py --repo django/django --n-tasks 50 --multi-file-first
python labs/benchmark/setup_benchmark.py --repo django/django --annotate --no-llm
```

2. Run benchmark (es. DeepSeek)

```bash
python benchmark_agent/swebench/run_agent_multi.py ^
  --model deepseek-chat ^
  --runs 3 ^
  --temperature 0.1 ^
  --projects-dir labs/benchmark/projects ^
  --tasks-file labs/benchmark/tasks.json
```

3. Analisi

```bash
python benchmark_agent/swebench/analyze_multi.py
python benchmark_agent/swebench/analyze_multi.py --qualitative
```

### Analisi run esistenti (zero costo API, consigliato)

```bash
python research_support/analyze_existing_runs.py
```

Output:
- `research_support/analysis/REPORT_IT.md`
- `research_support/analysis/model_summary.csv`
- `research_support/analysis/task_summary.csv`

Nota statistica:
- il report include sia `Wilcoxon p exact` (combinatorio) sia
  `Wilcoxon p approx` (normal approximation, allineata allo script benchmark del repo).

## Cosa consegnare al team

- `research_support/analysis/REPORT_IT.md`
- `research_support/analysis/model_summary.csv`
- `research_support/analysis/task_summary.csv`
- `research_support/analyze_existing_runs.py`
- `research_support/windows_cp1252_issue_report.md`
- breve nota: modello, numero task, runs, costo stimato, anomalie osservate

Per una PR pulita: non includere `research_support/logs/`.

## Casi in cui stai gia aiutando molto

- ripetere benchmark con stesso setup (replicabilita)
- validare su Windows/macOS/Linux (stabilita cross-platform)
- aggiungere run su modelli diversi mantenendo identico protocollo
