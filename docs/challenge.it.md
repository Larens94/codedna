# CodeDNA Challenge — €200

> **Lingua:** Italiano · [English](challenge.md)  
> **Stato:** bozza / aperta  
> **Premio:** €200  
> **Durata:** 1 mese dalla data ufficiale di inizio  
> **Iscrizione:** aprire la PR con le metriche = sei iscritto (niente signup ufficiale)  
> **Non è un rerun di SWE-bench.** Provi CodeDNA sul **tuo** progetto.  
> **Classifica pubblica:** [challenge.html](challenge.html) sul sito docs

Questa challenge pone una sola domanda:

> CodeDNA aiuta (o no) quando fai sviluppo reale assistito da AI — e possiamo misurarlo in modo onesto?

**Sperimentale.** La qualità di CodeDNA dipende ancora dall’**agente AI di coding** e dal **linguaggio / framework** che usi. Alcune combinazioni funzionano meglio di altre. Se install, annotation, hook o refresh non si comportano bene sul tuo stack, **apri una GitHub issue o una PR di fix** — fa parte della challenge, e sistemiamo upstream a partire dai tuoi report.

---

## In sintesi

1. Lavori sul **tuo progetto reale e funzionante** (non sui nostri vecchi benchmark — non un sito giocattolo).
2. Dichiari lo **stack tecnologico** completo (linguaggi, framework, agente, percorso di install).
3. Esegui **almeno 10 task** (mix facili / medi / difficili) — gli **stessi task due volte**: una **senza** CodeDNA e una **con** CodeDNA.
4. Tieni lo stack AI **equo** (vedi Livelli sotto).
5. Documenti **come hai installato CodeDNA**; segnali bug / apri PR di fix quando qualcosa si rompe (atteso — è ancora sperimentale).
6. Apri una **Pull Request** con `metrics.json` — anche se CodeDNA risulta peggiore. **Quella PR è la tua iscrizione.**
7. La **bacheca / classifica pubblica si aggiorna quando arrivano PR valide** e resta visibile sul sito docs.
8. Il progetto può essere chiamato a una **review live / presentazione** (call) così verifichiamo che i test siano reali.
9. Il premio si sblocca solo se si raggiunge il **minimo di partecipanti**.

---

## Premio e minimo partecipanti

| Voce | Regola |
|---|---|
| Montepremi | **€200** (pagati alla submission vincitrice dopo la review) |
| Submission valide minime | **5** per sbloccare il premio (obiettivo stretch: 10) |
| Se ci sono meno di 5 PR valide | I risultati si pubblicano comunque; il premio **non** viene assegnato (o passa all’edizione successiva) |
| Vincitore | Scelto da Fabrizio Corpora + team di review (non voto community) |
| Onestà | Le affermazioni devono essere vere e supportate da evidenze — metriche inventate, progetti finti o narrative false = squalifica |
| Verifica | Fabrizio o il team di review possono richiedere una **call + presentazione** (Google Meet / simile): mostrare il progetto reale, spiegare come hai fatto i test, ripercorrere install + `metrics.json` |
| Bacheca pubblica | La classifica su [challenge.html](challenge.html) si aggiorna **appena arrivano PR valide** (review maintainer → riga in bacheca) e resta visibile |
| Live | Quando possibile ospiteremo live pubbliche sui test inviati (con consenso del partecipante dove serve) |

### Cosa valutiamo (in ordine)

1. **Onestà del protocollo** — progetto reale, stack equo, modalità dichiarata, note riproducibili; **niente risultati inventati**  
2. **Qualità dei task** — mix reale facili/medi/difficili su una codebase funzionante  
3. **Evidenze** — metriche + percorso di install + breve narrativa; a favore **o** contro CodeDNA va bene  
4. **Bug report / PR di fix** — obbligatori quando CodeDNA si rompe sul tuo agente o linguaggio; le issue actionable contano positivamente  
5. **Chiarezza** — un altro engineer può ripetere il confronto  

### Onestà, call di review e live

- **Non puoi inventare** esiti pass/fail, tempi, dettagli di stack o claim narrativi. Se non riesci a riprodurre un numero, marca il task come inconclusive e dillo.
- **Progetti finti o throwaway non sono ammessi.** Possiamo richiedere una **conferenza live + breve presentazione** in cui:
  - dimostri che il progetto è reale e funzionante;
  - spieghi lo stack tecnologico;
  - mostri come hai installato CodeDNA;
  - mostri come hai eseguito gli **stessi task** con e senza CodeDNA;
  - rispondi su `metrics.json` / note.
- Rifiutare senza motivo valido una richiesta ragionevole di verifica può annullare l’eleggibilità al premio per quella entry.
- Quando possibile faremo anche **live pubbliche** sui test della challenge (metodologia, sorprese, gap agente × linguaggio). Partecipare a una live è opzionale, salvo richiesta di verifica.

---

## Timeline (da compilare prima della pubblicazione)

| Fase | Quando |
|---|---|
| Annuncio + video | **TBD** |
| Apertura submission (PR = iscrizione) | **TBD** |
| Finestra challenge | **1 mese** dalla data di inizio |
| Scadenza submission | fine della finestra (le PR devono essere aperte) |
| Bacheca / classifica | aggiornata in continuo quando arrivano PR valide |
| Review | ~1–2 settimane dopo la scadenza (più eventuali presentazioni Meet) |
| Annuncio vincitore | **TBD** |

---

## Chi può partecipare

- Chiunque usi un agente AI di coding (Cursor, Claude Code, Codex, Copilot, Cline, Roo, Windsurf, OpenCode, …)
- Solo o piccolo team (una PR per partecipante / team)
- Il progetto può restare privato durante la run; la **PR con le metriche** su questo repo deve essere pubblica

---

## Protocollo centrale (obbligatorio)

### 1. Il tuo progetto (deve essere reale)

Usa un repo che **mantieni tu** (lavoro o personale). Deve essere un **progetto reale e funzionante** — anche piccolo va bene; una pagina vetrina, un hello-world o una demo throwaway **no**.

**Esempi rifiutati:** sito vetrina monostrato, CRUD vuoto senza logica di dominio, repo sintetici costruiti solo per la challenge.

**Esempi accettati:** un servizio che usi o shippi davvero, un tool interno, una libreria con caller reali, un prodotto piccolo ma completo (≥ **25** file sorgente come soglia dura).

In `metrics.json` **devi** dichiarare lo **stack tecnologico**:

| Campo | Esempio |
|---|---|
| `languages` | `["TypeScript", "Python"]` |
| `frameworks` | `["NestJS", "FastAPI"]` — il solo linguaggio **non** basta |
| `approx_source_files` | `120` (minimo **25**) |
| `size_band` | `S` (<50) · `M` (50–199) · `L` (200–999) · `XL` (1000+) |
| `tech_stack_notes` | opzionale — DB, layout monorepo, infra, lib principali |
| `install.agent` + `install.steps` | quale agente AI + comandi esatti di install/init CodeDNA |

### 2. Almeno dieci task — gli stessi in entrambe le condizioni

Definisci **≥10** task **prima** delle run cronometrate (o congela l’elenco nella PR).

Mix suggerito:

| Difficoltà | Conteggio (min) | Esempi |
|---|---|---|
| Facile | ≥3 | rename + aggiornare i caller, aggiungere un campo, fix chiaro con file già noto |
| Media | ≥3 | feature cross-file, refactor con invarianti, cambio API |
| Difficile | ≥2 | bug multi-modulo, vincolo architetturale, “dove cambio questo in sicurezza?” |

Per ogni task registra: obiettivo, difficoltà, agente/tool, successo/fallimento, note.

**Critico:** ogni task va eseguito in **entrambe** le condizioni. Non inventare liste di task diverse per Control vs CodeDNA.

### 3. Due condizioni: senza vs con CodeDNA

Per **ciascuno degli stessi task** esegui:

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

Compila anche:

- `summary.favors`: `codedna` | `control` | `tie` | `inconclusive`
- `install` — **obbligatorio**: agente + passi esatti di install/init (e se ha funzionato)
- `bugs_reported` — array **obbligatorio** (vuoto se nessuno); se qualcosa si è rotto, apri issue o PR di fix e elencala qui

I numeri grezzi possono favorire CodeDNA **oppure no**. L’onestà batte il tifo.  
`notes.md` è narrativa opzionale — **non sostituisce** `metrics.json`.

### 6. Percorso di install + bug report (obbligatori quando rilevanti)

Pubblica **come hai installato CodeDNA** in `metrics.json` → `install` (comandi, flag `--tools`, agente).  
CodeDNA è ancora **sperimentale**: può fallire o comportarsi male con alcuni tool agentici (Claude Code, OpenCode, Cursor, Codex, …) o linguaggi.

Se install, annotation, hook o refresh si comportano male:

1. Riproduci una volta (agente + linguaggio/framework + comando).
2. Apri una **GitHub issue** o una **PR di fix**.
3. Elencala in `bugs_reported` e menzionala in `notes.md`.

Tooling rotto su un certo stack **non** ti squalifica — **nasconderlo** sì.

### 7. Submission = Pull Request

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

### 8. Bacheca / classifica pubblica

La classifica live è [challenge.html](challenge.html) (dati: [`challenge-board.json`](challenge-board.json)).

- Appena una PR metrics valida viene reviewata, aggiungiamo/aggiorniamo una riga — la bacheca resta **visibile pubblicamente**.
- Aprire una PR ti iscrive; comparire in bacheca significa che i maintainer hanno accettato formato e dichiarazione di stack.

---

## Come entrare (niente signup ufficiale)

**Non c’è iscrizione separata.** Quando apri una PR valida di challenge con `metrics.json`, sei iscritto.

1. Installa CodeDNA e annota il progetto (registra i passi esatti in `install`):

```bash
pipx install git+https://github.com/Larens94/codedna.git
codedna install --path . --tools <tuo-agente>
codedna init . --no-llm   # oppure con LLM per le rules:
```

2. Esegui i ≥10 **stessi** task due volte (Control vs CodeDNA, stack equo).
3. Apri una PR con `challenge/<handle>/metrics.json` (includi `install` + `bugs_reported`).
4. Facciamo review, aggiorniamo la [bacheca pubblica](challenge.html) e possiamo invitarti a una presentazione Meet.

Solo domande (opzionale): GitHub Discussions / Discord — il vecchio template “entry issue” non è obbligatorio.

### Se qualcosa si rompe sul tuo agente o linguaggio

CodeDNA è ancora sperimentale tra agenti e linguaggi (Claude Code, OpenCode, Cursor, Codex, …). Percorso consigliato:

1. Riproduci una volta (agente + linguaggio/framework + comando).
2. Apri una **issue** (bug) o una **PR** con fix minimo / test di regressione.
3. Continua la challenge se puoi; annota l’incidente in `metrics.json` → `bugs_reported` e in `notes.md`.

Tooling rotto su un certo stack **non** ti squalifica — **nasconderlo** sì.

---

## Cosa non è questa challenge

- Non è un rerun di SWE-bench / delle nostre tabelle F1 storiche  
- Non è “annota solo i nostri repo di fixture”  
- Non è un sito throwaway o hello-world costruito solo per il premio  
- Non è consulenza gratis per noi — tieni l’IP del tuo progetto; noi reviewiamo solo la PR delle metriche (+ eventuale presentazione Meet)  

---

## Comunicazione

- Issue / bug: GitHub Issues  
- Q&A challenge: GitHub Discussions (Announcements / Q&A)  
- Community: Discord (vedi badge in README)  
- Call di verifica / presentazione: Google Meet (o simile) su richiesta dei maintainer  
- Live pubbliche: annunciate su Discussions / Discord quando programmate  
- Maintainer: Fabrizio Corpora  

---

## Licenza delle submission

Aprendo una PR di challenge concedi il permesso di citare **metriche e sintesi anonimizzate** in docs / blog / video di CodeDNA. Non caricare secret, sorgenti proprietarie o credenziali. Redigi i log.
