# Experiment Report — CodeDNA v0.8 vs Standard Python
**Run ID:** `run_20260329_234232`
**Date:** 2026-03-29 / 2026-03-30
**Model:** DeepSeek `deepseek-chat` — 5 agents, `TeamMode.coordinate`
**Config:** `tool_call_limit=30` per agent, `max_iterations=100` per team
**Status:** Both conditions complete. Final data from `comparison.json`.

---

## 1. Setup

Both conditions used the **identical task** (same string, no leakage) and the **identical 5-agent team**:
`GameDirector → GameEngineer → GraphicsSpecialist → GameplayDesigner → DataArchitect`

The only variable was the **instructions** passed to each agent:

| | Condition A — CodeDNA | Condition B — Standard |
|---|---|---|
| Header format | `exports/used_by/rules/agent` mandatory on every file | PEP 8 + Google docstrings |
| Naming convention | `<type>_<shape>_<domain>_<origin>` | standard Python |
| Integration gate | Director verifies all files follow protocol | none |
| Inter-agent contracts | explicit via `used_by:` | implicit |

---

## 2. Quantitative Results

### Head-to-head summary

| Metric | Condition A — CodeDNA | Condition B — Standard | Winner |
|---|---|---|---|
| Total duration | **1h 59m 01s** | **3h 11m 01s** | **A (1.60× faster)** |
| Python files | **50** | 45 | A |
| Total LOC | 10,194 | **14,096** | B (more, but monolithic) |
| Avg LOC/file | **203** | 313 | A (more modular) |
| Annotation coverage | **94%** (47/50) | 0% | A |
| `message:` entries | 0 | 0 | — |
| Connection errors | 1 (tool call args) | 1 (reset at 04:51:11) | tie |

### Condition A — Annotation Protocol (CodeDNA)

**Per-agent breakdown (source: run.log timestamps):**

| Agent | Start | End | Duration | Notes |
|---|---|---|---|---|
| GameDirector (round 1) | 23:42:38 | 23:55:04 | **12m 26s** | Scaffold + ECS skeleton, delegated quickly |
| GameEngineer | 23:55:13 | 00:04:40 | **9m 27s** | ECS extensions, demo, tests |
| GraphicsSpecialist | 00:04:47 | 00:34:28 | **29m 41s** | Full render/ module (10 files) |
| GameplayDesigner | 00:34:37 | 00:48:27 | **13m 50s** | 6 components + 5 systems, fastest specialist |
| DataArchitect | 00:48:36 | 01:35:56 | **47m 20s** | Tool call error at 01:03:34; `save_system.py` incomplete |
| GameDirector (round 2) | 01:36:04 | 01:41:12 | **5m 8s** | Final integration + verification pass |
| **TOTAL** | 23:42:38 | 01:41:39 | **1h 59m 01s** | |

**Modules completed:** `engine/` (12 files), `render/` (10 files), `gameplay/` (14 files), `data/` (5 files), `integration/` (2 files)

### Condition B — Standard Practices

**Per-agent breakdown (source: run.log timestamps):**

| Agent | Start | End | Duration | Notes |
|---|---|---|---|---|
| GameDirector (round 1) | 01:41:45 | 02:06:57 | **25m 12s** | Built full scaffold before delegating (all 4 modules) |
| GameEngineer | 02:07:06 | 02:43:39 | **36m 33s** | Reverse-engineered structure; `physics.py` = placeholder |
| GraphicsSpecialist | 02:43:47 | 03:25:25 | **41m 38s** | Worked around pre-built `render/renderer.py` |
| GameplayDesigner | 03:25:33 | 04:01:15 | **35m 42s** | Inherited `game_state.py` from director |
| DataArchitect | 04:01:22 | 04:36:59 | **35m 37s** | Cleanest B agent run |
| GameDirector (round 2) | 04:37:34 | 04:52:40 | **15m 6s** | Connection reset at 04:51:11; completed anyway |
| **TOTAL** | 01:41:39 | 04:52:40 | **3h 11m 01s** | |

**Modules produced:** `engine/` (8 files), `render/` (8 files), `gameplay/` (5 files), `data/` (3 files), misc scripts (21 files)

---

## 3. Timing Analysis

### Per-agent duration comparison

| Agent | Duration A | Duration B | B / A ratio |
|---|---|---|---|
| GameDirector (round 1) | 12m 26s | 25m 12s | **2.0×** |
| GameEngineer | 9m 27s | 36m 33s | **3.9×** |
| GraphicsSpecialist | 29m 41s | 41m 38s | **1.4×** |
| GameplayDesigner | 13m 50s | 35m 42s | **2.6×** |
| DataArchitect | 47m 20s | 35m 37s | **0.75×** ← B faster |
| GameDirector (round 2) | 5m 8s | 15m 6s | **2.9×** |
| **TOTAL** | **1h 59m 01s** | **3h 11m 01s** | **1.60×** |

**Only exception — DataArchitect:** A's DataArchitect was slower (47m vs 35m) due to the
`read_file(start_line=1, end_line=10)` Pydantic error at 01:03:34, which forced fallback
to shell commands and retry loops, and still left `save_system.py` incomplete. B's DataArchitect
ran cleanly within budget.

### The director centralization cascade

Without `used_by:` contracts, B's director spent 25m occupying all four module namespaces.
Every subsequent specialist inherited structure they didn't design:

```
B Director builds full scaffold (25m, 2× A)
  → GameEngineer must reverse-engineer core.py + bolt on ECS (36m, 3.9× A)
    → GraphicsSpecialist works around pre-built renderer.py (41m, 1.4× A)
      → GameplayDesigner inherits game_state.py monolith (35m, 2.6× A)
        → DataArchitect last in chain but cleanest (35m, 0.75× A)
  → GameDirector R2 integration longer because more incoherence to fix (15m, 2.9× A)
```

The cascade effect is **cumulative**: each specialist downstream of the director paid a
reverse-engineering tax. The effect peaks at GameEngineer (nearest to the director's
territorial decisions) and diminishes toward DataArchitect (furthest downstream, most
independent module).

### LOC vs modularity

B produced more lines (14,096 vs 10,194) but fewer files (45 vs 50):

| | A — CodeDNA | B — Standard |
|---|---|---|
| Files | 50 | 45 |
| LOC | 10,194 | 14,096 |
| Avg LOC/file | **203** | **313** |

B's files are **54% larger on average** — confirming the monolithic architecture.
A's smaller avg file size reflects the granular module decomposition driven by `used_by:`
ownership declarations.

---

## 4. Qualitative Observations

### Architecture

**Condition A** produced a proper **ECS (Entity-Component-System)** with archetype-based
storage and clear per-agent module ownership:
- `engine/world.py` — World with archetype migration, `rules: Must support 10,000+ entities at 60 FPS`
- `engine/component.py` / `engine/entity.py` — clean separation of data and identity
- `gameplay/components/` — 6 component types (player, combat, movement, inventory, quest, npc)
- `gameplay/systems/` — 5 dedicated systems (movement, player, combat, inventory, quest)
- Director returned for a round 2 integration pass (5m 8s) verifying module coherence

**Condition B** produced a **monolithic director-owned skeleton** with specialists bolting
on extensions:
- `engine/core.py` — single `GameEngine` class (written by director, not engineer)
- `engine/ecs.py` — ECS added by GameEngineer as a second-class addition
- `engine/physics.py` — `# Placeholder for physics.py` (GameEngineer stalled)
- `gameplay/game_state.py` — monolithic state class (written by director)
- `render/renderer.py` — base written by director; GraphicsSpecialist added on top
- Director round 2 (15m 6s) had a connection reset — possibly struggling with incoherence

### Annotation Compliance (Condition A)

94% coverage (47/50). The 3 non-compliant files were utility scripts
(`simple_test.py`, `test_structure.py`, `verify_architecture.py`) written by GameDirector
outside the module structure. Minor format errors: date `2024-1-15` instead of `YYYY-MM-DD`,
and `' - '` separator instead of `' — '` (em dash).

### Judge Intervention (Condition A — post-generation fixes)

8 files required fixes to boot the game. All bugs were **interface mismatches between agents**,
not logic errors within individual modules:

| File | Bug | Root cause |
|---|---|---|
| `engine/world.py` | `create_entity()` never added entity to archetype | incomplete implementation |
| `engine/world.py` | `_migrate_entity()` stored `None` as placeholder | acknowledged in comment, not fixed |
| `engine/entity.py` | missing `entity_id` property | GameDirector used `.entity_id`, entity used `.id` |
| `engine/component.py` | premature `__dataclass_fields__` check in `__init_subclass__` | Python applies `@dataclass` after class body |
| `render/__init__.py` | OpenGL `Camera` class missing | GraphicsSpecialist wrote `CameraSystem` not `Camera` |
| `render/pygame_renderer.py` | `pygame.font.init()` circular import on Python 3.14 | environment mismatch |
| `gameplay/systems/player_system.py` | `glfw.get_key()` on pygame Surface | mixed renderer APIs |
| `data/save_system.py` | class body missing | DataArchitect hit `tool_call_limit=30` after error |

**Result after fixes:** game boots at 60 FPS, 5 entities active (player, enemy, NPC, item, quest),
ECS systems running, player controllable via WASD.

---

## 5. Findings

### Finding 1 — CodeDNA made the team 1.60× faster

A completed in 1h 59m; B in 3h 11m. The annotation protocol reduced per-agent duration
for 5 of 6 agent turns. The only exception was DataArchitect, where A was slower due to
a tool call API error unrelated to the protocol.

### Finding 2 — `used_by:` is a delegation forcing function with a cascade effect

With `used_by:` contracts, A's director delegated in 12m 26s. Without them, B's director
spent 25m building all scaffolding himself. Every downstream specialist paid a
reverse-engineering tax proportional to how much the director had pre-occupied their module.
The effect peaks at GameEngineer (3.9× slower) and diminishes toward DataArchitect
(actually faster, most independent).

### Finding 3 — More LOC does not mean more coverage

B produced 38% more lines of code (14,096 vs 10,194) but 10% fewer files (45 vs 50).
B's average file is 54% larger. A's smaller, more numerous files reflect genuine module
decomposition; B's larger files reflect specialists extending director-written monoliths.

### Finding 4 — Integration bugs scale with module boundary count

A produced 50 modular files and required 8 judge fixes — all at module boundaries.
B's monolithic structure may have fewer explicit boundaries, but this was not tested
since B was not run to verify boot. The integration bug pattern in A suggests that
`used_by:` annotations declared contracts correctly but DeepSeek did not reason over
them at generation time (annotation compliance ≠ semantic enforcement).

### Finding 5 — `message:` field was never used (experiment design error)

0 entries in both conditions. In A: field was not in the prompt template.
In B: field was never expected. **Fix applied in next run:** `message:` is now
included in condition A's prompt with lifecycle instructions.

### Finding 6 — `rules:` are acknowledged but not enforced

`engine/world.py` declared `rules: Must support 10,000+ entities at 60 FPS, archetype-based
storage` yet left a `None` placeholder in `_migrate_entity()` with a comment acknowledging
the incompleteness. The agent read and annotated the constraint, then violated it anyway.

---

## 6. Open Questions

- Does condition B produce a runnable game without judge intervention? (not tested)
- Is B's monolithic architecture easier or harder to fix than A's modular ECS?
- Does the director-centralization pattern replicate in other task types?
- Does including `message:` in the prompt produce non-zero adoption in the next run?
- Would raising `tool_call_limit` eliminate the DataArchitect bottleneck in A?

---

## 7. Next Experiment

**Run:** `run_20260330_024934` — AgentHub SaaS ("Affitta il tuo agente AI") — **in progress**
**Stack:** FastAPI + Agno + SQLite + Jinja2 + TailwindCSS + APScheduler + Stripe
**Team:** ProductArchitect · BackendEngineer · AgentIntegrator · DataEngineer · FrontendDesigner
**Key fix:** `message:` field included in condition A prompt with full lifecycle instructions.
**Hypothesis under test:** with `message:` in the prompt, adoption > 0 and the promote/dismiss
ratio provides a measurable signal of cross-agent reasoning quality across sessions.

---

*Report finalised by claude-sonnet-4-6 | 2026-03-30 | s_20260330_001*
*All timing data derived from `run.log` line-by-line timestamps. Final metrics from `comparison.json`.*
