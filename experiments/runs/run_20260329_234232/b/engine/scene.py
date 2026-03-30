"""
Scene management system.
Manages game scenes with hierarchical scene graphs and scene transitions.
"""

from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
import time
from .ecs import World, Entity, System


@dataclass
class SceneNode:
    """Node in a scene graph representing an entity with transform hierarchy."""
    
    entity: Entity
    parent: Optional['SceneNode'] = None
    children: List['SceneNode'] = field(default_factory=list)
    local_transform: Any = None  # Will be set by transform component
    world_transform: Any = None  # Will be set by transform component
    enabled: bool = True
    visible: bool = True
    
    def add_child(self, child: 'SceneNode'):
        """Add a child node to this node."""
        if child.parent is not None:
            child.parent.remove_child(child)
        
        child.parent = self
        self.children.append(child)
    
    def remove_child(self, child: 'SceneNode'):
        """Remove a child node from this node."""
        if child in self.children:
            child.parent = None
            self.children.remove(child)
    
    def get_world_position(self) -> tuple[float, float, float]:
        """
        Get world position by traversing parent hierarchy.
        
        Returns:
            Tuple of (x, y, z) world coordinates
        """
        # This would be calculated from local_transform and parent transforms
        # For now, return placeholder
        return (0.0, 0.0, 0.0)


class Scene:
    """
    Represents a game scene with its own entities, systems, and resources.
    """
    
    def __init__(self, name: str):
        """
        Initialize a scene.
        
        Args:
            name: Name of the scene
        """
        self.name = name
        self.world = World()
        self.scene_graph: Dict[Entity, SceneNode] = {}
        self.root_nodes: List[SceneNode] = []
        
        # Scene state
        self.is_loaded = False
        self.is_active = False
        self.is_paused = False
        
        # Scene resources
        self.resources: Dict[str, Any] = {}
        
        # Callbacks
        self.on_load_callbacks: List[Callable[[], None]] = []
        self.on_unload_callbacks: List[Callable[[], None]] = []
        self.on_activate_callbacks: List[Callable[[], None]] = []
        self.on_deactivate_callbacks: List[Callable[[], None]] = []
    
    def load(self):
        """Load the scene and its resources."""
        if self.is_loaded:
            return
        
        print(f"Loading scene: {self.name}")
        
        # Load scene resources
        self._load_resources()
        
        # Create scene entities
        self._create_entities()
        
        # Set up scene systems
        self._setup_systems()
        
        self.is_loaded = True
        
        # Call load callbacks
        for callback in self.on_load_callbacks:
            callback()
    
    def unload(self):
        """Unload the scene and free its resources."""
        if not self.is_loaded:
            return
        
        print(f"Unloading scene: {self.name}")
        
        # Call deactivate first if active
        if self.is_active:
            self.deactivate()
        
        # Call unload callbacks
        for callback in self.on_unload_callbacks:
            callback()
        
        # Clear scene graph
        self.scene_graph.clear()
        self.root_nodes.clear()
        
        # Clear world
        self.world.clear()
        
        # Free resources
        self._unload_resources()
        
        self.is_loaded = False
    
    def activate(self):
        """Activate the scene (make it the current scene)."""
        if not self.is_loaded:
            self.load()
        
        if self.is_active:
            return
        
        print(f"Activating scene: {self.name}")
        self.is_active = True
        self.is_paused = False
        
        # Call activate callbacks
        for callback in self.on_activate_callbacks:
            callback()
    
    def deactivate(self):
        """Deactivate the scene."""
        if not self.is_active:
            return
        
        print(f"Deactivating scene: {self.name}")
        self.is_active = False
        
        # Call deactivate callbacks
        for callback in self.on_deactivate_callbacks:
            callback()
    
    def pause(self):
        """Pause the scene."""
        if self.is_paused or not self.is_active:
            return
        
        print(f"Pausing scene: {self.name}")
        self.is_paused = True
    
    def resume(self):
        """Resume the scene from pause."""
        if not self.is_paused or not self.is_active:
            return
        
        print(f"Resuming scene: {self.name}")
        self.is_paused = False
    
    def _load_resources(self):
        """Load scene-specific resources."""
        # To be implemented by derived scenes
        pass
    
    def _unload_resources(self):
        """Unload scene-specific resources."""
        # To be implemented by derived scenes
        pass
    
    def _create_entities(self):
        """Create scene entities."""
        # To be implemented by derived scenes
        pass
    
    def _setup_systems(self):
        """Set up scene systems."""
        # To be implemented by derived scenes
        pass
    
    def create_entity(self, name: str = "") -> Entity:
        """
        Create a new entity in this scene.
        
        Args:
            name: Optional name for the entity
            
        Returns:
            The created entity
        """
        entity = self.world.create_entity()
        
        # Create scene node
        node = SceneNode(entity=entity)
        self.scene_graph[entity] = node
        self.root_nodes.append(node)
        
        return entity
    
    def destroy_entity(self, entity: Entity):
        """
        Destroy an entity in this scene.
        
        Args:
            entity: The entity to destroy
        """
        if entity in self.scene_graph:
            node = self.scene_graph[entity]
            
            # Remove from parent if has one
            if node.parent:
                node.parent.remove_child(node)
            
            # Remove children
            for child in list(node.children):
                self.destroy_entity(child.entity)
            
            # Remove from scene graph
            del self.scene_graph[entity]
            if node in self.root_nodes:
                self.root_nodes.remove(node)
        
        # Destroy in world
        self.world.destroy_entity(entity)
    
    def add_system(self, system: System):
        """
        Add a system to the scene.
        
        Args:
            system: The system to add
        """
        self.world.add_system(system)
    
    def remove_system(self, system: System):
        """
        Remove a system from the scene.
        
        Args:
            system: The system to remove
        """
        self.world.remove_system(system)
    
    def update(self, dt: float):
        """
        Update the scene.
        
        Args:
            dt: Delta time in seconds
        """
        if not self.is_active or self.is_paused:
            return
        
        self.world.update(dt)
    
    def fixed_update(self, dt: float):
        """
        Fixed update for the scene.
        
        Args:
            dt: Fixed delta time in seconds
        """
        if not self.is_active or self.is_paused:
            return
        
        self.world.fixed_update(dt)
    
    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """
        Get an entity by name.
        
        Args:
            name: Name of the entity
            
        Returns:
            The entity, or None if not found
        """
        # This would require storing entity names
        # For now, return None
        return None
    
    def get_render_data(self) -> List[Any]:
        """
        Get render data from the scene.
        
        Returns:
            List of renderable entities
        """
        # This would collect render data from render systems
        # For now, return empty list
        return []
    
    def on_load(self, callback: Callable[[], None]):
        """
        Register a callback for when the scene loads.
        
        Args:
            callback: Function to call when scene loads
        """
        self.on_load_callbacks.append(callback)
    
    def on_unload(self, callback: Callable[[], None]):
        """
        Register a callback for when the scene unloads.
        
        Args:
            callback: Function to call when scene unloads
        """
        self.on_unload_callbacks.append(callback)
    
    def on_activate(self, callback: Callable[[], None]):
        """
        Register a callback for when the scene activates.
        
        Args:
            callback: Function to call when scene activates
        """
        self.on_activate_callbacks.append(callback)
    
    def on_deactivate(self, callback: Callable[[], None]):
        """
        Register a callback for when the scene deactivates.
        
        Args:
            callback: Function to call when scene deactivates
        """
        self.on_deactivate_callbacks.append(callback)


class SceneManager:
    """
    Manages multiple scenes and scene transitions.
    """
    
    def __init__(self):
        """Initialize the scene manager."""
        self.scenes: Dict[str, Scene] = {}
        self.current_scene: Optional[Scene] = None
        self.next_scene: Optional[Scene] = None
        
        # Scene transition state
        self.is_transitioning = False
        self.transition_start_time = 0.0
        self.transition_duration = 0.5  # seconds
        self.transition_progress = 0.0
        
        # Scene stack for nested scenes (e.g., pause menu over gameplay)
        self.scene_stack: List[Scene] = []
        
        # Global systems (active across all scenes)
        self.global_systems: List[System] = []
    
    def register_scene(self, scene: Scene):
        """
        Register a scene with the manager.
        
        Args:
            scene: The scene to register
        """
        self.scenes[scene.name] = scene
        print(f"Registered scene: {scene.name}")
    
    def unregister_scene(self, scene_name: str):
        """
        Unregister a scene from the manager.
        
        Args:
            scene_name: Name of the scene to unregister
        """
        if scene_name in self.scenes:
            scene = self.scenes[scene_name]
            
            # If this is the current scene, deactivate it
            if self.current_scene == scene:
                self.current_scene.deactivate()
                self.current_scene = None
            
            # Unload the scene
            scene.unload()
            
            # Remove from scenes
            del self.scenes[scene_name]
            print(f"Unregistered scene: {scene_name}")
    
    def switch_scene(self, scene_name: str, transition: bool = True):
        """
        Switch to a different scene.
        
        Args:
            scene_name: Name of the scene to switch to
            transition: Whether to use a transition
        """
        if scene_name not in self.scenes:
            print(f"Scene not found: {scene_name}")
            return
        
        if self.current_scene and self.current_scene.name == scene_name:
            return  # Already on this scene
        
        self.next_scene = self.scenes[scene_name]
        
        if transition:
            self.start_transition()
        else:
            self._complete_scene_switch()
    
    def start_transition(self):
        """Start a scene transition."""
        if not self.next_scene or self.is_transitioning:
            return
        
        self.is_transitioning = True
        self.transition_start_time = time.time()
        self.transition_progress = 0.0
        
        print(f"Starting transition to: {self.next_scene.name}")
    
    def _complete_scene_switch(self):
        """Complete the scene switch."""
        if not self.next_scene:
            return
        
        # Deactivate current scene
        if self.current_scene:
            self.current_scene.deactivate()
        
        # Activate next scene
        self.current_scene = self.next_scene
        self.current_scene.activate()
        
        # Clear next scene
        self.next_scene = None
        
        print(f"Switched to scene: {self.current_scene.name}")
    
    def push_scene(self, scene_name: str):
        """
        Push a scene onto the stack (e.g., pause menu).
        
        Args:
            scene_name: Name of the scene to push
        """
        if scene_name not in self.scenes:
            print(f"Scene not found: {scene_name}")
            return
        
        scene = self.scenes[scene_name]
        
        # Pause current scene if any
        if self.current_scene:
            self.current_scene.pause()
            self.scene_stack.append(self.current_scene)
        
        # Activate new scene
        self.current_scene = scene
        self.current_scene.activate()
        
        print(f"Pushed scene: {scene_name}")
    
    def pop_scene(self):
        """Pop the top scene from the stack."""
        if not self.scene_stack:
            return
        
        # Deactivate current scene
        if self.current_scene:
            self.current_scene.deactivate()
        
        # Pop previous scene from stack
        self.current_scene = self.scene_stack.pop()
        
        # Resume previous scene
        self.current_scene.resume()
        
        print(f"Popped scene, returned to: {self.current_scene.name}")
    
    def update(self, dt: float):
        """
        Update the scene manager.
        
        Args:
            dt: Delta time in seconds
        """
        # Update transition
        if self.is_transitioning:
            current_time = time.time()
            elapsed = current_time - self.transition_start_time
            self.transition_progress = min(elapsed / self.transition_duration, 1.0)
            
            if self.transition_progress >= 1.0:
                self.is_transitioning = False
                self._complete_scene_switch()
        
        # Update global systems
        for system in self.global_systems:
            if system.enabled:
                system.update(dt)
        
        # Update current scene
        if self.current_scene:
            self.current_scene.update(dt)
    
    def fixed_update(self, dt: float):
        """
        Fixed update for the scene manager.
        
        Args:
            dt: Fixed delta time in seconds
        """
        # Update global systems
        for system in self.global_systems:
            if system.enabled:
                system.fixed_update(dt)
        
        # Update current scene
        if self.current_scene:
            self.current_scene.fixed_update(dt)
    
    def variable_update(self, dt: float):
        """
        Variable update for interpolation.
        
        Args:
            dt: Variable delta time
        """
        # Update current scene for interpolation
        if self.current_scene:
            # Scene could have interpolation systems
            pass
    
    def get_current_scene(self) -> Optional[Scene]:
        """
        Get the current active scene.
        
        Returns:
            The current scene, or None if no scene is active
        """
        return self.current_scene
    
    def get_scene(self, scene_name: str) -> Optional[Scene]:
        """
        Get a scene by name.
        
        Args:
            scene_name: Name of the scene
            
        Returns:
            The scene, or None if not found
        """
        return self.scenes.get(scene_name)
    
    def add_global_system(self, system: System):
        """
        Add a global system (active across all scenes).
        
        Args:
            system: The system to add
        """
        self.global_systems.append(system)
    
    def remove_global_system(self, system: System):
        """
        Remove a global system.
        
        Args:
            system: The system to remove
        """
        if system in self.global_systems:
            self.global_systems.remove(system)
    
    def is_in_transition(self) -> bool:
        """
        Check if a scene transition is in progress.
        
        Returns:
            True if transitioning
        """
        return self.is_transitioning
    
    def get_transition_progress(self) -> float:
        """
        Get current transition progress.
        
        Returns:
            Progress from 0.0 to 1.0
        """
        return self.transition_progress
    
    def shutdown(self):
        """Shutdown the scene manager."""
        # Deactivate current scene
        if self.current_scene:
            self.current_scene.deactivate()
        
        # Unload all scenes
        for scene in list(self.scenes.values()):
            scene.unload()
        
        # Clear all data
        self.scenes.clear()
        self.current_scene = None
        self.next_scene = None
        self.scene_stack.clear()
        self.global_systems.clear()