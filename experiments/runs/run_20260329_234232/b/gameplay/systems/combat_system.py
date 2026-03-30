"""
Combat System for the 2D RPG.
Handles damage calculation, enemy AI, and victory conditions.
"""

from typing import Dict, List, Optional, Any, Tuple
from engine.ecs import System, World, Entity
import random
import time

from ..components.combat import (
    HealthComponent, ManaComponent, CombatComponent,
    DamageComponent, DefenseComponent, DamageType, CombatState
)
from ..components.player import StatsComponent
from ..components.entity import CharacterComponent, Faction


class CombatSystem(System):
    """
    System for managing combat between entities.
    Handles damage calculation, combat states, and victory conditions.
    """
    
    def __init__(self, world: World):
        """
        Initialize the combat system.
        
        Args:
            world: The ECS world
        """
        super().__init__(world)
        
        # Combat tracking
        self.combat_groups: Dict[str, List[Entity]] = {}
        self.damage_history: List[Dict[str, Any]] = []
        
        # Combat settings
        self.global_damage_multiplier: float = 1.0
        self.critical_hit_multiplier: float = 1.5
        self.minimum_damage: float = 1.0
        
        # Performance optimization
        self.max_damage_history: int = 1000
    
    def fixed_update(self, dt: float):
        """
        Fixed update for combat logic.
        
        Args:
            dt: Fixed delta time in seconds
        """
        # Update all combat components
        for entity in self.world.query(CombatComponent):
            combat = self.world.get_component(entity, CombatComponent)
            if combat:
                combat.update(dt)
        
        # Update all health components
        for entity in self.world.query(HealthComponent):
            health = self.world.get_component(entity, HealthComponent)
            if health:
                health.update(dt)
        
        # Update all mana components
        for entity in self.world.query(ManaComponent):
            mana = self.world.get_component(entity, ManaComponent)
            if mana:
                mana.update(dt)
        
        # Check for dead entities
        self._check_for_dead_entities()
        
        # Clean up old damage history
        self._cleanup_damage_history()
    
    def attack(self, attacker: Entity, target: Entity) -> Optional[Dict[str, Any]]:
        """
        Perform an attack from attacker to target.
        
        Args:
            attacker: Attacking entity
            target: Target entity
            
        Returns:
            Damage result dictionary, or None if attack failed
        """
        # Check if entities can attack/be attacked
        if not self._can_attack(attacker, target):
            return None
        
        # Get combat components
        attacker_combat = self.world.get_component(attacker, CombatComponent)
        target_combat = self.world.get_component(target, CombatComponent)
        
        if not attacker_combat or not attacker_combat.can_attack():
            return None
        
        # Perform attack
        attacker_combat.attack()
        
        # Calculate damage
        damage_result = self._calculate_damage(attacker, target)
        
        if damage_result:
            # Apply damage
            self._apply_damage(target, damage_result, attacker)
            
            # Update combat states
            if target_combat:
                target_combat.target_entity = attacker
                target_combat.is_in_combat = True
                target_combat.combat_start_time = time.time()
            
            # Record damage
            self.damage_history.append(damage_result)
            
            # Check for kill
            if damage_result.get('killed', False):
                self._handle_death(target, attacker)
        
        return damage_result
    
    def _can_attack(self, attacker: Entity, target: Entity) -> bool:
        """
        Check if attacker can attack target.
        
        Args:
            attacker: Attacking entity
            target: Target entity
            
        Returns:
            True if attack is valid
        """
        # Check if entities exist
        if not attacker or not target:
            return False
        
        # Check if target is alive
        target_health = self.world.get_component(target, HealthComponent)
        if not target_health or not target_health.is_alive():
            return False
        
        # Check if attacker is alive
        attacker_health = self.world.get_component(attacker, HealthComponent)
        if not attacker_health or not attacker_health.is_alive():
            return False
        
        # Check factions (optional - can be expanded)
        attacker_char = self.world.get_component(attacker, CharacterComponent)
        target_char = self.world.get_component(target, CharacterComponent)
        
        if attacker_char and target_char:
            # Example: Don't allow friendly fire
            if attacker_char.faction == target_char.faction == Faction.FRIENDLY:
                return False
        
        return True
    
    def _calculate_damage(self, attacker: Entity, target: Entity) -> Dict[str, Any]:
        """
        Calculate damage from attacker to target.
        
        Args:
            attacker: Attacking entity
            target: Target entity
            
        Returns:
            Damage calculation result
        """
        # Get damage component from attacker
        attacker_damage = self.world.get_component(attacker, DamageComponent)
        if not attacker_damage:
            # Use default damage if no damage component
            attacker_damage = DamageComponent()
        
        # Get defense component from target
        target_defense = self.world.get_component(target, DefenseComponent)
        if not target_defense:
            target_defense = DefenseComponent()
        
        # Get stats for additional calculations
        attacker_stats = self.world.get_component(attacker, StatsComponent)
        target_stats = self.world.get_component(target, StatsComponent)
        
        # Determine damage type (use first type if multiple)
        damage_type = attacker_damage.damage_types[0] if attacker_damage.damage_types else DamageType.PHYSICAL
        
        # Get target defense/resist values
        target_defense_value = target_defense.armor if damage_type == DamageType.PHYSICAL else target_defense.magic_resistance
        
        # Calculate base damage
        base_damage = attacker_damage.base_damage
        
        # Apply attacker stats
        if attacker_stats:
            if damage_type == DamageType.PHYSICAL:
                base_damage += attacker_stats.attack_power
            else:
                base_damage += attacker_stats.spell_power
        
        # Apply damage multipliers
        multiplier = attacker_damage.damage_multipliers.get(damage_type, 1.0)
        base_damage *= multiplier
        
        # Apply global multiplier
        base_damage *= self.global_damage_multiplier
        
        # Calculate final damage with defense/resistance
        if damage_type == DamageType.PHYSICAL:
            penetration = attacker_damage.armor_penetration
            effective_defense = target_defense_value * (1.0 - penetration)
            damage = max(self.minimum_damage, base_damage - effective_defense)
        else:
            penetration = attacker_damage.magic_penetration
            effective_resist = target_defense_value * (1.0 - penetration)
            damage = max(self.minimum_damage, base_damage - effective_resist)
        
        # Check for critical hit
        is_critical = random.random() < attacker_damage.critical_chance
        if is_critical:
            damage *= attacker_damage.critical_multiplier
        
        # Apply target defense calculations (dodge, block, etc.)
        defense_result = target_defense.calculate_damage_reduction(damage, damage_type)
        
        # Build result dictionary
        result = {
            'attacker': attacker,
            'target': target,
            'damage_type': damage_type,
            'base_damage': base_damage,
            'calculated_damage': damage,
            'final_damage': defense_result['final_damage'],
            'is_critical': is_critical,
            'dodged': defense_result.get('dodged', False),
            'blocked': defense_result.get('blocked', False),
            'effective_defense': defense_result.get('effective_defense', 0),
            'timestamp': time.time()
        }
        
        return result
    
    def _apply_damage(self, target: Entity, damage_result: Dict[str, Any], source: Entity):
        """
        Apply damage to target entity.
        
        Args:
            target: Target entity
            damage_result: Damage calculation result
            source: Source entity (attacker)
        """
        if damage_result.get('dodged', False):
            # No damage if dodged
            return
        
        target_health = self.world.get_component(target, HealthComponent)
        if not target_health:
            return
        
        damage = damage_result['final_damage']
        damage_type = damage_result['damage_type']
        
        # Apply damage
        actual_damage = target_health.take_damage(
            damage, 
            damage_type,
            source=str(source)
        )
        
        # Update damage result with actual damage
        damage_result['actual_damage'] = actual_damage
        
        # Check if target was killed
        if not target_health.is_alive():
            damage_result['killed'] = True
            damage_result['killer'] = source
    
    def _handle_death(self, dead_entity: Entity, killer: Entity):
        """
        Handle entity death.
        
        Args:
            dead_entity: Entity that died
            killer: Entity that killed it
        """
        # Update combat component
        combat = self.world.get_component(dead_entity, CombatComponent)
        if combat:
            combat.combat_state = CombatState.DEAD
            combat.is_in_combat = False
        
        # Grant experience to killer if it's a player
        killer_player = self.world.get_component(killer, CharacterComponent)
        if killer_player and killer_player.entity_type.name == "PLAYER":
            self._grant_experience_for_kill(killer, dead_entity)
        
        # Drop loot
        self._drop_loot(dead_entity, killer)
        
        # Remove from combat groups
        self._remove_from_combat_groups(dead_entity)
        
        print(f"Entity {dead_entity} was killed by {killer}")
    
    def _grant_experience_for_kill(self, killer: Entity, victim: Entity):
        """
        Grant experience to killer for killing victim.
        
        Args:
            killer: Killer entity (should be player)
            victim: Victim entity
        """
        from ..components.player import LevelComponent, ExperienceComponent
        
        # Get killer's level component
        killer_level = self.world.get_component(killer, LevelComponent)
        if not killer_level:
            return
        
        # Get victim's character component for level
        victim_char = self.world.get_component(victim, CharacterComponent)
        if not victim_char:
            return
        
        # Calculate experience based on victim level
        base_exp = 10
        level_diff = victim_char.level - killer_level.level
        
        # Scale experience based on level difference
        if level_diff > 0:
            # Higher level enemy - bonus exp
            exp_multiplier = 1.0 + (level_diff * 0.1)
        elif level_diff < 0:
            # Lower level enemy - reduced exp
            exp_multiplier = max(0.1, 1.0 + (level_diff * 0.05))
        else:
            # Same level
            exp_multiplier = 1.0
        
        experience = int(base_exp * victim_char.level * exp_multiplier)
        
        # Add experience
        leveled_up = killer_level.add_experience(experience)
        
        # Record experience gain
        exp_comp = self.world.get_component(killer, ExperienceComponent)
        if exp_comp:
            exp_comp.add_experience_source('combat', experience)
        
        if leveled_up:
            print(f"Player leveled up to level {killer_level.level}!")
    
    def _drop_loot(self, dead_entity: Entity, killer: Entity):
        """
        Drop loot from dead entity.
        
        Args:
            dead_entity: Entity that died
            killer: Entity that killed it
        """
        from ..components.inventory import LootComponent
        
        loot = self.world.get_component(dead_entity, LootComponent)
        if loot:
            loot_data = loot.generate_loot()
            
            # Create loot entities in the world
            # This would be implemented based on your entity creation system
            
            print(f"Loot dropped: {loot_data}")
    
    def _remove_from_combat_groups(self, entity: Entity):
        """Remove entity from all combat groups."""
        for group_id, entities in list(self.combat_groups.items()):
            if entity in entities:
                entities.remove(entity)
                if not entities:
                    del self.combat_groups[group_id]
    
    def _check_for_dead_entities(self):
        """Check for and handle dead entities."""
        for entity in self.world.query(HealthComponent):
            health = self.world.get_component(entity, HealthComponent)
            if health and not health.is_alive():
                # Entity is dead but hasn't been handled yet
                combat = self.world.get_component(entity, CombatComponent)
                if combat and combat.combat_state != CombatState.DEAD:
                    combat.combat_state = CombatState.DEAD
                    print(f"Entity {entity} has died")
    
    def _cleanup_damage_history(self):
        """Clean up old damage history entries."""
        current_time = time.time()
        max_age = 60.0  # Keep last 60 seconds
        
        self.damage_history = [
            entry for entry in self.damage_history
            if current_time - entry.get('timestamp', 0) <= max_age
        ]
        
        # Limit total entries
        if len(self.damage_history) > self.max_damage_history:
            self.damage_history = self.damage_history[-self.max_damage_history:]
    
    def heal(self, target: Entity, amount: float, source: Optional[Entity] = None) -> float:
        """
        Heal a target entity.
        
        Args:
            target: Target entity
            amount: Amount to heal
            source: Source of healing (optional)
            
        Returns:
            Actual amount healed
        """
        health = self.world.get_component(target, HealthComponent)
        if not health:
            return 0.0
        
        healed = health.heal(amount)
        
        # Record healing
        if healed > 0:
            self.damage_history.append({
                'type': 'heal',
                'target': target,
                'source': source,
                'amount': healed,
                'timestamp': time.time()
            })
        
        return healed
    
    def get_combat_status(self, entity: Entity) -> Dict[str, Any]:
        """
        Get combat status for an entity.
        
        Args:
            entity: Entity to check
            
        Returns:
            Dictionary with combat status
        """
        status = {
            'in_combat': False,
            'health_percentage': 0.0,
            'combat_state': 'idle',
            'target': None
        }
        
        combat = self.world.get_component(entity, CombatComponent)
        if combat:
            status['in_combat'] = combat.is_in_combat
            status['combat_state'] = combat.combat_state.value
            status['target'] = combat.target_entity
        
        health = self.world.get_component(entity, HealthComponent)
        if health:
            status['health_percentage'] = health.get_health_percentage()
            status['is_alive'] = health.is_alive()
        
        return status
    
    def get_recent_damage(self, entity: Optional[Entity] = None, 
                         limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent damage events.
        
        Args:
            entity: Filter by entity (optional)
            limit: Maximum number of events to return
            
        Returns:
            List of recent damage events
        """
        if entity:
            filtered = [
                entry for entry in self.damage_history
                if entry.get('attacker') == entity or entry.get('target') == entity
            ]
        else:
            filtered = self.damage_history
        
        # Sort by timestamp (newest first)
        filtered.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        return filtered[:limit]
    
    def create_combat_group(self, group_id: str, entities: List[Entity]):
        """
        Create a combat group.
        
        Args:
            group_id: Group identifier
            entities: Entities in the group
        """
        self.combat_groups[group_id] = entities
    
    def add_to_combat_group(self, group_id: str, entity: Entity):
        """
        Add entity to combat group.
        
        Args:
            group_id: Group identifier
            entity: Entity to add
        """
        if group_id not in self.combat_groups:
            self.combat_groups[group_id] = []
        
        if entity not in self.combat_groups[group_id]:
            self.combat_groups[group_id].append(entity)
    
    def remove_from_combat_group(self, group_id: str, entity: Entity):
        """
        Remove entity from combat group.
        
        Args:
            group_id: Group identifier
            entity: Entity to remove
        """
        if group_id in self.combat_groups and entity in self.combat_groups[group_id]:
            self.combat_groups[group_id].remove(entity)
            
            # Clean up empty groups
            if not self.combat_groups[group_id]:
                del self.combat_groups[group_id]
    
    def get_combat_group(self, group_id: str) -> List[Entity]:
        """
        Get entities in a combat group.
        
        Args:
            group_id: Group identifier
            
        Returns:
            List of entities in the group
        """
        return self.combat_groups.get(group_id, [])