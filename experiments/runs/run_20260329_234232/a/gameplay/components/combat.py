"""combat.py — Combat-related components.

exports: Health, Damage, Attack, Enemy, CombatState
used_by: gameplay/systems/combat_system.py
rules:   Health component required for all combat entities
agent:   GameplayDesigner | 2024-01-15 | Created combat components
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from engine.component import Component


@dataclass
class Health(Component):
    """Health and vitality statistics.
    
    Attributes:
        current: Current health points
        maximum: Maximum health points
        regeneration: Health regeneration per second
        last_damage_time: Time when last damaged (for invulnerability)
        invulnerable: Whether entity can take damage
    """
    current: float = 100.0
    maximum: float = 100.0
    regeneration: float = 1.0
    last_damage_time: float = 0.0
    invulnerable: bool = False
    
    def is_alive(self) -> bool:
        """Check if entity is alive.
        
        Returns:
            bool: True if health > 0
        """
        return self.current > 0
    
    def take_damage(self, amount: float) -> float:
        """Apply damage to health.
        
        Args:
            amount: Damage amount
            
        Returns:
            float: Actual damage applied
        """
        if self.invulnerable:
            return 0.0
            
        actual_damage = min(amount, self.current)
        self.current -= actual_damage
        return actual_damage
    
    def heal(self, amount: float) -> float:
        """Heal entity.
        
        Args:
            amount: Healing amount
            
        Returns:
            float: Actual healing applied
        """
        actual_heal = min(amount, self.maximum - self.current)
        self.current += actual_heal
        return actual_heal


@dataclass
class Damage(Component):
    """Damage dealing capability.
    
    Attributes:
        base_damage: Base damage amount
        damage_type: Type of damage (physical, magical, fire, etc.)
        critical_chance: Chance for critical hit (0-1)
        critical_multiplier: Damage multiplier on critical
        attack_range: Maximum attack distance
        attack_speed: Attacks per second
    """
    base_damage: float = 10.0
    damage_type: str = "physical"
    critical_chance: float = 0.05
    critical_multiplier: float = 2.0
    attack_range: float = 1.5
    attack_speed: float = 1.0


@dataclass
class Attack(Component):
    """Current attack state.
    
    Attributes:
        target_id: Entity ID of attack target
        last_attack_time: Time of last attack
        attack_cooldown: Time between attacks
        is_attacking: Whether currently attacking
        attack_animation: Current attack animation state
    """
    target_id: Optional[int] = None
    last_attack_time: float = 0.0
    attack_cooldown: float = 1.0
    is_attacking: bool = False
    attack_animation: str = ""


@dataclass
class Enemy(Component):
    """Marks entity as an enemy with AI behavior.
    
    Attributes:
        enemy_type: Type of enemy (goblin, skeleton, boss, etc.)
        aggression_range: Distance at which enemy becomes aggressive
        patrol_radius: Radius for patrol behavior
        drop_table: Items dropped on death
        experience_value: XP awarded when killed
    """
    enemy_type: str = "generic"
    aggression_range: float = 5.0
    patrol_radius: float = 3.0
    drop_table: List[Tuple[str, float]] = field(default_factory=list)  # (item_id, drop_chance)
    experience_value: int = 10


@dataclass
class CombatState(Component):
    """Current combat status and state machine.
    
    Attributes:
        state: Current combat state (idle, aggressive, fleeing, dead)
        target_id: Current combat target entity ID
        aggro_list: List of entities that have attacked this entity
        combat_start_time: Time when combat started
        last_state_change: Time of last state change
    """
    state: str = "idle"  # idle, aggressive, attacking, fleeing, dead
    target_id: Optional[int] = None
    aggro_list: List[int] = field(default_factory=list)
    combat_start_time: float = 0.0
    last_state_change: float = 0.0