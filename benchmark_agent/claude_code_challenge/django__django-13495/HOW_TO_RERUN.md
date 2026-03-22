# Come rieseguire il benchmark django__django-13495

## Struttura

```
django__django-13495/
├── control/          ← Django vanilla, nessuna annotazione
├── codedna/          ← Django con annotazioni CodeDNA
├── _backup_control/  ← backup originale control
├── _backup_codedna/  ← backup originale codedna
├── problem_statement.txt
└── HOW_TO_RERUN.md
```

---

## Prima di ogni sessione: ripristino

Eseguire dal terminale:

```bash
BASE=~/Desktop/automation-lab/dynamic-bi-factory/codedna/benchmark_agent/projects_swebench/django__django-13495

# ripristina control
rm -rf "$BASE/control"
cp -r "$BASE/_backup_control" "$BASE/control"

# ripristina codedna
rm -rf "$BASE/codedna"
cp -r "$BASE/_backup_codedna" "$BASE/codedna"
```

---

## Apertura delle due istanze di Claude Code

**Istanza A — control:**
```bash
cd ~/Desktop/automation-lab/dynamic-bi-factory/codedna/benchmark_agent/projects_swebench/django__django-13495/control
claude
```

**Istanza B — codedna:**
```bash
cd ~/Desktop/automation-lab/dynamic-bi-factory/codedna/benchmark_agent/projects_swebench/django__django-13495/codedna
claude
```

---

## Prompt da incollare

### Istanza A (control)

```
Bug: Trunc() ignores tzinfo param when output_field=DateField()

I'm trying to use TruncDay() function like this:
  TruncDay('created_at', output_field=DateField(), tzinfo=tz_kyiv)

but for PostgreSQL the SQL generated is:
  (DATE_TRUNC('day', "storage_transaction"."created_at"))

So timezone conversion like AT TIME ZONE 'Europe/Kiev' was totally ignored.

Find the root cause and fix it.

---

Session logging (mandatory):
As you work, continuously append every step to session_log.md in the project root using this format:

## [EXPLORE] <what you opened/searched and why>
## [FOUND] <what you discovered>
## [DECISION] <what you decided to do and why>
## [ACTION] <what you changed and where>
## [VERIFY] <how you checked the fix is correct>

Write each entry immediately when it happens. Do not batch at the end.
```

### Istanza B (codedna)

```
Bug: Trunc() ignores tzinfo param when output_field=DateField()

I'm trying to use TruncDay() function like this:
  TruncDay('created_at', output_field=DateField(), tzinfo=tz_kyiv)

but for PostgreSQL the SQL generated is:
  (DATE_TRUNC('day', "storage_transaction"."created_at"))

So timezone conversion like AT TIME ZONE 'Europe/Kiev' was totally ignored.

Find the root cause and fix it.

Before writing any code, follow the CodeDNA reading protocol:
1. Read the .codedna manifest file first to understand recent project history (last 3-5 agent_sessions: entries).
2. Read the module docstring of every file you open before reading the code.
3. Parse exports:, used_by:, rules:, agent: fields.
4. For any function you edit, read its Rules: docstring first.
5. After editing, append an agent: line to the module docstring.
6. Update rules: if you discover a new constraint.
7. When checking used_by: dependencies, only follow the ones directly relevant to this task — do not explore the full dependency graph.

---

Session logging (mandatory):
As you work, continuously append every step to session_log.md in the project root using this format:

## [EXPLORE] <what you opened/searched and why>
## [FOUND] <what you discovered>
## [DECISION] <what you decided to do and why>
## [ACTION] <what you changed and where>
## [VERIFY] <how you checked the fix is correct>

Write each entry immediately when it happens. Do not batch at the end.
```

---

## Dopo ogni sessione: raccolta risultati

Raccogliere da entrambe le istanze:
- `session_log.md` — log delle azioni
- tutti i file modificati rispetto al backup

```bash
# vedere cosa ha cambiato control
diff -rq "$BASE/control" "$BASE/_backup_control" --exclude="session_log.md"

# vedere cosa ha cambiato codedna
diff -rq "$BASE/codedna" "$BASE/_backup_codedna" --exclude="session_log.md"
```

---

## Dimensioni da confrontare nell'analisi

| Dimensione | Cosa osservare |
|---|---|
| Navigazione | Quanti [EXPLORE] prima di trovare il file giusto? |
| Root cause | L'ha identificata correttamente e completamente? |
| Scope fix | Ha modificato solo i file necessari o di più? |
| Correttezza | Il patch coincide con quello atteso? |
| Reasoning | Il [DECISION] è motivato o meccanico? |
| Messaggi futuri | Il codedna ha lasciato agent:/rules:/message: utili? |
