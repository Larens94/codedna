"""
Entity-Component-System (ECS) implementation.
Provides a flexible, data-oriented architecture for game entities.
"""

from typing import Dict, List, Set, Type, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
import uuid


class Entity:
    """Represents a game entity with a unique identifier."""
    
    __slots__ = ('id',)
    
    def __init__(self, entity_id: Optional[int] = None):
        """
        Create a new entity.
        
        Args:
            entity_id: Optional ID for the entity. If None, generates a new ID.
        """
        self.id = entity_id if entity_id is not None else self._generate_id()
    
    @staticmethod
    def _generate_id() -> int:
        """Generate a unique entity ID."""
        return uuid.uuid4().int & (1 << 31) - 1  # 31-bit positive integer
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.id == other.id
    
    def __repr__(self) -> str:
        return f"Entity({self.id})"


class Component:
    """Base class for all components. Components are plain data containers."""
    
    def __init__(self, **kwargs):
        """Initialize component with keyword arguments."""
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__})"


@dataclass
class TransformComponent(Component):
    """Component for entity position, rotation, and scale."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    scale_z: float = 1.0


@dataclass
class VelocityComponent(Component):
    """Component for entity velocity."""
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0


@dataclass
class RenderComponent(Component):
    """Component for rendering information."""
    mesh_id: str = ""
    material_id: str = ""
    visible: bool = True
    layer: int = 0


@dataclass
class CollisionComponent(Component):
    """Component for collision information."""
    shape: str = "aabb"  # "aabb", "circle", "polygon"
    width: float = 1.0
    height: float = 1.0
    radius: float = 0.5
    is_trigger: bool = False
    layer: int = 0
    mask: int = 0xFFFFFFFF  # Bitmask for collision layers


class System:
    """Base class for all systems. Systems process entities with specific components."""
    
    def __init__(self, world: 'World'):
        """
        Initialize a system.
        
        Args:
            world: The world this system belongs to
        """
        self.world = world
        self.enabled = True
    
    def update(self, dt: float):
        """
        Update the system.
        
        Args:
            dt: Delta time in seconds
        """
        pass
    
    def fixed_update(self, dt: float):
        """
        Fixed update for physics and game logic.
        
        Args:
            dt: Fixed delta time in seconds
        """
        pass
    
    def on_entity_added(self, entity: Entity):
        """
        Called when an entity matching this system's requirements is added.
        
        Args:
            entity: The entity that was added
        """
        pass
    
    def on_entity_removed(self, entity: Entity):
        """
        Called when an entity matching this system's requirements is removed.
        
        Args:
            entity: The entity that was removed
        """
        pass


class World:
    """
    Manages all entities, components, and systems in the game world.
    """
    
    def __init__(self):
        """Initialize a new world."""
        self.entities: Set[Entity] = set()
        self.components: Dict[Type[Component], Dict[Entity, Component]] = {}
        self.systems: List[System] = []
        self.entity_to_components: Dict[Entity, Set[Type[Component]]] = {}
        
        # Cache for entity queries
        self._query_cache: Dict[Tuple[Type[Component], ...], List[Entity]] = {}
    
    def create_entity(self) -> Entity:
        """
        Create a new entity.
        
        Returns:
            The newly created entity
        """
        entity = Entity()
        self.entities.add(entity)
        self.entity_to_components[entity] = set()
        return entity
    
    def destroy_entity(self, entity: Entity):
        """
        Destroy an entity and all its components.
        
        Args:
            entity: The entity to destroy
        """
        if entity not in self.entities:
            return
        
        # Remove all components from this entity
        for component_type in list(self.entity_to_components[entity]):
            self.remove_component(entity, component_type)
        
        # Remove entity from tracking
        self.entities.remove(entity)
        del self.entity_to_components[entity]
        
        # Clear query cache
        self._query_cache.clear()
    
    def add_component(self, entity: Entity, component: Component):
        """
        Add a component to an entity.
        
        Args:
            entity: The entity to add the component to
            component: The component to add
        """
        component_type = type(component)
        
        # Initialize component storage if needed
        if component_type not in self.components:
            self.components[component_type] = {}
        
        # Add component
        self.components[component_type][entity] = component
        self.entity_to_components[entity].add(component_type)
        
        # Clear query cache
        self._query_cache.clear()
        
        # Notify systems
        for system in self.systems:
            system.on_entity_added(entity)
    
    def get_component(self, entity: Entity, component_type: Type[Component]) -> Optional[Component]:
        """
        Get a component from an entity.
        
        Args:
            entity: The entity to get the component from
            component_type: Type of component to get
            
        Returns:
            The component, or None if not found
        """
        if component_type not in self.components:
            return None
        return self.components[component_type].get(entity)
    
    def has_component(self, entity: Entity, component_type: Type[Component]) -> bool:
        """
        Check if an entity has a component.
        
        Args:
            entity: The entity to check
            component_type: Type of component to check for
            
        Returns:
            True if entity has the component
        """
        return component_type in self.entity_to_components.get(entity, set())
    
    def remove_component(self, entity: Entity, component_type: Type[Component]):
        """
        Remove a component from an entity.
        
        Args:
            entity: The entity to remove the component from
            component_type: Type of component to remove
        """
        if component_type not in self.components:
            return
        
        if entity in self.components[component_type]:
            del self.components[component_type][entity]
            self.entity_to_components[entity].remove(component_type)
            
            # Clear query cache
            self._query_cache.clear()
            
            # Notify systems
            for system in self.systems:
                system.on_entity_removed(entity)
    
    def query(self, *component_types: Type[Component]) -> List[Entity]:
        """
        Query for entities that have all specified components.
        
        Args:
            *component_types: Component types to query for
            
        Returns:
            List of entities matching the query
        """
        # Check cache first
        cache_key = component_types
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]
        
        if not component_types:
            return list(self.entities)
        
        # Start with entities that have the first component type
        first_type = component_types[0]
        if first_type not in self.components:
            result = []
        else:
            result = [entity for entity in self.components[first_type].keys()]
        
        # Filter by remaining component types
        for component_type in component_types[1:]:
            if component_type not in self.components:
                result = []
                break
            
            component_entities = set(self.components[component_type].keys())
            result = [entity for entity in result if entity in component_entities]
        
        # Cache the result
        self._query_cache[cache_key] = result
        return result
    
    def get_components(self, entity: Entity) -> List[Component]:
        """
        Get all components for an entity.
        
        Args:
            entity: The entity to get components for
            
        Returns:
            List of components attached to the entity
        """
        components = []
        for component_type in self.entity_to_components.get(entity, set()):
            component = self.components[component_type].get(entity)
            if component:
                components.append(component)
        return components
    
    def add_system(self, system: System):
        """
        Add a system to the world.
        
        Args:
            system: The system to add
        """
        self.systems.append(system)
    
    def remove_system(self, system: System):
        """
        Remove a system from the world.
        
        Args:
            system: The system to remove
        """
        if system in self.systems:
            self.systems.remove(system)
    
    def update(self, dt: float):
        """
        Update all systems.
        
        Args:
            dt: Delta time in seconds
        """
        for system in self.systems:
            if system.enabled:
                system.update(dt)
    
    def fixed_update(self, dt: float):
        """
        Fixed update for all systems.
        
        Args:
            dt: Fixed delta time in seconds
        """
        for system in self.systems:
            if system.enabled:
                system.fixed_update(dt)
    
    def clear(self):
        """Clear all entities, components, and systems from the world."""
        self.entities.clear()
        self.components.clear()
        self.systems.clear()
        self.entity_to_components.clear()
        self._query_cache.clear()


# Example systems for common functionality

class MovementSystem(System):
    """System that updates entity positions based on velocity."""
    
    def fixed_update(self, dt: float):
        """Update entity positions."""
        for entity in self.world.query(TransformComponent, VelocityComponent):
            transform = self.world.get_component(entity, TransformComponent)
            velocity = self.world.get_component(entity, VelocityComponent)
            
            if transform and velocity:
                transform.x += velocity.vx * dt
                transform.y += velocity.vy * dt
                transform.z += velocity.vz * dt


class RenderSystem(System):
    """System that collects renderable entities for the renderer."""
    
    def __init__(self, world: 'World'):
        super().__init__(world)
        self.renderable_entities: List[Entity] = []
    
    def update(self, dt: float):
        """Update the list of renderable entities."""
        self.renderable_entities = self.world.query(TransformComponent, RenderComponent)
    
    def get_render_data(self) -> List[Tuple[TransformComponent, RenderComponent]]:
        """
        Get render data for all renderable entities.
        
        Returns:
            List of (transform, render) component pairs
        """
        render_data = []
        for entity in self.renderable_entities:
            transform = self.world.get_component(entity, TransformComponent)
            render = self.world.get_component(entity, RenderComponent)
            if transform and render and render.visible:
                render_data.append((transform, render))
        return render_data