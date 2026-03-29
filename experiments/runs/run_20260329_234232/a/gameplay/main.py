"""main.py — Main gameplay module exports.

exports: PlayerSystem, CombatSystem, InventorySystem, QuestSystem, MovementSystem
used_by: main.py → GameApplication, gameplay/game.py → Game._initialize_gameplay
rules:   Exports gameplay systems for integration with main game
agent:   GameplayDesigner | 2024-01-15 | Created gameplay module exports
"""

from .systems.player_system import PlayerSystem
from .systems.combat_system import CombatSystem
from .systems.inventory_system import InventorySystem
from .systems.quest_system import QuestSystem
from .systems.movement_system import MovementSystem

__all__ = [
    'PlayerSystem',
    'CombatSystem', 
    'InventorySystem',
    'QuestSystem',
    'MovementSystem',
]