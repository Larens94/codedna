"""
Particle system for 2D RPG combat effects.
Handles sparks, smoke, magic effects, and other visual effects.
"""

import pygame
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import math
import random


@dataclass
class Particle:
    """Single particle with physics properties."""
    position: Tuple[float, float]
    velocity: Tuple[float, float]
    texture_id: str
    size: Tuple[float, float] = (10, 10)
    color: Tuple[int, int, int, int] = (255, 255, 255, 255)
    lifetime: float = 1.0
    max_lifetime: float = 1.0
    rotation: float = 0.0
    rotation_speed: float = 0.0
    scale: float = 1.0
    scale_speed: float = 0.0
    gravity: float = 0.0
    drag: float = 0.0
    fade_out: bool = True
    
    def update(self, delta_time: float) -> bool:
        """
        Update particle physics.
        
        Args:
            delta_time: Time since last update
            
        Returns:
            True if particle is still alive
        """
        self.lifetime -= delta_time
        
        if self.lifetime <= 0:
            return False
        
        # Update position
        self.position = (
            self.position[0] + self.velocity[0] * delta_time,
            self.position[1] + self.velocity[1] * delta_time
        )
        
        # Apply gravity
        self.velocity = (
            self.velocity[0],
            self.velocity[1] + self.gravity * delta_time
        )
        
        # Apply drag
        if self.drag > 0:
            drag_factor = 1.0 - self.drag * delta_time
            self.velocity = (
                self.velocity[0] * drag_factor,
                self.velocity[1] * drag_factor
            )
        
        # Update rotation
        self.rotation += self.rotation_speed * delta_time
        
        # Update scale
        self.scale += self.scale_speed * delta_time
        self.scale = max(0, self.scale)
        
        return True
    
    def get_alpha(self) -> int:
        """Get current alpha based on lifetime."""
        if not self.fade_out:
            return self.color[3]
        
        alpha = int(self.color[3] * (self.lifetime / self.max_lifetime))
        return max(0, min(255, alpha))


@dataclass
class ParticleEmitter:
    """Emits particles with specific properties."""
    position: Tuple[float, float]
    texture_id: str
    emission_rate: float = 10.0  # particles per second
    burst_count: int = 0  # 0 for continuous emission
    max_particles: int = 100
    particle_lifetime: Tuple[float, float] = (0.5, 2.0)  # min, max
    velocity_range: Tuple[float, float] = (50.0, 200.0)  # min speed, max speed
    angle_range: Tuple[float, float] = (0, 360)  # degrees
    size_range: Tuple[float, float] = (5.0, 20.0)
    color_range: Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]] = None
    gravity: float = 0.0
    drag: float = 0.0
    rotation_speed_range: Tuple[float, float] = (-180, 180)  # degrees per second
    scale_speed_range: Tuple[float, float] = (-1.0, 0.0)  # scale change per second
    
    def __post_init__(self):
        if self.color_range is None:
            self.color_range = ((255, 255, 255, 255), (255, 255, 255, 255))
        
        self.time_since_emission = 0.0
        self.burst_emitted = False
        self.active = True
    
    def update(self, delta_time: float) -> List[Particle]:
        """
        Update emitter and create new particles.
        
        Args:
            delta_time: Time since last update
            
        Returns:
            List of new particles
        """
        if not self.active:
            return []
        
        new_particles = []
        
        if self.burst_count > 0 and not self.burst_emitted:
            # Emit burst
            for _ in range(self.burst_count):
                particle = self._create_particle()
                new_particles.append(particle)
            self.burst_emitted = True
            self.active = False
        
        else:
            # Continuous emission
            self.time_since_emission += delta_time
            particles_to_emit = int(self.emission_rate * self.time_since_emission)
            
            if particles_to_emit > 0:
                self.time_since_emission = 0.0
                
                for _ in range(particles_to_emit):
                    particle = self._create_particle()
                    new_particles.append(particle)
        
        return new_particles
    
    def _create_particle(self) -> Particle:
        """Create a new particle with random properties."""
        # Random lifetime
        lifetime = random.uniform(*self.particle_lifetime)
        
        # Random velocity
        speed = random.uniform(*self.velocity_range)
        angle = math.radians(random.uniform(*self.angle_range))
        velocity = (
            math.cos(angle) * speed,
            math.sin(angle) * speed
        )
        
        # Random size
        size = random.uniform(*self.size_range)
        
        # Random color
        color_min, color_max = self.color_range
        color = (
            random.randint(color_min[0], color_max[0]),
            random.randint(color_min[1], color_max[1]),
            random.randint(color_min[2], color_max[2]),
            random.randint(color_min[3], color_max[3])
        )
        
        # Random rotation speed
        rotation_speed = random.uniform(*self.rotation_speed_range)
        
        # Random scale speed
        scale_speed = random.uniform(*self.scale_speed_range)
        
        return Particle(
            position=self.position,
            velocity=velocity,
            texture_id=self.texture_id,
            size=(size, size),
            color=color,
            lifetime=lifetime,
            max_lifetime=lifetime,
            rotation=random.uniform(0, 360),
            rotation_speed=rotation_speed,
            scale=1.0,
            scale_speed=scale_speed,
            gravity=self.gravity,
            drag=self.drag,
            fade_out=True
        )
    
    def set_position(self, position: Tuple[float, float]):
        """Update emitter position."""
        self.position = position
    
    def stop(self):
        """Stop emitting particles."""
        self.active = False
    
    def restart(self):
        """Restart emitter."""
        self.active = True
        self.burst_emitted = False
        self.time_since_emission = 0.0


class ParticleSystem:
    """
    Manages particle emitters and rendering.
    Uses object pooling for performance.
    """
    
    def __init__(self, sprite_renderer):
        """
        Initialize particle system.
        
        Args:
            sprite_renderer: SpriteRenderer instance
        """
        self.sprite_renderer = sprite_renderer
        self.emitters: Dict[str, ParticleEmitter] = {}
        self.particles: List[Particle] = []
        self.particle_sprites: Dict[int, str] = {}  # particle index -> sprite ID
        
        # Object pooling
        self.particle_pool: List[Particle] = []
        self.max_pool_size = 1000
        
        # Performance tracking
        self.particles_active = 0
        self.particles_spawned = 0
        self.particles_recycled = 0
        self.emitters_active = 0
    
    def create_emitter(self, emitter_id: str, emitter: ParticleEmitter) -> bool:
        """
        Create particle emitter.
        
        Args:
            emitter_id: Unique emitter ID
            emitter: ParticleEmitter instance
            
        Returns:
            True if successful
        """
        if emitter_id in self.emitters:
            return False
        
        self.emitters[emitter_id] = emitter
        return True
    
    def get_emitter(self, emitter_id: str) -> Optional[ParticleEmitter]:
        """
        Get emitter by ID.
        
        Args:
            emitter_id: Emitter ID
            
        Returns:
            ParticleEmitter or None
        """
        return self.emitters.get(emitter_id)
    
    def remove_emitter(self, emitter_id: str):
        """
        Remove emitter.
        
        Args:
            emitter_id: Emitter ID to remove
        """
        if emitter_id in self.emitters:
            del self.emitters[emitter_id]
    
    def update(self, delta_time: float):
        """
        Update all emitters and particles.
        
        Args:
            delta_time: Time since last update
        """
        # Update emitters and create new particles
        self.emitters_active = 0
        for emitter in self.emitters.values():
            if emitter.active:
                self.emitters_active += 1
                new_particles = emitter.update(delta_time)
                
                for particle in new_particles:
                    self._add_particle(particle)
        
        # Update existing particles
        particles_to_remove = []
        
        for i, particle in enumerate(self.particles):
            if not particle.update(delta_time):
                particles_to_remove.append(i)
            else:
                # Update sprite
                sprite_id = self.particle_sprites.get(i)
                if sprite_id:
                    self._update_particle_sprite(i, particle, sprite_id)
        
        # Remove dead particles
        for index in reversed(particles_to_remove):
            self._remove_particle(index)
    
    def _add_particle(self, particle: Particle):
        """Add new particle to system."""
        # Try to reuse from pool
        if self.particle_pool:
            pool_index = len(self.particles)
            self.particles.append(particle)
            self.particles_recycled += 1
        else:
            pool_index = len(self.particles)
            self.particles.append(particle)
        
        # Create sprite for particle
        sprite_id = f"particle_{pool_index}_{self.particles_spawned}"
        self.sprite_renderer.create_sprite(
            sprite_id=sprite_id,
            texture_id=particle.texture_id,
            position=particle.position,
            z_index=1000,  # Particles on top
            scale=(particle.scale, particle.scale),
            rotation=particle.rotation,
            color=particle.color
        )
        
        self.particle_sprites[pool_index] = sprite_id
        self.particles_spawned += 1
        self.particles_active = len(self.particles)
    
    def _update_particle_sprite(self, index: int, particle: Particle, sprite_id: str):
        """Update particle sprite properties."""
        alpha = particle.get_alpha()
        color = (particle.color[0], particle.color[1], particle.color[2], alpha)
        
        self.sprite_renderer.update_sprite(
            sprite_id,
            position=particle.position,
            scale=(particle.scale, particle.scale),
            rotation=particle.rotation,
            color=color
        )
    
    def _remove_particle(self, index: int):
        """Remove particle from system."""
        if index >= len(self.particles):
            return
        
        # Remove sprite
        sprite_id = self.particle_sprites.get(index)
        if sprite_id:
            self.sprite_renderer.remove_sprite(sprite_id)
            del self.particle_sprites[index]
        
        # Move particle to pool for reuse
        particle = self.particles[index]
        if len(self.particle_pool) < self.max_pool_size:
            self.particle_pool.append(particle)
        
        # Remove from active list
        self.particles.pop(index)
        
        # Update sprite indices
        new_sprites = {}
        for old_index, sprite_id in self.particle_sprites.items():
            if old_index > index:
                new_sprites[old_index - 1] = sprite_id
            elif old_index < index:
                new_sprites[old_index] = sprite_id
        self.particle_sprites = new_sprites
        
        self.particles_active = len(self.particles)
    
    def create_spark_effect(self, position: Tuple[float, float], 
                           intensity: float = 1.0) -> str:
        """
        Create spark effect for combat hits.
        
        Args:
            position: Effect position
            intensity: Effect intensity multiplier
            
        Returns:
            Emitter ID
        """
        emitter_id = f"sparks_{len(self.emitters)}"
        emitter = ParticleEmitter(
            position=position,
            texture_id="spark",
            emission_rate=50.0 * intensity,
            burst_count=int(20 * intensity),
            max_particles=100,
            particle_lifetime=(0.1, 0.5),
            velocity_range=(100.0 * intensity, 300.0 * intensity),
            angle_range=(0, 360),
            size_range=(3.0 * intensity, 8.0 * intensity),
            color_range=((255, 200, 0, 255), (255, 100, 0, 255)),
            gravity=200.0,
            drag=0.5,
            rotation_speed_range=(-360, 360),
            scale_speed_range=(-2.0, -0.5)
        )
        
        self.create_emitter(emitter_id, emitter)
        return emitter_id
    
    def create_smoke_effect(self, position: Tuple[float, float],
                           duration: float = 2.0) -> str:
        """
        Create smoke effect.
        
        Args:
            position: Effect position
            duration: Effect duration in seconds
            
        Returns:
            Emitter ID
        """
        emitter_id = f"smoke_{len(self.emitters)}"
        emitter = ParticleEmitter(
            position=position,
            texture_id="smoke",
            emission_rate=10.0,
            max_particles=50,
            particle_lifetime=(0.5, duration),
            velocity_range=(10.0, 50.0),
            angle_range=(0, 360),
            size_range=(10.0, 30.0),
            color_range=((100, 100, 100, 100), (150, 150, 150, 150)),
            gravity=-20.0,  # Smoke rises
            drag=0.1,
            rotation_speed_range=(-90, 90),
            scale_speed_range=(0.5, 1.5)  # Smoke expands
        )
        
        self.create_emitter(emitter_id, emitter)
        return emitter_id
    
    def create_magic_effect(self, position: Tuple[float, float],
                          color: Tuple[int, int, int, int] = (100, 100, 255, 255)) -> str:
        """
        Create magic spell effect.
        
        Args:
            position: Effect position
            color: Magic color
            
        Returns:
            Emitter ID
        """
        emitter_id = f"magic_{len(self.emitters)}"
        emitter = ParticleEmitter(
            position=position,
            texture_id="magic",
            emission_rate=30.0,
            burst_count=50,
            max_particles=100,
            particle_lifetime=(0.5, 1.5),
            velocity_range=(50.0, 150.0),
            angle_range=(0, 360),
            size_range=(5.0, 15.0),
            color_range=(color, color),
            gravity=0.0,
            drag=0.3,
            rotation_speed_range=(-180, 180),
            scale_speed_range=(-0.5, 0.5)
        )
        
        self.create_emitter(emitter_id, emitter)
        return emitter_id
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get particle system statistics.
        
        Returns:
            Dictionary with system metrics
        """
        return {
            'particles_active': self.particles_active,
            'particles_spawned': self.particles_spawned,
            'particles_recycled': self.particles_recycled,
            'emitters_active': self.emitters_active,
            'total_emitters': len(self.emitters),
            'particle_pool_size': len(self.particle_pool)
        }
    
    def cleanup(self):
        """Clean up particle system."""
        # Remove all particle sprites
        for sprite_id in self.particle_sprites.values():
            self.sprite_renderer.remove_sprite(sprite_id)
        
        self.emitters.clear()
        self.particles.clear()
        self.particle_sprites.clear()
        self.particle_pool.clear()
        
        print("ParticleSystem cleaned up")