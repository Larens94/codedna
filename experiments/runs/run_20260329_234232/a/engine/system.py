"""system.py - System base class for ECS logic.

exports: System class
used_by: gameplay/systems/*.py
rules:   Systems contain logic, no data storage
agent:   Game Director | 2024-1-15 | Defined System interface
"""

from abc import ABC, abstractmethod
from typing import Set, Type, Optional
from .component import Component
from .world import World


class System(ABC):
    """Base class for all ECS systems.
    
    Rules:
    - Systems contain logic but no persistent state
    - Should query entities and process them each frame
    - Can have both fixed_update (physics) and update (rendering) methods
    """
    
    def __init__(self, required_components: Optional[Set[Type[Component]]] = None):
        """Initialize system with required component types.
        
        Args:
            required_components: Set of component types this system processes
        """
        self.required_components = required_components or set()
        self._initialized = False
        
    def initialize(self, world: World) -> None:
        """Initialize system with world reference.
        
        Args:
            world: World this system operates on
            
        Rules: Called once when system is added to world.
        """
        self._world = world
        self._initialized = True
        
    @property
    def initialized(self) -> bool:
        """Check if system has been initialized."""
        return self._initialized
    
    def update(self, world: World, delta_time: float) -> None:
        """Update system with variable timestep.
        
        Args:
            world: World to operate on
            delta_time: Time since last update in seconds
            
        Rules: Override for rendering and game logic systems.
        """
        pass
    
    def fixed_update(self, world: World, fixed_delta_time: float) -> None:
        """Update system with fixed timestep.
        
        Args:
            world: World to operate on
            fixed_delta_time: Fixed timestep duration
            
        Rules: Override for physics and simulation systems.
        """
        pass
    
    def query_entities(self, world: World) -> list:
        """Query entities matching this system's requirements.
        
        Args:
            world: World to query
            
        Returns:
            List of entities with required components
            
        Rules: Systems should use this method to get entities to process.
        """
        if not self.required_components:
            return []
        return world.query_entities(self.required_components)
    
    def on_entity_added(self, entity: 'Entity') -> None:
        """Called when an entity matching system requirements is added.
        
        Args:
            entity: Newly added entity
            
        Rules: Override for initialization logic on new entities.
        """
        pass
    
    def on_entity_removed(self, entity: 'Entity') -> None:
        """Called when an entity matching system requirements is removed.
        
        Args:
            entity: Removed entity
            
        Rules: Override for cleanup logic on removed entities.
        """
        pass
    
    def shutdown(self) -> None:
        """Clean up system resources.
        
        Rules: Called when system is removed from world or game shuts down.
        """
        pass