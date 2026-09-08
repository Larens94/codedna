# CodeDNA Challenge — €200

> **Lingua:** Italiano · [English](challenge.md)  
> **Stato:** bozza / iscrizioni aperte  
> **Premio:** €200  
> **Durata:** 1 mese dalla data ufficiale di inizio  
> **Non è un rerun di SWE-bench.** Provi CodeDNA sul **tuo** progetto.

Questa challenge pone una sola domanda:

> CodeDNA aiuta (o no) quando fai sviluppo reale assistito da AI — e possiamo misurarlo in modo onesto?

I bug trovati durante la challenge sono benvenuti: apri una GitHub issue e li correggiamo upstream.

---

## In sintesi

1. Lavori sul **tuo** repo (non sui nostri vecchi benchmark).
2. Esegui **almeno 10 task** (mix facili / medi / difficili).
3. Confronti **con CodeDNA** vs **senza CodeDNA**.
4. Tieni lo stack AI **equo** (vedi Livelli sotto).
5. Apri una **Pull Request** con le metriche — anche se CodeDNA risulta peggiore.
6. Fabrizio + team valutano complessità, rispetto del protocollo ed evidenze.
7. Il premio si sblocca solo se si raggiunge il **minimo di partecipanti**.

---

## Premio e minimo partecipanti

| Voce | Regola |
|---|---|
| Montepremi | **€200** (pagati alla submission vincitrice dopo la review) |
| Submission valide minime | **5** per sbloccare il premio (obiettivo stretch: 10) |
| Se ci sono meno di 5 PR valide | I risultati si pubblicano comunque; il premio **non** viene assegnato (o passa all’edizione successiva) |
| Vincitore | Scelto da Fabrizio Corpora + team di review (non voto community) |

### Cosa valutiamo (in ordine)

1. **Onestà del protocollo** — stack equo, modalità dichiarata, note riproducibili  
2. **Qualità dei task** — mix reale facili/medi/difficili su una codebase vera  
3. **Evidenze** — metriche + breve narrativa; a favore **o** contro CodeDNA va bene  
4. **Bug report** — issue actionable aperte upstream contano positivamente  
5. **Chiarezza** — un altro engineer può ripetere il confronto  

---

## Timeline (da compilare prima della pubblicazione)

| Fase | Quando |
|---|---|
| Annuncio + video | **TBD** |
| Apertura iscrizioni | **TBD** |
| Finestra challenge | **1 mese** dalla data di inizio |
| Scadenza submission | fine della finestra (le PR devono essere aperte) |
| Review | ~1–2 settimane dopo la scadenza |
| Annuncio vincitore | **TBD** |

---

## Chi può partecipare

- Chiunque usi un agente AI di coding (Cursor, Claude Code, Codex, Copilot, Cline, Roo, Windsurf, OpenCode, …)
- Solo o piccolo team (una PR per partecipante / team)
- Il progetto può restare privato durante la run; la **PR con le metriche** su questo repo deve essere pubblica

---

## Protocollo centrale (obbligatorio)

### 1. Il tuo progetto

Usa un repo che **mantieni tu** (lavoro o personale). Linea guida dimensione: abbastanza superficie perché 10 task siano significativi (indicativamente ≥20 file sorgente). Linguaggio: qualsiasi stack supportato da CodeDNA.

### 2. Almeno dieci task

Definisci **≥10** task **prima** delle run cronometrate (o congela l’elenco nella PR).

Mix suggerito:

| Difficoltà | Conteggio (min) | Esempi |
|---|---|---|
| Facile | ≥3 | rename + aggiornare i caller, aggiungere un campo, fix chiaro con file già noto |
| Media | ≥3 | feature cross-file, refactor con invarianti, cambio API |
| Difficile | ≥2 | bug multi-modulo, vincolo architetturale, “dove cambio questo in sicurezza?” |

Per ogni task registra: obiettivo, difficoltà, agente/tool, successo/fallimento, note.

### 3. Due condizioni: senza vs con CodeDNA

Per ogni task (o batch accoppiati) esegui:

| Condizione | Setup |
|---|---|
| **A — Control** | Il tuo workflow AI normale **senza** annotation CodeDNA / senza affidarti agli header CodeDNA |
| **B — CodeDNA** | Stesso workflow **con** CodeDNA installato e annotato (`codedna init` / header mantenuti) |

Mantieni **agente, modello e layer superiori identici** tra A e B, tranne CodeDNA stesso (salvo modalità dichiarata — vedi sotto).

### 4. Stack equo — Livelli (critico)

Se già usi layer extra per lo sviluppo AI, CodeDNA va testato **sopra lo stesso stack**, non al posto di quelle cose per sbaglio.

| Livello | Esempi | Regola |
|---|---|---|
| **L0** | Header CodeDNA in-source | Layer sotto test |
| **L1** | Wiki LLM, memoria markdown curata, skill pack, file di istruzioni agente | Se il Control lo ha, ce l’ha anche la run CodeDNA |
| **L2** | Graphify / graph memory / layer strutturali simili | Se il Control lo ha, ce l’ha anche la run CodeDNA |

**Regola di parity:**  
`stack(Control) == stack(CodeDNA)` tranne L0 CodeDNA presente in B.

**Modalità solo-L0 dichiarata (opzionale):**  
Se testi deliberatamente se **solo CodeDNA** può sostituire L1/L2, lo **devi** dire nella PR (`mode: codedna-only-vs-higher-stack` o simile) e descrivere cosa hai rimosso. Curiosità non dichiarata o stack diseguali non dichiarati = submission **non valida**.

### 5. Metriche (set minimo) — **JSON obbligatorio**

La fonte di verità (mergeabile) è un solo file:

```text
challenge/<tuo-github-handle>/metrics.json
```

Copia [`challenge/metrics.example.json`](../challenge/metrics.example.json) e compilalo.  
Schema: [`challenge/metrics.schema.json`](../challenge/metrics.schema.json) (`schema_version: "1.0"`).

Obbligatorio per ogni task (Control + CodeDNA):

| Campo | Note |
|---|---|
| `passed` | La definizione di successo va in `success_definition` |
| `minutes` / `turns` / `tool_calls` | Usa ciò che riesci a misurare; `null` se sconosciuto |
| `wrong_file_or_module` | Quando applicabile |
| `human_interventions` | Quante volte hai dovuto guidare |
| `confidence_1_to_5` | Opzionale ma utile |

Compila anche `summary.favors`: `codedna` | `control` | `tie` | `inconclusive`.

I numeri grezzi possono favorire CodeDNA **oppure no**. L’onestà batte il tifo.  
`notes.md` è narrativa opzionale — **non sostituisce** `metrics.json`.

### 6. Submission = Pull Request

Apri una PR su `Larens94/codedna`. Copia la checklist nel body della PR:

- English: [`challenge/SUBMISSION_TEMPLATE.md`](../challenge/SUBMISSION_TEMPLATE.md)
- Italiano: [`challenge/SUBMISSION_TEMPLATE.it.md`](../challenge/SUBMISSION_TEMPLATE.it.md)

Aggiungi questa cartella:

```text
challenge/<tuo-github-handle>/
  metrics.json       # OBBLIGATORIO — risultati machine-readable (merge + aggregazione dopo)
  README.md          # sintesi + dichiarazione modalità + livelli di stack
  notes.md           # narrativa opzionale, sorprese, bug
  (opzionale) logs/  # estratti di sessione redatti
```

Titolo PR:

```text
challenge: <handle> — CodeDNA Challenge submission
```

**Perché JSON:** ogni partecipante ha la sua cartella, le PR si mergiano senza conflitti, e a fine challenge aggreghiamo tutti i `metrics.json`.
---

## Iscrizione

1. Apri una GitHub issue con il template **CodeDNA Challenge entry**  
2. Commenta nella Discussion di annuncio (quando pubblicata)  
3. Installa CodeDNA e annota il progetto all’apertura della finestra:

```bash
pipx install git+https://github.com/Larens94/codedna.git
codedna install --path . --tools <tuo-agente>
codedna init . --no-llm   # oppure con LLM per le rules:
```

---

## Cosa non è questa challenge

- Non è un rerun di SWE-bench / delle nostre tabelle F1 storiche  
- Non è “annota solo i nostri repo di fixture”  
- Non è consulenza gratis per noi — tieni l’IP del tuo progetto; noi reviewiamo solo la PR delle metriche  

---

## Comunicazione

- Issue / bug: GitHub Issues  
- Q&A challenge: GitHub Discussions (Announcements / Q&A)  
- Community: Discord (vedi badge in README)  
- Maintainer: Fabrizio Corpora  

---

## Licenza delle submission

Aprendo una PR di challenge concedi il permesso di citare **metriche e sintesi anonimizzate** in docs / blog / video di CodeDNA. Non caricare secret, sorgenti proprietarie o credenziali. Redigi i log.
