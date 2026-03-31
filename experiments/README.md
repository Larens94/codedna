# Experiments — comandi di riferimento

## Script disponibili

| Script | Descrizione |
|---|---|
| `run_experiment.py` | Esperimento originale (task generico) |
| `run_experiment_webapp2.py` | Esperimento AgentHub SaaS webapp (corrente) |

---

## run_experiment_webapp2.py

```bash
cd experiments

# Esegui entrambe le condizioni (A + B)
python run_experiment_webapp2.py

# Solo condizione A (CodeDNA annotation protocol)
python run_experiment_webapp2.py --condition a

# Solo condizione B (Standard practices)
python run_experiment_webapp2.py --condition b

# Riprendi un run interrotto
python run_experiment_webapp2.py --resume run_20260330_024934

# Lista tutti i run salvati
python run_experiment_webapp2.py --list-runs

# Cancella un run specifico
python run_experiment_webapp2.py --clean-run run_20260330_024934

# Cancella TUTTI i run
python run_experiment_webapp2.py --reset
```

> **Nota:** all'avvio, se esistono run incompleti (senza `comparison.json`),
> lo script li mostra e chiede se riprendere — rispondi `Y` per riprendere,
> `new` per creare comunque un nuovo run.

---

## visualizer/dashboard.py

```bash
cd experiments

# Selettore interattivo (lista run e chiede quale aprire)
python visualizer/dashboard.py

# Apri un run specifico direttamente
python visualizer/dashboard.py --run run_20260330_024934

# Seleziona automaticamente l'ultimo run (senza picker)
python visualizer/dashboard.py --latest

# Cambia frequenza di polling (default 2s)
python visualizer/dashboard.py --interval 5

# Esci: Ctrl-C
```

---

## Workflow consigliato (due terminali)

```bash
# Terminale 1 — avvia l'esperimento
cd experiments
python run_experiment_webapp2.py

# Terminale 2 — apri la dashboard mentre l'esperimento gira
cd experiments
python visualizer/dashboard.py --latest
```

---

## Cosa mostra la dashboard

- **Colonna cyan [A]** — team con CodeDNA annotation protocol
- **Colonna yellow [B]** — team con standard practices
- Per ciascuna: file creati + coverage, `agent:` entries timeline, `message:` channel, session events
- Stats bar in cima con coverage % in tempo reale

---

## Output di ogni run

```
runs/run_YYYYMMDD_HHMMSS/
  a/                    # output condizione A
  b/                    # output condizione B
  comparison.json       # risultati finali (creato al termine)
  partial_results.json  # checkpoint intermedi
  run.log               # log timestampato
  reports/
    summary.csv         # metriche in CSV
    report.html         # report HTML navigabile
```
