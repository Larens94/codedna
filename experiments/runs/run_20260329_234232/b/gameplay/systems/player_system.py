"""
Player System for the 2D RPG.
Handles player movement, input, stats, and progression.
"""

from typing import Dict, List, Optional, Any, Tuple
from engine.ecs import System, World, Entity
from engine.input import InputManager, InputAction
from engine.ecs import TransformComponent, VelocityComponent

from ..components.player import (
    PlayerComponent, StatsComponent, LevelComponent,
    ExperienceComponent, SkillComponent
)
from ..components.combat import HealthComponent, ManaComponent
from ..components.inventory import InventoryComponent, EquipmentComponent


class PlayerSystem(System):
    """
    System for managing player character.
    Handles input, movement, stats, leveling, and progression.
    """
    
    def __init__(self, world: World, input_manager: InputManager):
        """
        Initialize the player system.
        
        Args:
            world: The ECS world
            input_manager: Input manager for player controls
        """
        super().__init__(world)
        self.input_manager = input_manager
        self.player_entity: Optional[Entity] = None
        
        # Movement
        self.move_speed = 5.0
        self.sprint_multiplier = 1.5
        self.is_sprinting = False
        
        # Camera
        self.camera_offset = (0, 0)
        self.camera_smoothness = 0.1
        
        # Input buffering
        self.input_buffer: List[Tuple[str, float]] = []  # (action, timestamp)
        self.buffer_duration = 0.3  # seconds
        
    def set_player_entity(self, player_entity: Entity):
        """
        Set the player entity for this system.
        
        Args:
            player_entity: The player entity
        """
        self.player_entity = player_entity
        
        # Get player stats
        stats = self.world.get_component(player_entity, StatsComponent)
        if stats:
            self.move_speed = stats.move_speed
            self.sprint_multiplier = stats.sprint_multiplier
    
    def fixed_update(self, dt: float):
        """
        Fixed update for player logic.
        
        Args:
            dt: Fixed delta time in seconds
        """
        if not self.player_entity:
            return
        
        # Handle movement
        self._handle_movement(dt)
        
        # Handle actions
        self._handle_actions()
        
        # Update player components
        self._update_player_components(dt)
        
        # Update input buffer
        self._update_input_buffer(dt)
    
    def _handle_movement(self, dt: float):
        """Handle player movement based on input."""
        if not self.player_entity:
            return
        
        # Get movement vector from input
        move_vector = self.input_manager.get_vector(
            InputAction.MOVE_RIGHT,
            InputAction.MOVE_UP
        )
        
        # Check for sprint
        self.is_sprinting = self.input_manager.is_action_triggered(
            InputAction.ATTACK  # Using attack as sprint for now
        )
        
        # Apply sprint multiplier
        speed = self.move_speed
        if self.is_sprinting:
            speed *= self.sprint_multiplier
        
        # Get transform and velocity components
        transform = self.world.get_component(self.player_entity, TransformComponent)
        velocity = self.world.get_component(self.player_entity, VelocityComponent)
        
        if transform and velocity:
            # Update velocity based on input
            velocity.vx = move_vector[0] * speed
            velocity.vy = move_vector[1] * speed
            
            # Update rotation if moving
            if move_vector[0] != 0 or move_vector[1] != 0:
                # Calculate angle from movement vector
                import math
                angle = math.atan2(move_vector[1], move_vector[0])
                transform.rotation = angle
    
    def _handle_actions(self):
        """Handle player actions."""
        if not self.player_entity:
            return
        
        # Check for jump
        if self.input_manager.is_action_just_triggered(InputAction.JUMP):
            self._jump()
        
        # Check for attack
        if self.input_manager.is_action_just_triggered(InputAction.ATTACK):
            self._attack()
        
        # Check for interact
        if self.input_manager.is_action_just_triggered(InputAction.INTERACT):
            self._interact()
        
        # Check for inventory
        if self.input_manager.is_action_just_triggered(InputAction.PAUSE):
            self._toggle_inventory()
    
    def _jump(self):
        """Handle jump action."""
        # This would integrate with physics system
        # For now, just log
        print("Player jumped")
        
        # Buffer the jump input
        self._add_to_input_buffer('jump')
    
    def _attack(self):
        """Handle attack action."""
        print("Player attacked")
        
        # Get combat component
        if self.player_entity:
            from ..components.combat import CombatComponent
            combat = self.world.get_component(self.player_entity, CombatComponent)
            if combat:
                combat.attack()
        
        self._add_to_input_buffer('attack')
    
    def _interact(self):
        """Handle interact action."""
        print("Player interacted")
        
        # Find nearby interactable entities
        nearby = self._find_nearby_interactables()
        if nearby:
            # Interact with closest entity
            self._interact_with_entity(nearby[0])
        
        self._add_to_input_buffer('interact')
    
    def _toggle_inventory(self):
        """Toggle inventory screen."""
        print("Toggled inventory")
        
        # This would trigger UI system to show/hide inventory
        self._add_to_input_buffer('inventory')
    
    def _find_nearby_interactables(self, max_distance: float = 3.0) -> List[Entity]:
        """
        Find nearby interactable entities.
        
        Args:
            max_distance: Maximum interaction distance
            
        Returns:
            List of nearby interactable entities
        """
        if not self.player_entity:
            return []
        
        # Get player position
        transform = self.world.get_component(self.player_entity, TransformComponent)
        if not transform:
            return []
        
        player_pos = (transform.x, transform.y)
        
        # Find all entities with interactive component
        from ..components.entity import InteractiveComponent
        interactables = []
        
        # This would query the world for entities with InteractiveComponent
        # For now, return empty list
        return interactables
    
    def _interact_with_entity(self, entity: Entity):
        """
        Interact with an entity.
        
        Args:
            entity: Entity to interact with
        """
        from ..components.entity import InteractiveComponent
        interactive = self.world.get_component(entity, InteractiveComponent)
        if interactive:
            result = interactive.interact()
            print(f"Interaction result: {result}")
    
    def _update_player_components(self, dt: float):
        """Update player components."""
        if not self.player_entity:
            return
        
        # Update health regeneration
        health = self.world.get_component(self.player_entity, HealthComponent)
        if health:
            health.update(dt)
        
        # Update mana regeneration
        mana = self.world.get_component(self.player_entity, ManaComponent)
        if mana:
            mana.update(dt)
        
        # Update skill cooldowns
        skills = self.world.get_component(self.player_entity, SkillComponent)
        if skills:
            import time
            skills.update_cooldowns(time.time())
    
    def _add_to_input_buffer(self, action: str):
        """
        Add action to input buffer.
        
        Args:
            action: Action name
        """
        import time
        self.input_buffer.append((action, time.time()))
    
    def _update_input_buffer(self, dt: float):
        """Update input buffer, removing old entries."""
        import time
        current_time = time.time()
        
        # Remove old entries
        self.input_buffer = [
            (action, timestamp) for action, timestamp in self.input_buffer
            if current_time - timestamp <= self.buffer_duration
        ]
    
    def get_buffered_actions(self) -> List[str]:
        """
        Get actions in input buffer.
        
        Returns:
            List of buffered action names
        """
        return [action for action, _ in self.input_buffer]
    
    def clear_input_buffer(self):
        """Clear the input buffer."""
        self.input_buffer.clear()
    
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
        player = self.world.get_component(self.player_entity, PlayerComponent)
        if player:
            stats['player'] = {
                'name': player.player_name,
                'class': player.player_class.value,
                'play_time': player.play_time
            }
        
        # Get stats component
        character_stats = self.world.get_component(self.player_entity, StatsComponent)
        if character_stats:
            stats['attributes'] = character_stats.__dict__
        
        # Get health component
        health = self.world.get_component(self.player_entity, HealthComponent)
        if health:
            stats['health'] = {
                'current': health.current_health,
                'max': health.max_health,
                'percentage': health.get_health_percentage()
            }
        
        # Get level component
        level = self.world.get_component(self.player_entity, LevelComponent)
        if level:
            stats['level'] = {
                'level': level.level,
                'experience': level.experience,
                'next_level': level.experience_to_next_level,
                'progress': level.get_experience_progress()
            }
        
        return stats
    
    def add_experience(self, amount: int) -> bool:
        """
        Add experience to player.
        
        Args:
            amount: Amount of experience to add
            
        Returns:
            True if player leveled up
        """
        if not self.player_entity:
            return False
        
        level = self.world.get_component(self.player_entity, LevelComponent)
        if not level:
            return False
        
        return level.add_experience(amount)
    
    def use_skill(self, skill_id: str) -> bool:
        """
        Use a player skill.
        
        Args:
            skill_id: Skill identifier
            
        Returns:
            True if skill was used
        """
        if not self.player_entity:
            return False
        
        skills = self.world.get_component(self.player_entity, SkillComponent)
        if not skills:
            return False
        
        return skills.activate_skill(skill_id)
    
    def get_camera_position(self, screen_size: Tuple[int, int]) -> Tuple[float, float]:
        """
        Get camera position for player.
        
        Args:
            screen_size: Screen size (width, height)
            
        Returns:
            Camera position (x, y)
        """
        if not self.player_entity:
            return (0, 0)
        
        transform = self.world.get_component(self.player_entity, TransformComponent)
        if not transform:
            return (0, 0)
        
        # Center camera on player
        camera_x = transform.x - screen_size[0] / 2
        camera_y = transform.y - screen_size[1] / 2
        
        # Apply smoothing
        old_x, old_y = self.camera_offset
        smooth_factor = 1.0 - self.camera_smoothness
        
        new_x = old_x * smooth_factor + camera_x * (1.0 - smooth_factor)
        new_y = old_y * smooth_factor + camera_y * (1.0 - smooth_factor)
        
        self.camera_offset = (new_x, new_y)
        
        return self.camera_offset
    
    def on_entity_added(self, entity: Entity):
        """Called when an entity is added to the world."""
        # Check if this is the player entity
        player = self.world.get_component(entity, PlayerComponent)
        if player and player.is_main_player:
            self.set_player_entity(entity)
    
    def on_entity_removed(self, entity: Entity):
        """Called when an entity is removed from the world."""
        if entity == self.player_entity:
            self.player_entity = None