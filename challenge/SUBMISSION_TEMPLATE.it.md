## Submission CodeDNA Challenge

> **Lingua:** Italiano · [English](SUBMISSION_TEMPLATE.md)  
> Usa questo template per le PR della challenge.  
> Titolo: `challenge: <handle> — CodeDNA Challenge submission`

### Partecipante

- Handle:
- Issue di iscrizione collegata:
- Modalità challenge:
  - [ ] Parity (stessi L1/L2 su Control e CodeDNA)
  - [ ] Dichiarata `codedna-only` vs stack superiore

### Stack sotto test

| Livello | Tool / file | Presente in Control? | Presente in CodeDNA? |
|---|---|---|---|
| L0 CodeDNA | header in-source | no | sì |
| L1 | | | |
| L2 | | | |

### Progetto

- Linguaggio/i:
- Dimensione (file sorgente approx.):
- URL pubblico (opzionale) / “privato — solo metriche”:

### Metrics JSON (obbligatorio)

- [ ] Presente `challenge/<handle>/metrics.json`
- [ ] Partito da [`metrics.example.json`](./metrics.example.json) / conforme a [`metrics.schema.json`](./metrics.schema.json)
- [ ] `schema_version` = `"1.0"`
- [ ] ≥10 task con mix `difficulty` (easy ≥3, medium ≥3, hard ≥2)
- [ ] Ogni task ha risultati `control` e `codedna`
- [ ] `summary.favors` impostato (`codedna` | `control` | `tie` | `inconclusive`)
- [ ] I risultati possono favorire **oppure** sfavorire CodeDNA (onestà OK)

### Opzionale

- [ ] Narrativa in `README.md` / `notes.md`
- [ ] `logs/` redatti

### Bug trovati in CodeDNA

- Link (oppure “nessuno”) — elencarli anche in `metrics.json` → `bugs_reported`:

### Checklist

- [ ] Nessun secret / sorgente proprietaria in questa PR
- [ ] Solo log redatti
- [ ] Modalità + parity di stack dichiarate nel JSON (`mode`, `stack`)
