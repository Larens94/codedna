"""
Game state components for the 2D RPG.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from engine.ecs import Component


class GameStateType(Enum):
    """Game state types."""
    MAIN_MENU = "main_menu"
    PLAYING = "playing"
    PAUSED = "paused"
    DIALOGUE = "dialogue"
    INVENTORY = "inventory"
    COMBAT = "combat"
    GAME_OVER = "game_over"
    VICTORY = "victory"


class TimeOfDay(Enum):
    """Times of day."""
    DAWN = "dawn"
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"


@dataclass
class GameStateComponent(Component):
    """
    Component for global game state.
    """
    current_state: GameStateType = GameStateType.MAIN_MENU
    previous_state: GameStateType = GameStateType.MAIN_MENU
    
    # Game progress
    current_level: str = ""
    current_zone: str = ""
    game_time: float = 0.0  # Total game time in seconds
    play_time: float = 0.0  # Actual play time in seconds
    
    # Player progress
    player_level: int = 1
    player_experience: int = 0
    player_gold: int = 0
    
    # Quest progress
    active_quests: List[str] = field(default_factory=list)  # Quest IDs
    completed_quests: List[str] = field(default_factory=list)
    failed_quests: List[str] = field(default_factory=list)
    
    # World state
    world_flags: Dict[str, bool] = field(default_factory=dict)
    world_variables: Dict[str, Any] = field(default_factory=dict)
    
    # Time of day
    time_of_day: TimeOfDay = TimeOfDay.DAY
    day_night_cycle: bool = True
    time_scale: float = 1.0  # 1.0 = real time, 60.0 = 1 minute per second
    
    # Weather
    current_weather: str = "clear"
    weather_intensity: float = 0.0  # 0.0 to 1.0
    
    def change_state(self, new_state: GameStateType):
        """
        Change game state.
        
        Args:
            new_state: New game state
        """
        self.previous_state = self.current_state
        self.current_state = new_state
    
    def revert_state(self):
        """Revert to previous game state."""
        self.current_state, self.previous_state = self.previous_state, self.current_state
    
    def is_state(self, state: GameStateType) -> bool:
        """
        Check if current state matches.
        
        Args:
            state: State to check
            
        Returns:
            True if current state matches
        """
        return self.current_state == state
    
    def add_world_flag(self, flag: str, value: bool = True):
        """
        Set a world flag.
        
        Args:
            flag: Flag name
            value: Flag value
        """
        self.world_flags[flag] = value
    
    def check_world_flag(self, flag: str) -> bool:
        """
        Check a world flag.
        
        Args:
            flag: Flag name
            
        Returns:
            Flag value, False if not set
        """
        return self.world_flags.get(flag, False)
    
    def set_world_variable(self, name: str, value: Any):
        """
        Set a world variable.
        
        Args:
            name: Variable name
            value: Variable value
        """
        self.world_variables[name] = value
    
    def get_world_variable(self, name: str, default: Any = None) -> Any:
        """
        Get a world variable.
        
        Args:
            name: Variable name
            default: Default value if not found
            
        Returns:
            Variable value
        """
        return self.world_variables.get(name, default)
    
    def update_time(self, dt: float):
        """
        Update game time.
        
        Args:
            dt: Delta time in seconds
        """
        scaled_dt = dt * self.time_scale
        self.game_time += scaled_dt
        
        if self.current_state == GameStateType.PLAYING:
            self.play_time += dt
        
        # Update time of day if cycle is enabled
        if self.day_night_cycle:
            self._update_time_of_day(scaled_dt)
    
    def _update_time_of_day(self, dt: float):
        """
        Update time of day based on game time.
        
        Args:
            dt: Delta time in seconds
        """
        # 24-hour cycle in game time
        day_length = 24 * 60 * 60  # 24 hours in seconds
        
        # Calculate current hour (0-23)
        current_hour = (self.game_time % day_length) / 3600
        
        # Determine time of day
        if 5 <= current_hour < 7:
            self.time_of_day = TimeOfDay.DAWN
        elif 7 <= current_hour < 19:
            self.time_of_day = TimeOfDay.DAY
        elif 19 <= current_hour < 21:
            self.time_of_day = TimeOfDay.DUSK
        else:
            self.time_of_day = TimeOfDay.NIGHT
    
    def get_time_string(self) -> str:
        """
        Get formatted time string.
        
        Returns:
            Formatted time (HH:MM)
        """
        # Calculate current hour and minute
        seconds_in_day = self.game_time % (24 * 60 * 60)
        hours = int(seconds_in_day // 3600)
        minutes = int((seconds_in_day % 3600) // 60)
        
        return f"{hours:02d}:{minutes:02d}"
    
    def add_active_quest(self, quest_id: str):
        """
        Add a quest to active quests.
        
        Args:
            quest_id: Quest ID
        """
        if quest_id not in self.active_quests:
            self.active_quests.append(quest_id)
    
    def complete_quest(self, quest_id: str):
        """
        Mark a quest as completed.
        
        Args:
            quest_id: Quest ID
        """
        if quest_id in self.active_quests:
            self.active_quests.remove(quest_id)
        
        if quest_id not in self.completed_quests:
            self.completed_quests.append(quest_id)
    
    def fail_quest(self, quest_id: str):
        """
        Mark a quest as failed.
        
        Args:
            quest_id: Quest ID
        """
        if quest_id in self.active_quests:
            self.active_quests.remove(quest_id)
        
        if quest_id not in self.failed_quests:
            self.failed_quests.append(quest_id)


@dataclass
class SaveComponent(Component):
    """
    Component for save game data.
    """
    save_slot: int = 0
    save_name: str = "Save Game"
    save_time: float = 0.0  # Timestamp when saved
    play_time: float = 0.0  # Play time when saved
    
    # Save data
    player_data: Dict[str, Any] = field(default_factory=dict)
    world_data: Dict[str, Any] = field(default_factory=dict)
    quest_data: Dict[str, Any] = field(default_factory=dict)
    inventory_data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    version: str = "1.0.0"
    checksum: str = ""
    
    def create_save_data(self, game_state: GameStateComponent, 
                        player_entity: Any, world: Any) -> Dict[str, Any]:
        """
        Create save data from current game state.
        
        Args:
            game_state: Game state component
            player_entity: Player entity
            world: Game world
            
        Returns:
            Save data dictionary
        """
        import time
        
        self.save_time = time.time()
        self.play_time = game_state.play_time
        
        # Save player data
        self.player_data = {
            'level': game_state.player_level,
            'experience': game_state.player_experience,
            'gold': game_state.player_gold,
            'position': self._get_entity_position(player_entity),
            'stats': self._get_player_stats(player_entity)
        }
        
        # Save world data
        self.world_data = {
            'current_level': game_state.current_level,
            'current_zone': game_state.current_zone,
            'game_time': game_state.game_time,
            'world_flags': game_state.world_flags.copy(),
            'world_variables': game_state.world_variables.copy(),
            'time_of_day': game_state.time_of_day.value
        }
        
        # Save quest data
        self.quest_data = {
            'active_quests': game_state.active_quests.copy(),
            'completed_quests': game_state.completed_quests.copy(),
            'failed_quests': game_state.failed_quests.copy()
        }
        
        return self.get_save_dict()
    
    def load_save_data(self, save_data: Dict[str, Any]) -> bool:
        """
        Load save data.
        
        Args:
            save_data: Save data dictionary
            
        Returns:
            True if load successful
        """
        try:
            self.save_slot = save_data.get('save_slot', 0)
            self.save_name = save_data.get('save_name', 'Save Game')
            self.save_time = save_data.get('save_time', 0.0)
            self.play_time = save_data.get('play_time', 0.0)
            
            self.player_data = save_data.get('player_data', {})
            self.world_data = save_data.get('world_data', {})
            self.quest_data = save_data.get('quest_data', {})
            self.inventory_data = save_data.get('inventory_data', {})
            
            self.version = save_data.get('version', '1.0.0')
            self.checksum = save_data.get('checksum', '')
            
            return True
        except Exception as e:
            print(f"Error loading save data: {e}")
            return False
    
    def get_save_dict(self) -> Dict[str, Any]:
        """
        Get save data as dictionary.
        
        Returns:
            Save data dictionary
        """
        return {
            'save_slot': self.save_slot,
            'save_name': self.save_name,
            'save_time': self.save_time,
            'play_time': self.play_time,
            'player_data': self.player_data,
            'world_data': self.world_data,
            'quest_data': self.quest_data,
            'inventory_data': self.inventory_data,
            'version': self.version,
            'checksum': self.checksum
        }
    
    def _get_entity_position(self, entity: Any) -> Tuple[float, float]:
        """
        Get entity position.
        
        Args:
            entity: Entity
            
        Returns:
            Position (x, y)
        """
        # This would be implemented based on your entity system
        # For now, return default position
        return (0.0, 0.0)
    
    def _get_player_stats(self, player_entity: Any) -> Dict[str, Any]:
        """
        Get player stats.
        
        Args:
            player_entity: Player entity
            
        Returns:
            Player stats dictionary
        """
        # This would be implemented based on your component system
        # For now, return empty dict
        return {}


@dataclass
class TimeComponent(Component):
    """
    Component for time-based effects and cooldowns.
    """
    # Cooldowns
    cooldowns: Dict[str, float] = field(default_factory=dict)
    
    # Timers
    timers: Dict[str, float] = field(default_factory=dict)
    
    # Duration-based effects
    effects: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Time scaling
    time_scale: float = 1.0
    
    def set_cooldown(self, name: str, duration: float):
        """
        Set a cooldown.
        
        Args:
            name: Cooldown name
            duration: Duration in seconds
        """
        self.cooldowns[name] = duration
    
    def get_cooldown(self, name: str) -> float:
        """
        Get remaining cooldown time.
        
        Args:
            name: Cooldown name
            
        Returns:
            Remaining time in seconds, 0 if not on cooldown
        """
        return self.cooldowns.get(name, 0.0)
    
    def is_on_cooldown(self, name: str) -> bool:
        """
        Check if cooldown is active.
        
        Args:
            name: Cooldown name
            
        Returns:
            True if on cooldown
        """
        return self.get_cooldown(name) > 0
    
    def set_timer(self, name: str, duration: float):
        """
        Set a timer.
        
        Args:
            name: Timer name
            duration: Duration in seconds
        """
        self.timers[name] = duration
    
    def get_timer(self, name: str) -> float:
        """
        Get remaining timer time.
        
        Args:
            name: Timer name
            
        Returns:
            Remaining time in seconds, 0 if timer expired
        """
        return self.timers.get(name, 0.0)
    
    def timer_expired(self, name: str) -> bool:
        """
        Check if timer has expired.
        
        Args:
            name: Timer name
            
        Returns:
            True if timer expired
        """
        return self.get_timer(name) <= 0
    
    def add_effect(self, name: str, duration: float, data: Dict[str, Any] = None):
        """
        Add a timed effect.
        
        Args:
            name: Effect name
            duration: Duration in seconds
            data: Effect data
        """
        self.effects[name] = {
            'duration': duration,
            'remaining': duration,
            'data': data or {}
        }
    
    def get_effect(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get effect data.
        
        Args:
            name: Effect name
            
        Returns:
            Effect data, or None if effect not found
        """
        return self.effects.get(name)
    
    def remove_effect(self, name: str):
        """
        Remove an effect.
        
        Args:
            name: Effect name
        """
        if name in self.effects:
            del self.effects[name]
    
    def update(self, dt: float):
        """
        Update all timers and cooldowns.
        
        Args:
            dt: Delta time in seconds
        """
        scaled_dt = dt * self.time_scale
        
        # Update cooldowns
        for name in list(self.cooldowns.keys()):
            self.cooldowns[name] -= scaled_dt
            if self.cooldowns[name] <= 0:
                del self.cooldowns[name]
        
        # Update timers
        for name in list(self.timers.keys()):
            self.timers[name] -= scaled_dt
            if self.timers[name] <= 0:
                del self.timers[name]
        
        # Update effects
        for name in list(self.effects.keys()):
            effect = self.effects[name]
            effect['remaining'] -= scaled_dt
            if effect['remaining'] <= 0:
                del self.effects[name]