"""
Animation system for 2D RPG.
Handles character movement, combat animations, and sprite sheet management.
"""

import pygame
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import time


class AnimationState(Enum):
    """Animation states for characters."""
    IDLE = "idle"
    WALK = "walk"
    RUN = "run"
    ATTACK = "attack"
    HURT = "hurt"
    DEATH = "death"
    CAST = "cast"
    INTERACT = "interact"


@dataclass
class AnimationFrame:
    """Single frame in an animation sequence."""
    texture_id: str
    duration: float  # in seconds
    offset: Tuple[float, float] = (0, 0)  # sprite offset
    flip_x: bool = False
    flip_y: bool = False
    hitbox: Optional[pygame.Rect] = None  # for combat frames
    event: Optional[str] = None  # event to trigger on this frame


@dataclass
class Animation:
    """Complete animation sequence."""
    name: str
    frames: List[AnimationFrame]
    loop: bool = True
    speed: float = 1.0  # playback speed multiplier
    priority: int = 0  # higher priority animations override lower ones
    
    def __post_init__(self):
        self.total_duration = sum(frame.duration for frame in self.frames)
        self.frame_count = len(self.frames)


class AnimationController:
    """
    Controls animation playback for a sprite.
    Manages state transitions and blending.
    """
    
    def __init__(self, sprite_renderer, sprite_id: str):
        """
        Initialize animation controller.
        
        Args:
            sprite_renderer: SpriteRenderer instance
            sprite_id: ID of sprite to animate
        """
        self.sprite_renderer = sprite_renderer
        self.sprite_id = sprite_id
        
        # Animation state
        self.animations: Dict[str, Animation] = {}
        self.current_animation: Optional[Animation] = None
        self.current_frame_index = 0
        self.current_frame_time = 0.0
        self.is_playing = False
        
        # State machine
        self.state = AnimationState.IDLE
        self.next_state: Optional[AnimationState] = None
        self.state_transition_time = 0.0
        self.state_blend_duration = 0.1  # seconds
        
        # Callbacks
        self.on_frame_event: Dict[str, List[Callable]] = {}
        self.on_animation_end: List[Callable] = []
        
        # Performance tracking
        self.frame_updates = 0
        self.state_changes = 0
    
    def add_animation(self, animation: Animation):
        """
        Add an animation to the controller.
        
        Args:
            animation: Animation to add
        """
        self.animations[animation.name] = animation
    
    def play(self, animation_name: str, force_restart: bool = False):
        """
        Play an animation.
        
        Args:
            animation_name: Name of animation to play
            force_restart: If True, restart even if already playing
        """
        if animation_name not in self.animations:
            print(f"Animation not found: {animation_name}")
            return
        
        animation = self.animations[animation_name]
        
        # Check if already playing this animation
        if (self.current_animation == animation and 
            not force_restart and self.is_playing):
            return
        
        self.current_animation = animation
        self.current_frame_index = 0
        self.current_frame_time = 0.0
        self.is_playing = True
        
        # Apply first frame
        self._apply_current_frame()
    
    def play_state(self, state: AnimationState, force: bool = False):
        """
        Play animation for a state.
        
        Args:
            state: Animation state to play
            force: Force state change even if already in this state
        """
        if not force and self.state == state:
            return
        
        self.next_state = state
        self.state_transition_time = self.state_blend_duration
        self.state_changes += 1
    
    def update(self, delta_time: float):
        """
        Update animation playback.
        
        Args:
            delta_time: Time since last update in seconds
        """
        if not self.is_playing or not self.current_animation:
            return
        
        # Update state transition
        if self.next_state and self.state_transition_time > 0:
            self.state_transition_time -= delta_time
            if self.state_transition_time <= 0:
                self.state = self.next_state
                self.next_state = None
                self.play(self.state.value)
        
        # Update current frame
        self.current_frame_time += delta_time * self.current_animation.speed
        current_frame = self.current_animation.frames[self.current_frame_index]
        
        # Check if frame duration elapsed
        if self.current_frame_time >= current_frame.duration:
            self.current_frame_time = 0.0
            self.current_frame_index += 1
            self.frame_updates += 1
            
            # Check if animation ended
            if self.current_frame_index >= len(self.current_animation.frames):
                if self.current_animation.loop:
                    self.current_frame_index = 0
                else:
                    self.is_playing = False
                    self._trigger_animation_end()
                    return
            
            # Apply new frame
            self._apply_current_frame()
    
    def _apply_current_frame(self):
        """Apply current frame to sprite."""
        if not self.current_animation:
            return
        
        frame = self.current_animation.frames[self.current_frame_index]
        
        # Update sprite properties
        self.sprite_renderer.update_sprite(
            self.sprite_id,
            texture_id=frame.texture_id,
            flip_x=frame.flip_x,
            flip_y=frame.flip_y
        )
        
        # Trigger frame event if any
        if frame.event and frame.event in self.on_frame_event:
            for callback in self.on_frame_event[frame.event]:
                callback()
    
    def _trigger_animation_end(self):
        """Trigger animation end callbacks."""
        for callback in self.on_animation_end:
            callback()
    
    def pause(self):
        """Pause animation playback."""
        self.is_playing = False
    
    def resume(self):
        """Resume animation playback."""
        self.is_playing = True
    
    def stop(self):
        """Stop animation playback."""
        self.is_playing = False
        self.current_animation = None
        self.current_frame_index = 0
        self.current_frame_time = 0.0
    
    def register_frame_event(self, event_name: str, callback: Callable):
        """
        Register callback for frame event.
        
        Args:
            event_name: Name of frame event
            callback: Function to call when event triggers
        """
        if event_name not in self.on_frame_event:
            self.on_frame_event[event_name] = []
        self.on_frame_event[event_name].append(callback)
    
    def register_animation_end(self, callback: Callable):
        """
        Register callback for animation end.
        
        Args:
            callback: Function to call when animation ends
        """
        self.on_animation_end.append(callback)
    
    def get_current_frame(self) -> Optional[AnimationFrame]:
        """
        Get current animation frame.
        
        Returns:
            Current frame or None if no animation playing
        """
        if (not self.current_animation or 
            self.current_frame_index >= len(self.current_animation.frames)):
            return None
        
        return self.current_animation.frames[self.current_frame_index]
    
    def get_progress(self) -> float:
        """
        Get animation progress (0-1).
        
        Returns:
            Progress through current animation
        """
        if not self.current_animation:
            return 0.0
        
        total_time = self.current_animation.total_duration
        if total_time == 0:
            return 0.0
        
        elapsed = sum(frame.duration for frame in 
                     self.current_animation.frames[:self.current_frame_index])
        elapsed += self.current_frame_time
        
        return elapsed / total_time
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get animation statistics.
        
        Returns:
            Dictionary with animation metrics
        """
        return {
            'current_state': self.state.value,
            'current_animation': self.current_animation.name if self.current_animation else None,
            'frame_index': self.current_frame_index,
            'is_playing': self.is_playing,
            'frame_updates': self.frame_updates,
            'state_changes': self.state_changes,
            'animations_loaded': len(self.animations)
        }


class AnimationSystem:
    """
    Manages multiple animation controllers.
    Provides batch updating and resource management.
    """
    
    def __init__(self, sprite_renderer):
        """
        Initialize animation system.
        
        Args:
            sprite_renderer: SpriteRenderer instance
        """
        self.sprite_renderer = sprite_renderer
        self.controllers: Dict[str, AnimationController] = {}
        self.animation_templates: Dict[str, Animation] = {}
        
        # Performance tracking
        self.updates_per_frame = 0
        self.active_controllers = 0
    
    def create_controller(self, sprite_id: str, 
                         controller_id: Optional[str] = None) -> str:
        """
        Create animation controller for a sprite.
        
        Args:
            sprite_id: ID of sprite to animate
            controller_id: Optional custom ID
            
        Returns:
            Controller ID
        """
        if controller_id is None:
            controller_id = f"anim_{sprite_id}_{len(self.controllers)}"
        
        controller = AnimationController(self.sprite_renderer, sprite_id)
        self.controllers[controller_id] = controller
        
        # Load template animations
        for name, anim in self.animation_templates.items():
            controller.add_animation(anim)
        
        return controller_id
    
    def register_template(self, animation: Animation):
        """
        Register animation template for reuse.
        
        Args:
            animation: Animation template
        """
        self.animation_templates[animation.name] = animation
        
        # Add to existing controllers
        for controller in self.controllers.values():
            controller.add_animation(animation)
    
    def update_all(self, delta_time: float):
        """
        Update all animation controllers.
        
        Args:
            delta_time: Time since last update in seconds
        """
        self.updates_per_frame = 0
        self.active_controllers = 0
        
        for controller in self.controllers.values():
            if controller.is_playing:
                controller.update(delta_time)
                self.updates_per_frame += 1
                self.active_controllers += 1
    
    def get_controller(self, controller_id: str) -> Optional[AnimationController]:
        """
        Get animation controller by ID.
        
        Args:
            controller_id: Controller ID
            
        Returns:
            AnimationController or None if not found
        """
        return self.controllers.get(controller_id)
    
    def remove_controller(self, controller_id: str):
        """
        Remove animation controller.
        
        Args:
            controller_id: Controller ID to remove
        """
        if controller_id in self.controllers:
            del self.controllers[controller_id]
    
    def create_simple_animation(self, name: str, texture_ids: List[str], 
                               frame_duration: float = 0.1, 
                               loop: bool = True) -> Animation:
        """
        Create simple animation from texture IDs.
        
        Args:
            name: Animation name
            texture_ids: List of texture IDs for frames
            frame_duration: Duration of each frame in seconds
            loop: Whether animation loops
            
        Returns:
            Created Animation
        """
        frames = []
        for texture_id in texture_ids:
            frames.append(AnimationFrame(
                texture_id=texture_id,
                duration=frame_duration
            ))
        
        return Animation(name=name, frames=frames, loop=loop)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get animation system statistics.
        
        Returns:
            Dictionary with system metrics
        """
        return {
            'total_controllers': len(self.controllers),
            'active_controllers': self.active_controllers,
            'updates_per_frame': self.updates_per_frame,
            'animation_templates': len(self.animation_templates),
            'total_animations': sum(len(c.animations) for c in self.controllers.values())
        }
    
    def cleanup(self):
        """Clean up animation resources."""
        self.controllers.clear()
        self.animation_templates.clear()
        print("AnimationSystem cleaned up")