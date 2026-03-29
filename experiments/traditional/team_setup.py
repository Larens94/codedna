#!/usr/bin/env python3
"""team_setup.py — Agno Team setup for modular 2D RPG game development.

exports: create_team(tracker: DevelopmentTracker) -> Team, run_development() -> None
used_by: [manual execution] → python3 traditional/team_setup.py
rules:   Standard Python best practices only — no CodeDNA annotations in agent instructions;
         base_dir=Path(".") is intentional for standalone manual execution
agent:   claude-sonnet-4-6 | anthropic | 2026-03-29 | Standalone runner for traditional condition; not used by run_experiment.py
"""

from agno.team import Team
from agno.team.mode import TeamMode
from agno.agent import Agent
from agno.models.deepseek import DeepSeek
from agno.tools.file import FileTools
from agno.tools.shell import ShellTools
from datetime import datetime
import json
from pathlib import Path


class DevelopmentTracker:
    """Tracks agent interactions, tokens, and reasoning."""

    def __init__(self):
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.session_dir = Path("session_logs") / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.interactions = []
        self.token_counts = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost_estimate_usd": 0.0
        }

    def log_interaction(self, agent_name: str, interaction_type: str, content: dict):
        """Log an agent interaction."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "type": interaction_type,
            "content": content,
            "session_id": self.session_id
        }
        self.interactions.append(entry)
        self.save_logs()

    def update_token_count(self, prompt_tokens: int, completion_tokens: int):
        """Update token counts and cost estimate."""
        self.token_counts["prompt_tokens"] += prompt_tokens
        self.token_counts["completion_tokens"] += completion_tokens
        self.token_counts["total_tokens"] = (
            self.token_counts["prompt_tokens"] + self.token_counts["completion_tokens"]
        )
        total_cost = (self.token_counts["total_tokens"] / 1000) * 0.01
        self.token_counts["cost_estimate_usd"] = total_cost

    def save_logs(self):
        """Save all logs to files."""
        interactions_file = self.session_dir / "interactions.json"
        with open(interactions_file, 'w') as f:
            json.dump(self.interactions, f, indent=2)

        tokens_file = self.session_dir / "token_counts.json"
        with open(tokens_file, 'w') as f:
            json.dump(self.token_counts, f, indent=2)

        summary = {
            "session_id": self.session_id,
            "start_time": self.interactions[0]["timestamp"] if self.interactions else datetime.now().isoformat(),
            "total_interactions": len(self.interactions),
            **self.token_counts
        }
        summary_file = self.session_dir / "session_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)


def create_team(tracker: DevelopmentTracker):
    """Create Agno Team with specialized agents."""

    team_leader = Agent(
        name="GameDirector",
        role="Lead and coordinate the game development team",
        instructions="""
        You are the Game Director. You coordinate the entire development of a 2D RPG game.

        RESPONSIBILITIES:
        1. Create project structure: engine/, render/, gameplay/, data/, integration/
        2. Delegate tasks to specialists
        3. Ensure consistent interfaces between modules
        4. Track progress and resolve conflicts
        5. Assemble final game from modules

        PROJECT STRUCTURE:
        - engine/: Game loop, state machine, event system (GameEngineer)
        - render/: Sprite rendering, camera, UI (GraphicsSpecialist)
        - gameplay/: Player, combat, inventory, quests (GameplayDesigner)
        - data/: Save system, asset management (DataArchitect)
        - integration/: Main game assembly
        - reasoning_logs/: Team decision tracking
        - session_logs/: Automated interaction tracking

        GAME REQUIREMENTS:
        - 2D RPG with Pygame
        - Player movement and combat
        - Enemy AI
        - Inventory system
        - Quest system
        - SQLite database for saves
        - 60 FPS target

        Track all decisions in reasoning_logs/team_decisions.md
        """,
        model=DeepSeek(id="deepseek-chat"),
        tools=[FileTools(base_dir=Path(".")), ShellTools()],
    )

    game_engineer = Agent(
        name="GameEngineer",
        role="Implement engine/ module",
        instructions="""
        You are the Game Engineer responsible for engine/ module.

        MODULE: engine/
        TASKS:
        1. Create GameEngine class with fixed timestep loop (60 FPS)
        2. Implement StateMachine for game states
        3. Create EventSystem for game events
        4. Entity management system

        PUBLIC API:
        - engine/main.py must expose: GameEngine(), run_game(), StateMachine()

        TECHNICAL:
        - Use Pygame for window management
        - SQLite integration for game state
        - Modular design for other modules to use

        You will provide entity data to GraphicsSpecialist.
        You will receive game events from GameplayDesigner.

        Document decisions in reasoning_logs/engine_decisions.md
        """,
        model=DeepSeek(id="deepseek-chat"),
        tools=[FileTools(base_dir=Path(".")), ShellTools()],
    )

    graphics_specialist = Agent(
        name="GraphicsSpecialist",
        role="Implement render/ module",
        instructions="""
        You are the Graphics Specialist responsible for render/ module.

        MODULE: render/
        TASKS:
        1. SpriteRenderer for entity rendering
        2. CameraSystem with viewport management
        3. UIRenderer for health bars, inventory, quest log
        4. Particle effects system

        PUBLIC API:
        - render/main.py must expose: SpriteRenderer(), CameraSystem(), draw_ui()

        TECHNICAL:
        - Receive entity data from GameEngineer
        - Convert world to screen coordinates
        - Optimize rendering performance
        - Asset loading system

        You will render everything GameplayDesigner creates.

        Document decisions in reasoning_logs/graphics_decisions.md
        """,
        model=DeepSeek(id="deepseek-chat"),
        tools=[FileTools(base_dir=Path(".")), ShellTools()],
    )

    gameplay_designer = Agent(
        name="GameplayDesigner",
        role="Implement gameplay/ module",
        instructions="""
        You are the Gameplay Designer responsible for gameplay/ module.

        MODULE: gameplay/
        TASKS:
        1. PlayerSystem: movement, stats, progression
        2. CombatSystem: damage, AI, victory conditions
        3. InventorySystem: items, equipment, currency
        4. QuestSystem: objectives, NPCs, rewards

        PUBLIC API:
        - gameplay/main.py must expose: PlayerSystem(), CombatSystem(), InventorySystem()

        TECHNICAL:
        - Send game events to GameEngineer
        - Provide gameplay data to GraphicsSpecialist
        - Save/load data through DataArchitect
        - Balance game mechanics

        Document decisions in reasoning_logs/gameplay_decisions.md
        """,
        model=DeepSeek(id="deepseek-chat"),
        tools=[FileTools(base_dir=Path(".")), ShellTools()],
    )

    data_architect = Agent(
        name="DataArchitect",
        role="Implement data/ module",
        instructions="""
        You are the Data Architect responsible for data/ module.

        MODULE: data/
        TASKS:
        1. SaveSystem: SQLite database for game state
        2. AssetManager: load sprites, sounds, configs
        3. ConfigLoader: game configuration
        4. Schema management and migrations

        PUBLIC API:
        - data/main.py must expose: SaveSystem(), AssetManager(), load_config()

        TECHNICAL:
        - SQLite with proper schemas
        - JSON for configuration files
        - Error handling for missing assets
        - Backup and restore functionality

        All other modules will use your services.

        Document decisions in reasoning_logs/data_decisions.md
        """,
        model=DeepSeek(id="deepseek-chat"),
        tools=[FileTools(base_dir=Path(".")), ShellTools()],
    )

    development_team = Team(
        name="RPG Development Team",
        members=[
            team_leader,
            game_engineer,
            graphics_specialist,
            gameplay_designer,
            data_architect,
        ],
        model=DeepSeek(id="deepseek-chat"),
        mode=TeamMode.coordinate,
    )

    return development_team


def run_development():
    """Run the development team."""
    print("=" * 80)
    print("AGNO TEAM DEVELOPMENT - 2D RPG GAME")
    print("=" * 80)

    tracker = DevelopmentTracker()
    tracker.log_interaction("System", "session_start", {
        "description": "Starting Agno Team development session",
        "timestamp": datetime.now().isoformat()
    })

    print(f"\nSession ID: {tracker.session_id}")
    print("Session logs will be saved to:", tracker.session_dir)

    print("\nCreating development team...")
    team = create_team(tracker)

    task = """
    Develop a complete 2D RPG game using Pygame with modular architecture.

    REQUIREMENTS:
    1. Create directory structure: engine/, render/, gameplay/, data/, integration/, reasoning_logs/
    2. Game features:
       - Player movement (WASD/arrows)
       - Combat system with enemy AI
       - Inventory and item management
       - Quest system with NPCs
       - Save/load functionality with SQLite
    3. Target performance: 60 FPS
    4. Clean modular architecture with clear interfaces

    DEVELOPMENT PROCESS:
    1. Team Leader creates project structure and delegates tasks
    2. Specialists implement modules concurrently
    3. Regular coordination through module interfaces
    4. Integration testing
    5. Final assembly and testing

    TRACKING REQUIREMENTS:
    1. All agent interactions logged in session_logs/
    2. All decisions documented in reasoning_logs/
    3. Token usage tracked

    OUTPUT: Complete, runnable 2D RPG game.
    """

    print("\nStarting development task...")
    tracker.log_interaction("System", "task_assignment", {"task": task})

    try:
        result = team.run(task)
        tracker.log_interaction("System", "task_completion", {
            "result": str(result)[:500],
            "success": True
        })
        print("\nDevelopment completed!")
    except Exception as e:
        tracker.log_interaction("System", "task_error", {
            "error": str(e),
            "success": False
        })
        print(f"\nDevelopment error: {e}")

    tracker.save_logs()

    print("\nSESSION SUMMARY:")
    print(f"   Total interactions: {len(tracker.interactions)}")
    print(f"   Total tokens: {tracker.token_counts['total_tokens']}")
    print(f"   Cost estimate: ${tracker.token_counts['cost_estimate_usd']:.4f}")
    print(f"   Logs saved to: {tracker.session_dir}")

    print("\nTo reset and start fresh:")
    print("   rm -rf engine/ render/ gameplay/ data/ integration/ reasoning_logs/ session_logs/")


if __name__ == "__main__":
    run_development()
