"""__init__.py — Engine module exports.

exports: World, Entity, Component, System
used_by: gameplay/, render/, main.py
rules:   All engine classes must be immutable or thread-safe
agent:   Game Director | 2024-01-15 | Defined engine public interface
"""

from .world import World
from .entity import Entity
from .component import Component
from .system import System

__all__ = ['World', 'Entity', 'Component', 'System']