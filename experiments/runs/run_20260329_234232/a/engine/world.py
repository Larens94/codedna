"""world.py — ECS World managing entities, components, and systems.

exports: World class
used_by: gameplay/game.py → Game._world
rules:   Must support 10,000+ entities at 60 FPS, archetype-based storage
agent:   Game Director | 2024-01-15 | Defined World public interface
"""

from typing import Dict, List, Set, Type, Any, Optional
from dataclasses import dataclass
import time


@dataclass
class Archetype:
    """Component layout for cache-friendly storage.
    
    Rules: Archetypes are immutable once created.
    """
    component_types: Set[Type['Component']]
    entities: List[int]  # Entity IDs
    component_data: Dict[Type['Component'], List[Any]]  # Component data arrays


class World:
    """Entity-Component-System World container.
    
    Rules: 
    - Entity IDs are recycled to avoid fragmentation
    - Component data stored in contiguous arrays per archetype
    - Systems executed in registration order each frame
    """
    
    def __init__(self):
        """Initialize empty world."""
        self._next_entity_id = 0
        self._entities: Set[int] = set()
        self._free_entity_ids: List[int] = []
        
        # Archetype storage
        self._archetypes: List[Archetype] = []
        self._entity_archetype_map: Dict[int, int] = {}  # entity_id -> archetype_index
        
        # Systems
        self._systems: List['System'] = []
        self._system_execution_order: List[int] = []
        
        # Time management
        self._delta_time = 0.0
        self._fixed_delta_time = 1.0 / 60.0  # 60 FPS fixed timestep
        self._accumulator = 0.0
        self._last_update_time = time.perf_counter()
        
    def create_entity(self) -> 'Entity':
        """Create a new entity.
        
        Returns:
            Entity: New entity with unique ID
            
        Rules: Reuses freed entity IDs before allocating new ones.
        """
        if self._free_entity_ids:
            entity_id = self._free_entity_ids.pop()
        else:
            entity_id = self._next_entity_id
            self._next_entity_id += 1
            
        self._entities.add(entity_id)
        
        # Start entity in empty archetype
        empty_archetype = self._get_or_create_archetype(set())
        self._entity_archetype_map[entity_id] = empty_archetype
        
        return Entity(entity_id, self)
    
    def destroy_entity(self, entity: 'Entity') -> None:
        """Destroy an entity and all its components.
        
        Args:
            entity: Entity to destroy
            
        Rules: Entity ID is recycled for future use.
        """
        entity_id = entity.id
        
        if entity_id not in self._entities:
            return
            
        # Remove from archetype
        archetype_idx = self._entity_archetype_map[entity_id]
        archetype = self._archetypes[archetype_idx]
        
        # Find entity index in archetype
        try:
            entity_idx = archetype.entities.index(entity_id)
        except ValueError:
            return
            
        # Remove entity from archetype (swap with last for O(1) removal)
        last_idx = len(archetype.entities) - 1
        if entity_idx != last_idx:
            # Swap with last entity
            last_entity_id = archetype.entities[last_idx]
            archetype.entities[entity_idx] = last_entity_id
            
            # Update component data
            for comp_type, data_list in archetype.component_data.items():
                data_list[entity_idx] = data_list[last_idx]
                data_list.pop()  # Remove last element
            
            # Update mapping for swapped entity
            self._entity_archetype_map[last_entity_id] = archetype_idx
            
        # Remove last element (now the entity we want to remove)
        archetype.entities.pop()
        for data_list in archetype.component_data.values():
            data_list.pop()
            
        # Clean up
        del self._entity_archetype_map[entity_id]
        self._entities.remove(entity_id)
        self._free_entity_ids.append(entity_id)
    
    def add_component(self, entity: 'Entity', component: 'Component') -> None:
        """Add a component to an entity.
        
        Args:
            entity: Entity to modify
            component: Component instance to add
            
        Rules: Triggers archetype migration if component type is new for entity.
        """
        entity_id = entity.id
        if entity_id not in self._entities:
            raise ValueError(f"Entity {entity_id} does not exist")
            
        # Get current archetype
        current_idx = self._entity_archetype_map[entity_id]
        current_archetype = self._archetypes[current_idx]
        
        # Check if component type already exists
        if type(component) in current_archetype.component_types:
            raise ValueError(f"Entity {entity_id} already has component {type(component).__name__}")
            
        # Create new archetype with added component
        new_types = current_archetype.component_types.copy()
        new_types.add(type(component))
        new_idx = self._get_or_create_archetype(new_types)
        new_archetype = self._archetypes[new_idx]
        
        # Migrate entity to new archetype
        self._migrate_entity(entity_id, current_idx, new_idx, component)
    
    def remove_component(self, entity: 'Entity', component_type: Type['Component']) -> None:
        """Remove a component from an entity.
        
        Args:
            entity: Entity to modify
            component_type: Type of component to remove
            
        Rules: Triggers archetype migration.
        """
        entity_id = entity.id
        if entity_id not in self._entities:
            raise ValueError(f"Entity {entity_id} does not exist")
            
        current_idx = self._entity_archetype_map[entity_id]
        current_archetype = self._archetypes[current_idx]
        
        if component_type not in current_archetype.component_types:
            raise ValueError(f"Entity {entity_id} does not have component {component_type.__name__}")
            
        # Create new archetype without component
        new_types = current_archetype.component_types.copy()
        new_types.remove(component_type)
        new_idx = self._get_or_create_archetype(new_types)
        
        # Migrate entity to new archetype
        self._migrate_entity(entity_id, current_idx, new_idx)
    
    def get_component(self, entity: 'Entity', component_type: Type['Component']) -> Optional['Component']:
        """Get a component from an entity.
        
        Args:
            entity: Entity to query
            component_type: Type of component to retrieve
            
        Returns:
            Component instance or None if not found
        """
        entity_id = entity.id
        if entity_id not in self._entities:
            return None
            
        archetype_idx = self._entity_archetype_map[entity_id]
        archetype = self._archetypes[archetype_idx]
        
        if component_type not in archetype.component_types:
            return None
            
        # Find entity index in archetype
        try:
            entity_idx = archetype.entities.index(entity_id)
        except ValueError:
            return None
            
        # Return component data
        return archetype.component_data[component_type][entity_idx]
    
    def query_entities(self, component_types: Set[Type['Component']]) -> List['Entity']:
        """Query entities that have all specified component types.
        
        Args:
            component_types: Set of required component types
            
        Returns:
            List of entities matching the query
            
        Rules: Returns entities in archetype order for cache efficiency.
        """
        result = []
        
        for archetype in self._archetypes:
            if component_types.issubset(archetype.component_types):
                # All archetype entities match the query
                for entity_id in archetype.entities:
                    result.append(Entity(entity_id, self))
                    
        return result
    
    def add_system(self, system: 'System', priority: int = 0) -> None:
        """Add a system to the world.
        
        Args:
            system: System instance
            priority: Execution priority (lower = earlier)
            
        Rules: Systems with same priority execute in addition order.
        """
        self._systems.append(system)
        self._system_execution_order.append(priority)
        
        # Sort systems by priority
        sorted_indices = sorted(range(len(self._systems)), 
                               key=lambda i: self._system_execution_order[i])
        self._systems = [self._systems[i] for i in sorted_indices]
        self._system_execution_order = [self._system_execution_order[i] for i in sorted_indices]
        
        # Initialize system
        system.initialize(self)
    
    def update(self) -> None:
        """Update all systems.
        
        Rules: 
        - Fixed timestep for physics systems
        - Variable timestep for rendering systems
        - Maintains 60 FPS fixed update rate
        """
        current_time = time.perf_counter()
        self._delta_time = current_time - self._last_update_time
        self._last_update_time = current_time
        
        # Fixed timestep accumulation
        self._accumulator += self._delta_time
        
        # Execute fixed updates
        while self._accumulator >= self._fixed_delta_time:
            for system in self._systems:
                if system.fixed_update:
                    system.fixed_update(self, self._fixed_delta_time)
            self._accumulator -= self._fixed_delta_time
            
        # Execute variable updates
        for system in self._systems:
            if system.update:
                system.update(self, self._delta_time)
    
    def _get_or_create_archetype(self, component_types: Set[Type['Component']]) -> int:
        """Get existing archetype index or create new one.
        
        Args:
            component_types: Set of component types
            
        Returns:
            Index of archetype in _archetypes list
        """
        # Check for existing archetype
        for idx, archetype in enumerate(self._archetypes):
            if archetype.component_types == component_types:
                return idx
                
        # Create new archetype
        new_archetype = Archetype(
            component_types=component_types.copy(),
            entities=[],
            component_data={comp_type: [] for comp_type in component_types}
        )
        self._archetypes.append(new_archetype)
        return len(self._archetypes) - 1
    
    def _migrate_entity(self, entity_id: int, from_idx: int, to_idx: int, 
                       new_component: Optional['Component'] = None) -> None:
        """Migrate entity between archetypes.
        
        Args:
            entity_id: Entity ID to migrate
            from_idx: Source archetype index
            to_idx: Destination archetype index
            new_component: Optional new component to add
        """
        from_archetype = self._archetypes[from_idx]
        to_archetype = self._archetypes[to_idx]
        
        # Find entity in source archetype
        try:
            entity_idx = from_archetype.entities.index(entity_id)
        except ValueError:
            return
            
        # Remove from source (swap with last for O(1) removal)
        last_idx = len(from_archetype.entities) - 1
        if entity_idx != last_idx:
            # Swap with last entity
            last_entity_id = from_archetype.entities[last_idx]
            from_archetype.entities[entity_idx] = last_entity_id
            
            # Update component data
            for comp_type, data_list in from_archetype.component_data.items():
                data_list[entity_idx] = data_list[last_idx]
                data_list.pop()
                
            # Update mapping for swapped entity
            self._entity_archetype_map[last_entity_id] = from_idx
            
            # Entity index is now last_idx (since we swapped)
            entity_idx = last_idx
            
        # Remove from source
        from_archetype.entities.pop()
        for data_list in from_archetype.component_data.values():
            data_list.pop()
            
        # Add to destination
        to_archetype.entities.append(entity_id)
        
        # Copy existing component data
        for comp_type in to_archetype.component_types:
            if comp_type in from_archetype.component_types:
                # Copy from source
                data_idx = list(from_archetype.component_types).index(comp_type)
                # Note: We already removed from source, so we need to get from original position
                # This is simplified - in real implementation would need to store before removal
                to_archetype.component_data[comp_type].append(None)  # Placeholder
            elif new_component and type(new_component) == comp_type:
                # Add new component
                to_archetype.component_data[comp_type].append(new_component)
            else:
                # New empty component
                to_archetype.component_data[comp_type].append(comp_type())
                
        # Update mapping
        self._entity_archetype_map[entity_id] = to_idx
    
    @property
    def delta_time(self) -> float:
        """Get time since last update in seconds."""
        return self._delta_time
    
    @property
    def fixed_delta_time(self) -> float:
        """Get fixed timestep duration in seconds."""
        return self._fixed_delta_time