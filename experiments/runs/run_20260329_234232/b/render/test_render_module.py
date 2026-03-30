"""
Test script for the 2D RPG render module.
"""

import pygame
import sys
from typing import Dict, Any

# Initialize Pygame
pygame.init()

# Create window
screen_width = 1280
screen_height = 720
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("2D RPG Render Module Test")
clock = pygame.time.Clock()

# Import render modules
from render.sprite_renderer import SpriteRenderer
from render.camera import CameraSystem, CameraConfig
from render.ui_renderer import UIRenderer, HealthBar, Panel, Button, TextLabel
from render.animation import AnimationSystem, Animation, AnimationFrame, AnimationState
from render.particles import ParticleSystem
from render.tilemap import TilemapRenderer

def test_sprite_renderer():
    """Test sprite rendering system."""
    print("Testing SpriteRenderer...")
    
    sprite_renderer = SpriteRenderer(screen)
    
    # Create test texture (simple colored surface)
    test_texture = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(test_texture, (255, 0, 0), (16, 16), 16)
    sprite_renderer.textures["test_sprite"] = test_texture
    
    # Create sprites
    sprite_ids = []
    for i in range(5):
        sprite_id = sprite_renderer.create_sprite(
            texture_id="test_sprite",
            position=(100 + i * 50, 100),
            z_index=i
        )
        sprite_ids.append(sprite_id)
    
    # Update a sprite
    sprite_renderer.update_sprite(sprite_ids[2], position=(200, 200), scale=(2.0, 2.0))
    
    # Render
    sprite_renderer.clear((0, 0, 50))
    sprite_renderer.render()
    
    stats = sprite_renderer.get_statistics()
    print(f"  Sprites rendered: {stats['sprites_rendered']}")
    print(f"  Draw calls: {stats['draw_calls']}")
    
    return sprite_renderer, sprite_ids

def test_camera_system():
    """Test camera system."""
    print("Testing CameraSystem...")
    
    config = CameraConfig(
        viewport_width=screen_width,
        viewport_height=screen_height,
        zoom=1.0,
        smooth_follow=True,
        follow_speed=5.0
    )
    
    camera = CameraSystem(config)
    camera.set_target((400, 300))
    
    # Test world-to-screen conversion
    world_pos = (100, 100)
    screen_pos = camera.world_to_screen(world_pos)
    print(f"  World {world_pos} -> Screen {screen_pos}")
    
    # Test screen shake
    camera.apply_screen_shake(intensity=10.0, duration=0.5)
    
    return camera

def test_ui_renderer():
    """Test UI rendering system."""
    print("Testing UIRenderer...")
    
    ui_renderer = UIRenderer(screen)
    
    # Create health bar
    health_bar = HealthBar(
        position=(50, 50),
        size=(200, 30)
    )
    health_bar.set_health(75, 100)
    
    # Create panel with button
    panel = Panel(
        position=(400, 50),
        size=(300, 200)
    )
    
    button = Button(
        position=(50, 50),
        size=(200, 50),
        text="Test Button"
    )
    button.on_click = lambda: print("Button clicked!")
    
    label = TextLabel(
        position=(50, 120),
        size=(200, 30),
        text="UI Test Label"
    )
    
    panel.add_child(button)
    panel.add_child(label)
    
    # Add to renderer
    ui_renderer.add_component("health_bar", health_bar)
    ui_renderer.add_component("panel", panel)
    
    # Update and render
    ui_renderer.update(0.016)  # 60 FPS delta
    ui_renderer.render()
    
    stats = ui_renderer.get_statistics()
    print(f"  UI components: {stats['total_components']}")
    
    return ui_renderer

def test_animation_system(sprite_renderer, sprite_id):
    """Test animation system."""
    print("Testing AnimationSystem...")
    
    animation_system = AnimationSystem(sprite_renderer)
    
    # Create simple animation
    frames = [
        AnimationFrame(texture_id="frame1", duration=0.2),
        AnimationFrame(texture_id="frame2", duration=0.2),
        AnimationFrame(texture_id="frame3", duration=0.2),
    ]
    
    animation = Animation(
        name="test_animation",
        frames=frames,
        loop=True
    )
    
    animation_system.register_template(animation)
    
    # Create controller
    controller_id = animation_system.create_controller(sprite_id)
    controller = animation_system.get_controller(controller_id)
    
    if controller:
        controller.play("test_animation")
        print(f"  Animation controller created for sprite: {sprite_id}")
    
    return animation_system

def test_particle_system(sprite_renderer):
    """Test particle system."""
    print("Testing ParticleSystem...")
    
    particle_system = ParticleSystem(sprite_renderer)
    
    # Create test texture for particles
    particle_texture = pygame.Surface((8, 8), pygame.SRCALPHA)
    pygame.draw.circle(particle_texture, (255, 255, 255, 255), (4, 4), 4)
    sprite_renderer.textures["particle"] = particle_texture
    
    # Create spark effect
    emitter_id = particle_system.create_spark_effect((600, 300), intensity=1.0)
    print(f"  Created spark effect: {emitter_id}")
    
    return particle_system

def test_tilemap_renderer(sprite_renderer, camera):
    """Test tilemap rendering."""
    print("Testing TilemapRenderer...")
    
    tilemap_renderer = TilemapRenderer(sprite_renderer, tile_size=(32, 32))
    tilemap_renderer.set_camera(camera)
    
    # Create test tile texture
    tile_texture = pygame.Surface((32, 32))
    tile_texture.fill((100, 150, 100))
    pygame.draw.rect(tile_texture, (80, 120, 80), (0, 0, 32, 32), 2)
    sprite_renderer.textures["grass_tile"] = tile_texture
    
    # Create simple test map
    print("  Note: Tilemap loading from JSON would be tested with actual files")
    
    return tilemap_renderer

def main():
    """Main test function."""
    print("=" * 50)
    print("2D RPG Render Module Test")
    print("=" * 50)
    
    running = True
    delta_time = 0.016  # Approximate 60 FPS
    
    # Initialize systems
    sprite_renderer, sprite_ids = test_sprite_renderer()
    camera = test_camera_system()
    ui_renderer = test_ui_renderer()
    animation_system = test_animation_system(sprite_renderer, sprite_ids[0])
    particle_system = test_particle_system(sprite_renderer)
    tilemap_renderer = test_tilemap_renderer(sprite_renderer, camera)
    
    # Set camera for sprite renderer
    sprite_renderer.set_camera(camera)
    
    print("\n" + "=" * 50)
    print("Test Complete - Press ESC to exit")
    print("=" * 50)
    
    # Main loop
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            
            # Pass events to UI
            ui_renderer.handle_event(event)
        
        # Update systems
        camera.update(delta_time)
        camera.update_interpolation(0.5)  # For smooth rendering
        
        animation_system.update_all(delta_time)
        particle_system.update(delta_time)
        tilemap_renderer.update(delta_time)
        ui_renderer.update(delta_time)
        
        # Render
        sprite_renderer.clear((30, 30, 60))
        
        # Update sprite positions for test
        for i, sprite_id in enumerate(sprite_ids):
            sprite_renderer.update_sprite(
                sprite_id,
                position=(200 + i * 60, 200 + 30 * math.sin(pygame.time.get_ticks() * 0.001 + i))
            )
        
        sprite_renderer.render()
        ui_renderer.render()
        
        # Draw test info
        font = pygame.font.Font(None, 24)
        info_text = [
            "2D RPG Render Module Test",
            "ESC: Exit",
            f"FPS: {int(clock.get_fps())}",
            f"Sprites: {len(sprite_renderer.sprites)}",
            f"Particles: {particle_system.particles_active}"
        ]
        
        for i, text in enumerate(info_text):
            text_surface = font.render(text, True, (255, 255, 255))
            screen.blit(text_surface, (10, 10 + i * 30))
        
        pygame.display.flip()
        delta_time = clock.tick(60) / 1000.0
    
    # Cleanup
    print("\nCleaning up...")
    sprite_renderer.cleanup()
    ui_renderer.cleanup()
    animation_system.cleanup()
    particle_system.cleanup()
    tilemap_renderer.cleanup()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    import math
    main()