#!/usr/bin/env python3
"""
Simple demonstration of the game architecture.
This runs a mock version of the game without requiring OpenGL/GLFW.
"""

import sys
import time
from typing import Dict, Any


class MockGameEngine:
    """Mock engine for demonstration."""
    
    def __init__(self, title="Mock Game", width=800, height=600):
        self.title = title
        self.width = width
        self.height = height
        self.frame_count = 0
        self.start_time = time.time()
    
    def process_input(self):
        """Mock input processing."""
        pass
    
    def should_close(self):
        """Check if should close."""
        return self.frame_count >= 300  # Run for 300 frames
    
    def end_frame(self):
        """End frame."""
        self.frame_count += 1
    
    def get_time(self):
        """Get current time."""
        return time.time() - self.start_time
    
    def shutdown(self):
        """Shutdown."""
        print("Mock engine shutdown")


class MockRenderer:
    """Mock renderer for demonstration."""
    
    def __init__(self):
        self.draw_calls = 0
    
    def render(self, render_data, alpha=0.0):
        """Mock rendering."""
        entities = render_data.get('entities', [])
        self.draw_calls += len(entities)
    
    def shutdown(self):
        """Shutdown."""
        print(f"Mock renderer shutdown (draw calls: {self.draw_calls})")


class MockGameState:
    """Mock game state for demonstration."""
    
    def __init__(self):
        self.entities = []
        self.game_time = 0.0
        
        # Create some mock entities
        for i in range(100):
            self.entities.append({
                'id': f'entity_{i}',
                'position': [i * 0.1, 0, 0],
                'mesh_id': f'mesh_{i % 5}'
            })
    
    def fixed_update(self, dt):
        """Fixed update."""
        self.game_time += dt
        
        # Simple movement
        for entity in self.entities:
            entity['position'][0] += 0.1 * dt
    
    def variable_update(self, dt, alpha):
        """Variable update."""
        pass
    
    def get_render_data(self):
        """Get render data."""
        return {
            'entities': self.entities,
            'camera': {'position': [0, 0, 10], 'target': [0, 0, 0]},
            'lights': [{'position': [5, 5, 5], 'color': [1, 1, 1]}],
            'ui_elements': [{'type': 'fps_counter', 'position': [10, 10]}]
        }
    
    def shutdown(self):
        """Shutdown."""
        print(f"Mock game state shutdown (game time: {self.game_time:.2f}s)")


def run_mock_game():
    """Run a mock version of the game to demonstrate architecture."""
    print("=" * 60)
    print("Game Architecture Demonstration")
    print("=" * 60)
    
    # Create mock components
    engine = MockGameEngine("Architecture Demo", 1280, 720)
    renderer = MockRenderer()
    game_state = MockGameState()
    
    # Game loop variables
    target_fps = 60
    target_frame_time = 1.0 / target_fps
    max_frame_time = 0.1
    
    current_time = time.perf_counter()
    accumulator = 0.0
    fixed_dt = 1.0 / target_fps
    
    frame_times = []
    fps_history = []
    frame_count = 0
    fps_timer = current_time
    fps_counter = 0
    
    print("\nStarting mock game loop...")
    print(f"Target FPS: {target_fps}")
    print(f"Target frame time: {target_frame_time*1000:.2f}ms")
    
    try:
        while not engine.should_close():
            # Calculate delta time
            new_time = time.perf_counter()
            frame_time = new_time - current_time
            
            # Cap frame time
            if frame_time > max_frame_time:
                frame_time = max_frame_time
            
            current_time = new_time
            accumulator += frame_time
            
            # Process input
            engine.process_input()
            
            # Fixed updates
            update_count = 0
            max_updates = 5
            
            while accumulator >= fixed_dt and update_count < max_updates:
                game_state.fixed_update(fixed_dt)
                accumulator -= fixed_dt
                update_count += 1
            
            # Variable update
            alpha = accumulator / fixed_dt
            game_state.variable_update(frame_time, alpha)
            
            # Render
            render_data = game_state.get_render_data()
            renderer.render(render_data, alpha)
            
            # End frame
            engine.end_frame()
            
            # Track performance
            frame_count += 1
            fps_counter += 1
            frame_times.append(frame_time * 1000)  # Convert to ms
            
            # Calculate FPS every second
            if current_time - fps_timer >= 1.0:
                fps = fps_counter / (current_time - fps_timer)
                fps_history.append(fps)
                
                # Keep only last 60 FPS measurements
                if len(fps_history) > 60:
                    fps_history.pop(0)
                
                # Print FPS every 5 seconds
                if frame_count % (target_fps * 5) == 0:
                    avg_fps = sum(fps_history) / len(fps_history)
                    avg_frame_time = sum(frame_times[-target_fps:]) / min(target_fps, len(frame_times))
                    print(f"Frame {frame_count:4d} | FPS: {fps:5.1f} (Avg: {avg_fps:5.1f}) | Frame: {avg_frame_time:5.2f}ms")
                
                fps_counter = 0
                fps_timer = current_time
            
            # Simple sleep to approximate target FPS
            elapsed = time.perf_counter() - current_time
            if elapsed < target_frame_time:
                time.sleep(target_frame_time - elapsed)
        
        # Calculate final statistics
        total_time = engine.get_time()
        avg_fps = frame_count / total_time if total_time > 0 else 0
        avg_frame_time = sum(frame_times) / len(frame_times) if frame_times else 0
        
        print("\n" + "=" * 60)
        print("Game Loop Statistics:")
        print(f"  Total Frames: {frame_count}")
        print(f"  Total Time: {total_time:.2f}s")
        print(f"  Average FPS: {avg_fps:.1f}")
        print(f"  Average Frame Time: {avg_frame_time:.2f}ms")
        
        # Frame time distribution
        under_16ms = sum(1 for t in frame_times if t <= 16.67)
        over_33ms = sum(1 for t in frame_times if t > 33.33)
        
        print(f"\nFrame Time Distribution:")
        print(f"  ≤ 16.67ms (60 FPS): {under_16ms/len(frame_times)*100:.1f}%")
        print(f"  > 33.33ms (<30 FPS): {over_33ms/len(frame_times)*100:.1f}%")
        
    except KeyboardInterrupt:
        print("\nGame interrupted by user")
    
    finally:
        # Clean shutdown
        print("\n" + "=" * 60)
        print("Shutting down...")
        game_state.shutdown()
        renderer.shutdown()
        engine.shutdown()
        print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(run_mock_game())