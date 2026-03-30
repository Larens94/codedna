"""
Combat-related components for the 2D RPG.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from engine.ecs import Component


class DamageType(Enum):
    """Types of damage."""
    PHYSICAL = "physical"
    MAGIC = "magic"
    FIRE = "fire"
    ICE = "ice"
    LIGHTNING = "lightning"
    POISON = "poison"
    HOLY = "holy"
    SHADOW = "shadow"


class CombatState(Enum):
    """Combat states for entities."""
    IDLE = "idle"
    ATTACKING = "attacking"
    DEFENDING = "defending"
    CASTING = "casting"
    STUNNED = "stunned"
    DEAD = "dead"


@dataclass
class HealthComponent(Component):
    """
    Component for entity health and damage tracking.
    """
    current_health: float = 100.0
    max_health: float = 100.0
    health_regeneration: float = 1.0  # Health per second
    last_damage_time: float = 0.0
    damage_history: List[Dict[str, Any]] = field(default_factory=list)
    is_invulnerable: bool = False
    invulnerability_end_time: float = 0.0
    
    def take_damage(self, damage: float, damage_type: DamageType, 
                   source: Optional[str] = None) -> float:
        """
        Apply damage to health.
        
        Args:
            damage: Amount of damage
            damage_type: Type of damage
            source: Source of damage (optional)
            
        Returns:
            Actual damage taken after reductions
        """
        if self.is_invulnerable:
            return 0.0
        
        # Record damage
        damage_event = {
            'damage': damage,
            'damage_type': damage_type,
            'source': source,
            'timestamp': time.time()
        }
        self.damage_history.append(damage_event)
        
        # Apply damage
        self.current_health -= damage
        self.last_damage_time = time.time()
        
        # Clamp health
        if self.current_health < 0:
            self.current_health = 0
        
        return damage
    
    def heal(self, amount: float) -> float:
        """
        Heal the entity.
        
        Args:
            amount: Amount to heal
            
        Returns:
            Actual amount healed
        """
        old_health = self.current_health
        self.current_health += amount
        
        # Clamp to max health
        if self.current_health > self.max_health:
            self.current_health = self.max_health
        
        return self.current_health - old_health
    
    def is_alive(self) -> bool:
        """
        Check if entity is alive.
        
        Returns:
            True if health > 0
        """
        return self.current_health > 0
    
    def get_health_percentage(self) -> float:
        """
        Get health as percentage.
        
        Returns:
            Health percentage (0.0 to 1.0)
        """
        if self.max_health == 0:
            return 0.0
        return self.current_health / self.max_health
    
    def update(self, dt: float):
        """
        Update health regeneration.
        
        Args:
            dt: Delta time in seconds
        """
        if self.is_alive() and self.current_health < self.max_health:
            # Only regenerate if not recently damaged
            if time.time() - self.last_damage_time > 5.0:  # 5 second delay
                self.heal(self.health_regeneration * dt)
        
        # Update invulnerability
        if self.is_invulnerable and time.time() >= self.invulnerability_end_time:
            self.is_invulnerable = False
    
    def set_invulnerable(self, duration: float):
        """
        Make entity invulnerable for a duration.
        
        Args:
            duration: Duration in seconds
        """
        self.is_invulnerable = True
        self.invulnerability_end_time = time.time() + duration


@dataclass
class ManaComponent(Component):
    """
    Component for entity mana (magic energy).
    """
    current_mana: float = 50.0
    max_mana: float = 50.0
    mana_regeneration: float = 2.0  # Mana per second
    last_mana_use_time: float = 0.0
    
    def use_mana(self, amount: float) -> bool:
        """
        Use mana if available.
        
        Args:
            amount: Amount of mana to use
            
        Returns:
            True if mana was used successfully
        """
        if self.current_mana >= amount:
            self.current_mana -= amount
            self.last_mana_use_time = time.time()
            return True
        return False
    
    def restore_mana(self, amount: float) -> float:
        """
        Restore mana.
        
        Args:
            amount: Amount to restore
            
        Returns:
            Actual amount restored
        """
        old_mana = self.current_mana
        self.current_mana += amount
        
        # Clamp to max mana
        if self.current_mana > self.max_mana:
            self.current_mana = self.max_mana
        
        return self.current_mana - old_mana
    
    def get_mana_percentage(self) -> float:
        """
        Get mana as percentage.
        
        Returns:
            Mana percentage (0.0 to 1.0)
        """
        if self.max_mana == 0:
            return 0.0
        return self.current_mana / self.max_mana
    
    def update(self, dt: float):
        """
        Update mana regeneration.
        
        Args:
            dt: Delta time in seconds
        """
        if self.current_mana < self.max_mana:
            self.restore_mana(self.mana_regeneration * dt)


@dataclass
class CombatComponent(Component):
    """
    Component for combat state and abilities.
    """
    combat_state: CombatState = CombatState.IDLE
    attack_range: float = 1.5
    attack_speed: float = 1.0  # Attacks per second
    attack_cooldown: float = 0.0
    target_entity: Optional[Any] = None  # Entity reference
    attack_damage: float = 10.0
    attack_types: List[DamageType] = field(default_factory=lambda: [DamageType.PHYSICAL])
    
    # Special attacks
    special_attacks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    active_special_attack: Optional[str] = None
    
    # Combat flags
    is_in_combat: bool = False
    combat_start_time: float = 0.0
    last_attack_time: float = 0.0
    
    def can_attack(self) -> bool:
        """
        Check if entity can attack.
        
        Returns:
            True if attack cooldown is complete
        """
        return self.attack_cooldown <= 0.0
    
    def attack(self) -> bool:
        """
        Perform an attack.
        
        Returns:
            True if attack was performed
        """
        if not self.can_attack():
            return False
        
        # Set cooldown
        self.attack_cooldown = 1.0 / self.attack_speed
        self.last_attack_time = time.time()
        self.combat_state = CombatState.ATTACKING
        
        # Enter combat if not already
        if not self.is_in_combat:
            self.is_in_combat = True
            self.combat_start_time = time.time()
        
        return True
    
    def update(self, dt: float):
        """
        Update combat state.
        
        Args:
            dt: Delta time in seconds
        """
        # Update attack cooldown
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        
        # Return to idle if not attacking
        if self.combat_state == CombatState.ATTACKING and self.attack_cooldown <= 0:
            self.combat_state = CombatState.IDLE
        
        # Exit combat if no activity for a while
        if self.is_in_combat and time.time() - self.last_attack_time > 10.0:
            self.is_in_combat = False
    
    def add_special_attack(self, attack_id: str, attack_data: Dict[str, Any]):
        """
        Add a special attack.
        
        Args:
            attack_id: Unique attack identifier
            attack_data: Attack properties
        """
        self.special_attacks[attack_id] = attack_data
    
    def use_special_attack(self, attack_id: str) -> bool:
        """
        Use a special attack.
        
        Args:
            attack_id: Attack identifier
            
        Returns:
            True if attack was used
        """
        if attack_id not in self.special_attacks:
            return False
        
        attack_data = self.special_attacks[attack_id]
        
        # Check cooldown
        cooldown = attack_data.get('cooldown', 0)
        last_used = attack_data.get('last_used', 0)
        
        if time.time() - last_used < cooldown:
            return False
        
        # Set as active
        self.active_special_attack = attack_id
        attack_data['last_used'] = time.time()
        
        return True


@dataclass
class DamageComponent(Component):
    """
    Component for dealing damage.
    """
    base_damage: float = 10.0
    damage_types: List[DamageType] = field(default_factory=lambda: [DamageType.PHYSICAL])
    damage_multipliers: Dict[DamageType, float] = field(default_factory=dict)
    critical_chance: float = 0.05
    critical_multiplier: float = 1.5
    armor_penetration: float = 0.0  # Percentage
    magic_penetration: float = 0.0  # Percentage
    
    def calculate_damage(self, target_defense: float, target_resist: float, 
                        damage_type: DamageType) -> Dict[str, Any]:
        """
        Calculate damage against a target.
        
        Args:
            target_defense: Target's physical defense
            target_resist: Target's magic resistance
            damage_type: Type of damage being dealt
            
        Returns:
            Dictionary with damage details
        """
        # Get damage multiplier for this type
        multiplier = self.damage_multipliers.get(damage_type, 1.0)
        base = self.base_damage * multiplier
        
        # Apply penetration
        if damage_type == DamageType.PHYSICAL:
            effective_defense = target_defense * (1.0 - self.armor_penetration)
            damage = max(1.0, base - effective_defense)
        else:
            effective_resist = target_resist * (1.0 - self.magic_penetration)
            damage = max(1.0, base - effective_resist)
        
        # Check for critical hit
        is_critical = random.random() < self.critical_chance
        if is_critical:
            damage *= self.critical_multiplier
        
        return {
            'damage': damage,
            'damage_type': damage_type,
            'is_critical': is_critical,
            'base_damage': base,
            'effective_defense': effective_defense if damage_type == DamageType.PHYSICAL else effective_resist
        }


@dataclass
class DefenseComponent(Component):
    """
    Component for defense and damage reduction.
    """
    armor: float = 5.0
    magic_resistance: float = 5.0
    dodge_chance: float = 0.05
    block_chance: float = 0.1
    block_amount: float = 0.5  # Percentage of damage blocked
    damage_reduction: Dict[DamageType, float] = field(default_factory=dict)
    
    def calculate_damage_reduction(self, damage: float, damage_type: DamageType) -> Dict[str, Any]:
        """
        Calculate damage reduction for incoming damage.
        
        Args:
            damage: Incoming damage amount
            damage_type: Type of damage
            
        Returns:
            Dictionary with reduction details
        """
        result = {
            'original_damage': damage,
            'damage_type': damage_type,
            'dodged': False,
            'blocked': False,
            'final_damage': damage
        }
        
        # Check for dodge
        if random.random() < self.dodge_chance:
            result['dodged'] = True
            result['final_damage'] = 0
            return result
        
        # Check for block
        if random.random() < self.block_chance:
            result['blocked'] = True
            damage *= (1.0 - self.block_amount)
        
        # Apply damage reduction based on type
        reduction = self.damage_reduction.get(damage_type, 0.0)
        damage *= (1.0 - reduction)
        
        # Apply armor/magic resistance
        if damage_type == DamageType.PHYSICAL:
            damage = max(1.0, damage - self.armor)
        else:
            damage = max(1.0, damage - self.magic_resistance)
        
        result['final_damage'] = damage
        return result
    
    def add_damage_reduction(self, damage_type: DamageType, reduction: float):
        """
        Add damage reduction for a specific type.
        
        Args:
            damage_type: Type of damage
            reduction: Reduction percentage (0.0 to 1.0)
        """
        self.damage_reduction[damage_type] = reduction


# Import required modules
import time
import random