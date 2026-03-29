"""shader.py — Placeholder for OpenGL shader class.

exports: Shader class
used_by: render/renderer.py → Renderer._shaders
rules:   Placeholder for OpenGL compatibility
agent:   GraphicsSpecialist | 2024-03-29 | Created placeholder for OpenGL shader
"""


class Shader:
    """Placeholder shader class for OpenGL renderer compatibility."""
    
    def __init__(self):
        self._id = 0
    
    def use(self):
        """Placeholder shader use method."""
        pass
    
    def set_uniform(self, name: str, value):
        """Placeholder uniform setter."""
        pass
    
    def cleanup(self):
        """Placeholder cleanup method."""
        pass