"""__init__.py — Render module exports.
"""__init__.py — Render module exports.

exports: Renderer, PygameRenderer, SpriteRenderer, CameraSystem, components, systems
used_by: gameplay/, main.py
rules:   Supports both OpenGL 3.3+ and Pygame 2D rendering
agent:   GraphicsSpecialist | 2024-03-29 | Added Pygame renderer and ECS components
"""

# OpenGL renderer (existing)
from .renderer import Renderer
from .shader import Shader
from .mesh import Mesh
from .texture import Texture
from .camera import Camera

# Pygame 2D renderer (new)
from .pygame_renderer import PygameRenderer
from .main import SpriteRenderer, CameraSystem, draw_ui

# ECS components and systems
from .components import Sprite, Transform, CameraFollow, ParticleEmitter, UIElement, RenderLayer
from .systems import RenderingSystem, ParticleSystem, UISystem

# Particle system
from .particles import ParticleEmitter as ParticleEmitterClass, ParticleRenderer

__all__ = [
    # OpenGL
    'Renderer', 'Shader', 'Mesh', 'Texture', 'Camera',
    
    # Pygame 2D
    'PygameRenderer', 'SpriteRenderer', 'CameraSystem', 'draw_ui',
    
    # ECS
    'Sprite', 'Transform', 'CameraFollow', 'ParticleEmitter', 'UIElement', 'RenderLayer',
    'RenderingSystem', 'ParticleSystem', 'UISystem',
    
    # Particle system
    'ParticleEmitterClass', 'ParticleRenderer'
]