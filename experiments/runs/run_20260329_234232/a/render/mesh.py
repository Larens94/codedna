"""mesh.py — Placeholder for OpenGL mesh class.

exports: Mesh class
used_by: render/renderer.py → Renderer._meshes
rules:   Placeholder for OpenGL compatibility
agent:   GraphicsSpecialist | 2024-03-29 | Created placeholder for OpenGL mesh
"""


class Mesh:
    """Placeholder mesh class for OpenGL renderer compatibility."""
    
    def __init__(self):
        self._vao = 0
        self._vbo = 0
        self._ebo = 0
        self._vertex_count = 0
    
    def render(self):
        """Placeholder render method."""
        pass
    
    def cleanup(self):
        """Placeholder cleanup method."""
        pass