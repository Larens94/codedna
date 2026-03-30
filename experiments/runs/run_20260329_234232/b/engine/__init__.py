"""
Engine module - Core engine systems.
Provides Entity-Component-System, input management, scene management,
time management, event system, and physics basics.
"""

# Core engine
from .core import GameEngine, EngineConfig
from .main import run_game, quick_start

# Entity-Component-System
from .ecs import (
    World, Entity, Component, System,
    TransformComponent, VelocityComponent,
    RenderComponent, CollisionComponent,
    MovementSystem, RenderSystem
)

# Input management
from .input import (
    InputManager, InputAction, Key, InputContext,
    InputState
)

# Scene management
from .scene import Scene, SceneManager, SceneNode

# Time management
from .time import TimeManager, TimeSample

# Event system
from .events import (
    Event, EventManager, EventBus, EventPriority,
    InputEvent, KeyEvent, MouseEvent, MouseMoveEvent,
    MouseScrollEvent, WindowEvent, SceneEvent,
    EntityEvent, CollisionEvent, GameEvent,
    subscribe_to
)

# Physics (to be implemented)
# from .physics import PhysicsEngine

__all__ = [
    # Core
    'GameEngine',
    'EngineConfig',
    'run_game',
    'quick_start',
    
    # ECS
    'World',
    'Entity',
    'Component',
    'System',
    'TransformComponent',
    'VelocityComponent',
    'RenderComponent',
    'CollisionComponent',
    'MovementSystem',
    'RenderSystem',
    
    # Input
    'InputManager',
    'InputAction',
    'Key',
    'InputContext',
    'InputState',
    
    # Scene
    'Scene',
    'SceneManager',
    'SceneNode',
    
    # Time
    'TimeManager',
    'TimeSample',
    
    # Events
    'Event',
    'EventManager',
    'EventBus',
    'EventPriority',
    'InputEvent',
    'KeyEvent',
    'MouseEvent',
    'MouseMoveEvent',
    'MouseScrollEvent',
    'WindowEvent',
    'SceneEvent',
    'EntityEvent',
    'CollisionEvent',
    'GameEvent',
    'subscribe_to',
    
    # Physics
    # 'PhysicsEngine',
]