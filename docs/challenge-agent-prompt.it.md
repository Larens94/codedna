# Prompt agente — CodeDNA Challenge (€200)

> Incolla questo intero messaggio nel tuo agente AI (Cursor, Claude Code, OpenCode, Codex, …).  
> Pagina classifica: https://larens94.github.io/codedna/challenge.html  
> Regolamento: https://github.com/Larens94/codedna/blob/main/docs/challenge.it.md  
> English: [challenge-agent-prompt.md](challenge-agent-prompt.md)

---

## Ruolo

Aiutami a eseguire la **CodeDNA Challenge** sul **mio progetto reale** in modo onesto e riproducibile. Non inventare metriche. Se qualcosa non è misurabile, marca `inconclusive`.

## Metodologia (uguale per tutti)

Confrontiamo gli **stessi ≥10 task** in due condizioni:

| Condizione | Cosa |
|---|---|
| **A — Control** | Workflow AI **senza** CodeDNA (niente header / senza affidarsi a CodeDNA) |
| **B — CodeDNA** | Stesso agente/modello **con** CodeDNA installato e annotato |

### Setup ammesso (scegline uno e dichiaralo)

1. **Due branch** nello stesso repo — es. `challenge/control` e `challenge/codedna`  
2. **Due checkout / due cartelle** dello stesso progetto  
3. **Due progetti gemelli** (stesso codice di partenza)

Regole:

- Gli **stessi task** in A e in B (stessa lista, stesso ordine se possibile).
- Stesso agente, stesso modello, stessi layer L1/L2 (wiki/skills/Graphify) salvo modalità `codedna_only` dichiarata.
- Progetto **reale e funzionante** (≥25 file sorgente). Niente sito vetrina / hello-world.

## Stack da dichiarare

Annota e poi metti in `metrics.json`:

- linguaggi, framework (non solo il linguaggio), approx file, size band S/M/L/XL
- agente + modello
- come hai installato CodeDNA (`install.steps`)
- layout usato: `two_branches` | `two_checkouts` | `two_projects`

## Install CodeDNA (condizione B)

```bash
pipx install git+https://github.com/Larens94/codedna.git
codedna install --path . --tools <mio-agente>
codedna init . --no-llm
```

Se fallisce: riproduci, apri issue o PR di fix su Larens94/codedna, elenca in `bugs_reported`. È sperimentale — gap agente×linguaggio sono attesi.

## Lista attività (adattale al mio repo, poi congelale)

Crea **≥10 task** sul mio codice. Mix obbligatorio: easy ≥3, medium ≥3, hard ≥2.

Usa questa checklist come scheletro (sostituisci i titoli con task **reali** del mio progetto):

### Easy (≥3)

- [ ] **E1** — Rename di un simbolo + aggiornare tutti i caller
- [ ] **E2** — Aggiungere un campo/DTO/prop con validazione
- [ ] **E3** — Fix bug chiaro con file già noto
- [ ] **E4** (opz.) — Aggiornare un test esistente dopo un rename

### Medium (≥3)

- [ ] **M1** — Feature piccola cross-file (API + service + test)
- [ ] **M2** — Refactor con invariante da non rompere
- [ ] **M3** — Cambio firma / contratto e aggiornamento caller
- [ ] **M4** (opz.) — Aggiungere logging/metriche in un percorso esistente

### Hard (≥2)

- [ ] **H1** — Bug multi-modulo (“dove cambio questo in sicurezza?”)
- [ ] **H2** — Vincolo architetturale / auth / multi-tenant / confini di package
- [ ] **H3** (opz.) — Migrazione o cambio schema con impatto su più layer

Per **ogni** task registra Control e CodeDNA: `passed`, `minutes`/`turns`/`tool_calls` se disponibili, `wrong_file_or_module`, `human_interventions`, note.

## Deliverable

1. Congela la lista task **prima** delle run cronometrate.
2. Esegui tutti i task in **A**, poi gli **stessi** in **B** (o interleaved, ma stessi ID).
3. Compila `challenge/<mio-github-handle>/metrics.json` da  
   https://github.com/Larens94/codedna/blob/main/challenge/metrics.example.json  
   (schema: `metrics.schema.json`).
4. Apri PR su `Larens94/codedna` con titolo:  
   `challenge: <handle> — CodeDNA Challenge submission`  
   Checklist: `challenge/SUBMISSION_TEMPLATE.it.md`
5. Onestà: niente risultati inventati. Possibile Meet di verifica.

## Cosa fare ora

1. Ispeziona il mio repo e proponi la lista ≥10 task adattata (easy/medium/hard).
2. Chiedimi quale setup uso: **due branch** / **due checkout** / **due progetti**.
3. Prepara i comandi di install per la condizione B.
4. Solo dopo conferma mia: esegui i task e compila le metriche.
