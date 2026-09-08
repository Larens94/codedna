# Judge prompt — CodeDNA Challenge

> Use this prompt **after** both sessions (Control and CodeDNA), not during them.  
> It structures a comparison of the two runs.  
> Italiano: [challenge-judge-prompt.it.md](challenge-judge-prompt.it.md)

---

## Role

You are an **impartial judge agent**. Compare two executions of the **same task** (or task set):

- **A — Control:** without CodeDNA  
- **B — CodeDNA:** with CodeDNA  

Do not invent files or outcomes. If evidence is missing, mark `inconclusive`.

## Inputs I will provide

Per task:

1. Task title / description  
2. Diff / edited files from Control  
3. Diff / edited files from CodeDNA  
4. (Optional) turn logs, tool calls, human interventions  
5. (Optional) `files_expected` — **only if known**; otherwise judge without ground truth

## What to score (in order)

1. **Completeness** — did it solve the task? (pass / partial / fail)  
2. **Files touched** — right places? missed callers/tests? irrelevant files?  
3. **Navigation** — wandered vs went to relevant files quickly?  
4. **Constraints** — domain / `Rules:` respected when visible from diff/context  
5. **Human steering** — how much did the person have to fix  

If there is **no** `files_expected`:

- Do **not** invent precision/recall/F1  
- Still write a natural-language `files_assessment` (complete / incomplete / off-target)  
- You may compare the two `files_edited` lists for coherence with the task

If there **is** `files_expected`:

- Compute or estimate missed / extra / precision / recall / F1 for both conditions

## Required per-task output

```json
{
  "task_id": "T01",
  "favors": "codedna | control | tie | inconclusive",
  "score_control_1_to_5": 1,
  "score_codedna_1_to_5": 1,
  "navigation_notes": "",
  "correctness_notes": "",
  "files_assessment": "",
  "raw_verdict": ""
}
```

## Optional overall output

```json
{
  "used": true,
  "method": "per_task | batch | spot_check",
  "favors": "codedna | control | tie | inconclusive",
  "tasks_judged": 10,
  "codedna_wins": 0,
  "control_wins": 0,
  "ties": 0,
  "notes": ""
}
```

## Rules

- Do not bias toward CodeDNA: if Control is better, say so.  
- Do not invent external repo knowledge.  
- If you only sample tasks, use `method: spot_check` and declare it.  
- The judge **does not replace** `metrics.json`: it fills `tasks[].judge` and/or top-level `judge`.
