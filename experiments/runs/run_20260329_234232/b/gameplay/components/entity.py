"""
Entity-related components for the 2D RPG.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from engine.ecs import Component


class EntityType(Enum):
    """Types of entities."""
    PLAYER = "player"
    ENEMY = "enemy"
    NPC = "npc"
    ITEM = "item"
    CONTAINER = "container"
    DOOR = "door"
    TRAP = "trap"
    TRIGGER = "trigger"
    SPAWNER = "spawner"
    PROJECTILE = "projectile"


class Faction(Enum):
    """Entity factions."""
    PLAYER = "player"
    ENEMY = "enemy"
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    HOSTILE = "hostile"


@dataclass
class CharacterComponent(Component):
    """
    Base component for all character entities.
    """
    character_id: str = ""
    character_name: str = "Character"
    entity_type: EntityType = EntityType.NPC
    faction: Faction = Faction.NEUTRAL
    level: int = 1
    
    # Stats
    base_stats: Dict[str, float] = field(default_factory=dict)
    
    # Visual
    sprite_id: str = ""
    animation_set: str = "default"
    
    # AI
    ai_behavior: str = "idle"
    ai_state: str = "idle"
    
    # Combat
    is_aggressive: bool = False
    aggression_range: float = 10.0
    leash_range: float = 20.0
    
    def get_stat(self, stat_name: str, default: float = 0.0) -> float:
        """
        Get a stat value.
        
        Args:
            stat_name: Name of stat
            default: Default value if stat not found
            
        Returns:
            Stat value
        """
        return self.base_stats.get(stat_name, default)
    
    def set_stat(self, stat_name: str, value: float):
        """
        Set a stat value.
        
        Args:
            stat_name: Name of stat
            value: Value to set
        """
        self.base_stats[stat_name] = value
    
    def modify_stat(self, stat_name: str, amount: float):
        """
        Modify a stat value.
        
        Args:
            stat_name: Name of stat
            amount: Amount to add/subtract
        """
        current = self.get_stat(stat_name, 0.0)
        self.set_stat(stat_name, current + amount)


@dataclass
class InteractiveComponent(Component):
    """
    Component for interactive objects.
    """
    interactive_id: str = ""
    interactive_type: str = "chest"
    is_active: bool = True
    requires_key: bool = False
    key_id: str = ""
    is_locked: bool = False
    lock_difficulty: int = 0  # 0 = no lock, higher = harder
    
    # State
    current_state: str = "closed"  # open, closed, broken, etc.
    states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Interaction
    interaction_range: float = 2.0
    interaction_cooldown: float = 1.0
    last_interaction_time: float = 0.0
    
    # Contents
    contents: List[Dict[str, Any]] = field(default_factory=list)
    has_been_looted: bool = False
    
    def interact(self) -> Dict[str, Any]:
        """
        Interact with the object.
        
        Returns:
            Interaction result
        """
        current_time = time.time()
        
        # Check cooldown
        if current_time - self.last_interaction_time < self.interaction_cooldown:
            return {'success': False, 'message': 'Cannot interact yet'}
        
        self.last_interaction_time = current_time
        
        # Check if locked
        if self.is_locked:
            return {'success': False, 'message': 'It is locked', 'locked': True}
        
        # Perform interaction based on type
        result = {'success': True, 'message': ''}
        
        if self.interactive_type == "chest":
            if self.current_state == "closed":
                self.current_state = "open"
                result['message'] = 'Chest opened'
                result['contents'] = self.contents
                self.has_been_looted = True
            else:
                result['message'] = 'Chest is already open'
        
        elif self.interactive_type == "door":
            if self.current_state == "closed":
                self.current_state = "open"
                result['message'] = 'Door opened'
            else:
                self.current_state = "closed"
                result['message'] = 'Door closed'
        
        elif self.interactive_type == "lever":
            if self.current_state == "off":
                self.current_state = "on"
                result['message'] = 'Lever activated'
            else:
                self.current_state = "off"
                result['message'] = 'Lever deactivated'
        
        return result
    
    def unlock(self, key_id: str = "") -> bool:
        """
        Attempt to unlock the object.
        
        Args:
            key_id: Key ID to use
            
        Returns:
            True if unlocked successfully
        """
        if not self.is_locked:
            return True
        
        if self.requires_key:
            if key_id == self.key_id:
                self.is_locked = False
                return True
            return False
        
        # Lockpicking or other unlocking methods could be implemented here
        return False
    
    def add_content(self, item_data: Dict[str, Any]):
        """
        Add content to the interactive object.
        
        Args:
            item_data: Item data to add
        """
        self.contents.append(item_data)
    
    def take_content(self, index: int = 0) -> Optional[Dict[str, Any]]:
        """
        Take content from the interactive object.
        
        Args:
            index: Index of content to take
            
        Returns:
            Item data, or None if index invalid
        """
        if 0 <= index < len(self.contents):
            return self.contents.pop(index)
        return None


@dataclass
class SpawnerComponent(Component):
    """
    Component for entity spawners.
    """
    spawner_id: str = ""
    spawn_type: EntityType = EntityType.ENEMY
    template_id: str = ""  # ID of entity template to spawn
    max_spawns: int = 5
    current_spawns: int = 0
    spawn_radius: float = 5.0
    
    # Spawn timing
    spawn_interval: float = 30.0  # seconds
    spawn_cooldown: float = 0.0
    initial_spawn_delay: float = 0.0
    
    # Spawn conditions
    requires_clear_area: bool = True
    clear_radius: float = 2.0
    spawn_at_night: bool = False
    spawn_at_day: bool = True
    
    # Spawned entities
    spawned_entities: List[Any] = field(default_factory=list)  # List of entity references
    
    def can_spawn(self, current_time: float, is_daytime: bool = True) -> bool:
        """
        Check if spawner can spawn an entity.
        
        Args:
            current_time: Current game time
            is_daytime: Whether it's daytime
            
        Returns:
            True if can spawn
        """
        # Check time of day conditions
        if self.spawn_at_day and not is_daytime:
            return False
        if self.spawn_at_night and is_daytime:
            return False
        
        # Check spawn limits
        if self.current_spawns >= self.max_spawns:
            return False
        
        # Check cooldown
        if self.spawn_cooldown > 0:
            return False
        
        return True
    
    def spawn_entity(self, position: Tuple[float, float]) -> Optional[Any]:
        """
        Spawn an entity.
        
        Args:
            position: Spawn position
            
        Returns:
            Spawned entity, or None
        """
        if not self.can_spawn(time.time()):
            return None
        
        # Create entity based on template
        # This would be implemented in the spawn system
        entity = None  # Placeholder
        
        if entity:
            self.current_spawns += 1
            self.spawned_entities.append(entity)
            self.spawn_cooldown = self.spawn_interval
        
        return entity
    
    def entity_died(self, entity: Any):
        """
        Notify spawner that an entity died.
        
        Args:
            entity: Entity that died
        """
        if entity in self.spawned_entities:
            self.spawned_entities.remove(entity)
            self.current_spawns -= 1
    
    def update(self, dt: float):
        """
        Update spawner cooldown.
        
        Args:
            dt: Delta time in seconds
        """
        if self.spawn_cooldown > 0:
            self.spawn_cooldown -= dt


@dataclass
class ZoneComponent(Component):
    """
    Component for game zones/areas.
    """
    zone_id: str = ""
    zone_name: str = "Zone"
    bounds: Tuple[float, float, float, float] = (0, 0, 100, 100)  # x1, y1, x2, y2
    zone_type: str = "normal"  # normal, safe, hostile, dungeon, etc.
    
    # Environment
    environment_id: str = ""
    music_track: str = ""
    ambient_sounds: List[str] = field(default_factory=list)
    
    # Weather
    weather_enabled: bool = True
    weather_types: List[str] = field(default_factory=lambda: ["clear", "rain", "snow"])
    current_weather: str = "clear"
    weather_change_interval: float = 300.0  # 5 minutes
    weather_change_timer: float = 0.0
    
    # Spawns
    enemy_spawners: List[Any] = field(default_factory=list)  # List of spawner entities
    item_spawners: List[Any] = field(default_factory=list)
    
    # Triggers
    triggers: List[Any] = field(default_factory=list)  # List of trigger entities
    
    def contains_point(self, x: float, y: float) -> bool:
        """
        Check if a point is within zone bounds.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if point is within zone
        """
        x1, y1, x2, y2 = self.bounds
        return x1 <= x <= x2 and y1 <= y <= y2
    
    def get_random_point(self) -> Tuple[float, float]:
        """
        Get a random point within zone bounds.
        
        Returns:
            Random (x, y) coordinates
        """
        import random
        x1, y1, x2, y2 = self.bounds
        x = random.uniform(x1, x2)
        y = random.uniform(y1, y2)
        return (x, y)
    
    def update_weather(self, dt: float):
        """
        Update weather system.
        
        Args:
            dt: Delta time in seconds
        """
        if not self.weather_enabled:
            return
        
        self.weather_change_timer -= dt
        if self.weather_change_timer <= 0:
            self.change_weather()
            self.weather_change_timer = self.weather_change_interval
    
    def change_weather(self):
        """Change to a random weather type."""
        import random
        if self.weather_types:
            available_weathers = [w for w in self.weather_types if w != self.current_weather]
            if available_weathers:
                self.current_weather = random.choice(available_weathers)


@dataclass
class TriggerComponent(Component):
    """
    Component for area triggers.
    """
    trigger_id: str = ""
    trigger_type: str = "area"  # area, proximity, interaction, etc.
    bounds: Tuple[float, float, float, float] = (0, 0, 10, 10)  # x1, y1, x2, y2
    radius: float = 5.0  # For circular triggers
    
    # Trigger conditions
    trigger_once: bool = True
    has_triggered: bool = False
    cooldown: float = 0.0
    cooldown_timer: float = 0.0
    
    # Trigger actions
    actions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Target filtering
    target_types: List[EntityType] = field(default_factory=list)
    target_factions: List[Faction] = field(default_factory=list)
    
    def check_trigger(self, entity: Any, entity_type: EntityType, 
                     entity_faction: Faction, position: Tuple[float, float]) -> bool:
        """
        Check if trigger should activate for an entity.
        
        Args:
            entity: Entity to check
            entity_type: Entity type
            entity_faction: Entity faction
            position: Entity position (x, y)
            
        Returns:
            True if trigger should activate
        """
        # Check if already triggered (for one-time triggers)
        if self.trigger_once and self.has_triggered:
            return False
        
        # Check cooldown
        if self.cooldown_timer > 0:
            return False
        
        # Check target filters
        if self.target_types and entity_type not in self.target_types:
            return False
        
        if self.target_factions and entity_faction not in self.target_factions:
            return False
        
        # Check position based on trigger type
        x, y = position
        
        if self.trigger_type == "area":
            x1, y1, x2, y2 = self.bounds
            if not (x1 <= x <= x2 and y1 <= y <= y2):
                return False
        
        elif self.trigger_type == "proximity":
            # Use radius for circular trigger
            import math
            center_x = (self.bounds[0] + self.bounds[2]) / 2
            center_y = (self.bounds[1] + self.bounds[3]) / 2
            distance = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
            if distance > self.radius:
                return False
        
        # All checks passed
        return True
    
    def activate(self):
        """Activate the trigger."""
        self.has_triggered = True
        self.cooldown_timer = self.cooldown
        
        # Execute actions
        for action in self.actions:
            self._execute_action(action)
    
    def _execute_action(self, action: Dict[str, Any]):
        """
        Execute a trigger action.
        
        Args:
            action: Action data
        """
        action_type = action.get('type')
        
        if action_type == "spawn":
            # Spawn entities
            pass
        elif action_type == "despawn":
            # Despawn entities
            pass
        elif action_type == "teleport":
            # Teleport entity
            pass
        elif action_type == "damage":
            # Apply damage
            pass
        elif action_type == "heal":
            # Apply healing
            pass
        elif action_type == "quest_update":
            # Update quest
            pass
        elif action_type == "dialogue":
            # Start dialogue
            pass
        elif action_type == "change_zone":
            # Change zone
            pass
    
    def update(self, dt: float):
        """
        Update trigger cooldown.
        
        Args:
            dt: Delta time in seconds
        """
        if self.cooldown_timer > 0:
            self.cooldown_timer -= dt


# Import required modules
import time