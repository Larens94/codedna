"""renderer.py — Main rendering system.

exports: Renderer class
used_by: gameplay/game.py → Game._renderer
rules:   Must maintain 60 FPS, support vsync, handle window events
agent:   Game Director | 2024-01-15 | Defined Renderer interface
"""

from typing import Optional, Tuple, List
import glm
from .camera import Camera


class Renderer:
    """Main rendering system managing OpenGL context and rendering.
    
    Rules:
    - Must initialize GLFW and OpenGL context
    - Must support window resizing
    - Must maintain consistent framerate
    - Must clean up all OpenGL resources on shutdown
    """
    
    def __init__(self):
        """Initialize renderer (does not create window)."""
        self._initialized = False
        self._window = None
        self._clear_color = (0.1, 0.1, 0.1, 1.0)
        self._main_camera: Optional[Camera] = None
        self._shaders: List['Shader'] = []
        self._meshes: List['Mesh'] = []
        self._textures: List['Texture'] = []
        
    def initialize(self, title: str = "Game", width: int = 1280, 
                  height: int = 720, fullscreen: bool = False) -> bool:
        """Initialize rendering system and create window.
        
        Args:
            title: Window title
            width: Window width in pixels
            height: Window height in pixels
            fullscreen: Whether to start in fullscreen mode
            
        Returns:
            bool: True if initialization successful
            
        Rules: Must be called before any rendering operations.
        """
        try:
            # Import here to avoid GLFW dependency if not using renderer
            import glfw
            from OpenGL.GL import glViewport, glClearColor
            
            # Initialize GLFW
            if not glfw.init():
                raise RuntimeError("Failed to initialize GLFW")
                
            # Configure OpenGL context
            glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
            glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
            glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
            glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
            
            # Create window
            monitor = glfw.get_primary_monitor() if fullscreen else None
            self._window = glfw.create_window(width, height, title, monitor, None)
            
            if not self._window:
                glfw.terminate()
                raise RuntimeError("Failed to create GLFW window")
                
            # Make context current
            glfw.make_context_current(self._window)
            
            # Enable vsync
            glfw.swap_interval(1)
            
            # Set viewport
            glViewport(0, 0, width, height)
            
            # Set clear color
            glClearColor(*self._clear_color)
            
            # Enable depth testing
            from OpenGL.GL import glEnable, GL_DEPTH_TEST
            glEnable(GL_DEPTH_TEST)
            
            # Enable blending
            from OpenGL.GL import GL_BLEND, glBlendFunc, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            self._initialized = True
            self._window_size = (width, height)
            
            # Create default camera
            self._main_camera = Camera()
            self._main_camera.set_perspective(45.0, width / height, 0.1, 100.0)
            self._main_camera.position = glm.vec3(0, 0, 5)
            self._main_camera.look_at(glm.vec3(0, 0, 0))
            
            return True
            
        except Exception as e:
            print(f"Failed to initialize renderer: {e}")
            self.shutdown()
            return False
    
    def set_clear_color(self, r: float, g: float, b: float, a: float = 1.0) -> None:
        """Set background clear color.
        
        Args:
            r: Red component (0-1)
            g: Green component (0-1)
            b: Blue component (0-1)
            a: Alpha component (0-1)
        """
        self._clear_color = (r, g, b, a)
        if self._initialized:
            from OpenGL.GL import glClearColor
            glClearColor(r, g, b, a)
    
    def begin_frame(self) -> bool:
        """Begin rendering frame.
        
        Returns:
            bool: True if should continue rendering, False if window should close
            
        Rules: Must be called at start of each frame.
        """
        if not self._initialized or not self._window:
            return False
            
        import glfw
        from OpenGL.GL import glClear, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT
        
        # Poll events
        glfw.poll_events()
        
        # Check if window should close
        if glfw.window_should_close(self._window):
            return False
            
        # Clear buffers
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        return True
    
    def end_frame(self) -> None:
        """End rendering frame and swap buffers.
        
        Rules: Must be called at end of each frame.
        """
        if self._initialized and self._window:
            import glfw
            glfw.swap_buffers(self._window)
    
    def render_mesh(self, mesh: 'Mesh', shader: 'Shader', 
                   model_matrix: glm.mat4, texture: Optional['Texture'] = None) -> None:
        """Render a mesh with shader and transform.
        
        Args:
            mesh: Mesh to render
            shader: Shader program to use
            model_matrix: Model transformation matrix
            texture: Optional texture to apply
            
        Rules: Shader must be bound before calling.
        """
        if not self._initialized:
            return
            
        # Bind shader
        shader.use()
        
        # Set uniforms
        if self._main_camera:
            shader.set_uniform("view", self._main_camera.view_matrix)
            shader.set_uniform("projection", self._main_camera.projection_matrix)
        shader.set_uniform("model", model_matrix)
        
        # Bind texture if provided
        if texture:
            texture.bind(0)
            shader.set_uniform("texture_sampler", 0)
        
        # Render mesh
        mesh.render()
        
        # Unbind texture
        if texture:
            texture.unbind()
    
    def set_main_camera(self, camera: Camera) -> None:
        """Set the main camera for rendering.
        
        Args:
            camera: Camera to use for rendering
        """
        self._main_camera = camera
    
    def get_main_camera(self) -> Optional[Camera]:
        """Get the main camera.
        
        Returns:
            Current main camera or None
        """
        return self._main_camera
    
    def get_window_size(self) -> Tuple[int, int]:
        """Get current window size.
        
        Returns:
            (width, height) tuple
        """
        return self._window_size
    
    def window_should_close(self) -> bool:
        """Check if window should close.
        
        Returns:
            True if window should close
        """
        if not self._initialized or not self._window:
            return True
            
        import glfw
        return glfw.window_should_close(self._window)
    
    def set_window_should_close(self, value: bool) -> None:
        """Set window should close flag.
        
        Args:
            value: True to request window close
        """
        if self._initialized and self._window:
            import glfw
            glfw.set_window_should_close(self._window, value)
    
    def register_shader(self, shader: 'Shader') -> None:
        """Register shader for automatic cleanup.
        
        Args:
            shader: Shader to register
        """
        self._shaders.append(shader)
    
    def register_mesh(self, mesh: 'Mesh') -> None:
        """Register mesh for automatic cleanup.
        
        Args:
            mesh: Mesh to register
        """
        self._meshes.append(mesh)
    
    def register_texture(self, texture: 'Texture') -> None:
        """Register texture for automatic cleanup.
        
        Args:
            texture: Texture to register
        """
        self._textures.append(texture)
    
    def shutdown(self) -> None:
        """Shutdown renderer and clean up resources."""
        # Clean up registered resources
        for shader in self._shaders:
            shader.cleanup()
        for mesh in self._meshes:
            mesh.cleanup()
        for texture in self._textures:
            texture.cleanup()
        
        # Clean up window
        if self._window:
            import glfw
            glfw.destroy_window(self._window)
            self._window = None
            
        # Terminate GLFW
        try:
            import glfw
            glfw.terminate()
        except:
            pass
            
        self._initialized = False
    
    @property
    def initialized(self) -> bool:
        """Check if renderer is initialized."""
        return self._initialized