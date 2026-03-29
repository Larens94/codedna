"""__init__.py - Engine module exports.

exports: World, Entity, Component, System, GameEngine, StateMachine, run_game
used_by: gameplay/, render/, main.py
rules:   All engine classes must be immutable or thread-safe
agent:   GameEngineer | 2024-1-15 | Added GameEngine and example components/systems
"""

from .world import World
from .entity import Entity
from .component import Component
from .system import System
from .main import GameEngine, StateMachine, run_game

# Example components and systems for demonstration
from .components import Position, Velocity, PlayerInput, Sprite, Transform
from .systems import MovementSystem, PlayerMovementSystem, InputSystem, RenderingSystem, ExampleSystem

__all__ = [
    'World', 'Entity', 'Component', 'System',
    'GameEngine', 'StateMachine', 'run_game',
    'Position', 'Velocity', 'PlayerInput', 'Sprite', 'Transform',
    'MovementSystem', 'PlayerMovementSystem', 'InputSystem', 
    'RenderingSystem', 'ExampleSystem'
]