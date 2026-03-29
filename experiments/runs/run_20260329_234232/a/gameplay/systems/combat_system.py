"""combat_system.py — Handles combat logic and enemy AI.

exports: CombatSystem class
used_by: gameplay/main.py → Game._initialize_gameplay
rules:   Processes attacks, damage, death, and enemy behavior
agent:   GameplayDesigner | 2024-01-15 | Created combat system
"""

import random
import math
from typing import Set, Type, List, Optional
from engine.system import System
from engine.component import Component
from gameplay.components.combat import (
    Health, Damage, Attack, Enemy, CombatState
)
from gameplay.components.movement import Position
from gameplay.components.player import Player


class CombatSystem(System):
    """System for handling combat mechanics and enemy AI.
    
    Rules:
    - Processes attacks and applies damage
    - Updates combat states
    - Implements enemy AI behavior
    - Handles death and loot drops
    """
    
    def __init__(self):
        """Initialize combat system."""
        required_components: Set[Type[Component]] = {Health}
        super().__init__(required_components)
        self._current_time = 0.0
        
    def update(self, world, delta_time: float) -> None:
        """Update combat states and process attacks.
        
        Args:
            world: World to operate on
            delta_time: Time since last update
        """
        self._current_time += delta_time
        entities = self.query_entities(world)
        
        # Process all entities with health
        for entity in entities:
            health = entity.get_component(Health)
            combat_state = entity.get_component(CombatState)
            attack = entity.get_component(Attack)
            enemy = entity.get_component(Enemy)
            position = entity.get_component(Position)
            
            # Regenerate health
            if health.regeneration > 0 and health.current < health.maximum:
                health.heal(health.regeneration * delta_time)
            
            # Update invulnerability
            if health.invulnerable and self._current_time - health.last_damage_time > 1.0:
                health.invulnerable = False
            
            # Handle death
            if not health.is_alive():
                self._handle_death(world, entity)
                continue
            
            # Process combat state
            if combat_state:
                self._update_combat_state(world, entity, combat_state, position, enemy)
            
            # Process attacks
            if attack and attack.is_attacking:
                self._process_attack(world, entity, attack, position)
    
    def _update_combat_state(self, world, entity, combat_state: CombatState, 
                           position: Optional[Position], enemy: Optional[Enemy]) -> None:
        """Update entity combat state based on situation.
        
        Args:
            world: World reference
            entity: Entity to update
            combat_state: CombatState component
            position: Position component
            enemy: Enemy component (if entity is enemy)
        """
        if combat_state.state == "dead":
            return
        
        # Find player entity
        player_entity = self._find_player_entity(world)
        if not player_entity or not position:
            return
        
        player_position = player_entity.get_component(Position)
        if not player_position:
            return
        
        # Calculate distance to player
        distance = position.distance_to(player_position)
        
        if enemy:
            # Enemy AI logic
            if combat_state.state == "idle":
                # Check if player is in aggression range
                if distance <= enemy.aggression_range:
                    combat_state.state = "aggressive"
                    combat_state.target_id = player_entity.entity_id
                    combat_state.combat_start_time = self._current_time
                    
            elif combat_state.state == "aggressive":
                # Move toward player or attack
                if distance <= 1.5:  # Attack range
                    combat_state.state = "attacking"
                    # Set up attack
                    attack = entity.get_component(Attack)
                    if not attack:
                        attack = Attack()
                        entity.add_component(attack)
                    attack.target_id = player_entity.entity_id
                    
                # TODO: Add movement toward player
                    
            elif combat_state.state == "attacking":
                # Check if still in range
                if distance > 1.5:
                    combat_state.state = "aggressive"
        
        else:
            # Player or friendly NPC combat state
            if combat_state.target_id:
                target_entity = world.get_entity(combat_state.target_id)
                if target_entity:
                    target_health = target_entity.get_component(Health)
                    if not target_health or not target_health.is_alive():
                        combat_state.target_id = None
                        combat_state.state = "idle"
    
    def _process_attack(self, world, attacker_entity, attack: Attack, 
                       attacker_position: Optional[Position]) -> None:
        """Process an attack from an entity.
        
        Args:
            world: World reference
            attacker_entity: Attacking entity
            attack: Attack component
            attacker_position: Attacker position
        """
        # Check attack cooldown
        if self._current_time - attack.last_attack_time < attack.attack_cooldown:
            return
        
        # Get target entity
        if not attack.target_id:
            attack.is_attacking = False
            return
        
        target_entity = world.get_entity(attack.target_id)
        if not target_entity:
            attack.is_attacking = False
            attack.target_id = None
            return
        
        # Check range
        target_position = target_entity.get_component(Position)
        if attacker_position and target_position:
            distance = attacker_position.distance_to(target_position)
            damage_component = attacker_entity.get_component(Damage)
            if damage_component and distance > damage_component.attack_range:
                # Target out of range
                return
        
        # Perform attack
        self._perform_attack(world, attacker_entity, target_entity)
        attack.last_attack_time = self._current_time
        
        # Check if attack should continue
        target_health = target_entity.get_component(Health)
        if not target_health or not target_health.is_alive():
            attack.is_attacking = False
            attack.target_id = None
    
    def _perform_attack(self, world, attacker_entity, target_entity) -> None:
        """Perform damage calculation and apply to target.
        
        Args:
            world: World reference
            attacker_entity: Attacking entity
            target_entity: Target entity
        """
        damage_component = attacker_entity.get_component(Damage)
        target_health = target_entity.get_component(Health)
        
        if not damage_component or not target_health:
            return
        
        # Calculate damage
        base_damage = damage_component.base_damage
        
        # Check for critical hit
        is_critical = random.random() < damage_component.critical_chance
        if is_critical:
            base_damage *= damage_component.critical_multiplier
        
        # Apply damage
        actual_damage = target_health.take_damage(base_damage)
        target_health.last_damage_time = self._current_time
        target_health.invulnerable = True  # Brief invulnerability
        
        # TODO: Create visual/audio effects for attack
        
        # Update combat state for target
        target_combat_state = target_entity.get_component(CombatState)
        if target_combat_state:
            if attacker_entity.entity_id not in target_combat_state.aggro_list:
                target_combat_state.aggro_list.append(attacker_entity.entity_id)
            
            # If target is enemy and not already in combat
            enemy_component = target_entity.get_component(Enemy)
            if enemy_component and target_combat_state.state == "idle":
                target_combat_state.state = "aggressive"
                target_combat_state.target_id = attacker_entity.entity_id
    
    def _handle_death(self, world, entity) -> None:
        """Handle entity death.
        
        Args:
            world: World reference
            entity: Dead entity
        """
        # Update combat state
        combat_state = entity.get_component(CombatState)
        if combat_state:
            combat_state.state = "dead"
        
        # Handle enemy death rewards
        enemy = entity.get_component(Enemy)
        if enemy:
            # Award experience to player
            player_entity = self._find_player_entity(world)
            if player_entity:
                experience = player_entity.get_component(Experience)
                if experience:
                    experience.add_xp(enemy.experience_value)
            
            # TODO: Drop loot from drop_table
        
        # TODO: Schedule entity removal or play death animation
    
    def _find_player_entity(self, world) -> Optional['Entity']:
        """Find the player entity.
        
        Args:
            world: World to search
            
        Returns:
            Optional[Entity]: Player entity if found
        """
        # Query for entities with Player component
        player_entities = world.query_entities({Player})
        return player_entities[0] if player_entities else None
    
    def attack_target(self, world, attacker_entity_id: int, target_entity_id: int) -> bool:
        """Initiate an attack from one entity to another.
        
        Args:
            world: World reference
            attacker_entity_id: ID of attacking entity
            target_entity_id: ID of target entity
            
        Returns:
            bool: True if attack was initiated
        """
        attacker_entity = world.get_entity(attacker_entity_id)
        target_entity = world.get_entity(target_entity_id)
        
        if not attacker_entity or not target_entity:
            return False
        
        # Get or create Attack component
        attack = attacker_entity.get_component(Attack)
        if not attack:
            attack = Attack()
            attacker_entity.add_component(attack)
        
        # Set up attack
        attack.target_id = target_entity_id
        attack.is_attacking = True
        
        # Update combat state
        combat_state = attacker_entity.get_component(CombatState)
        if not combat_state:
            combat_state = CombatState()
            attacker_entity.add_component(combat_state)
        
        combat_state.state = "attacking"
        combat_state.target_id = target_entity_id
        
        return True