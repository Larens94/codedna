"""systems.py — ECS systems for rendering.

exports: RenderingSystem, ParticleSystem, UISystem
used_by: engine/world.py → system updates
rules:   Systems contain logic, no persistent state between frames
agent:   GraphicsSpecialist | 2024-03-29 | Created rendering systems for ECS
"""

import pygame
import glm
from typing import Set, Type, Optional, List, Dict, Any
import logging
from engine.system import System
from engine.world import World
from .components import Sprite, Transform, CameraFollow, ParticleEmitter, UIElement, RenderLayer
from .pygame_renderer import PygameRenderer

logger = logging.getLogger(__name__)


class RenderingSystem(System):
    """Rendering system for drawing sprites with ECS integration.
    
    Queries entities with Sprite and Transform components,
    batches them by texture, and renders through PygameRenderer.
    """
    
    def __init__(self, renderer: PygameRenderer):
        """Initialize rendering system.
        
        Args:
            renderer: PygameRenderer instance for actual drawing
        """
        super().__init__(required_components={Sprite, Transform})
        self._renderer = renderer
        self._texture_cache: Dict[str, pygame.Surface] = {}
        
    def update(self, world: World, delta_time: float) -> None:
        """Update and render all sprites.
        
        Args:
            world: ECS world to query
            delta_time: Time since last frame
        """
        if not self._renderer.initialized:
            return
        
        # Begin frame
        if not self._renderer.begin_frame():
            return
        
        # Query all entities with Sprite and Transform components
        entities = self.query_entities(world)
        
        # Process each entity
        for entity in entities:
            sprite = entity.get_component(Sprite)
            transform = entity.get_component(Transform)
            
            if not sprite.visible:
                continue
            
            # Update animation if needed
            if sprite.animation_speed > 0:
                self._update_animation(sprite, delta_time)
            
            # Load texture if not loaded
            if not sprite._texture_loaded and sprite.texture_path:
                self._load_texture(sprite)
            
            if sprite._texture is None:
                continue
            
            # Get 2D position from transform
            pos_2d = transform.get_position_2d()
            
            # Calculate scale from transform
            scale = max(transform.scale.x, transform.scale.y)
            
            # Calculate rotation from transform (using Z rotation for 2D)
            rotation = transform.rotation.z
            
            # Prepare source rectangle
            source_rect = None
            if sprite.texture_rect:
                source_rect = pygame.Rect(*sprite.texture_rect)
            
            # Queue sprite for rendering
            self._renderer.draw_sprite(
                texture=sprite._texture,
                position=pos_2d,
                source_rect=source_rect,
                scale=scale,
                rotation=rotation,
                layer=sprite.layer,
                blend_mode=sprite.blend_mode
            )
        
        # End frame (rendering happens here)
        self._renderer.end_frame()
    
    def _update_animation(self, sprite: Sprite, delta_time: float) -> None:
        """Update sprite animation.
        
        Args:
            sprite: Sprite component to update
            delta_time: Time since last frame
        """
        sprite.frame_time += delta_time
        frame_duration = 1.0 / sprite.animation_speed
        
        while sprite.frame_time >= frame_duration:
            sprite.frame_time -= frame_duration
            sprite.current_frame += 1
            
            # Handle frame bounds
            # Note: In a full implementation, this would use an animation atlas
            # For now, just reset to frame 0
            if sprite.current_frame >= 4:  # Arbitrary frame count
                if sprite.looping:
                    sprite.current_frame = 0
                else:
                    sprite.current_frame = 3  # Stay on last frame
    
    def _load_texture(self, sprite: Sprite) -> None:
        """Load texture for sprite.
        
        Args:
            sprite: Sprite component needing texture
        """
        if sprite.texture_path in self._texture_cache:
            sprite._texture = self._texture_cache[sprite.texture_path]
            sprite._texture_loaded = True
            return
        
        # Load through renderer
        texture = self._renderer.load_texture(sprite.texture_path)
        if texture:
            sprite._texture = texture
            sprite._texture_loaded = True
            self._texture_cache[sprite.texture_path] = texture
            logger.debug(f"Loaded texture for sprite: {sprite.texture_path}")
    
    def on_entity_removed(self, entity: 'Entity') -> None:
        """Clean up when an entity with sprite is removed.
        
        Args:
            entity: Removed entity
        """
        sprite = entity.get_component(Sprite)
        if sprite and sprite.texture_path:
            # Release texture reference
            self._renderer.release_texture(sprite.texture_path)
            
            # Remove from cache if no other references
            if sprite.texture_path in self._texture_cache:
                # Check if this was the last reference
                # In a full implementation, we'd track references
                del self._texture_cache[sprite.texture_path]
    
    def shutdown(self) -> None:
        """Clean up texture cache."""
        self._texture_cache.clear()
        logger.debug("Rendering system shutdown complete")


class ParticleSystem(System):
    """Particle system for visual effects."""
    
    def __init__(self, renderer: PygameRenderer):
        """Initialize particle system.
        
        Args:
            renderer: PygameRenderer for drawing particles
        """
        super().__init__(required_components={ParticleEmitter, Transform})
        self._renderer = renderer
        self._particles: Dict[int, List[Dict[str, Any]]] = {}  # entity_id -> particles
        
    def update(self, world: World, delta_time: float) -> None:
        """Update and render particles.
        
        Args:
            world: ECS world to query
            delta_time: Time since last frame
        """
        entities = self.query_entities(world)
        
        for entity in entities:
            emitter = entity.get_component(ParticleEmitter)
            transform = entity.get_component(Transform)
            
            if not emitter.emitting and emitter._particle_count == 0:
                continue
            
            # Get or create particle list for this entity
            entity_id = id(entity)
            if entity_id not in self._particles:
                self._particles[entity_id] = []
            
            particles = self._particles[entity_id]
            
            # Emit new particles
            self._emit_particles(emitter, transform, particles, delta_time)
            
            # Update existing particles
            self._update_particles(emitter, particles, delta_time)
            
            # Render particles
            self._render_particles(emitter, transform, particles)
            
            # Remove dead particles
            particles[:] = [p for p in particles if p['life'] > 0]
            emitter._particle_count = len(particles)
    
    def _emit_particles(self, emitter: ParticleEmitter, transform: Transform,
                       particles: List[Dict[str, Any]], delta_time: float) -> None:
        """Emit new particles from emitter.
        
        Args:
            emitter: Particle emitter component
            transform: Transform component for position
            particles: List of particles to add to
            delta_time: Time since last frame
        """
        if not emitter.emitting:
            return
        
        # Handle burst emission
        if emitter.burst_count > 0:
            for _ in range(emitter.burst_count):
                if emitter._particle_count < emitter._max_particles:
                    self._create_particle(emitter, transform, particles)
            emitter.burst_count = 0
        
        # Handle continuous emission
        emitter._time_since_emission += delta_time
        emission_interval = 1.0 / emitter.emission_rate
        
        while (emitter._time_since_emission >= emission_interval and 
               emitter._particle_count < emitter._max_particles):
            emitter._time_since_emission -= emission_interval
            self._create_particle(emitter, transform, particles)
    
    def _create_particle(self, emitter: ParticleEmitter, transform: Transform,
                        particles: List[Dict[str, Any]]) -> None:
        """Create a new particle.
        
        Args:
            emitter: Particle emitter component
            transform: Transform component for position
            particles: List to add particle to
        """
        import random
        
        # Calculate emission position
        pos = transform.get_position_2d()
        if emitter.emission_radius > 0:
            angle = random.uniform(0, 360)
            radius = random.uniform(0, emitter.emission_radius)
            pos = (
                pos[0] + radius * random.uniform(-1, 1),
                pos[1] + radius * random.uniform(-1, 1)
            )
        
        # Calculate emission angle and velocity
        angle = random.uniform(*emitter.emission_angle)
        speed = random.uniform(*emitter.particle_speed)
        rad = glm.radians(angle)
        velocity = glm.vec2(
            speed * glm.cos(rad),
            speed * glm.sin(rad)
        )
        
        # Create particle
        particle = {
            'position': glm.vec2(*pos),
            'velocity': velocity,
            'life': random.uniform(*emitter.particle_lifetime),
            'max_life': 0,  # Will be set below
            'size': random.uniform(*emitter.particle_size),
            'color_start': emitter.particle_color_start,
            'color_end': emitter.particle_color_end,
            'age': 0.0
        }
        particle['max_life'] = particle['life']
        
        particles.append(particle)
        emitter._particle_count += 1
    
    def _update_particles(self, emitter: ParticleEmitter, 
                         particles: List[Dict[str, Any]], delta_time: float) -> None:
        """Update particle physics and lifetime.
        
        Args:
            emitter: Particle emitter component
            particles: List of particles to update
            delta_time: Time since last frame
        """
        for particle in particles:
            # Update lifetime
            particle['life'] -= delta_time
            particle['age'] += delta_time
            
            if particle['life'] <= 0:
                continue
            
            # Update physics
            particle['velocity'] += emitter.gravity * delta_time
            particle['velocity'] *= emitter.damping ** delta_time
            particle['position'] += particle['velocity'] * delta_time
            
            # Update size (optional: could shrink/grow over time)
            # particle['size'] *= 0.99  # Example: shrink slightly
    
    def _render_particles(self, emitter: ParticleEmitter, transform: Transform,
                         particles: List[Dict[str, Any]]) -> None:
        """Render particles.
        
        Args:
            emitter: Particle emitter component
            transform: Transform component (for reference)
            particles: List of particles to render
        """
        for particle in particles:
            if particle['life'] <= 0:
                continue
            
            # Calculate color interpolation
            life_ratio = 1.0 - (particle['life'] / particle['max_life'])
            color = self._interpolate_color(
                particle['color_start'],
                particle['color_end'],
                life_ratio
            )
            
            # Create particle surface (in a real implementation, would use texture)
            # For now, draw as circle
            size = int(particle['size'])
            if size <= 0:
                continue
            
            # Note: In a full implementation, we'd create a texture or use
            # Pygame's drawing functions. For now, this is a placeholder.
            # Actual rendering would happen in the renderer.
            
            # For demonstration, we'll just pass the position
            # A real implementation would create a sprite for each particle
            pass
    
    def _interpolate_color(self, start: Tuple[int, int, int, int],
                          end: Tuple[int, int, int, int],
                          t: float) -> Tuple[int, int, int, int]:
        """Interpolate between two colors.
        
        Args:
            start: Start color (RGBA)
            end: End color (RGBA)
            t: Interpolation factor (0-1)
            
        Returns:
            Interpolated color
        """
        t = max(0.0, min(1.0, t))
        return (
            int(start[0] + (end[0] - start[0]) * t),
            int(start[1] + (end[1] - start[1]) * t),
            int(start[2] + (end[2] - start[2]) * t),
            int(start[3] + (end[3] - start[3]) * t)
        )
    
    def on_entity_removed(self, entity: 'Entity') -> None:
        """Clean up particles when entity is removed.
        
        Args:
            entity: Removed entity
        """
        entity_id = id(entity)
        if entity_id in self._particles:
            del self._particles[entity_id]
    
    def shutdown(self) -> None:
        """Clean up all particles."""
        self._particles.clear()
        logger.debug("Particle system shutdown complete")


class UISystem(System):
    """UI rendering system."""
    
    def __init__(self, renderer: PygameRenderer):
        """Initialize UI system.
        
        Args:
            renderer: PygameRenderer for drawing UI
        """
        super().__init__(required_components={UIElement})
        self._renderer = renderer
        
    def update(self, world: World, delta_time: float) -> None:
        """Update and render UI elements.
        
        Args:
            world: ECS world to query
            delta_time: Time since last frame
        """
        if not self._renderer.initialized or not self._renderer.screen:
            return
        
        entities = self.query_entities(world)
        
        for entity in entities:
            ui_element = entity.get_component(UIElement)
            
            if not ui_element.visible:
                continue
            
            # Render UI element based on type
            if ui_element.element_type == "panel":
                self._render_panel(ui_element)
            elif ui_element.element_type == "button":
                self._render_button(ui_element)
            elif ui_element.element_type == "label":
                self._render_label(ui_element)
            elif ui_element.element_type == "progress_bar":
                self._render_progress_bar(ui_element)
    
    def _render_panel(self, element: UIElement) -> None:
        """Render a panel UI element.
        
        Args:
            element: UIElement component
        """
        screen = self._renderer.screen
        if not screen:
            return
        
        # Draw background
        rect = pygame.Rect(*element.position, *element.size)
        pygame.draw.rect(screen, element.background_color, rect)
        
        # Draw border
        if element.border_width > 0:
            pygame.draw.rect(screen, element.border_color, rect, element.border_width)
    
    def _render_button(self, element: UIElement) -> None:
        """Render a button UI element.
        
        Args:
            element: UIElement component
        """
        # Draw as panel with text
        self._render_panel(element)
        
        if element.text:
            self._render_text(element)
    
    def _render_label(self, element: UIElement) -> None:
        """Render a label UI element.
        
        Args:
            element: UIElement component
        """
        if element.text:
            self._render_text(element)
    
    def _render_progress_bar(self, element: UIElement) -> None:
        """Render a progress bar UI element.
        
        Args:
            element: UIElement component
        """
        screen = self._renderer.screen
        if not screen:
            return
        
        # Draw background
        bg_rect = pygame.Rect(*element.position, *element.size)
        pygame.draw.rect(screen, element.background_color, bg_rect)
        
        # Draw progress fill
        progress_width = int(element.size[0] * max(0.0, min(1.0, element.progress)))
        if progress_width > 0:
            fill_rect = pygame.Rect(*element.position, progress_width, element.size[1])
            pygame.draw.rect(screen, element.progress_color, fill_rect)
        
        # Draw border
        if element.border_width > 0:
            pygame.draw.rect(screen, element.border_color, bg_rect, element.border_width)
        
        # Draw text if any
        if element.text:
            self._render_text(element)
    
    def _render_text(self, element: UIElement) -> None:
        """Render text for a UI element.
        
        Args:
            element: UIElement component with text
        """
        screen = self._renderer.screen
        if not screen or not element.text:
            return
        
        # Create font
        font = pygame.font.Font(None, element.font_size)
        
        # Render text
        text_surface = font.render(element.text, True, element.text_color)
        text_rect = text_surface.get_rect()
        
        # Position text based on alignment
        element_rect = pygame.Rect(*element.position, *element.size)
        
        if element.text_align == "left":
            text_rect.left = element_rect.left + 5
            text_rect.centery = element_rect.centery
        elif element.text_align == "right":
            text_rect.right = element_rect.right - 5
            text_rect.centery = element_rect.centery
        else:  # center
            text_rect.center = element_rect.center
        
        # Draw text
        screen.blit(text_surface, text_rect)
    
    def shutdown(self) -> None:
        """Clean up UI system."""
        logger.debug("UI system shutdown complete")