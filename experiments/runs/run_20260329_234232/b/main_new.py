#!/usr/bin/env python3
#!/usr/bin/env python3
"""
Final Integrated RPG Game
Main entry point that integrates all modules: engine, render, gameplay, data
"""

import sys
import time
import pygame
import sqlite3
import json
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np


# ============================================================================
# Configuration Classes
# ============================================================================

@dataclass
class GameConfig:
    """Configuration for the entire game."""
    title: str = "RPG Adventure"
    width: int = 1280
    height: int = 720
    fullscreen: bool = False
    vsync: bool = True
    target_fps: int = 60
    max_frame_time: float = 0.1
    asset_path: str = "assets/"
    config_path: str = "config/"
    save_path: str = "saves/"
    debug_mode: bool = False


class GameStateEnum(Enum):
    """Game state enumeration."""
    MAIN_MENU = "main_menu"
    PLAYING = "playing"
    PAUSED = "paused"
    INVENTORY = "inventory"
    COMBAT = "combat"
    DIALOGUE = "dialogue"
    GAME_OVER = "game_over"


# ============================================================================
# Entity Component System
# ============================================================================

class Entity:
    """Game entity with components."""
    
    def __init__(self, entity_id: int, name: str = "Entity"):
        self.id = entity_id
        self.name = name
        self.components: Dict[str, Any] = {}
        self.active = True
    
    def add_component(self, component_type: str, component: Any):
        """Add a component to the entity."""
        self.components[component_type] = component
    
    def get_component(self, component_type: str) -> Optional[Any]:
        """Get a component from the entity."""
        return self.components.get(component_type)
    
    def has_component(self, component_type: str) -> bool:
        """Check if entity has a component."""
        return component_type in self.components


@dataclass
class Transform:
    """Transform component for position, rotation, scale."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0


@dataclass
class Sprite:
    """Sprite component for rendering."""
    texture_id: str = "default"
    width: int = 32
    height: int = 32
    color: tuple = (255, 255, 255, 255)
    visible: bool = True


@dataclass
class Player:
    """Player component."""
    health: int = 100
    max_health: int = 100
    mana: int = 50
    max_mana: int = 50
    stamina: int = 100
    max_stamina: int = 100
    level: int = 1
    experience: int = 0
    gold: int = 0


@dataclass
class Combat:
    """Combat component."""
    attack_power: int = 10
    defense: int = 5
    attack_range: float = 50.0
    attack_speed: float = 1.0
    last_attack_time: float = 0.0
    target_id: Optional[int] = None


@dataclass
class Inventory:
    """Inventory component."""
    items: List[Dict] = None
    max_items: int = 20
    equipped: Dict[str, Optional[int]] = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
        if self.equipped is None:
            self.equipped = {
                "weapon": None,
                "armor": None,
                "helmet": None,
                "boots": None
            }


@dataclass
class NPC:
    """NPC component."""
    npc_type: str = "villager"
    dialogue_tree: List[Dict] = None
    quest_giver: bool = False
    shop_keeper: bool = False
    
    def __post_init__(self):
        if self.dialogue_tree is None:
            self.dialogue_tree = [
                {"id": 1, "text": "Hello traveler!", "responses": [2]},
                {"id": 2, "text": "How can I help you?", "responses": [3, 4]},
                {"id": 3, "text": "Tell me about this place.", "responses": []},
                {"id": 4, "text": "Goodbye.", "responses": []}
            ]
    MAIN_MENU = "main_menu"
    PLAYING = "playing"
    PAUSED = "paused"
    INVENTORY = "inventory"
    COMBAT = "combat"
    DIALOGUE = "dialogue"
    GAME_OVER = "game_over"