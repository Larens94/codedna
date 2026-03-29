#!/usr/bin/env python3
"""run_experiment.py — Blind controlled experiment: same 5-agent team, two annotation styles.

exports: run_experiment(condition: str) -> dict, reset_runs(run_id: str | None) -> None
used_by: [manual execution] → see --help
rules:   SHARED_TASK must be byte-identical for both conditions;
         agents must never know they are part of an experiment;
         the word 'codedna' must NEVER appear in any traditional-condition instruction or comment;
         each condition writes only inside its own isolated output_dir (os.chdir + FileTools base_dir);
         --reset deletes only experiments/runs/ — never other project files
agent:   claude-sonnet-4-6 | anthropic | 2026-03-29 | s_20260329_002 | Initial design
         claude-sonnet-4-6 | anthropic | 2026-03-29 | s_20260329_003 | Fixed silent-failure bug: RunErrorEvent no longer masked as success; added file-count guard on success flag; resume now requires file_count>0; added max_iterations=100 to Team (agno 2.5.11 default=10 causes premature RunCancelledEvent)

USAGE:
    python run_experiment.py                          # run both conditions
    python run_experiment.py --condition a            # run condition-A only
    python run_experiment.py --condition b            # run condition-B only
    python run_experiment.py --list-runs              # show all saved runs
    python run_experiment.py --reset                  # delete ALL runs (asks for confirmation)
    python run_experiment.py --clean-run <run_id>     # delete one specific run
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from agno.agent import Agent
from agno.team import Team
from agno.team.mode import TeamMode
from agno.models.deepseek import DeepSeek
from agno.tools.file import FileTools
from agno.tools.shell import ShellTools

RUNS_ROOT = Path(__file__).parent / "runs"


# ─────────────────────────────────────────────────────────────────────────────
# REAL-TIME LOGGER — writes to run_dir/run.log and stdout simultaneously
# ─────────────────────────────────────────────────────────────────────────────

class RunLogger:
    """Writes timestamped log entries to run.log and stdout.

    Rules:   Always append — never overwrite; flush after every write so the
             dashboard can tail the file in real-time.
    """

    def __init__(self, run_dir: Path):
        self.log_file = run_dir / "run.log"
        self._fh = open(self.log_file, "a", buffering=1, encoding="utf-8")

    def log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line, flush=True)
        self._fh.write(line + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


# ─────────────────────────────────────────────────────────────────────────────
# SHARED TASK — exact same string for both conditions, no leakage
# ─────────────────────────────────────────────────────────────────────────────

SHARED_TASK = """Build a 2D RPG game using Pygame.

GAME REQUIREMENTS:
- Player movement (WASD / arrow keys)
- Combat system with enemy AI
- Inventory and item management (equip, drop, pick up)
- Quest system with NPCs and objectives
- Save / load game state via SQLite database
- Target performance: stable 60 FPS

DELIVERABLES:
1. Organise code into modules with clear responsibilities (you decide the architecture)
2. Each module must expose a clean public interface
3. Document all architectural decisions in reasoning_logs/
4. The game must be runnable with: python main.py

OUTPUT: A complete, runnable 2D RPG game.
"""


# ─────────────────────────────────────────────────────────────────────────────
# CONDITION-A INSTRUCTIONS  (in-source annotation protocol)
# ─────────────────────────────────────────────────────────────────────────────

def _instr_a_director() -> str:
    return """You are the Game Director on a professional game development team.
You coordinate all five specialists and are responsible for the overall architecture.

Your team uses an in-source annotation protocol as its standard.
Every Python file your team produces must open with this exact header:

    \"\"\"filename.py — <purpose, max 15 words>.

    exports: <function(arg) -> return_type>
    used_by: <consumer_file.py → consumer_function>
    rules:   <hard architectural constraints — update when you discover new ones>
    agent:   <YourName> | <YYYY-MM-DD> | <what you implemented and what you noticed>
    \"\"\"

For functions with non-obvious domain constraints, add a Rules: docstring:

    def process(x: int) -> str:
        \"\"\"One-line description.
        Rules: constraint the next developer must respect here.
        \"\"\"

Semantic naming — data-carrying variables use <type>_<shape>_<domain>_<origin>:
    list_dict_entities_from_engine = engine.get_entities()   # correct
    data = engine.get_entities()                              # avoid

YOUR RESPONSIBILITIES:
- Create the directory structure: engine/, render/, gameplay/, data/, integration/, reasoning_logs/
- Delegate each module to the right specialist
- Verify all files follow the annotation protocol before integration
- Log all architectural decisions in reasoning_logs/team_decisions.md
"""


def _instr_a_engineer() -> str:
    return """You are the Game Engineer on a professional game development team.
Your module is engine/ — game loop, state machine, entity manager.

Your team uses an in-source annotation protocol as its standard.
Every Python file you produce must open with this exact header:

    \"\"\"filename.py — <purpose, max 15 words>.

    exports: <function(arg) -> return_type>
    used_by: <consumer_file.py → consumer_function>
    rules:   <hard architectural constraints — update when you discover new ones>
    agent:   GameEngineer | <YYYY-MM-DD> | <what you implemented and what you noticed>
    \"\"\"

DELIVERABLES for engine/:
- GameEngine class with fixed-timestep loop (60 FPS)
- StateMachine for game states (menu, playing, paused, game_over)
- EventSystem for decoupled game events
- Entity manager for all game objects

engine/main.py must export: GameEngine(), StateMachine(), run_game() -> None
Log decisions in reasoning_logs/engine_decisions.md
"""


def _instr_a_graphics() -> str:
    return """You are the Graphics Specialist on a professional game development team.
Your module is render/ — sprite rendering, camera, UI.

Your team uses an in-source annotation protocol as its standard.
Every Python file you produce must open with this exact header:

    \"\"\"filename.py — <purpose, max 15 words>.

    exports: <function(arg) -> return_type>
    used_by: <consumer_file.py → consumer_function>
    rules:   <hard architectural constraints — update when you discover new ones>
    agent:   GraphicsSpecialist | <YYYY-MM-DD> | <what you implemented and what you noticed>
    \"\"\"

DELIVERABLES for render/:
- SpriteRenderer: loads and draws sprites with z-ordering
- CameraSystem: viewport management and world-to-screen transform
- UIRenderer: health bars, inventory overlay, quest log panel
- Particle system for combat effects

render/main.py must export: SpriteRenderer(), CameraSystem(), draw_ui() -> None
Log decisions in reasoning_logs/graphics_decisions.md
"""


def _instr_a_gameplay() -> str:
    return """You are the Gameplay Designer on a professional game development team.
Your module is gameplay/ — player, combat, inventory, quests.

Your team uses an in-source annotation protocol as its standard.
Every Python file you produce must open with this exact header:

    \"\"\"filename.py — <purpose, max 15 words>.

    exports: <function(arg) -> return_type>
    used_by: <consumer_file.py → consumer_function>
    rules:   <hard architectural constraints — update when you discover new ones>
    agent:   GameplayDesigner | <YYYY-MM-DD> | <what you implemented and what you noticed>
    \"\"\"

DELIVERABLES for gameplay/:
- PlayerSystem: movement, stats, levelling, progression
- CombatSystem: damage calculation, enemy AI, victory conditions
- InventorySystem: item stack, equip/unequip, currency
- QuestSystem: objectives, NPC dialogue, rewards

gameplay/main.py must export: PlayerSystem(), CombatSystem(), InventorySystem()
Log decisions in reasoning_logs/gameplay_decisions.md
"""


def _instr_a_data() -> str:
    return """You are the Data Architect on a professional game development team.
Your module is data/ — SQLite save system, asset manager, config loader.

Your team uses an in-source annotation protocol as its standard.
Every Python file you produce must open with this exact header:

    \"\"\"filename.py — <purpose, max 15 words>.

    exports: <function(arg) -> return_type>
    used_by: <consumer_file.py → consumer_function>
    rules:   <hard architectural constraints — update when you discover new ones>
    agent:   DataArchitect | <YYYY-MM-DD> | <what you implemented and what you noticed>
    \"\"\"

DELIVERABLES for data/:
- SaveSystem: SQLite schema, save/load/delete slots
- AssetManager: lazy sprite/sound loading with cache
- ConfigLoader: JSON game configuration with defaults

data/main.py must export: SaveSystem(), AssetManager(), load_config() -> dict
Log decisions in reasoning_logs/data_decisions.md
"""


# ─────────────────────────────────────────────────────────────────────────────
# CONDITION-B INSTRUCTIONS  (standard Python best practices — no annotations)
# ─────────────────────────────────────────────────────────────────────────────

def _instr_b_director() -> str:
    return """You are the Game Director on a professional game development team.
You coordinate all five specialists and are responsible for the overall architecture.

YOUR RESPONSIBILITIES:
- Create the directory structure: engine/, render/, gameplay/, data/, integration/, reasoning_logs/
- Delegate each module to the right specialist
- Ensure consistent interfaces across modules
- Log all architectural decisions in reasoning_logs/team_decisions.md

CODING STANDARDS:
- Follow PEP 8 style guidelines
- Write clear docstrings (Google style) for all public APIs
- Use type hints for all public functions
- Keep functions focused and small
- Prefer composition over inheritance
"""


def _instr_b_engineer() -> str:
    return """You are the Game Engineer on a professional game development team.
Your module is engine/ — game loop, state machine, entity manager.

DELIVERABLES for engine/:
- GameEngine class with fixed-timestep loop (60 FPS)
- StateMachine for game states (menu, playing, paused, game_over)
- EventSystem for decoupled game events
- Entity manager for all game objects

engine/main.py must expose: GameEngine, StateMachine, run_game
Log decisions in reasoning_logs/engine_decisions.md

CODING STANDARDS:
- Follow PEP 8 style guidelines
- Write clear Google-style docstrings for all public APIs
- Use type hints for all public functions
- Apply SOLID principles and separation of concerns
"""


def _instr_b_graphics() -> str:
    return """You are the Graphics Specialist on a professional game development team.
Your module is render/ — sprite rendering, camera, UI.

DELIVERABLES for render/:
- SpriteRenderer: loads and draws sprites with z-ordering
- CameraSystem: viewport management and world-to-screen transform
- UIRenderer: health bars, inventory overlay, quest log panel
- Particle system for combat effects

render/main.py must expose: SpriteRenderer, CameraSystem, draw_ui
Log decisions in reasoning_logs/graphics_decisions.md

CODING STANDARDS:
- Follow PEP 8 style guidelines
- Write clear Google-style docstrings for all public APIs
- Use type hints for all public functions
- Apply SOLID principles and separation of concerns
"""


def _instr_b_gameplay() -> str:
    return """You are the Gameplay Designer on a professional game development team.
Your module is gameplay/ — player, combat, inventory, quests.

DELIVERABLES for gameplay/:
- PlayerSystem: movement, stats, levelling, progression
- CombatSystem: damage calculation, enemy AI, victory conditions
- InventorySystem: item stack, equip/unequip, currency
- QuestSystem: objectives, NPC dialogue, rewards

gameplay/main.py must expose: PlayerSystem, CombatSystem, InventorySystem
Log decisions in reasoning_logs/gameplay_decisions.md

CODING STANDARDS:
- Follow PEP 8 style guidelines
- Write clear Google-style docstrings for all public APIs
- Use type hints for all public functions
- Apply SOLID principles and separation of concerns
"""


def _instr_b_data() -> str:
    return """You are the Data Architect on a professional game development team.
Your module is data/ — SQLite save system, asset manager, config loader.

DELIVERABLES for data/:
- SaveSystem: SQLite schema, save/load/delete slots
- AssetManager: lazy sprite/sound loading with cache
- ConfigLoader: JSON game configuration with defaults

data/main.py must expose: SaveSystem, AssetManager, load_config
Log decisions in reasoning_logs/data_decisions.md

CODING STANDARDS:
- Follow PEP 8 style guidelines
- Write clear Google-style docstrings for all public APIs
- Use type hints for all public functions
- Apply SOLID principles and separation of concerns
"""


# ─────────────────────────────────────────────────────────────────────────────
# TEAM FACTORY
# ─────────────────────────────────────────────────────────────────────────────

def _build_team(condition: str, output_dir: Path) -> Team:
    """Build the identical 5-agent team for the given condition.

    Rules:   output_dir must be absolute and already exist;
             caller must os.chdir(output_dir) before team.run() to isolate stray writes.
    """
    model = DeepSeek(id="deepseek-chat")
    tools = [FileTools(base_dir=output_dir), ShellTools()]

    if condition == "a":
        specs = [
            ("GameDirector",       "Lead and coordinate the game development team", _instr_a_director()),
            ("GameEngineer",       "Implement engine/ module",                       _instr_a_engineer()),
            ("GraphicsSpecialist", "Implement render/ module",                        _instr_a_graphics()),
            ("GameplayDesigner",   "Implement gameplay/ module",                      _instr_a_gameplay()),
            ("DataArchitect",      "Implement data/ module",                          _instr_a_data()),
        ]
    else:
        specs = [
            ("GameDirector",       "Lead and coordinate the game development team", _instr_b_director()),
            ("GameEngineer",       "Implement engine/ module",                       _instr_b_engineer()),
            ("GraphicsSpecialist", "Implement render/ module",                        _instr_b_graphics()),
            ("GameplayDesigner",   "Implement gameplay/ module",                      _instr_b_gameplay()),
            ("DataArchitect",      "Implement data/ module",                          _instr_b_data()),
        ]

    members = [
        Agent(name=name, role=role, instructions=instr, model=model, tools=tools,
              tool_call_limit=30)
        for name, role, instr in specs
    ]

    return Team(
        name=f"RPG Dev Team [{condition.upper()}]",
        members=members,
        model=model,
        mode=TeamMode.coordinate,
        max_iterations=100,
    )


# ─────────────────────────────────────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────────────────────────────────────

def _collect_metrics(output_dir: Path) -> dict:
    """Scan output_dir for code metrics. Read-only."""
    py_files = list(output_dir.rglob("*.py"))
    total_lines = 0
    files_with_header = 0
    annotation_counts = {"exports": 0, "used_by": 0, "rules": 0, "agent": 0, "message": 0}

    for f in py_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            lines = text.splitlines()
            total_lines += len(lines)
            header = "\n".join(lines[:25])
            if "exports:" in header:
                files_with_header += 1
            for key in annotation_counts:
                if f"{key}:" in header:
                    annotation_counts[key] += 1
        except OSError:
            pass

    n = len(py_files)
    return {
        "python_file_count": n,
        "total_lines_of_code": total_lines,
        "files_with_annotation_header": files_with_header,
        "annotation_coverage_pct": round(100 * files_with_header / n, 1) if n else 0.0,
        "annotation_counts": annotation_counts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE CONDITION RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_condition(condition: str, run_dir: Path, logger: "RunLogger") -> dict:
    """Run one condition inside its isolated output directory."""
    output_dir = (run_dir / condition).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    label = "Annotation Protocol" if condition == "a" else "Standard Practices"
    logger.log(f"=== CONDITION {condition.upper()} — {label} ===")
    logger.log(f"Output dir: {output_dir}")

    original_cwd = Path.cwd()
    result: dict = {
        "condition": condition,
        "label": label,
        "output_dir": str(output_dir),
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "duration_seconds": None,
        "success": False,
        "error": None,
        "agent_response_preview": None,
        "metrics": {},
    }

    try:
        os.chdir(output_dir)
        logger.log(f"[{condition.upper()}] Building team...")
        team = _build_team(condition, output_dir)
        logger.log(f"[{condition.upper()}] Team ready — starting task...")
        chunks = []
        _last_member = None
        _error_events: list[str] = []
        _SKIP = {"RunContentEvent", "RunResponseContentEvent",
                 "TeamRunResponseContentEvent", "AgentRunResponseContentEvent"}
        for event in team.run(SHARED_TASK, stream=True):
            event_type = type(event).__name__
            chunks.append(str(event))

            # detect and log agent-level error events (e.g. RunErrorEvent, TeamRunErrorEvent)
            if "Error" in event_type:
                err_content = (getattr(event, "content", None)
                               or getattr(event, "error", None)
                               or event_type)
                _error_events.append(str(err_content))
                logger.log(f"[{condition.upper()}] ERROR EVENT ({event_type}): {str(err_content)[:120]}")
                continue

            # skip token-level streaming events
            if event_type in _SKIP:
                continue

            member = (getattr(event, "member_name", None)
                      or getattr(event, "agent_name", None)
                      or "Team")
            tool   = getattr(event, "tool_name", None)
            tool_args = getattr(event, "tool_args", None) or getattr(event, "function_call", None)

            if tool:
                args_str = ""
                if isinstance(tool_args, dict):
                    # show first meaningful arg (e.g. file path or command)
                    first = next(iter(tool_args.values()), "")
                    args_str = f" ({str(first)[:60]})"
                logger.log(f"[{condition.upper()}] {member} → {tool}{args_str}")
            else:
                # log member transitions and task-level events
                if member != _last_member:
                    logger.log(f"[{condition.upper()}] → {member} [{event_type}]")
                    _last_member = member
                elif event_type not in ("RunEvent", "TeamRunEvent"):
                    content = getattr(event, "content", None)
                    if content and len(str(content)) > 20:
                        snippet = str(content)[:100].replace("\n", " ")
                        logger.log(f"[{condition.upper()}] {member}: {snippet}")

        result["agent_response_preview"] = "".join(chunks)[:800]
        if _error_events:
            result["error"] = "; ".join(_error_events[:3])
        result["success"] = True
        logger.log(f"[{condition.upper()}] Task completed successfully.")
    except Exception as exc:
        result["error"] = str(exc)
        logger.log(f"[{condition.upper()}] ERROR: {exc}")
    finally:
        os.chdir(original_cwd)

    result["end_time"] = datetime.now().isoformat()
    result["duration_seconds"] = round(
        (datetime.fromisoformat(result["end_time"]) -
         datetime.fromisoformat(result["start_time"])).total_seconds(), 1
    )
    result["metrics"] = _collect_metrics(output_dir)
    m = result["metrics"]
    # downgrade success if no files were produced — indicates a silent agent failure
    if result["success"] and m.get("python_file_count", 0) == 0:
        result["success"] = False
        if not result["error"]:
            result["error"] = "No Python files produced — agent may have failed silently"
        logger.log(f"[{condition.upper()}] WARNING: 0 files produced — marking success=False")
    logger.log(
        f"[{condition.upper()}] Metrics: files={m.get('python_file_count',0)}"
        f" LOC={m.get('total_lines_of_code',0)}"
        f" annotated={m.get('annotation_coverage_pct',0):.1f}%"
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# RESET / LIST HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def reset_runs(run_id: str | None = None) -> None:
    """Delete run directories — only inside RUNS_ROOT."""
    if not RUNS_ROOT.exists():
        print("  Nothing to reset — runs/ does not exist.")
        return
    if run_id:
        target = RUNS_ROOT / run_id
        if not target.exists():
            print(f"  Not found: {run_id}")
            return
        shutil.rmtree(target)
        print(f"  Deleted: {target}")
    else:
        shutil.rmtree(RUNS_ROOT)
        print(f"  Deleted: {RUNS_ROOT}")


def list_runs() -> None:
    """Print all saved runs with quick stats."""
    if not RUNS_ROOT.exists() or not any(RUNS_ROOT.iterdir()):
        print("  No runs found.")
        return
    print(f"\n  {'RUN ID':<30} {'CONDITIONS':<12} {'STATUS'}")
    print(f"  {'-'*30} {'-'*12} {'-'*30}")
    for run_dir in sorted(RUNS_ROOT.iterdir()):
        cmp = run_dir / "comparison.json"
        if cmp.exists():
            data = json.loads(cmp.read_text())
            conds = list(data.get("conditions", {}).keys())
            status = " | ".join(
                f"{c}={'ok' if data['conditions'][c]['success'] else 'err'}"
                for c in conds
            )
            print(f"  {run_dir.name:<30} {','.join(conds):<12} {status}")
        else:
            subdirs = [d.name for d in run_dir.iterdir() if d.is_dir()]
            print(f"  {run_dir.name:<30} {','.join(subdirs):<12} (in progress)")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def _load_partial_results(run_dir: Path) -> dict:
    """Load already-completed condition results from a partial run.

    Rules:   A condition is considered complete only if its result JSON exists
             AND success=True; partial/errored conditions are re-run.
    """
    partial_file = run_dir / "partial_results.json"
    if partial_file.exists():
        try:
            return json.loads(partial_file.read_text())
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _save_partial_results(run_dir: Path, results: dict) -> None:
    """Persist completed condition results so a resumed run can skip them."""
    (run_dir / "partial_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False)
    )


def resume_experiment(run_id: str) -> dict:
    """Resume an interrupted run — skip already-successful conditions.

    Rules:   Only conditions with success=False or missing are re-run;
             files already generated are preserved.
    """
    run_dir = RUNS_ROOT / run_id
    if not run_dir.exists():
        print(f"  Run not found: {run_id}")
        sys.exit(1)

    partial = _load_partial_results(run_dir)
    done = {c for c, r in partial.items()
            if r.get("success") and r.get("metrics", {}).get("python_file_count", 0) > 0}
    todo = [c for c in ("a", "b") if c not in done]

    print(f"\n{'#'*68}")
    print(f"  RESUME    : {run_id}")
    print(f"  Already done : {', '.join(done) or 'none'}")
    print(f"  To run       : {', '.join(todo) or 'none — already complete!'}")
    print(f"{'#'*68}")

    if not todo:
        print("  Nothing to do.")
        return partial

    logger = RunLogger(run_dir)
    logger.log(f"Resuming run_id={run_id} — skipping {done}, running {set(todo)}")

    results = dict(partial)
    for cond in todo:
        results[cond] = run_condition(cond, run_dir, logger)
        _save_partial_results(run_dir, results)

    final = {"run_id": run_id, "run_dir": str(run_dir), "conditions": results}
    cmp_file = run_dir / "comparison.json"
    cmp_file.write_text(json.dumps(final, indent=2, ensure_ascii=False))
    logger.log("Resume complete — comparison.json saved.")
    logger.close()
    return final


def run_experiment(condition: str = "both") -> dict:
    """Create a fresh timestamped run and execute the requested condition(s).

    Rules:   Never reuses an existing run_id; use resume_experiment() to continue.
    """
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = RUNS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'#'*68}")
    print(f"  RUN ID    : {run_id}")
    print(f"  CONDITION : {condition}")
    print(f"  TASK      : identical for both conditions")
    print(f"  OUTPUT    : {run_dir}")
    print(f"{'#'*68}")

    logger = RunLogger(run_dir)
    logger.log(f"Experiment started — run_id={run_id}  condition={condition}")
    logger.log(f"Run dir: {run_dir}")

    to_run = ["a", "b"] if condition == "both" else [condition]
    results: dict = {"run_id": run_id, "run_dir": str(run_dir), "conditions": {}}

    for cond in to_run:
        results["conditions"][cond] = run_condition(cond, run_dir, logger)
        # persist after each condition so resume can skip it
        _save_partial_results(run_dir, results["conditions"])

    cmp_file = run_dir / "comparison.json"
    cmp_file.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    logger.log(f"Experiment finished — comparison.json saved.")
    logger.close()

    print(f"\n{'='*68}")
    print("  SUMMARY")
    print(f"{'='*68}")
    labels = {"a": "Annotation Protocol", "b": "Standard Practices  "}
    for cond, res in results["conditions"].items():
        m = res["metrics"]
        print(
            f"  [{cond.upper()}] {labels.get(cond, cond)}"
            f" | files={m.get('python_file_count', 0):3d}"
            f" | LOC={m.get('total_lines_of_code', 0):5d}"
            f" | annotated={m.get('annotation_coverage_pct', 0):5.1f}%"
            f" | {res['duration_seconds']}s"
            f" | {'OK' if res['success'] else 'ERROR'}"
        )
    print(f"\n  Saved → {cmp_file}")
    print(f"\n{'='*68}")
    print("  RESET")
    print(f"{'='*68}")
    print(f"  This run  → python run_experiment.py --clean-run {run_id}")
    print(f"  All runs  → python run_experiment.py --reset")
    print(f"  Manual    → rm -rf {run_dir}")
    print(f"{'='*68}\n")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli = argparse.ArgumentParser(
        description="Controlled experiment: same 5-agent team, two annotation approaches.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_experiment.py                       # run both conditions
  python run_experiment.py --condition a         # run condition-A only
  python run_experiment.py --condition b         # run condition-B only
  python run_experiment.py --list-runs           # list all previous runs
  python run_experiment.py --reset               # delete ALL runs (asks confirmation)
  python run_experiment.py --clean-run run_20260329_153000
        """
    )
    cli.add_argument("--condition", choices=["a", "b", "both"], default="both",
                     help="a=annotation-protocol, b=standard-practices, both=run both (default)")
    cli.add_argument("--reset", action="store_true",
                     help="Delete ALL runs in experiments/runs/ (irreversible)")
    cli.add_argument("--clean-run", metavar="RUN_ID",
                     help="Delete a specific run by ID")
    cli.add_argument("--list-runs", action="store_true",
                     help="List all saved runs with quick stats")
    cli.add_argument("--resume-run", metavar="RUN_ID",
                     help="Resume an interrupted run — skips already-successful conditions")
    args = cli.parse_args()

    if args.reset:
        ans = input("Delete ALL runs? Type 'yes' to confirm: ")
        reset_runs() if ans.strip().lower() == "yes" else print("Aborted.")
    elif args.clean_run:
        reset_runs(args.clean_run)
    elif args.list_runs:
        list_runs()
    elif args.resume_run:
        resume_experiment(args.resume_run)
    else:
        run_experiment(args.condition)
