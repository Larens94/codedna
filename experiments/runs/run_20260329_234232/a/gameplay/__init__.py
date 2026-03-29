"""__init__.py — Gameplay module exports.

exports: Game class, common components and systems
used_by: main.py
rules:   Game-specific logic only, no engine or render internals
agent:   Game Director | 2024-01-15 | Defined gameplay public interface
"""

from .game import Game

# Common components will be exported here
# from .components.position import Position
# from .components.velocity import Velocity
# from .components.sprite import Sprite

# Common systems will be exported here  
# from .systems.movement import MovementSystem
# from .systems.rendering import RenderingSystem

__all__ = ['Game']