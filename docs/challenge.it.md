# CodeDNA Challenge — €200

> **Lingua:** Italiano · [English](challenge.md)  
> **Stato:** bozza / aperta  
> **Premio:** €200  
> **Durata:** 1 mese dalla data ufficiale di inizio  
> **Iscrizione:** aprire la PR con le metriche = sei iscritto (niente signup ufficiale)  
> **Non è un rerun di SWE-bench.** Provi CodeDNA sul **tuo** progetto.  
> **Bacheca pubblica:** [challenge.html](challenge.html) sul sito docs

Questa challenge pone una sola domanda:

> CodeDNA aiuta (o no) quando fai sviluppo reale assistito da AI — e possiamo misurarlo in modo onesto?

**Sperimentale.** La qualità di CodeDNA dipende ancora dall’**agente AI di coding** e dal **linguaggio / framework** che usi. Alcune combinazioni funzionano meglio di altre. Se install, annotation, hook o refresh non si comportano bene sul tuo stack, **apri una GitHub issue o una PR di fix** — fa parte della challenge, e sistemiamo upstream a partire dai tuoi report.

---

## In sintesi

1. Lavori sul **tuo** repo (non sui nostri vecchi benchmark).
2. Esegui **almeno 10 task** (mix facili / medi / difficili).
3. Confronti **con CodeDNA** vs **senza CodeDNA**.
4. Tieni lo stack AI **equo** (vedi Livelli sotto).
5. Apri una **Pull Request** con `metrics.json` — anche se CodeDNA risulta peggiore. **Quella PR è la tua iscrizione.**
6. Fabrizio + team valutano complessità, protocollo ed evidenze; la bacheca pubblica si aggiorna a mano.
7. Il premio si sblocca solo se si raggiunge il **minimo di partecipanti**.

---

## Premio e minimo partecipanti

| Voce | Regola |
|---|---|
| Montepremi | **€200** (pagati alla submission vincitrice dopo la review) |
| Submission valide minime | **5** per sbloccare il premio (obiettivo stretch: 10) |
| Se ci sono meno di 5 PR valide | I risultati si pubblicano comunque; il premio **non** viene assegnato (o passa all’edizione successiva) |
| Vincitore | Scelto da Fabrizio Corpora + team di review (non voto community) |
| Onestà | Le affermazioni devono essere vere e supportate da evidenze — metriche o narrative inventate = squalifica |
| Verifica | Fabrizio o il team di review possono chiedere una review live (Google Meet / simile) per ripercorrere run, log e setup del repo |
| Live | Quando possibile ospiteremo live pubbliche sui test inviati (con consenso del partecipante dove serve) |

### Cosa valutiamo (in ordine)

1. **Onestà del protocollo** — stack equo, modalità dichiarata, note riproducibili; **niente risultati inventati**  
2. **Qualità dei task** — mix reale facili/medi/difficili su una codebase vera  
3. **Evidenze** — metriche + breve narrativa; a favore **o** contro CodeDNA va bene  
4. **Bug report** — issue actionable aperte upstream contano positivamente  
5. **Chiarezza** — un altro engineer può ripetere il confronto  

### Onestà, call di review e live

- **Non puoi inventare** esiti pass/fail, tempi, dettagli di stack o claim narrativi. Se non riesci a riprodurre un numero, marca il task come inconclusive e dillo.
- Fabrizio Corpora e/o il team di review **possono chiedere una video call** (es. Google Meet) per verificare la submission: screen-share del progetto, riesecuzione di un task campione, walkthrough di `metrics.json` / note.
- Rifiutare senza motivo valido una richiesta ragionevole di verifica può annullare l’eleggibilità al premio per quella entry.
- Quando possibile faremo anche **live pubbliche** sui test della challenge (metodologia, sorprese, gap agente × linguaggio). Partecipare a una live è opzionale, salvo finalisti chiamati in verifica.

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

Usa un repo che **mantieni tu** (lavoro o personale). Linea guida dimensione: abbastanza superficie perché 10 task siano significativi (indicativamente ≥20 file sorgente).

In `metrics.json` **devi** dichiarare:

| Campo | Esempio |
|---|---|
| `languages` | `["TypeScript", "Python"]` |
| `frameworks` | `["NestJS", "FastAPI"]` — il solo linguaggio non basta |
| `approx_source_files` | `120` |
| `size_band` | `S` (<50) · `M` (50–199) · `L` (200–999) · `XL` (1000+) |

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

## Come entrare (niente signup ufficiale)

**Non c’è iscrizione separata.** Quando apri una PR valida di challenge con `metrics.json`, sei iscritto.

1. Installa CodeDNA e annota il progetto:

```bash
pipx install git+https://github.com/Larens94/codedna.git
codedna install --path . --tools <tuo-agente>
codedna init . --no-llm   # oppure con LLM per le rules:
```

2. Esegui i ≥10 task (Control vs CodeDNA, stack equo).
3. Apri una PR con `challenge/<handle>/metrics.json`.
4. Facciamo review, merge e aggiorniamo la [bacheca pubblica](challenge.html).

Solo domande (opzionale): GitHub Discussions / Discord — il vecchio template “entry issue” non è obbligatorio.

### Se qualcosa si rompe sul tuo agente o linguaggio

CodeDNA è ancora sperimentale tra agenti e linguaggi. Percorso consigliato:

1. Riproduci una volta (agente + linguaggio/framework + comando).
2. Apri una **issue** (bug) o una **PR** con fix minimo / test di regressione.
3. Continua la challenge se puoi; annota l’incidente in `metrics.json` → `bugs_reported` e in `notes.md`.

Tooling rotto su un certo stack **non** ti squalifica — segnalarlo è utile.

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
- Call di verifica: Google Meet (o simile) su richiesta dei maintainer  
- Live pubbliche: annunciate su Discussions / Discord quando programmate  
- Maintainer: Fabrizio Corpora  

---

## Licenza delle submission

Aprendo una PR di challenge concedi il permesso di citare **metriche e sintesi anonimizzate** in docs / blog / video di CodeDNA. Non caricare secret, sorgenti proprietarie o credenziali. Redigi i log.
