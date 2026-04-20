# Consegna Per La Ricerca CodeDNA

Ciao, ho preparato un contributo concreto lato ricerca senza toccare il core del progetto.

## 1) Re-analisi quantitativa indipendente dei run esistenti

Ho analizzato i risultati gia presenti in `benchmark_agent/runs/*/results.json`
con uno script dedicato.

Output generati:
- `research_support/analysis/model_summary.csv`
- `research_support/analysis/task_summary.csv`
- `research_support/analysis/REPORT_IT.md`

Script usato:
- `research_support/analyze_existing_runs.py`

### Risultati principali (dati attuali)

- **gemini-2.5-flash**: Control F1 `0.597` -> CodeDNA F1 `0.724` (**+0.127**), 4 task vinti su 5.
- **gemini-2.5-pro**: Control F1 `0.596` -> CodeDNA F1 `0.690` (**+0.094**), 3 task vinti su 5.
- **deepseek-chat**: Control F1 `0.420` -> CodeDNA F1 `0.497` (**+0.077**), 4 task vinti, 1 perso, 1 pareggio.

Nota metodologica:
- nel report sono presenti sia `Wilcoxon p exact` (combinatorio) sia
  `Wilcoxon p approx` (normal approximation, allineata allo script benchmark del repo).

Insight utile:
la re-analisi conferma un vantaggio medio positivo di CodeDNA su piu modelli,
ma evidenzia anche task specifici con regressione
(es. `django__django-13495` su alcuni modelli), utili per analisi causale/ablation.

## 2) Pacchetto operativo per benchmark replicabile (no-code contribution)

Ho aggiunto un kit per contributor inesperti:
- `research_support/README_IT.md` (procedura semplice)
- `research_support/run_benchmark_team.ps1` (runner guidato Windows)
- `research_support/results_template.csv` (raccolta dati standard)
- `research_support/methods_draft_en.md` (bozza sezione Methods)
- `research_support/call_plan_it.md` (agenda call ricerca)

Obiettivo: permettere al gruppo di produrre evidenza robusta in modo coordinato,
ripetibile e paper-ready.

## 3) Segnalazione tecnica utile (Windows)

Durante i test ho osservato un problema riproducibile su Windows/cp1252:
- `setup_benchmark.py` puo fallire con `UnicodeEncodeError` su caratteri Unicode nel log (es. freccia `->`).

Questo e un fix piccolo ma ad alto impatto per allargare i contributor
e migliorare la replicabilita cross-platform.

---
