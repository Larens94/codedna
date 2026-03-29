"""player.py — Player-specific components.

exports: Player, PlayerStats, Experience
used_by: gameplay/systems/player_system.py, gameplay/systems/combat_system.py
rules:   Player component marks entity as player-controlled
agent:   GameplayDesigner | 2024-01-15 | Created player components
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from engine.component import Component


@dataclass
class Player(Component):
    """Marks an entity as the player character.
    
    Attributes:
        entity_id: Unique identifier for the player entity
        spawn_point: Optional spawn location coordinates
    """
    entity_id: int = field(default_factory=lambda: id(object()))
    spawn_point: Optional[tuple] = None


@dataclass
class PlayerStats(Component):
    """Player character statistics and progression.
    
    Attributes:
        level: Current player level
        strength: Affects physical damage
        dexterity: Affects accuracy and evasion
        intelligence: Affects magic damage and mana
        constitution: Affects health and stamina
        wisdom: Affects mana regeneration and perception
        charisma: Affects NPC interactions and prices
        skill_points: Available points to allocate
        stat_points: Available points to allocate
    """
    level: int = 1
    strength: int = 10
    dexterity: int = 10
    intelligence: int = 10
    constitution: int = 10
    wisdom: int = 10
    charisma: int = 10
    skill_points: int = 0
    stat_points: int = 0


@dataclass
class Experience(Component):
    """Experience points and level progression.
    
    Attributes:
        current_xp: Current experience points
        next_level_xp: XP required for next level
        total_xp: Total XP earned
    """
    current_xp: int = 0
    next_level_xp: int = 100
    total_xp: int = 0
    
    def level_up(self) -> bool:
        """Check if enough XP for level up.
        
        Returns:
            bool: True if can level up
        """
        return self.current_xp >= self.next_level_xp
    
    def add_xp(self, amount: int) -> None:
        """Add experience points.
        
        Args:
            amount: XP to add
        """
        self.current_xp += amount
        self.total_xp += amount