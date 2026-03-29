# Graphics Decisions Log

## 2024-03-29 - Initial Implementation

### Decision 1: Pygame vs OpenGL Renderer
- **Problem**: Existing renderer uses OpenGL/GLFW, but task specifies Pygame-based 2D rendering
- **Solution**: Create new Pygame-based renderer while keeping OpenGL renderer for 3D
- **Reasoning**: 
  - Pygame is better suited for 2D sprite-based games
  - Pygame has built-in sprite batching and texture management
  - Can maintain OpenGL renderer for future 3D features
  - Pygame is already listed as optional dependency

### Decision 2: Architecture Integration
- **Problem**: Need to integrate with existing ECS architecture
- **Solution**: Create Sprite and Transform components, and RenderingSystem
- **Reasoning**:
  - ECS architecture requires data components and logic systems
  - Sprite component stores texture/surface data
  - Transform component stores position, rotation, scale
  - RenderingSystem queries entities with both components

### Decision 3: Performance Considerations
- **Problem**: Need to maintain 60 FPS with sprite batching
- **Solution**: 
  - Use Pygame's built-in sprite groups for batching
  - Implement camera/viewport culling
  - Texture atlas support for reduced draw calls
  - Z-ordering for proper rendering order

### Decision 4: Module Structure
- **Problem**: How to organize render module files
- **Solution**:
  - `render/main.py`: Main exports (SpriteRenderer, CameraSystem, draw_ui)
  - `render/pygame_renderer.py`: Pygame-based renderer implementation
  - `render/camera.py`: Camera/viewport management
  - `render/ui.py`: UI rendering system
  - `render/particles.py`: Particle system for effects
  - `render/components.py`: ECS components for rendering
  - `render/systems.py`: ECS systems for rendering

### Decision 5: Texture Loading Strategy
- **Problem**: Need efficient texture loading and caching
- **Solution**: 
  - Integrate with existing AssetManager
  - Cache loaded Pygame surfaces
  - Support texture atlases
  - Automatic cleanup of unused textures

### Decision 6: Camera System Design
- **Problem**: Need world-to-screen coordinate transformation
- **Solution**:
  - Camera class with position, zoom, rotation
  - Viewport management with bounds checking
  - Screen shake and other camera effects
  - Multiple camera support (for splitscreen, minimap, etc.)

### Decision 7: UI System Design
- **Problem**: Need health bars, inventory, quest log
- **Solution**:
  - Layered UI rendering (background, game, UI, overlay)
  - Component-based UI elements
  - Event handling for UI interactions
  - Support for different screen resolutions

### Decision 8: Particle System
- **Problem**: Need combat effects (sparks, smoke, etc.)
- **Solution**:
  - Particle emitter component
  - Particle pool for performance
  - Configurable particle properties (lifetime, velocity, color, size)
  - Integration with ECS for entity-based effects

## Implementation Plan

1. Create PygameRenderer class with window management
2. Implement Sprite and Transform ECS components
3. Create RenderingSystem for ECS integration
4. Implement CameraSystem for viewport management
5. Create UIRenderer for UI elements
6. Implement particle system
7. Add sprite batching and performance optimizations
8. Integrate with existing AssetManager

## Notes
- Will need to add pygame to requirements.txt as required dependency
- Should maintain backward compatibility with existing OpenGL renderer
- Consider creating abstract Renderer base class for both implementations
- Performance testing needed for sprite batching efficiency