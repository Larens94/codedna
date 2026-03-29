"""entity.py — Entity class representing game objects.

exports: Entity class
used_by: gameplay/, systems querying entities
rules:   Entity is a lightweight handle, all data in components
agent:   Game Director | 2024-01-15 | Defined Entity interface
"""

from typing import Optional, Type
from .component import Component


class Entity:
    """Lightweight handle to a game object in the ECS world.
    
    Rules: 
    - Entity objects are cheap to create/destroy
    - All game data stored in components, not in Entity
    - Entity ID is unique within its World
    """
    
    __slots__ = ('_id', '_world')
    
    def __init__(self, entity_id: int, world: 'World'):
        """Create entity handle.
        
        Args:
            entity_id: Unique identifier
            world: World containing this entity
        """
        self._id = entity_id
        self._world = world
        
    @property
    def id(self) -> int:
        """Get entity ID."""
        return self._id
    
    def add_component(self, component: Component) -> 'Entity':
        """Add a component to this entity.
        
        Args:
            component: Component instance to add
            
        Returns:
            Self for method chaining
        """
        self._world.add_component(self, component)
        return self
    
    def remove_component(self, component_type: Type[Component]) -> 'Entity':
        """Remove a component from this entity.
        
        Args:
            component_type: Type of component to remove
            
        Returns:
            Self for method chaining
        """
        self._world.remove_component(self, component_type)
        return self
    
    def get_component(self, component_type: Type[Component]) -> Optional[Component]:
        """Get a component from this entity.
        
        Args:
            component_type: Type of component to retrieve
            
        Returns:
            Component instance or None if not found
        """
        return self._world.get_component(self, component_type)
    
    def has_component(self, component_type: Type[Component]) -> bool:
        """Check if entity has a component type.
        
        Args:
            component_type: Type to check
            
        Returns:
            True if entity has component, False otherwise
        """
        return self._world.get_component(self, component_type) is not None
    
    def destroy(self) -> None:
        """Destroy this entity and all its components."""
        self._world.destroy_entity(self)
    
    def __eq__(self, other: object) -> bool:
        """Check if two entities are the same.
        
        Rules: Entities are equal if they have same ID and same World.
        """
        if not isinstance(other, Entity):
            return False
        return self._id == other._id and self._world is other._world
    
    def __hash__(self) -> int:
        """Hash based on entity ID and world identity."""
        return hash((self._id, id(self._world)))
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"Entity(id={self._id})"