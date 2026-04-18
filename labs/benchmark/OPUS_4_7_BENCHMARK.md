# CodeDNA Benchmark — Opus 4.7 A/B (control vs codedna)

**Obiettivo scientifico**: misurare se CodeDNA v0.8 offre un beneficio quantificabile
all'agente Opus 4.7 in task di bug-fix navigation su codebase reali (Django SWE-bench).

**Domanda di ricerca**: a parità di modello (Opus 4.7), task e prompt, il protocollo
CodeDNA riduce il numero di tool call, letture ridondanti, e il tempo al primo hit GT?

---

## 1. Setup hardware/ambiente

- Repo: `/Users/fabriziocorpora/Desktop/workspaces/codedna/labs/benchmark/`
- CLI: `codedna_tool` (modulo Python, importato via `python3 -m codedna_tool.cli`)
- Runner: `benchmark_agent/swebench/run_agent_multi.py`
- API:
  - Anthropic (Opus 4.7): `ANTHROPIC_API_KEY`
  - DeepSeek (annotazione): `DEEPSEEK_API_KEY`

---

## 2. Dataset

**5 task Django da SWE-bench (full, 2294 task)** — scelte per:
- range difficoltà: da media (14480 XOR) a alta (11808 __eq__ multi-classe)
- cross-file: 7–10 file ground-truth ciascuno
- dominio omogeneo (solo Django) → confronti comparabili

| Task | Problema | GT files |
|---|---|---|
| django__django-14480 | Logical XOR support per Q()/QuerySet() | 7 |
| django__django-13495 | Trunc() ignora tzinfo per DateField | 7 |
| django__django-12508 | `manage.py dbshell -c SQL` | 8 |
| django__django-11991 | INCLUDE clause su indici | 9 |
| django__django-11808 | `__eq__` returns `NotImplemented` multi-classe | 10 |

---

## 3. Pipeline riproducibile

### 3.1 Download pristine da SWE-bench
```bash
cd labs/benchmark/
python3 setup_benchmark.py \
    --task-id 14480 13495 12508 11991 11808 \
    --repo django/django \
    --dataset full
```
Produce: `projects/django__django-<id>/{control,files_in_patch.json,problem_statement.txt}`.

### 3.2 Master backup PRIMA di qualsiasi annotazione
```bash
cd labs/benchmark/
tar -czf backups/pristine_5tasks_YYYY-MM-DD.tar.gz \
    -C projects \
    django__django-14480 django__django-13495 django__django-12508 \
    django__django-11991 django__django-11808
shasum -a 256 backups/pristine_5tasks_YYYY-MM-DD.tar.gz
```
**Regola**: mai annotare prima del backup. La master copy è il punto di ripartenza
per qualunque nuova sperimentazione.

### 3.3 Ripristino dal master backup
```bash
cd labs/benchmark/projects/
rm -rf django__django-14480 django__django-13495 django__django-12508 \
       django__django-11991 django__django-11808
tar -xzf ../backups/pristine_5tasks_YYYY-MM-DD.tar.gz
```

### 3.4 Annotazione CodeDNA
```bash
# Per ogni task: cp control → codedna, poi annotate
for tid in 14480 13495 12508 11991 11808; do
    TASK=django__django-${tid}
    cp -r projects/$TASK/control projects/$TASK/codedna

    DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY python3 -m codedna_tool.cli init \
        projects/$TASK/codedna \
        --force \
        --model deepseek/deepseek-chat \
        --exclude "tests/*" "docs/*" "js_tests/*" "extras/*" "scripts/*"

    python3 -m codedna_tool.cli refresh projects/$TASK/codedna

    DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY python3 -m codedna_tool.cli manifest \
        projects/$TASK/codedna \
        --model deepseek/deepseek-chat \
        --exclude "tests/*" "docs/*" "js_tests/*"
done
```

Perché **DeepSeek** per annotare: (1) costo ~15× minore di Opus, (2) **non vede mai
`problem_statement`**, quindi le `rules:` generate sono architettura-derived, non
fix-derived. Anchor scientifico contro l'obiezione "le annotazioni contengono hint
sulla soluzione".

### 3.5 Snapshot post-annotazione (pre-benchmark)
```bash
tar -czf backups/annotated_5tasks_YYYY-MM-DD.tar.gz \
    -C projects \
    django__django-14480 django__django-13495 django__django-12508 \
    django__django-11991 django__django-11808
```

### 3.6 Audit integrità PRIMA del run
```bash
python3 labs/benchmark/tools/audit_benchmark_integrity.py \
    --task-id 14480 13495 12508 11991 11808 --verbose
```
Il tool verifica:
- **body integrity**: `codedna/` ≡ `control/` (stesso AST, dopo strip docstring)
- **fix leak**: nessuna firma di funzione patched appare nel codedna/
- **problem_statement leak**: `rules:`/`Rules:`/`message:` non contengono keyword del bug

Se il tool esce con exit=1, NON lanciare il benchmark.

### 3.7 Registrazione Opus 4.7 nel runner
Applicata in `benchmark_agent/swebench/run_agent_multi.py`:
- `_ANTHROPIC_COSTS["claude-opus-4-7"] = (15.00, 75.00)`
- `MODELS["claude-opus-4-7"] = {"provider": "anthropic", "model_id": "claude-opus-4-7"}`

### 3.8 Mini-test validazione (Haiku, ~$0.10)
```bash
ANTHROPIC_API_KEY=... python3 benchmark_agent/swebench/run_agent_multi.py \
    --model claude-haiku-4-5 --runs 1 --task 14480 \
    --projects-dir labs/benchmark/projects \
    --tasks-file labs/benchmark/tasks.json
```
Usato per verificare che la pipeline end-to-end (trace, F1, tokens) funzioni prima
di bruciare budget Opus.

### 3.9 Dry run Opus 4.7 (~$8–12)
```bash
ANTHROPIC_API_KEY=... python3 benchmark_agent/swebench/run_agent_multi.py \
    --model claude-opus-4-7 --runs 1 --task 14480 \
    --projects-dir labs/benchmark/projects \
    --tasks-file labs/benchmark/tasks.json
```

### 3.10 Full benchmark Opus 4.7
```bash
ANTHROPIC_API_KEY=... python3 benchmark_agent/swebench/run_agent_multi.py \
    --model claude-opus-4-7 --runs 3 --temperature 0.1 \
    --task 14480 13495 12508 11991 11808 \
    --projects-dir labs/benchmark/projects \
    --tasks-file labs/benchmark/tasks.json
```

---

## 4. Metriche misurate

Per ogni run (file: `benchmark_agent/runs/claude-opus-4-7/results.json` +
`session_traces/bench_*.json`):

| Metrica | Significato |
|---|---|
| `tool_calls` | totale read+grep+list |
| `read_calls` / `grep_calls` / `list_calls` | breakdown |
| `files_read_unique` / `n_files_read` | file distinti esplorati |
| `redundant_reads` | riletture dello stesso file (`reads − unique`) |
| `nav_efficiency` | `∣reads ∩ GT∣ / ∣reads∣` |
| `first_hit` | bool: uno dei primi 3 `read_file` è GT |
| `tokens_per_gt_file` | input+output / `∣reads ∩ GT∣` |
| `input_tokens` / `output_tokens` | dal campo `usage` della risposta API |
| `metrics_read` / `metrics_proposed` | `{recall, precision, f1}` su GT |
| `trace` | lista ordinata+timestamped di tool call |

**Ipotesi da testare**:
- `H1`: `tool_calls(codedna) < tool_calls(control)` su media delle 5 task
- `H2`: `first_hit(codedna) > first_hit(control)` (agent trova GT prima)
- `H3`: `nav_efficiency(codedna) > nav_efficiency(control)`
- `H4`: `F1(codedna) ≥ F1(control)` (nessun degrado, possibile miglioramento)

**Test statistico**: Wilcoxon signed-rank su paired runs (5 task × 3 run), α=0.05.

---

## 5. Configurazione riproducibile

- **Temperature**: 0.1 (multi-run)
- **Max turns**: 30 per run
- **History window**: 8 turn pairs (trim nel runner)
- **Max tokens/response**: 4096
- **Provider Opus**: Anthropic Claude API diretta (no router)
- **Seeds**: non fissi (Anthropic API non espone seed). La varianza è assorbita
  dalla media su 3 run.

---

## 6. Disclaimer scientifici

1. **Non comparabile con benchmark storici in `benchmark_agent/projects_swebench/`**:
   quei dataset hanno body corrotto da una vecchia versione del tool CodeDNA (fino
   a ~150 file Python divergenti per task, alcuni con sintassi invalida, e almeno
   un caso — django-13495 — con la patch del fix già applicata nel codedna/).
   Per confrontare i nuovi risultati Opus 4.7 con Haiku/DeepSeek/Gemini serve
   rifarli sul dataset pulito di `labs/benchmark/`.

2. **Bias di auto-validazione**: Opus 4.7 e questo benchmark sono stati entrambi
   prodotti da Anthropic. Il risultato va riportato con questa nota — il protocollo
   CodeDNA è language-agnostic e model-agnostic, ma l'ecosistema resta lo stesso.

3. **DeepSeek come annotator**: scelto proprio per romperepotenziali correlazioni
   "stesso modello annota e risolve". DeepSeek non vede problem_statement; verifica
   via `audit_benchmark_integrity.py`.

---

## 7. Artefatti di backup

- `backups/pristine_5tasks_2026-04-17.tar.gz` — master pristine (5 task, solo control/)
  - SHA256: `7718c749685827b5adea3a24fbb34c1d81a692d44bbaec5764ba5878c0b9ae64`
  - 46,877 file, ~44 MB

Nuovi backup (dopo annotazione, dopo benchmark) vanno aggiunti qui con SHA256.

---

## 8. Agent history di questo setup

- 2026-04-17 — claude-opus-4-7 (s_20260417_opus47):
  - Patch `setup_benchmark.py` (flag `--task-id`, `--dataset`)
  - Patch `run_agent_multi.py` (registrato Opus 4.7)
  - Download pristine da SWE-bench full
  - Master backup SHA256-verificato
  - Annotazione codedna/ via DeepSeek (esclusi tests/docs/js_tests/extras/scripts)
  - Creato `tools/audit_benchmark_integrity.py` per pre-flight check
