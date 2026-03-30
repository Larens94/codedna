"""
Time management system.
Handles game timing, delta time calculations, and time scaling.
"""

import time
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class TimeSample:
    """A sample of time data for performance tracking."""
    
    timestamp: float
    frame_time: float
    delta_time: float
    fps: float


class TimeManager:
    """
    Manages game timing with support for fixed and variable timesteps,
    time scaling, and performance tracking.
    """
    
    def __init__(self, target_fps: int = 60):
        """
        Initialize the time manager.
        
        Args:
            target_fps: Target frames per second
        """
        # Timing constants
        self.target_fps = target_fps
        self.target_frame_time = 1.0 / target_fps
        self.max_frame_time = 0.1  # Maximum frame time to prevent spiral of death
        
        # Current time state
        self.real_time = 0.0
        self.game_time = 0.0
        self.delta_time = 0.0
        self.fixed_delta_time = self.target_frame_time
        
        # Time scaling
        self.time_scale = 1.0
        self.min_time_scale = 0.0
        self.max_time_scale = 10.0
        
        # Frame tracking
        self.frame_count = 0
        self.fps = 0.0
        self.frame_times: List[float] = []
        self.max_frame_history = 60  # Keep last second of frame times
        
        # Performance samples
        self.samples: List[TimeSample] = []
        self.max_samples = 300  # Keep 5 seconds at 60 FPS
        
        # Internal timing
        self._last_real_time = 0.0
        self._last_game_time = 0.0
        self._start_time = time.perf_counter()
        self._fps_timer = self._start_time
        self._fps_counter = 0
        
        # Fixed timestep accumulator
        self._accumulator = 0.0
        self._max_updates_per_frame = 5  # Prevent spiral of death
        
        # Pause state
        self._is_paused = False
        self._pause_time = 0.0
        
        # Slow motion
        self._slow_motion_factor = 1.0
        self._slow_motion_duration = 0.0
        self._slow_motion_timer = 0.0
    
    def update(self, dt: float):
        """
        Update time manager with current frame's delta time.
        
        Args:
            dt: Raw delta time from the game loop
        """
        # Cap delta time to prevent spiral of death
        if dt > self.max_frame_time:
            dt = self.max_frame_time
        
        # Update real time
        self.real_time = time.perf_counter() - self._start_time
        
        # Apply time scaling
        scaled_dt = dt * self.time_scale
        
        # Update game time if not paused
        if not self._is_paused:
            self.game_time += scaled_dt
        
        # Store delta time
        self.delta_time = scaled_dt
        
        # Update frame tracking
        self.frame_count += 1
        self._fps_counter += 1
        
        # Track frame times
        self.frame_times.append(dt * 1000)  # Convert to milliseconds
        if len(self.frame_times) > self.max_frame_history:
            self.frame_times.pop(0)
        
        # Calculate FPS every second
        current_time = self.real_time
        if current_time - self._fps_timer >= 1.0:
            self.fps = self._fps_counter / (current_time - self._fps_timer)
            self._fps_counter = 0
            self._fps_timer = current_time
            
            # Store sample
            sample = TimeSample(
                timestamp=current_time,
                frame_time=dt * 1000,
                delta_time=scaled_dt,
                fps=self.fps
            )
            self.samples.append(sample)
            if len(self.samples) > self.max_samples:
                self.samples.pop(0)
        
        # Update slow motion timer
        if self._slow_motion_duration > 0:
            self._slow_motion_timer += dt
            if self._slow_motion_timer >= self._slow_motion_duration:
                self.set_time_scale(1.0)
                self._slow_motion_duration = 0.0
                self._slow_motion_timer = 0.0
        
        # Store for next frame
        self._last_real_time = self.real_time
        self._last_game_time = self.game_time
    
    def get_delta_time(self) -> float:
        """
        Get the current delta time (scaled by time scale).
        
        Returns:
            Scaled delta time in seconds
        """
        return self.delta_time
    
    def get_fixed_delta_time(self) -> float:
        """
        Get the fixed delta time for physics.
        
        Returns:
            Fixed delta time in seconds
        """
        return self.fixed_delta_time
    
    def get_real_delta_time(self) -> float:
        """
        Get the real (unscaled) delta time.
        
        Returns:
            Real delta time in seconds
        """
        return self.delta_time / self.time_scale if self.time_scale > 0 else 0.0
    
    def get_game_time(self) -> float:
        """
        Get the current game time.
        
        Returns:
            Game time in seconds
        """
        return self.game_time
    
    def get_real_time(self) -> float:
        """
        Get the current real time.
        
        Returns:
            Real time in seconds
        """
        return self.real_time
    
    def get_fps(self) -> float:
        """
        Get current frames per second.
        
        Returns:
            Current FPS
        """
        return self.fps
    
    def get_frame_count(self) -> int:
        """
        Get total frame count.
        
        Returns:
            Frame count
        """
        return self.frame_count
    
    def set_time_scale(self, scale: float):
        """
        Set the time scale (1.0 = normal, 0.5 = half speed, 2.0 = double speed).
        
        Args:
            scale: Time scale factor
        """
        self.time_scale = max(self.min_time_scale, min(scale, self.max_time_scale))
    
    def get_time_scale(self) -> float:
        """
        Get the current time scale.
        
        Returns:
            Current time scale
        """
        return self.time_scale
    
    def pause(self):
        """Pause the game time."""
        if not self._is_paused:
            self._is_paused = True
            self._pause_time = self.game_time
    
    def resume(self):
        """Resume the game time."""
        if self._is_paused:
            self._is_paused = False
            # Adjust game time to account for pause duration
            pause_duration = self.game_time - self._pause_time
            self.game_time = self._pause_time
    
    def is_paused(self) -> bool:
        """
        Check if game time is paused.
        
        Returns:
            True if paused
        """
        return self._is_paused
    
    def slow_motion(self, factor: float = 0.5, duration: float = 1.0):
        """
        Apply slow motion effect.
        
        Args:
            factor: Slow motion factor (0.1 = 10% speed, 0.5 = 50% speed)
            duration: Duration in seconds
        """
        self.set_time_scale(factor)
        self._slow_motion_factor = factor
        self._slow_motion_duration = duration
        self._slow_motion_timer = 0.0
    
    def is_in_slow_motion(self) -> bool:
        """
        Check if slow motion is active.
        
        Returns:
            True if in slow motion
        """
        return self._slow_motion_duration > 0
    
    def get_frame_time_stats(self) -> dict:
        """
        Get frame time statistics.
        
        Returns:
            Dictionary with frame time statistics
        """
        if not self.frame_times:
            return {
                'avg': 0.0,
                'min': 0.0,
                'max': 0.0,
                'current': 0.0
            }
        
        return {
            'avg': sum(self.frame_times) / len(self.frame_times),
            'min': min(self.frame_times),
            'max': max(self.frame_times),
            'current': self.frame_times[-1] if self.frame_times else 0.0
        }
    
    def get_performance_summary(self) -> dict:
        """
        Get performance summary.
        
        Returns:
            Dictionary with performance statistics
        """
        frame_stats = self.get_frame_time_stats()
        
        # Calculate frame time distribution
        under_16ms = sum(1 for t in self.frame_times if t <= 16.67)
        over_33ms = sum(1 for t in self.frame_times if t > 33.33)
        total_frames = len(self.frame_times)
        
        distribution = {
            'under_16ms': under_16ms / total_frames * 100 if total_frames > 0 else 0.0,
            'over_33ms': over_33ms / total_frames * 100 if total_frames > 0 else 0.0
        }
        
        return {
            'fps': self.fps,
            'frame_count': self.frame_count,
            'game_time': self.game_time,
            'real_time': self.real_time,
            'time_scale': self.time_scale,
            'frame_time': frame_stats,
            'distribution': distribution,
            'is_paused': self._is_paused,
            'is_slow_motion': self.is_in_slow_motion()
        }
    
    def reset(self):
        """Reset all timing statistics."""
        self.frame_count = 0
        self.fps = 0.0
        self.frame_times.clear()
        self.samples.clear()
        self._fps_counter = 0
        self._fps_timer = time.perf_counter()
    
    def calculate_fixed_updates(self, dt: float) -> int:
        """
        Calculate how many fixed updates are needed for this frame.
        
        Args:
            dt: Current delta time
            
        Returns:
            Number of fixed updates needed
        """
        self._accumulator += dt
        
        # Cap accumulator to prevent spiral of death
        max_accumulator = self.fixed_delta_time * self._max_updates_per_frame
        if self._accumulator > max_accumulator:
            self._accumulator = max_accumulator
        
        # Calculate number of fixed updates
        update_count = 0
        while self._accumulator >= self.fixed_delta_time and update_count < self._max_updates_per_frame:
            self._accumulator -= self.fixed_delta_time
            update_count += 1
        
        return update_count
    
    def get_interpolation_alpha(self) -> float:
        """
        Get interpolation alpha for smooth rendering between fixed updates.
        
        Returns:
            Interpolation alpha (0.0 to 1.0)
        """
        if self.fixed_delta_time > 0:
            return self._accumulator / self.fixed_delta_time
        return 0.0
    
    def sleep_if_ahead(self, current_time: float):
        """
        Sleep if we're ahead of target frame rate to save power.
        
        Args:
            current_time: Current time in seconds
        """
        elapsed = time.perf_counter() - current_time
        
        if elapsed < self.target_frame_time:
            sleep_time = self.target_frame_time - elapsed - 0.001  # 1ms buffer
            if sleep_time > 0.001:  # Only sleep if significant time
                time.sleep(sleep_time)