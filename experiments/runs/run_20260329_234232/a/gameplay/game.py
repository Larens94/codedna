"""game.py — Main game class coordinating all systems.

exports: Game class
used_by: main.py → GameApplication
rules:   Must initialize all modules in correct order
agent:   Game Director | 2024-01-15 | Defined Game interface
         GameplayDesigner | 2024-01-15 | Integrated gameplay systems
"""

import logging
from typing import Optional
from engine import World
from render import Renderer
from data import AssetManager
from .systems import (
    PlayerSystem, CombatSystem, InventorySystem, 
    QuestSystem, MovementSystem
)
from .components import (
    Player, PlayerStats, Experience, Health, Damage, Attack,
    Enemy, CombatState, Position, Velocity, Acceleration,
    InputState, Inventory, Item, Equipment, Currency,
    Quest, Objective, QuestProgress, NPC, Dialogue, Behavior
)

logger = logging.getLogger(__name__)


class Game:
    """Main game class coordinating engine, render, and gameplay systems.
    
    Rules:
    - Initialize modules in order: data → engine → render → gameplay
    - Clean up in reverse order
    - Handle game state transitions
    """
    
    def __init__(self):
        """Initialize game (does not create resources)."""
        self._initialized = False
        self._world: Optional[World] = None
        self._renderer: Optional[Renderer] = None
        self._asset_manager: Optional[AssetManager] = None
        self._systems = []
        
    def initialize(self) -> bool:
        """Initialize all game modules.
        
        Returns:
            bool: True if initialization successful
            
        Rules: Must be called before update/render.
        """
        try:
            logger.info("Initializing game...")
            
            # 1. Initialize asset manager (data module)
            self._asset_manager = AssetManager(asset_root="assets", cache_size_mb=50)
            logger.info("Asset manager initialized")
            
            # 2. Initialize ECS world (engine module)
            self._world = World()
            logger.info("ECS world initialized")
            
            # 3. Initialize renderer (render module)
            self._renderer = Renderer()
            if not self._renderer.initialize(title="2D RPG Game", width=1280, height=720):
                logger.error("Failed to initialize renderer")
                return False
            logger.info("Renderer initialized")
            
            # 4. Initialize gameplay systems
            if not self._initialize_gameplay():
                logger.error("Failed to initialize gameplay systems")
                return False
            logger.info("Gameplay systems initialized")
            
            # 5. Create initial game entities
            self._create_initial_entities()
            logger.info("Initial entities created")
            
            self._initialized = True
            logger.info("Game initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize game: {e}")
            return False
    
    def _initialize_gameplay(self) -> bool:
        """Initialize gameplay-specific systems and entities.
        
        Returns:
            bool: True if gameplay initialization successful
        """
        try:
            # Initialize gameplay systems
            logger.info("Initializing gameplay systems...")
            
            # Movement system (priority 0 - runs first)
            movement_system = MovementSystem()
            self._world.add_system(movement_system, priority=0)
            self._systems.append(movement_system)
            
            # Player system (priority 10 - handles input)
            if self._renderer and hasattr(self._renderer, '_window'):
                player_system = PlayerSystem(self._renderer._window)
                self._world.add_system(player_system, priority=10)
                self._systems.append(player_system)
            else:
                logger.warning("Renderer window not available, PlayerSystem not initialized")
            
            # Combat system (priority 20 - handles combat logic)
            combat_system = CombatSystem()
            self._world.add_system(combat_system, priority=20)
            self._systems.append(combat_system)
            
            # Inventory system (priority 30 - handles items)
            inventory_system = InventorySystem()
            self._world.add_system(inventory_system, priority=30)
            self._systems.append(inventory_system)
            
            # Quest system (priority 40 - handles quests and NPCs)
            quest_system = QuestSystem()
            self._world.add_system(quest_system, priority=40)
            self._systems.append(quest_system)
            
            logger.info("All gameplay systems initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize gameplay: {e}")
            return False
    
    def _create_initial_entities(self):
        """Create initial game entities.
        
        Rules: Override this method to create game-specific entities.
        """
        logger.info("Creating initial game entities...")
        
        # Create player entity
        player = self._world.create_entity()
        player.add_component(Player())
        player.add_component(PlayerStats())
        player.add_component(Experience())
        player.add_component(Health(current=100, maximum=100))
        player.add_component(Damage(base_damage=15.0))
        player.add_component(Position(x=0, y=0, z=0))
        player.add_component(Velocity(max_speed=5.0))
        player.add_component(Acceleration(max_acceleration=10.0))
        player.add_component(InputState())
        player.add_component(Inventory(max_slots=20, weight_capacity=50.0))
        player.add_component(Currency(gold=10))
        player.add_component(QuestProgress())
        player.add_component(CombatState())
        
        logger.info(f"Created player entity: {player.entity_id}")
        
        # Create a test enemy
        enemy = self._world.create_entity()
        enemy.add_component(Enemy(
            enemy_type="goblin",
            aggression_range=5.0,
            experience_value=25,
            drop_table=[("health_potion", 0.5), ("gold_coin", 1.0)]
        ))
        enemy.add_component(Health(current=50, maximum=50))
        enemy.add_component(Damage(base_damage=5.0, attack_range=1.5))
        enemy.add_component(Position(x=5, y=0, z=0))
        enemy.add_component(Velocity(max_speed=3.0))
        enemy.add_component(CombatState())
        
        logger.info(f"Created enemy entity: {enemy.entity_id}")
        
        # Create a test NPC
        npc = self._world.create_entity()
        npc.add_component(NPC(
            npc_type="merchant",
            dialogue_tree={"greeting": "Welcome traveler!", "farewell": "Safe travels!"}
        ))
        npc.add_component(Position(x=-5, y=0, z=0))
        npc.add_component(Dialogue(
            current_state="idle",
            available_quests=["find_lost_ring"]
        ))
        npc.add_component(Behavior(
            behavior_type="stationary",
            patrol_route=[],
            idle_animation="stand"
        ))
        
        logger.info(f"Created NPC entity: {npc.entity_id}")
        
        # Create a test item
        item = self._world.create_entity()
        item.add_component(Item(
            item_id="health_potion",
            item_type="consumable",
            name="Health Potion",
            description="Restores 50 health points",
            weight=0.5,
            value=25
        ))
        item.add_component(Position(x=2, y=2, z=0))
        
        logger.info(f"Created item entity: {item.entity_id}")
        
        # Create a quest
        quest = self._world.create_entity()
        quest.add_component(Quest(
            quest_id="find_lost_ring",
            title="Find the Lost Ring",
            description="The merchant lost his precious ring in the forest",
            objectives=[Objective(
                objective_id="find_ring",
                description="Find the merchant's lost ring",
                target_type="item",
                target_id="lost_ring",
                required_count=1,
                completed=False
            )],
            rewards=[{"type": "experience", "amount": 100}, {"type": "gold", "amount": 50}],
            giver_entity_id=npc.entity_id,
            available=True
        ))
        
        logger.info(f"Created quest entity: {quest.entity_id}")
    
    def update(self) -> bool:
        """Update game state.
        
        Returns:
            bool: True if should continue, False if game should end
            
        Rules: Called once per frame before render.
        """
        if not self._initialized:
            return False
        
        try:
            # Update ECS world (runs all systems)
            self._world.update()
            
            # Check for window close
            if self._renderer and self._renderer.window_should_close():
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in game update: {e}")
            return False
    
    def render(self) -> None:
        """Render current game state.
        
        Rules: Called once per frame after update.
        """
        if not self._initialized or not self._renderer:
            return
        
        try:
            # Begin frame
            if not self._renderer.begin_frame():
                return
            
            # TODO: Add actual rendering logic here
            # For now, just render a simple colored background
            
            # End frame
            self._renderer.end_frame()
            
        except Exception as e:
            logger.error(f"Error in game render: {e}")
    
    def handle_input(self) -> None:
        """Handle user input.
        
        Rules: Called once per frame, can be integrated with ECS.
        """
        if not self._initialized:
            return
        
        # Input is handled by PlayerSystem via GLFW callbacks
        # Additional input handling can be added here
        
        # Example: Check for escape key to quit
        if self._renderer and hasattr(self._renderer, '_window'):
            import glfw
            if glfw.get_key(self._renderer._window, glfw.KEY_ESCAPE) == glfw.PRESS:
                self._renderer.set_window_should_close(True)
    
    def shutdown(self) -> None:
        """Shutdown all game modules."""
        logger.info("Shutting down game...")
        
        # Shutdown in reverse initialization order
        
        # 1. Shutdown gameplay systems
        for system in self._systems:
            try:
                system.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down system: {e}")
        self._systems.clear()
        
        # 2. Shutdown renderer
        if self._renderer:
            try:
                self._renderer.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down renderer: {e}")
            self._renderer = None
        
        # 3. Clear world (entities will be destroyed)
        self._world = None
        
        # 4. Shutdown asset manager
        if self._asset_manager:
            try:
                self._asset_manager.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down asset manager: {e}")
            self._asset_manager = None
        
        self._initialized = False
        logger.info("Game shutdown complete")
    
    @property
    def world(self) -> Optional[World]:
        """Get the ECS world."""
        return self._world
    
    @property
    def renderer(self) -> Optional[Renderer]:
        """Get the renderer."""
        return self._renderer
    
    @property
    def asset_manager(self) -> Optional[AssetManager]:
        """Get the asset manager."""
        return self._asset_manager
    
    @property
    def initialized(self) -> bool:
        """Check if game is initialized."""
        return self._initialized