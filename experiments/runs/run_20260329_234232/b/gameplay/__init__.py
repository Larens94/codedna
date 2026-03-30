"""
Gameplay module - Game logic and mechanics.
Responsible for game-specific logic, entity behaviors, physics, and AI.
"""

from .game_state import GameState
# JUDGE FIX 3: files never written by GameplayDesigner (director pre-occupied the namespace)
# from .entity_system import EntitySystem
# from .physics_engine import PhysicsEngine, Collision
# from .ai_system import AISystem, BehaviorTree
# from .player_controller import PlayerController

__all__ = [
    'GameState',
]