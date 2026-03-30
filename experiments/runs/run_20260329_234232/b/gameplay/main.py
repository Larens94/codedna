"""
Gameplay Module - Main Entry Point
Provides all gameplay systems for the 2D RPG.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import json
import time

# Import engine systems
from engine.ecs import World, Entity, Component, System
from engine.input import InputManager, InputAction

# Import gameplay components
from .components.player import (
    PlayerComponent, StatsComponent, LevelComponent,
    ExperienceComponent, SkillComponent
)
from .components.combat import (
    HealthComponent, ManaComponent, CombatComponent,
    DamageComponent, DefenseComponent
)
from .components.inventory import (
    InventoryComponent, ItemComponent, EquipmentComponent,
    CurrencyComponent, LootComponent
)
from .components.quest import (
    QuestComponent, NPCComponent, DialogueComponent,
    ObjectiveComponent, QuestState
)
from .components.entity import (
    CharacterComponent, InteractiveComponent,
    SpawnerComponent, ZoneComponent, TriggerComponent
)
from .components.state import (
    GameStateComponent, SaveComponent, TimeComponent
)

# Import gameplay systems
from .systems.player_system import PlayerSystem
from .systems.combat_system import CombatSystem
from .systems.inventory_system import InventorySystem
from .systems.quest_system import QuestSystem
from .systems.ai_system import AISystem
from .systems.save_system import SaveSystem
from .systems.movement_system import MovementSystem

# Import entity factories
from .entities.player import create_player_entity
from .entities.enemy import create_enemy_entity
from .entities.npc import create_npc_entity
from .entities.interactive import create_interactive_entity

# Import managers
from .managers.level_manager import LevelManager
from .managers.game_state_manager import GameStateManager


class GameplayModule:
    """
    Main gameplay module that orchestrates all gameplay systems.
    Integrates with the engine's ECS and provides RPG functionality.
    """
    
    def __init__(self, world: World, input_manager: InputManager):
        """
        Initialize the gameplay module.
        
        Args:
            world: The ECS world
            input_manager: Input manager for player controls
        """
        self.world = world
        self.input_manager = input_manager
        
        # Systems
        self.systems: Dict[str, System] = {}
        
        # Managers
        self.level_manager = LevelManager(world)
        self.game_state_manager = GameStateManager(world)
        
        # Player entity reference
        self.player_entity: Optional[Entity] = None
        
        # Initialize all systems
        self._initialize_systems()
        
        # Game state
        self.is_paused = False
        self.game_time = 0.0
        
        print("Gameplay module initialized")
    
    def _initialize_systems(self):
        """Initialize all gameplay systems."""
        # Player systems
        self.systems['player'] = PlayerSystem(self.world, self.input_manager)
        self.systems['movement'] = MovementSystem(self.world, self.input_manager)
        
        # Combat systems
        self.systems['combat'] = CombatSystem(self.world)
        self.systems['ai'] = AISystem(self.world)
        
        # Inventory system
        self.systems['inventory'] = InventorySystem(self.world)
        
        # Quest system
        self.systems['quest'] = QuestSystem(self.world)
        
        # Save system
        self.systems['save'] = SaveSystem(self.world)
        
        # Add all systems to the world
        for system in self.systems.values():
            self.world.add_system(system)
    
    def create_player(self, position: Tuple[float, float] = (0, 0)) -> Entity:
        """
        Create a player entity.
        
        Args:
            position: Starting position (x, y)
            
        Returns:
            The created player entity
        """
        self.player_entity = create_player_entity(
            self.world,
            position=position,
            input_manager=self.input_manager
        )
        
        # Register player with systems
        for system in self.systems.values():
            if hasattr(system, 'set_player_entity'):
                system.set_player_entity(self.player_entity)
        
        print(f"Player created at position {position}")
        return self.player_entity
    
    def create_enemy(self, enemy_type: str, position: Tuple[float, float]) -> Entity:
        """
        Create an enemy entity.
        
        Args:
            enemy_type: Type of enemy (goblin, skeleton, etc.)
            position: Position (x, y)
            
        Returns:
            The created enemy entity
        """
        enemy = create_enemy_entity(
            self.world,
            enemy_type=enemy_type,
            position=position
        )
        
        print(f"Enemy '{enemy_type}' created at position {position}")
        return enemy
    
    def create_npc(self, npc_type: str, position: Tuple[float, float], 
                  dialogue_id: str = "") -> Entity:
        """
        Create an NPC entity.
        
        Args:
            npc_type: Type of NPC (merchant, quest_giver, etc.)
            position: Position (x, y)
            dialogue_id: ID of dialogue tree to use
            
        Returns:
            The created NPC entity
        """
        npc = create_npc_entity(
            self.world,
            npc_type=npc_type,
            position=position,
            dialogue_id=dialogue_id
        )
        
        print(f"NPC '{npc_type}' created at position {position}")
        return npc
    
    def create_interactive(self, interactive_type: str, 
                          position: Tuple[float, float]) -> Entity:
        """
        Create an interactive object.
        
        Args:
            interactive_type: Type of object (chest, door, lever, etc.)
            position: Position (x, y)
            
        Returns:
            The created interactive entity
        """
        interactive = create_interactive_entity(
            self.world,
            interactive_type=interactive_type,
            position=position
        )
        
        print(f"Interactive '{interactive_type}' created at position {position}")
        return interactive
    
    def load_level(self, level_id: str):
        """
        Load a game level.
        
        Args:
            level_id: ID of the level to load
        """
        self.level_manager.load_level(level_id)
        print(f"Level '{level_id}' loaded")
    
    def update(self, dt: float):
        """
        Update all gameplay systems.
        
        Args:
            dt: Delta time in seconds
        """
        if self.is_paused:
            return
        
        # Update game time
        self.game_time += dt
        
        # Update game state manager
        self.game_state_manager.update(dt)
        
        # Update all systems
        self.world.update(dt)
    
    def fixed_update(self, dt: float):
        """
        Fixed update for physics and game logic.
        
        Args:
            dt: Fixed delta time in seconds
        """
        if self.is_paused:
            return
        
        # Fixed update all systems
        self.world.fixed_update(dt)
    
    def pause(self):
        """Pause the game."""
        self.is_paused = True
        print("Game paused")
    
    def resume(self):
        """Resume the game."""
        self.is_paused = False
        print("Game resumed")
    
    def save_game(self, slot: int = 0) -> bool:
        """
        Save the current game state.
        
        Args:
            slot: Save slot number
            
        Returns:
            True if save successful
        """
        save_system = self.systems.get('save')
        if save_system:
            return save_system.save_game(slot)
        return False
    
    def load_game(self, slot: int = 0) -> bool:
        """
        Load a saved game.
        
        Args:
            slot: Save slot number
            
        Returns:
            True if load successful
        """
        save_system = self.systems.get('save')
        if save_system:
            return save_system.load_game(slot)
        return False
    
    def get_player_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get player stats.
        
        Returns:
            Dictionary of player stats, or None if no player
        """
        if not self.player_entity:
            return None
        
        stats = {}
        
        # Get player component
        player_comp = self.world.get_component(self.player_entity, PlayerComponent)
        if player_comp:
            stats['player'] = player_comp.__dict__
        
        # Get stats component
        stats_comp = self.world.get_component(self.player_entity, StatsComponent)
        if stats_comp:
            stats['attributes'] = stats_comp.__dict__
        
        # Get health component
        health_comp = self.world.get_component(self.player_entity, HealthComponent)
        if health_comp:
            stats['health'] = health_comp.__dict__
        
        # Get level component
        level_comp = self.world.get_component(self.player_entity, LevelComponent)
        if level_comp:
            stats['level'] = level_comp.__dict__
        
        return stats
    
    def get_player_inventory(self) -> Optional[Dict[str, Any]]:
        """
        Get player inventory.
        
        Returns:
            Dictionary of inventory data, or None if no player
        """
        if not self.player_entity:
            return None
        
        inventory_comp = self.world.get_component(self.player_entity, InventoryComponent)
        if not inventory_comp:
            return None
        
        return inventory_comp.get_inventory_data()
    
    def get_active_quests(self) -> List[Dict[str, Any]]:
        """
        Get active quests.
        
        Returns:
            List of active quest data
        """
        quest_system = self.systems.get('quest')
        if quest_system:
            return quest_system.get_active_quests()
        return []
    
    def interact_with(self, entity: Entity) -> Optional[str]:
        """
        Interact with an entity.
        
        Args:
            entity: Entity to interact with
            
        Returns:
            Interaction result message, or None
        """
        # Check if entity has interactive component
        interactive_comp = self.world.get_component(entity, InteractiveComponent)
        if interactive_comp:
            return interactive_comp.interact()
        
        # Check if entity has NPC component
        npc_comp = self.world.get_component(entity, NPCComponent)
        if npc_comp:
            return npc_comp.start_dialogue()
        
        return None
    
    def attack(self, target: Entity) -> Optional[Dict[str, Any]]:
        """
        Attack a target entity.
        
        Args:
            target: Target entity to attack
            
        Returns:
            Damage result, or None if attack failed
        """
        if not self.player_entity:
            return None
        
        combat_system = self.systems.get('combat')
        if combat_system:
            return combat_system.attack(self.player_entity, target)
        
        return None
    
    def use_item(self, item_slot: int) -> Optional[str]:
        """
        Use an item from inventory.
        
        Args:
            item_slot: Slot number of item to use
            
        Returns:
            Result message, or None
        """
        if not self.player_entity:
            return None
        
        inventory_system = self.systems.get('inventory')
        if inventory_system:
            return inventory_system.use_item(self.player_entity, item_slot)
        
        return None
    
    def equip_item(self, item_slot: int) -> Optional[str]:
        """
        Equip an item from inventory.
        
        Args:
            item_slot: Slot number of item to equip
            
        Returns:
            Result message, or None
        """
        if not self.player_entity:
            return None
        
        inventory_system = self.systems.get('inventory')
        if inventory_system:
            return inventory_system.equip_item(self.player_entity, item_slot)
        
        return None
    
    def drop_item(self, item_slot: int) -> Optional[str]:
        """
        Drop an item from inventory.
        
        Args:
            item_slot: Slot number of item to drop
            
        Returns:
            Result message, or None
        """
        if not self.player_entity:
            return None
        
        inventory_system = self.systems.get('inventory')
        if inventory_system:
            return inventory_system.drop_item(self.player_entity, item_slot)
        
        return None
    
    def pickup_item(self, item_entity: Entity) -> Optional[str]:
        """
        Pick up an item entity.
        
        Args:
            item_entity: Item entity to pick up
            
        Returns:
            Result message, or None
        """
        if not self.player_entity:
            return None
        
        inventory_system = self.systems.get('inventory')
        if inventory_system:
            return inventory_system.pickup_item(self.player_entity, item_entity)
        
        return None
    
    def get_game_state(self) -> Dict[str, Any]:
        """
        Get current game state.
        
        Returns:
            Dictionary of game state data
        """
        return self.game_state_manager.get_game_state()
    
    def shutdown(self):
        """Shutdown the gameplay module."""
        print("Shutting down gameplay module...")
        
        # Clear the world
        self.world.clear()
        
        # Clear references
        self.player_entity = None
        self.systems.clear()
        
        print("Gameplay module shutdown complete.")


# Export main systems for easy access
__all__ = [
    'GameplayModule',
    'PlayerSystem',
    'CombatSystem',
    'InventorySystem',
    'QuestSystem',
    'AISystem',
    'SaveSystem',
    'MovementSystem',
    
    # Components
    'PlayerComponent', 'StatsComponent', 'LevelComponent',
    'ExperienceComponent', 'SkillComponent',
    'HealthComponent', 'ManaComponent', 'CombatComponent',
    'DamageComponent', 'DefenseComponent',
    'InventoryComponent', 'ItemComponent', 'EquipmentComponent',
    'CurrencyComponent', 'LootComponent',
    'QuestComponent', 'NPCComponent', 'DialogueComponent',
    'ObjectiveComponent', 'QuestState',
    'CharacterComponent', 'InteractiveComponent',
    'SpawnerComponent', 'ZoneComponent', 'TriggerComponent',
    'GameStateComponent', 'SaveComponent', 'TimeComponent',
    
    # Entity factories
    'create_player_entity',
    'create_enemy_entity',
    'create_npc_entity',
    'create_interactive_entity',
    
    # Managers
    'LevelManager',
    'GameStateManager'
]