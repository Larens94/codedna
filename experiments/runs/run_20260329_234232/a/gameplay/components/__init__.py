"""__init__.py — Gameplay component exports.

exports: All gameplay components
used_by: gameplay/systems/*.py, engine/world.py
rules:   Components must be dataclasses, no logic
agent:   GameplayDesigner | 2024-01-15 | Created all gameplay components
"""

from .player import *
from .combat import *
from .movement import *
from .inventory import *
from .quest import *
from .npc import *

__all__ = [
    # Player components
    'Player',
    'PlayerStats',
    'Experience',
    
    # Combat components
    'Health',
    'Damage',
    'Attack',
    'Enemy',
    'CombatState',
    
    # Movement components
    'Position',
    'Velocity',
    'Acceleration',
    'InputState',
    
    # Inventory components
    'Inventory',
    'Item',
    'Equipment',
    'Currency',
    
    # Quest components
    'Quest',
    'Objective',
    'QuestProgress',
    
    # NPC components
    'NPC',
    'Dialogue',
    'Behavior',
]