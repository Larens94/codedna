"""__init__.py — Render module exports.

exports: Renderer, PygameRenderer, SpriteRenderer, CameraSystem, components, systems
used_by: gameplay/, main.py
rules:   Supports both OpenGL 3.3+ and Pygame 2D rendering
agent:   GraphicsSpecialist | 2024-03-29 | Added Pygame renderer and ECS components
"""

# Pygame 2D renderer (primary)
from .pygame_renderer import PygameRenderer as Renderer
from .pygame_renderer import PygameRenderer
from .main import SpriteRenderer, CameraSystem, draw_ui

# ECS components and systems
from .components import Sprite, Transform, CameraFollow, ParticleEmitter, UIElement, RenderLayer
from .systems import RenderingSystem, ParticleSystem, UISystem

# Particle system
from .particles import ParticleEmitter as ParticleEmitterClass, ParticleRenderer

__all__ = [
    # Pygame 2D (Renderer alias)
    'PygameRenderer', 'SpriteRenderer', 'CameraSystem', 'draw_ui',
    
    # ECS
    'Sprite', 'Transform', 'CameraFollow', 'ParticleEmitter', 'UIElement', 'RenderLayer',
    'RenderingSystem', 'ParticleSystem', 'UISystem',
    
    # Particle system
    'ParticleEmitterClass', 'ParticleRenderer'
]