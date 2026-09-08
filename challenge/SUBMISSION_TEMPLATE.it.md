## Submission CodeDNA Challenge

> **Lingua:** Italiano · [English](SUBMISSION_TEMPLATE.md)  
> Usa questo template per le PR della challenge.  
> Titolo: `challenge: <handle> — CodeDNA Challenge submission`

### Partecipante

- Handle:
- Modalità challenge:
  - [ ] Parity (stessi L1/L2 su Control e CodeDNA)
  - [ ] Dichiarata `codedna-only` vs stack superiore

### Stack tecnologico (obbligatorio)

- Linguaggio/i:
- Framework (obbligatorio — non solo il linguaggio):
- Agente / modello:
- File sorgente approx. (≥ **25**):
- Size band (`S`/`M`/`L`/`XL`):
- Note stack (DB, monorepo, infra — opzionale):
- URL pubblico (opzionale) / “privato — solo metriche”:
- [ ] È un **progetto reale e funzionante** (non sito giocattolo / hello-world / demo throwaway)

### Install CodeDNA (obbligatorio)

- Agente usato con CodeDNA:
- Passi esatti di install / init (incolla i comandi):
- Valore di `codedna install --tools` (se usato):
- Install + annotation ok? sì / no — note:

### Stack sotto test (L0/L1/L2)

| Livello | Tool / file | Presente in Control? | Presente in CodeDNA? |
|---|---|---|---|
| L0 CodeDNA | header in-source | no | sì |
| L1 | | | |
| L2 | | | |

### Metrics JSON (obbligatorio)

- [ ] Presente `challenge/<handle>/metrics.json`
- [ ] Partito da [`metrics.example.json`](./metrics.example.json) / conforme a [`metrics.schema.json`](./metrics.schema.json)
- [ ] `schema_version` = `"1.0"`
- [ ] Compilati `project.languages` + `project.frameworks` + `approx_source_files` (≥25) + `size_band`
- [ ] Compilati `install.agent` + `install.steps`
- [ ] Presente `bugs_reported` (array vuoto OK se nessuno)
- [ ] ≥10 task con mix `difficulty` (easy ≥3, medium ≥3, hard ≥2)
- [ ] Gli **stessi task** hanno risultati `control` e `codedna`
- [ ] `summary.favors` impostato (`codedna` | `control` | `tie` | `inconclusive`)
- [ ] I risultati possono favorire **oppure** sfavorire CodeDNA (onestà OK)

### Opzionale

- [ ] Narrativa in `README.md` / `notes.md`
- [ ] `logs/` redatti

### Bug trovati in CodeDNA

- Link (oppure “nessuno”) — elencarli anche in `metrics.json` → `bugs_reported`:
- [ ] Se qualcosa si è rotto su agente/linguaggio, ho aperto issue o PR di fix

### Checklist

- [ ] Nessun secret / sorgente proprietaria in questa PR
- [ ] Solo log redatti
- [ ] Modalità + parity di stack dichiarate nel JSON (`mode`, `stack`)
- [ ] Metriche e narrativa sono veritiere (non inventate)
- [ ] Posso presentare progetto e processo di test in una call di review (Meet / simile) se richiesto
- [ ] Capisco che claim inventati o progetti finti = squalifica
