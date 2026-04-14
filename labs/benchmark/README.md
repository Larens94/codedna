# CodeDNA Benchmark — SWE-bench Verified

Benchmark per validare CodeDNA su SWE-bench Verified (500 task, 12 repo Python).

## Requisiti

```bash
pip install datasets   # per scaricare SWE-bench da HuggingFace
pip install git+https://github.com/Larens94/codedna.git   # CLI per annotare
```

API key (almeno una):
- `DEEPSEEK_API_KEY` — DeepSeek Chat (~$0.15/run)
- `GEMINI_API_KEY` — Gemini Flash (~$0.10/run)
- Oppure: Ollama locale (costo zero, serve GPU)

## Workflow

### 1. Esplorare i task disponibili

```bash
# Tutti i task Django (231)
python3 setup_benchmark.py --list --repo django/django

# Tutti i task di tutte le repo (500)
python3 setup_benchmark.py --list
```

### 2. Scaricare e preparare i task

```bash
# 50 task Django, multi-file prima (raccomandato per iniziare)
python3 setup_benchmark.py --repo django/django --n-tasks 50 --multi-file-first

# Tutti i 231 task Django
python3 setup_benchmark.py --repo django/django

# Tutti i 500 task (tutte le 12 repo)
python3 setup_benchmark.py --all
```

Questo crea per ogni task:
```
projects/<instance_id>/
    control/              <- repo al commit base (vanilla, nessuna annotazione)
    problem_statement.txt <- descrizione del bug (GitHub issue)
    files_in_patch.json   <- ground truth (file da modificare)
```

### 3. Annotare con CodeDNA

```bash
# Senza LLM (solo struttura: exports/used_by via AST) — gratis
python3 setup_benchmark.py --repo django/django --annotate --no-llm

# Con modello locale via Ollama — gratis, serve GPU
python3 setup_benchmark.py --repo django/django --annotate --model ollama/llama3

# Con API — qualità migliore per rules:
python3 setup_benchmark.py --repo django/django --annotate --model claude-haiku-4-5-20251001
```

Questo crea `codedna/` accanto a `control/` per ogni task.

### 4. Lanciare il benchmark

Lo script di run è in `benchmark_agent/swebench/run_agent_multi.py` (dalla root del repo):

```bash
cd /path/to/codedna

# DeepSeek Chat, 3 run per task
DEEPSEEK_API_KEY=... python3 benchmark_agent/swebench/run_agent_multi.py \
    --model deepseek-chat --runs 3 --temperature 0.1

# Gemini Flash
GEMINI_API_KEY=... python3 benchmark_agent/swebench/run_agent_multi.py \
    --model gemini-2.5-flash --runs 3 --temperature 0.1

# Un task specifico
python3 benchmark_agent/swebench/run_agent_multi.py \
    --model deepseek-chat --task django__django-11532
```

### 5. Analizzare i risultati

```bash
python3 benchmark_agent/swebench/analyze_multi.py
python3 benchmark_agent/swebench/analyze_multi.py --qualitative
```

## Setup raccomandato per il gruppo

| Parametro | Valore |
|---|---|
| Task | 50 Django (multi-file first) |
| Run per task | 3 |
| Condizioni | 2 (control vs codedna) |
| Modelli | 2 (DeepSeek Chat + Gemini Flash) |
| Temperatura | 0.1 |
| Run totali | 50 x 3 x 2 x 2 = 600 |
| Costo stimato | ~$75 via API, ~$30 se DeepSeek locale |

## Hardware per modelli locali (costo zero)

| Modello | VRAM | Hardware |
|---|---|---|
| Qwen 2.5 32B | 24 GB | 1x RTX 4090 |
| Llama 3.1 70B (Q4) | 40 GB | 2x RTX 3090 o 1x A100 |
| DeepSeek-V3 (Q4) | 48 GB | 2x RTX 3090 o 1x A6000 |

Setup con Ollama:
```bash
ollama pull qwen2.5:32b
ollama serve   # espone su localhost:11434
```

Poi aggiungere al registry in `run_agent_multi.py`:
```python
"local-qwen-32b": {"provider": "openai", "model_id": "qwen2.5:32b"},
```

E impostare `base_url`:
```bash
OPENAI_BASE_URL=http://localhost:11434/v1 python3 run_agent_multi.py --model local-qwen-32b
```

## Struttura directory

```
labs/benchmark/
    README.md               <- questo file
    setup_benchmark.py      <- scarica e prepara i task
    tasks.json              <- generato automaticamente
    _repo_cache/            <- clone bare delle repo (cache)
    projects/               <- task preparati
        django__django-XXXXX/
            control/
            codedna/
            problem_statement.txt
            files_in_patch.json
```

## Metriche

- **File Localization F1** — precision x recall sui file letti vs ground truth
- **Wilcoxon signed-rank test** — one-tailed, H1: CodeDNA > Control
- Analisi per strato: single-file vs multi-file

## Note

- I 5 task del benchmark originale (`benchmark_agent/`) sono nel SWE-bench Full, non nel Verified
- Questa cartella usa SWE-bench Verified (500 task curati, gold standard per paper)
- Le due cartelle sono indipendenti — non condividono dati
