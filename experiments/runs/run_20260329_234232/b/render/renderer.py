"""
Main renderer interface.
Abstracts graphics API and manages the rendering pipeline.
"""

from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
import numpy as np


@dataclass
class RenderConfig:
    """Configuration for the renderer."""
    window: Any  # GLFW window or similar
    width: int = 1280
    height: int = 720
    vsync: bool = True
    msaa_samples: int = 4
    anisotropy_level: int = 8
    shadow_map_size: int = 2048
    max_lights: int = 32
    gamma_correction: bool = True
    hdr: bool = False


class Renderer:
    """
    Main renderer class that abstracts graphics API.
    Supports OpenGL with potential for Vulkan/Metal backends.
    """
    
    def __init__(self, config: RenderConfig):
        """
        Initialize the renderer.
        
        Args:
            config: Renderer configuration
        """
        self.config = config
        self.is_initialized = False
        
        # Subsystems
        self.shader_manager = None
        self.material_system = None
        self.lighting_system = None
        
        # State
        self.current_camera = None
        self.viewport_size = (config.width, config.height)
        self.clear_color = (0.1, 0.1, 0.1, 1.0)
        
        # Render targets
        self.main_framebuffer = None
        self.postprocess_framebuffer = None
        self.shadow_framebuffers = {}
        
        # Statistics
        self.draw_calls = 0
        self.triangle_count = 0
        self.batch_count = 0
        
        # Asset manager reference
        self.asset_manager = None
        
        # Initialize graphics API
        self._initialize_graphics()
    
    def _initialize_graphics(self):
        """Initialize the graphics API (OpenGL by default)."""
        try:
            import OpenGL.GL as gl
            import OpenGL.GL.shaders as shaders
            
            # Set up OpenGL state
            gl.glViewport(0, 0, self.config.width, self.config.height)
            gl.glClearColor(*self.clear_color)
            
            # Enable depth testing
            gl.glEnable(gl.GL_DEPTH_TEST)
            gl.glDepthFunc(gl.GL_LEQUAL)
            
            # Enable blending
            gl.glEnable(gl.GL_BLEND)
            gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            
            # Enable face culling
            gl.glEnable(gl.GL_CULL_FACE)
            gl.glCullFace(gl.GL_BACK)
            gl.glFrontFace(gl.GL_CCW)
            
            # Enable MSAA if configured
            if self.config.msaa_samples > 1:
                gl.glEnable(gl.GL_MULTISAMPLE)
            
            # Set anisotropy if supported
            if self.config.anisotropy_level > 1:
                max_anisotropy = gl.glGetIntegerv(gl.GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT)
                anisotropy = min(self.config.anisotropy_level, max_anisotropy)
                gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAX_ANISOTROPY_EXT, anisotropy)
            
            print(f"Renderer initialized: {self.config.width}x{self.config.height}")
            print(f"OpenGL Version: {gl.glGetString(gl.GL_VERSION).decode()}")
            print(f"GPU: {gl.glGetString(gl.GL_RENDERER).decode()}")
            
            self.is_initialized = True
            
        except ImportError:
            print("OpenGL not available. Using mock renderer for development.")
            self.is_initialized = True  # Allow development without OpenGL
    
    def set_asset_manager(self, asset_manager):
        """
        Set the asset manager for resource loading.
        
        Args:
            asset_manager: AssetManager instance
        """
        self.asset_manager = asset_manager
    
    def set_camera(self, camera):
        """
        Set the active camera.
        
        Args:
            camera: Camera instance
        """
        self.current_camera = camera
    
    def prepare_frame(self, render_data: Dict[str, Any]):
        """
        Prepare render data for the frame (can be done async).
        
        Args:
            render_data: Data needed for rendering
        """
        # This method can be called from a background thread
        # Prepare buffers, sort render queue, etc.
        pass
    
    def render(self, render_data: Dict[str, Any], alpha: float = 0.0):
        """
        Render a frame with interpolation.
        
        Args:
            render_data: Data needed for rendering
            alpha: Interpolation factor between fixed updates
        """
        if not self.is_initialized:
            return
        
        # Reset statistics
        self.draw_calls = 0
        self.triangle_count = 0
        self.batch_count = 0
        
        try:
            import OpenGL.GL as gl
            
            # Clear buffers
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            
            # Update camera interpolation
            if self.current_camera:
                self.current_camera.update_interpolation(alpha)
            
            # Render shadow maps (first pass)
            self._render_shadow_maps(render_data)
            
            # Main rendering pass
            self._render_main_pass(render_data)
            
            # Post-processing
            self._apply_post_processing()
            
            # UI rendering (last)
            self._render_ui(render_data.get('ui_elements', []))
            
        except ImportError:
            # Mock rendering for development
            self._mock_render(render_data)
    
    def _render_shadow_maps(self, render_data: Dict[str, Any]):
        """Render shadow maps for all lights."""
        if not self.lighting_system:
            return
        
        lights = render_data.get('lights', [])
        shadow_casters = render_data.get('shadow_casters', [])
        
        for light in lights:
            if light.cast_shadows and shadow_casters:
                self._render_shadow_map(light, shadow_casters)
    
    def _render_shadow_map(self, light, shadow_casters):
        """Render shadow map for a single light."""
        # Implementation depends on graphics API
        pass
    
    def _render_main_pass(self, render_data: Dict[str, Any]):
        """Render the main geometry pass."""
        entities = render_data.get('entities', [])
        camera_data = render_data.get('camera', {})
        
        # Set up camera
        if self.current_camera:
            view_matrix = self.current_camera.get_view_matrix()
            projection_matrix = self.current_camera.get_projection_matrix()
            
            # Upload matrices to shaders
            self._upload_camera_matrices(view_matrix, projection_matrix)
        
        # Upload lighting data
        if self.lighting_system:
            lights = render_data.get('lights', [])
            self.lighting_system.upload_lights(lights)
        
        # Sort entities for efficient rendering
        sorted_entities = self._sort_entities_for_rendering(entities)
        
        # Render entities
        for entity in sorted_entities:
            self._render_entity(entity)
    
    def _sort_entities_for_rendering(self, entities: List[Dict]) -> List[Dict]:
        """
        Sort entities for optimal rendering performance.
        
        Args:
            entities: List of entity data dictionaries
            
        Returns:
            Sorted list of entities
        """
        # Sort by:
        # 1. Shader program
        # 2. Material
        # 3. Texture
        # 4. Depth (for transparency)
        # 5. Distance from camera
        
        if not entities:
            return []
        
        # Simple implementation - sort by shader then material
        return sorted(entities, key=lambda e: (
            e.get('shader_id', ''),
            e.get('material_id', ''),
            e.get('texture_id', '')
        ))
    
    def _render_entity(self, entity: Dict[str, Any]):
        """Render a single entity."""
        # Extract entity data
        mesh_id = entity.get('mesh_id')
        material_id = entity.get('material_id')
        transform = entity.get('transform', np.identity(4))
        
        if not mesh_id or not material_id:
            return
        
        # Get assets from asset manager
        if self.asset_manager:
            mesh = self.asset_manager.get_mesh(mesh_id)
            material = self.asset_manager.get_material(material_id)
            
            if mesh and material:
                # Bind material
                material.bind()
                
                # Upload model matrix
                self._upload_model_matrix(transform)
                
                # Render mesh
                mesh.render()
                
                # Update statistics
                self.draw_calls += 1
                self.triangle_count += mesh.triangle_count
    
    def _upload_camera_matrices(self, view_matrix, projection_matrix):
        """Upload camera matrices to shaders."""
        # Implementation depends on shader system
        pass
    
    def _upload_model_matrix(self, model_matrix):
        """Upload model matrix to shaders."""
        # Implementation depends on shader system
        pass
    
    def _apply_post_processing(self):
        """Apply post-processing effects."""
        if not self.postprocess_framebuffer:
            return
        
        # Bind post-processing framebuffer
        # Apply effects (bloom, tone mapping, FXAA, etc.)
        # Composite back to main framebuffer
        pass
    
    def _render_ui(self, ui_elements: List[Dict[str, Any]]):
        """Render UI elements."""
        if not ui_elements:
            return
        
        # Switch to orthographic projection
        # Disable depth testing
        # Render UI elements in order
        for element in ui_elements:
            self._render_ui_element(element)
    
    def _render_ui_element(self, element: Dict[str, Any]):
        """Render a single UI element."""
        # Implementation for UI rendering
        pass
    
    def _mock_render(self, render_data: Dict[str, Any]):
        """Mock rendering for development without OpenGL."""
        entities = render_data.get('entities', [])
        print(f"Mock rendering {len(entities)} entities")
    
    def update_interpolation(self, alpha: float):
        """
        Update interpolation for smooth rendering.
        
        Args:
            alpha: Interpolation factor between fixed updates
        """
        if self.current_camera:
            self.current_camera.update_interpolation(alpha)
    
    def resize(self, width: int, height: int):
        """
        Handle window resize.
        
        Args:
            width: New width in pixels
            height: New height in pixels
        """
        self.viewport_size = (width, height)
        
        try:
            import OpenGL.GL as gl
            gl.glViewport(0, 0, width, height)
            
            # Recreate framebuffers if needed
            if self.main_framebuffer:
                self._recreate_framebuffers(width, height)
            
        except ImportError:
            pass
    
    def _recreate_framebuffers(self, width: int, height: int):
        """Recreate framebuffers after resize."""
        # Implementation depends on graphics API
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get rendering statistics for the last frame.
        
        Returns:
            Dictionary of statistics
        """
        return {
            'draw_calls': self.draw_calls,
            'triangles': self.triangle_count,
            'batches': self.batch_count,
            'viewport_size': self.viewport_size,
            'fps': self._calculate_fps()
        }
    
    def _calculate_fps(self) -> float:
        """Calculate current FPS."""
        # Implementation with frame timing
        return 60.0  # Placeholder
    
    def shutdown(self):
        """Clean up rendering resources."""
        print("Shutting down renderer...")
        
        if self.shader_manager:
            self.shader_manager.shutdown()
        
        if self.material_system:
            self.material_system.shutdown()
        
        if self.lighting_system:
            self.lighting_system.shutdown()
        
        # Clean up framebuffers
        self._cleanup_framebuffers()
        
        print("Renderer shutdown complete.")
    
    def _cleanup_framebuffers(self):
        """Clean up framebuffer resources."""
        # Implementation depends on graphics API
        pass