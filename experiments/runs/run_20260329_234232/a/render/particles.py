"""particles.py — Particle system for visual effects.

exports: ParticleSystem class (alternative to ECS version)
used_by: render/systems.py → ParticleSystem
rules:   Must be efficient with particle pooling
agent:   GraphicsSpecialist | 2024-03-29 | Created particle system
"""

import pygame
import glm
import random
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ParticleType(Enum):
    """Types of particles."""
    SPARK = "spark"
    SMOKE = "smoke"
    FIRE = "fire"
    BLOOD = "blood"
    MAGIC = "magic"
    WATER = "water"


@dataclass
class Particle:
    """Individual particle data."""
    position: glm.vec2
    velocity: glm.vec2
    life: float
    max_life: float
    size: float
    color_start: Tuple[int, int, int, int]
    color_end: Tuple[int, int, int, int]
    particle_type: ParticleType = ParticleType.SPARK
    rotation: float = 0.0
    rotation_speed: float = 0.0
    size_over_life: bool = True
    fade_out: bool = True
    
    # Internal state
    age: float = 0.0
    current_color: Tuple[int, int, int, int] = field(default=(255, 255, 255, 255), init=False)
    current_size: float = field(default=1.0, init=False)


class ParticleEmitter:
    """Emitter that creates and manages particles."""
    
    def __init__(self, position: glm.vec2, particle_type: ParticleType = ParticleType.SPARK):
        """Initialize particle emitter.
        
        Args:
            position: World position of emitter
            particle_type: Type of particles to emit
        """
        self.position = position
        self.particle_type = particle_type
        self.emitting = True
        self.particles: List[Particle] = []
        self.max_particles = 1000
        
        # Emission properties
        self.emission_rate = 10.0  # Particles per second
        self.burst_count = 0
        self.time_since_emission = 0.0
        
        # Particle properties (defaults based on type)
        self._set_defaults_by_type()
    
    def _set_defaults_by_type(self):
        """Set default properties based on particle type."""
        if self.particle_type == ParticleType.SPARK:
            self.lifetime_range = (0.2, 0.8)
            self.speed_range = (100.0, 300.0)
            self.size_range = (2.0, 6.0)
            self.color_start = (255, 255, 100, 255)
            self.color_end = (255, 100, 0, 0)
            self.emission_angle = (-30, 30)
            self.gravity = glm.vec2(0, 98.0)
            self.damping = 0.95
            
        elif self.particle_type == ParticleType.SMOKE:
            self.lifetime_range = (1.0, 3.0)
            self.speed_range = (20.0, 60.0)
            self.size_range = (8.0, 20.0)
            self.color_start = (100, 100, 100, 200)
            self.color_end = (50, 50, 50, 0)
            self.emission_angle = (0, 360)
            self.gravity = glm.vec2(0, -20.0)  # Smoke rises
            self.damping = 0.99
            
        elif self.particle_type == ParticleType.FIRE:
            self.lifetime_range = (0.5, 1.5)
            self.speed_range = (50.0, 150.0)
            self.size_range = (6.0, 12.0)
            self.color_start = (255, 100, 0, 255)
            self.color_end = (255, 255, 100, 0)
            self.emission_angle = (0, 360)
            self.gravity = glm.vec2(0, -50.0)  # Fire rises
            self.damping = 0.98
            
        elif self.particle_type == ParticleType.BLOOD:
            self.lifetime_range = (0.5, 2.0)
            self.speed_range = (80.0, 200.0)
            self.size_range = (3.0, 8.0)
            self.color_start = (200, 0, 0, 255)
            self.color_end = (100, 0, 0, 0)
            self.emission_angle = (0, 360)
            self.gravity = glm.vec2(0, 98.0)
            self.damping = 0.9
            
        elif self.particle_type == ParticleType.MAGIC:
            self.lifetime_range = (1.0, 2.0)
            self.speed_range = (30.0, 80.0)
            self.size_range = (4.0, 10.0)
            self.color_start = (100, 100, 255, 255)
            self.color_end = (200, 200, 255, 0)
            self.emission_angle = (0, 360)
            self.gravity = glm.vec2(0, 0)
            self.damping = 0.99
            
        else:  # WATER
            self.lifetime_range = (0.8, 1.5)
            self.speed_range = (60.0, 120.0)
            self.size_range = (3.0, 6.0)
            self.color_start = (100, 150, 255, 200)
            self.color_end = (100, 150, 255, 0)
            self.emission_angle = (0, 360)
            self.gravity = glm.vec2(0, 98.0)
            self.damping = 0.92
    
    def update(self, delta_time: float):
        """Update emitter and particles.
        
        Args:
            delta_time: Time since last update
        """
        # Emit new particles
        if self.emitting:
            self._emit_particles(delta_time)
        
        # Update existing particles
        self._update_particles(delta_time)
        
        # Remove dead particles
        self.particles = [p for p in self.particles if p.life > 0]
    
    def _emit_particles(self, delta_time: float):
        """Emit new particles.
        
        Args:
            delta_time: Time since last emission
        """
        # Handle burst
        if self.burst_count > 0:
            for _ in range(min(self.burst_count, self.max_particles - len(self.particles))):
                self._create_particle()
            self.burst_count = 0
        
        # Handle continuous emission
        self.time_since_emission += delta_time
        emission_interval = 1.0 / self.emission_rate
        
        while (self.time_since_emission >= emission_interval and 
               len(self.particles) < self.max_particles):
            self.time_since_emission -= emission_interval
            self._create_particle()
    
    def _create_particle(self):
        """Create a new particle."""
        # Randomize properties
        life = random.uniform(*self.lifetime_range)
        speed = random.uniform(*self.speed_range)
        size = random.uniform(*self.size_range)
        angle = random.uniform(*self.emission_angle)
        
        # Calculate velocity
        rad = glm.radians(angle)
        velocity = glm.vec2(
            speed * glm.cos(rad),
            speed * glm.sin(rad)
        )
        
        # Add some random offset to position
        pos_offset = glm.vec2(
            random.uniform(-5, 5),
            random.uniform(-5, 5)
        )
        
        # Create particle
        particle = Particle(
            position=self.position + pos_offset,
            velocity=velocity,
            life=life,
            max_life=life,
            size=size,
            color_start=self.color_start,
            color_end=self.color_end,
            particle_type=self.particle_type,
            rotation=random.uniform(0, 360),
            rotation_speed=random.uniform(-180, 180)
        )
        
        self.particles.append(particle)
    
    def _update_particles(self, delta_time: float):
        """Update all particles.
        
        Args:
            delta_time: Time since last update
        """
        for particle in self.particles:
            # Update lifetime
            particle.life -= delta_time
            particle.age += delta_time
            
            if particle.life <= 0:
                continue
            
            # Update physics
            particle.velocity += self.gravity * delta_time
            particle.velocity *= self.damping ** delta_time
            particle.position += particle.velocity * delta_time
            
            # Update rotation
            particle.rotation += particle.rotation_speed * delta_time
            
            # Update visual properties
            life_ratio = 1.0 - (particle.life / particle.max_life)
            
            # Interpolate color
            particle.current_color = self._interpolate_color(
                particle.color_start,
                particle.color_end,
                life_ratio
            )
            
            # Update size
            if particle.size_over_life:
                particle.current_size = particle.size * (1.0 - life_ratio * 0.5)
            else:
                particle.current_size = particle.size
            
            # Apply fade out
            if particle.fade_out:
                r, g, b, a = particle.current_color
                a = int(a * (1.0 - life_ratio))
                particle.current_color = (r, g, b, a)
    
    def _interpolate_color(self, start: Tuple[int, int, int, int],
                          end: Tuple[int, int, int, int],
                          t: float) -> Tuple[int, int, int, int]:
        """Interpolate between two colors.
        
        Args:
            start: Start color
            end: End color
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
    
    def burst(self, count: int):
        """Emit a burst of particles.
        
        Args:
            count: Number of particles to burst
        """
        self.burst_count = count
    
    def clear(self):
        """Clear all particles."""
        self.particles.clear()


class ParticleRenderer:
    """Renders particles to screen."""
    
    def __init__(self, renderer: Any):
        """Initialize particle renderer.
        
        Args:
            renderer: PygameRenderer instance
        """
        self._renderer = renderer
        self._particle_surfaces: Dict[ParticleType, pygame.Surface] = {}
        self._create_particle_surfaces()
    
    def _create_particle_surfaces(self):
        """Create particle surfaces for each type."""
        # Create simple circle surfaces for each particle type
        for particle_type in ParticleType:
            # Create surface with per-pixel alpha
            size = 32  # Base size, will be scaled
            surface = pygame.Surface((size, size), pygame.SRCALPHA)
            
            # Draw particle shape based on type
            center = (size // 2, size // 2)
            
            if particle_type == ParticleType.SPARK:
                # Spark: small bright circle
                pygame.draw.circle(surface, (255, 255, 200, 255), center, 8)
                pygame.draw.circle(surface, (255, 255, 100, 200), center, 4)
                
            elif particle_type == ParticleType.SMOKE:
                # Smoke: soft gray circle
                pygame.draw.circle(surface, (150, 150, 150, 150), center, 12)
                pygame.draw.circle(surface, (100, 100, 100, 100), center, 8)
                
            elif particle_type == ParticleType.FIRE:
                # Fire: orange-yellow gradient
                pygame.draw.circle(surface, (255, 200, 100, 200), center, 10)
                pygame.draw.circle(surface, (255, 100, 0, 150), center, 6)
                
            elif particle_type == ParticleType.BLOOD:
                # Blood: red circle
                pygame.draw.circle(surface, (200, 0, 0, 200), center, 6)
                pygame.draw.circle(surface, (150, 0, 0, 150), center, 4)
                
            elif particle_type == ParticleType.MAGIC:
                # Magic: blue-purple circle
                pygame.draw.circle(surface, (150, 150, 255, 200), center, 8)
                pygame.draw.circle(surface, (100, 100, 200, 150), center, 5)
                
            else:  # WATER
                # Water: blue circle
                pygame.draw.circle(surface, (100, 150, 255, 180), center, 8)
                pygame.draw.circle(surface, (80, 120, 220, 120), center, 5)
            
            self._particle_surfaces[particle_type] = surface
    
    def render(self, emitter: ParticleEmitter):
        """Render particles from emitter.
        
        Args:
            emitter: ParticleEmitter to render
        """
        if not self._renderer.initialized:
            return
        
        for particle in emitter.particles:
            if particle.life <= 0:
                continue
            
            # Get particle surface
            surface = self._particle_surfaces.get(particle.particle_type)
            if not surface:
                continue
            
            # Scale surface based on particle size
            scaled_size = int(particle.current_size * 2)  * 2  # *2 for visibility
            if scaled_size <= 0:
                continue
            
            # Scale surface (in a real implementation, we'd cache scaled versions)
            scaled_surface = pygame.transform.scale(surface, (scaled_size, scaled_size))
            
            # Apply color tint
            if particle.current_color != (255, 255, 255, 255):
                # Create colorized version
                color_surface = scaled_surface.copy()
                color_surface.fill(particle.current_color[:3], special_flags=pygame.BLEND_RGBA_MULT)
                color_surface.set_alpha(particle.current_color[3])
                scaled_surface = color_surface
            
            # Rotate if needed
            if abs(particle.rotation) > 0.1:
                scaled_surface = pygame.transform.rotate(scaled_surface, particle.rotation)
            
            # Calculate screen position
            screen_pos = self._renderer.world_to_screen((particle.position.x, particle.position.y))
            
            # Draw particle
            if self._renderer.screen:
                particle_rect = scaled_surface.get_rect(center=screen_pos)
                self._renderer.screen.blit(scaled_surface, particle_rect)