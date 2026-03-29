"""main.py — Main exports for render module.

exports: SpriteRenderer(), CameraSystem(), draw_ui() -> None
used_by: gameplay/game.py → Game._renderer
rules:   Must support Pygame-based 2D rendering with sprite batching
agent:   GraphicsSpecialist | 2024-03-29 | Created Pygame-based renderer with ECS integration
"""

from .pygame_renderer import PygameRenderer as SpriteRenderer
from .camera import CameraSystem
from .ui import draw_ui

__all__ = ['SpriteRenderer', 'CameraSystem', 'draw_ui']