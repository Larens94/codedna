"""performance.py — Performance monitoring and FPS tracking.

exports: PerformanceMonitor class
used_by: main.py → GameApplication._monitor
rules:   Must have minimal overhead to not affect measurements
agent:   Game Director | 2024-01-15 | Created performance monitoring system
"""

import time
import statistics
from typing import List, Dict, Optional
from collections import deque
import logging

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor game performance and maintain 60 FPS target.
    
    Rules:
    - Overhead must be < 0.1ms per frame
    - Tracks frame times, FPS, and slow frames
    - Provides warnings when performance degrades
    """
    
    def __init__(self, window_size: int = 300):
        """Initialize performance monitor.
        
        Args:
            window_size: Number of frames to track for averages
        """
        self.window_size = window_size
        self.frame_times = deque(maxlen=window_size)
        self.slow_frames = deque(maxlen=100)  # Track last 100 slow frames
        self.frame_count = 0
        self.total_time = 0.0
        self.start_time = time.perf_counter()
        
        # Performance thresholds (in seconds)
        self.target_frame_time = 1.0 / 60.0  # 60 FPS
        self.warning_threshold = self.target_frame_time * 1.1  # 10% over
        self.critical_threshold = self.target_frame_time * 1.5  # 50% over
        
        # Statistics
        self.min_frame_time = float('inf')
        self.max_frame_time = 0.0
        
        # Warnings
        self.warnings = []
        self.last_warning_time = 0
        self.warning_cooldown = 5.0  # seconds between warnings
        
    def record_frame(self, frame_time: float) -> None:
        """Record frame time for performance tracking.
        
        Args:
            frame_time: Time taken for frame in seconds
        """
        self.frame_times.append(frame_time)
        self.frame_count += 1
        self.total_time += frame_time
        
        # Update min/max
        if frame_time < self.min_frame_time:
            self.min_frame_time = frame_time
        if frame_time > self.max_frame_time:
            self.max_frame_time = frame_time
        
        # Check for slow frame
        if frame_time > self.warning_threshold:
            self.slow_frames.append((time.time(), frame_time))
    
    def record_slow_frame(self, frame_time: float) -> None:
        """Record a frame that exceeded budget.
        
        Args:
            frame_time: Time taken for slow frame
        """
        self.slow_frames.append((time.time(), frame_time))
    
    def get_current_fps(self) -> float:
        """Get current FPS based on recent frames.
        
        Returns:
            Current frames per second
        """
        if not self.frame_times:
            return 0.0
        
        # Average of last N frames
        avg_frame_time = statistics.mean(self.frame_times)
        return 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
    
    def get_average_fps(self) -> float:
        """Get average FPS since start.
        
        Returns:
            Average frames per second
        """
        if self.total_time == 0:
            return 0.0
        return self.frame_count / self.total_time
    
    def get_frame_time_stats(self) -> Dict[str, float]:
        """Get frame time statistics.
        
        Returns:
            Dictionary with min, max, avg, and current frame times
        """
        if not self.frame_times:
            return {
                'min': 0.0,
                'max': 0.0,
                'avg': 0.0,
                'current': 0.0,
                'fps': 0.0
            }
        
        current_frame_time = self.frame_times[-1] if self.frame_times else 0.0
        
        return {
            'min': self.min_frame_time,
            'max': self.max_frame_time,
            'avg': statistics.mean(self.frame_times),
            'current': current_frame_time,
            'fps': self.get_current_fps()
        }
    
    def get_slow_frame_count(self, threshold: Optional[float] = None) -> int:
        """Count slow frames exceeding threshold.
        
        Args:
            threshold: Optional custom threshold (default: warning_threshold)
            
        Returns:
            Number of slow frames in recent history
        """
        if threshold is None:
            threshold = self.warning_threshold
        
        count = 0
        for _, frame_time in self.slow_frames:
            if frame_time > threshold:
                count += 1
        return count
    
    def should_warn(self) -> bool:
        """Check if performance warnings should be issued.
        
        Returns:
            True if warnings should be issued
        """
        current_time = time.time()
        
        # Cooldown check
        if current_time - self.last_warning_time < self.warning_cooldown:
            return False
        
        # Check for sustained poor performance
        if len(self.frame_times) < 10:
            return False
        
        # Check if recent frames are consistently slow
        recent_frames = list(self.frame_times)[-10:]  # Last 10 frames
        slow_count = sum(1 for ft in recent_frames if ft > self.warning_threshold)
        
        if slow_count >= 5:  # 50% of recent frames are slow
            self.last_warning_time = current_time
            return True
        
        # Check for critical frames
        critical_count = sum(1 for ft in recent_frames if ft > self.critical_threshold)
        if critical_count > 0:
            self.last_warning_time = current_time
            return True
        
        return False
    
    def get_warnings(self) -> List[str]:
        """Get current performance warnings.
        
        Returns:
            List of warning messages
        """
        warnings = []
        current_time = time.time()
        
        # Don't warn too frequently
        if current_time - self.last_warning_time < 1.0:
            return warnings
        
        stats = self.get_frame_time_stats()
        
        # Check current FPS
        current_fps = stats['fps']
        if current_fps < 55:  # Below 55 FPS is concerning for 60 FPS target
            warnings.append(f"Low FPS: {current_fps:.1f} (target: 60)")
        
        # Check frame time consistency
        if stats['max'] > stats['avg'] * 2.0 and stats['max'] > self.target_frame_time:
            warnings.append(f"Frame time spikes: max {stats['max']*1000:.1f}ms vs avg {stats['avg']*1000:.1f}ms")
        
        # Check for many slow frames
        slow_count = self.get_slow_frame_count()
        if slow_count > 20:  # More than 20 slow frames in history
            warnings.append(f"Many slow frames: {slow_count} exceeding {self.warning_threshold*1000:.1f}ms")
        
        return warnings
    
    def report(self) -> None:
        """Print performance report."""
        if self.frame_count == 0:
            logger.info("No frames recorded")
            return
        
        stats = self.get_frame_time_stats()
        avg_fps = self.get_average_fps()
        slow_count = self.get_slow_frame_count()
        
        logger.info("=" * 50)
        logger.info("PERFORMANCE REPORT")
        logger.info("=" * 50)
        logger.info(f"Total frames: {self.frame_count}")
        logger.info(f"Total time: {self.total_time:.2f}s")
        logger.info(f"Average FPS: {avg_fps:.1f}")
        logger.info(f"Current FPS: {stats['fps']:.1f}")
        logger.info(f"Frame times: min={stats['min']*1000:.1f}ms, "
                   f"avg={stats['avg']*1000:.1f}ms, "
                   f"max={stats['max']*1000:.1f}ms")
        logger.info(f"Slow frames (> {self.warning_threshold*1000:.1f}ms): {slow_count}")
        logger.info(f"60 FPS target: {'✓' if avg_fps >= 58 else '✗'} "
                   f"({'OK' if avg_fps >= 58 else 'NEEDS OPTIMIZATION'})")
        logger.info("=" * 50)
        
        # Detailed slow frame analysis
        if slow_count > 0:
            logger.info("Slow frame analysis:")
            recent_slow = list(self.slow_frames)[-5:]  # Last 5 slow frames
            for timestamp, frame_time in recent_slow:
                time_str = time.strftime('%H:%M:%S', time.localtime(timestamp))
                logger.info(f"  {time_str}: {frame_time*1000:.1f}ms "
                          f"({frame_time/self.target_frame_time:.1f}x target)")
    
    def reset(self) -> None:
        """Reset all performance counters."""
        self.frame_times.clear()
        self.slow_frames.clear()
        self.frame_count = 0
        self.total_time = 0.0
        self.start_time = time.perf_counter()
        self.min_frame_time = float('inf')
        self.max_frame_time = 0.0
        self.warnings.clear()
        logger.debug("Performance monitor reset")