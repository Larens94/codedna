# Piano Call Ricerca (45 min)

## 1. Obiettivo comune (5 min)

- Obiettivo: validare CodeDNA con protocollo replicabile da paper
- Vincolo: non cambiare il core tool durante la fase di raccolta dati

## 2. Setup sperimentale bloccato (10 min)

- Dataset: SWE-bench Verified
- Fase 1: 50 task Django, multi-file-first
- Condizioni: control vs codedna
- Runs per task: 3 (minimo), target 5
- Temperatura: 0.1

## 3. Ruoli operativi (10 min)

- Runner A: modello 1 (es. DeepSeek Chat)
- Runner B: modello 2 (es. Gemini Flash)
- Curatore dati: unifica CSV e controlla qualita
- Reviewer metodi: aggiorna sezione Methods/Limitations

## 4. Standard output (10 min)

Ogni runner consegna:
- log setup + run
- JSON risultati run
- riga/e in `results_template.csv`
- nota breve con anomalie

## 5. Rischi e mitigazioni (10 min)

- Rate limit API: batch piccoli, retry, finestre orarie
- Differenze OS: riportare OS e Python version in ogni run
- Drift configurazione: usare script condiviso e parametri fissi
- Bias involontario: stessa prompt/toolchain per entrambe le condizioni

