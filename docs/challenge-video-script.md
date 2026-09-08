# Video script — CodeDNA Challenge (€200)

Target length: **3–5 minutes**. Language: Italian (with English titles on screen optional).

## Goal of the video

Explain **how the challenge starts**, what people must do, and the **fair-stack rule** — not a deep product demo.

---

## Shot list / outline

### 0. Hook (0:00–0:20)

**On screen:** `CodeDNA Challenge · €200`

**Say:**  
“Stiamo aprendo una challenge pubblica da 200 euro. Non è un altro SWE-bench: ognuno prova CodeDNA sul **proprio** progetto, con metriche vere, anche se vanno contro CodeDNA.”

### 1. Perché (0:20–0:50)

**Say:**  
“I benchmark interni li abbiamo già fatti. Ora serve altro: sviluppatori reali, stack reali, task facili/medi/difficili. Obiettivo: capire se CodeDNA aiuta — e dove no. I bug si segnalano e li correggiamo.”

### 2. Cosa fare (0:50–1:50)

**On screen bullets:**

1. Progetto tuo  
2. ≥10 task (easy / medium / hard)  
3. Senza CodeDNA vs con CodeDNA  
4. PR con metriche  
5. Durata 1 mese  

**Say:**  
“Definisci almeno dieci attività sul tuo repo. Le fai in due condizioni: controllo senza CodeDNA, e stessa cosa con CodeDNA annotato. Poi apri una pull request su GitHub con i numeri. Io e il team supervisiamo complessità e onestà del protocollo.”

### 3. Regola d’oro — livelli (1:50–3:00)  ★ important

**On screen diagram:**

```text
L2  Graphify / graph memory
L1  LLM wiki · skills · instruction packs
L0  CodeDNA (in-source)     ← layer under test
```

**Say:**  
“Se già usi skill, wiki, ricerche LSP, Graphify o altro, CodeDNA non si testa ‘al posto’ di quelle cose di nascosto. Controllo e CodeDNA devono avere **lo stesso stack sopra**.  
Livello 0 è CodeDNA. Livello 1 è wiki/skill/memoria LLM. Livello 2 è Graphify o simili.  
Se invece vuoi capire se **solo CodeDNA** può sostituire i livelli superiori, lo dichiari esplicitamente nei test. Altrimenti la submission non è valida.”

### 4. Premio e minimo partecipanti (3:00–3:40)

**Say:**  
“Il premio è 200 euro. Si sblocca con almeno **cinque** submission valide. Meno di cinque: pubblichiamo comunque i risultati, ma il premio non parte. Vince chi porta il protocollo più pulito e le evidenze più utili — non chi ‘difende’ CodeDNA.”

### 5. Come iscriversi (3:40–4:20)

**On screen:**

- Docs: `docs/challenge.md`  
- Issue template: Challenge entry  
- Install one-liner  

**Say:**  
“Apri l’issue di iscrizione, leggi il regolamento, installa CodeDNA, e quando parte la finestra da un mese parti con i tuoi dieci task. Link in descrizione.”

### 6. Close (4:20–4:45)

**Say:**  
“Se CodeDNA perde su qualche metrica, va bene: ci serve la verità. Ci vediamo nelle PR.”

**End card:** GitHub repo + Discord + `docs/challenge.md`

---

## B-roll ideas

- Terminal: `codedna init . --no-llm`  
- Diff of a CodeDNA header in a real file  
- Table mock: Control vs CodeDNA  
- Level diagram L0/L1/L2  

## Description box (YouTube / LinkedIn)

```text
CodeDNA Challenge — premio €200

Regolamento: https://github.com/Larens94/codedna/blob/main/docs/challenge.md
Iscrizione: apri una issue “CodeDNA Challenge entry”
Durata: 1 mese · min. 5 submission valide per sbloccare il premio

Testi CodeDNA sul TUO progetto (≥10 task). Stack L1/L2 a pari livello.
EOF
```

## Recording tips

- One take for section 3 (levels) — slow and clear  
- Show the parity table on screen while speaking  
- Avoid SWE-bench charts in this video (different experiment)
