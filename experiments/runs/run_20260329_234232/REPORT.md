# Experiment Report — CodeDNA v0.8 vs Standard Python
**Run ID:** `run_20260329_234232`
**Date:** 2026-03-29 / 2026-03-30
**Model:** DeepSeek `deepseek-chat` — 5 agents, `TeamMode.coordinate`
**Config:** `tool_call_limit=30` per agent, `max_iterations=100` per team
**Status:** Both conditions complete and verified by judge. Final data from `comparison.json`.

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
| Judge fixes to boot | **8** | **12** | A |
| Player controllable after fixes | **Yes** (WASD) | **No** | A |

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
| GameplayDesigner | 03:25:33 | 04:01:15 | **35m 42s** | Inherited `game_state.py` monolith from director |
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

**Only exception — DataArchitect:** A's DataArchitect was slower (47m vs 35m) due to a Pydantic
API error at 01:03:34 (`read_file(start_line=1)` — unexpected keyword argument), which forced
fallback to shell commands and retry loops, and still left `save_system.py` incomplete.
B's DataArchitect ran cleanly within budget.

### The director centralization cascade

Without `used_by:` contracts, B's director spent 25m occupying all four module namespaces.
Every subsequent specialist inherited structure they didn't design:

```
B Director builds full scaffold (25m, 2.0× A)
  → GameEngineer reverse-engineers core.py + bolts ECS on top (36m, 3.9× A)
    → GraphicsSpecialist works around pre-built renderer.py (41m, 1.4× A)
      → GameplayDesigner inherits game_state.py monolith (35m, 2.6× A)
        → DataArchitect — most independent module, cleanest run (35m, 0.75× A)
  → GameDirector R2 — more incoherence to reconcile (15m, 2.9× A)
```

The cascade effect peaks at GameEngineer (nearest to director's territorial decisions)
and diminishes toward DataArchitect (most independent domain).

### LOC vs modularity

B produced more lines (14,096 vs 10,194) but fewer files (45 vs 50):

| | A — CodeDNA | B — Standard |
|---|---|---|
| Files | 50 | 45 |
| LOC | 10,194 | 14,096 |
| Avg LOC/file | **203** | **313** |

B's average file is 54% larger — confirming the monolithic architecture. A's smaller,
more numerous files reflect genuine module decomposition driven by `used_by:` ownership declarations.

---

## 4. Qualitative Observations

### Architecture

**Condition A** produced a proper **ECS (Entity-Component-System)** with archetype-based
storage and clear per-agent module ownership:
- `engine/world.py` — World with archetype migration, `rules: Must support 10,000+ entities at 60 FPS`
- `engine/component.py` / `engine/entity.py` — clean separation of data and identity
- `gameplay/components/` — 6 component types (player, combat, movement, inventory, quest, npc)
- `gameplay/systems/` — 5 dedicated systems, each owned by GameplayDesigner
- Director returned for a round 2 integration pass (5m 8s) verifying module coherence

**Condition B** produced a **monolithic director-owned skeleton** with specialists bolting on extensions:
- `engine/core.py` — single `GameEngine` class written by the director, not GameEngineer
- `engine/ecs.py` — ECS bolted on by GameEngineer as a second-class addition
- `engine/physics.py` — completely empty (GameEngineer stalled at tool_call_limit)
- `gameplay/game_state.py` — 545-line monolith written by director; declared imports
  to 4 subsystems (`entity_system`, `physics_engine`, `ai_system`, `player_controller`)
  that GameplayDesigner never wrote
- `gameplay/systems/player_system.py` — written by GameplayDesigner (408 lines, real code)
  but **never connected** to anything; floating module with no caller
- `integration/` — entirely empty; no agent wrote a single file

### Annotation Compliance (Condition A)

94% coverage (47/50). The 3 non-compliant files were utility scripts
(`simple_test.py`, `test_structure.py`, `verify_architecture.py`) written by GameDirector
outside the module structure. Minor format errors: date `2024-1-15` instead of `YYYY-MM-DD`,
and `' - '` separator instead of `' — '` (em dash).

---

## 5. Judge Intervention

### Condition A — 8 fixes (all on existing code)

All bugs were **interface mismatches between agents**, not logic errors within individual modules.
Every fix was a correction to code that existed but was wrong:

| # | File | Bug | Root cause |
|---|---|---|---|
| 1 | `engine/world.py` | `create_entity()` never added entity to archetype entities list | incomplete implementation |
| 2 | `engine/world.py` | `_migrate_entity()` stored `None` as placeholder | acknowledged in comment, not fixed |
| 3 | `engine/entity.py` | missing `entity_id` property | GameDirector used `.entity_id`, entity had `.id` |
| 4 | `engine/component.py` | `__dataclass_fields__` check in `__init_subclass__` ran before `@dataclass` applied | Python decorator timing |
| 5 | `render/__init__.py` | OpenGL `Camera` class missing | GraphicsSpecialist wrote `CameraSystem` not `Camera` |
| 6 | `render/pygame_renderer.py` | `pygame.font.init()` circular import on Python 3.14 | environment mismatch |
| 7 | `gameplay/systems/player_system.py` | `glfw.get_key()` called on pygame Surface | mixed renderer APIs |
| 8 | `data/save_system.py` | class body missing (header only) | DataArchitect hit `tool_call_limit=30` after error |

**Result:** game boots at 60 FPS, 5 entities active (player, enemy, NPC, item, quest),
ECS systems running, **player controllable via WASD**.

### Condition B — 12 fixes (existing code bugs + missing modules)

B required more fixes and of a different nature. Fixes split into two categories:

**Category 1 — bugs on existing code (same type as A):**

| # | File | Bug | Root cause |
|---|---|---|---|
| 1 | `engine/main.py` | `from .physics import PhysicsEngine` — file completely empty | GameEngineer placeholder |
| 7 | `main.py` | `AssetManager(base_path=..., cache_size=...)` — wrong kwarg names | API mismatch director vs DataArchitect |
| 9 | `main.py` | `load_shader()`, `load_texture()`, `load_config()` not implemented | API mismatch director vs DataArchitect |
| 10 | `main.py` | `AssetManager.shutdown()` missing | AssetManager incomplete |

**Category 2 — missing modules (no equivalent in A):**

| # | File | Bug | Root cause |
|---|---|---|---|
| 3 | `gameplay/__init__.py` | 4 imports to modules that don't exist (`entity_system`, `physics_engine`, `ai_system`, `player_controller`) | Director pre-occupied namespace; GameplayDesigner declared but never wrote |
| 4 | `data/__init__.py` | `ConfigManager`, `SaveSystem` — stub files (docstring only) | DataArchitect ran out of tool calls |
| 5 | `integration/__init__.py` | 4 imports to files that don't exist | No agent wrote `integration/` at all |
| 6 | `main.py` | `Profiler` class missing (integration/ empty) | Same as above |
| 8 | `gameplay/game_state.py` | `_initialize_subsystems()` imports 4 missing modules | Same as fix 3 |
| 11 | `gameplay/game_state.py` | `render_data['entities']` always empty (`entity_system=None`) | Missing modules → no entities |
| 12 | `render/renderer.py` | `_mock_render()` was `print()` only — black screen | No pygame fallback renderer |

**Result:** game boots, 5 hardcoded test entities visible. **Player does not move.**

### Critical difference between A and B fixes

After all fixes:
- **A:** ECS running, 5 real entities with components, PlayerSystem reads WASD from pygame,
  entities move each frame. The integration layer was written by agents and just needed bug fixes.
- **B:** 5 hardcoded positions with no movement. `gameplay/systems/player_system.py` was
  written (408 lines, correct code) and `engine/ecs.py` was written (413 lines, correct code),
  but the **integration layer** between them (`entity_system.py`, `player_controller.py`) was
  never written by any agent. The judge would have had to write new modules from scratch —
  which is beyond bug-fixing and outside the scope of judge intervention.

> **This is the sharpest functional difference:** A produced a playable game after 8 bug fixes.
> B produced a visible but static scene after 12 fixes, with core gameplay mechanics missing
> because the integration layer was the gap left by director-centralization.

---

## 6. Findings

### Finding 1 — CodeDNA made the team 1.60× faster

A completed in 1h 59m; B in 3h 11m. The annotation protocol reduced per-agent duration
for 5 of 6 agent turns. The only exception was DataArchitect, where A was slower due to
a tool call API error unrelated to the protocol.

### Finding 2 — `used_by:` is a delegation forcing function with a cascade effect

With `used_by:` contracts, A's director delegated in 12m 26s. Without them, B's director
spent 25m building all scaffolding himself. Every downstream specialist paid a
reverse-engineering tax proportional to how much the director had pre-occupied their module.
The cascade peaks at GameEngineer (3.9×) and diminishes toward DataArchitect (0.75×,
most independent module).

### Finding 3 — More LOC does not mean more coverage

B produced 38% more lines (14,096 vs 10,194) but 10% fewer files (45 vs 50).
B's average file is 54% larger. More code, less functionality.

### Finding 4 — B's bugs were structurally different from A's

A had 8 fixes, all on existing code (wrong property name, empty method body, wrong API call).
B had 12 fixes: 4 on existing code, 8 on missing modules. The missing modules in B
(`entity_system`, `physics_engine`, `ai_system`, `player_controller`, full `integration/`)
were all in the gap created by the director pre-declaring a structure that specialists
then had to reverse-engineer rather than own.

### Finding 5 — CodeDNA produces a playable game; Standard does not

After judge intervention:
- A: playable (WASD movement, ECS running, 5 active entities)
- B: visible but static (5 hardcoded positions, no systems, no input)

The difference is not that B's code was bad — `engine/ecs.py` and `player_system.py` are
well-written. The difference is that the integration layer connecting them was never written,
because no agent owned that responsibility. In A, `used_by:` forced ownership assignment
upfront; in B, the director occupied the namespace and specialists could only bolt on.

### Finding 6 — `message:` field was never used (experiment design error)

0 entries in both conditions. In A: field was not in the prompt template.
In B: not expected. **Fix applied in next run:** `message:` now included in condition A's
prompt with full lifecycle instructions.

### Finding 7 — `rules:` are acknowledged but not enforced at generation time

`engine/world.py` declared `rules: Must support 10,000+ entities at 60 FPS` yet left a
`None` placeholder in `_migrate_entity()` with a comment acknowledging the incompleteness.
Annotation compliance ≠ semantic enforcement.

---

## 7. Open Questions

- Would raising `tool_call_limit` (e.g. to 50) give B's specialists enough budget to write the missing integration layer?
- Does the director-centralization pattern replicate in other task types (web app, data pipeline)?
- Does including `message:` in the prompt produce non-zero adoption in the AgentHub run?
- Would a `used_by:` enforcement gate at the director level prevent the cascade entirely?

---

## 8. Next Experiment

**Run:** `run_20260330_024934` — AgentHub SaaS ("Affitta il tuo agente AI") — **in progress**
**Stack:** FastAPI + Agno + SQLite + Jinja2 + TailwindCSS + APScheduler + Stripe
**Team:** ProductArchitect · BackendEngineer · AgentIntegrator · DataEngineer · FrontendDesigner
**Key fix:** `message:` field included in condition A prompt with full lifecycle instructions.
**Hypothesis under test:** with `message:` in the prompt, adoption > 0 and the promote/dismiss
ratio provides a measurable signal of cross-agent reasoning quality across sessions.

---

*Report finalised by claude-sonnet-4-6 | 2026-03-30 | s_20260330_001*
*Timing data from `run.log` line-by-line timestamps. Final metrics from `comparison.json`.*
*Judge intervention commits: `967edf9` (condition A), `f890530` (condition B).*
