"""main.py — Game entry point and main loop.

exports: main()
used_by: CLI execution
rules:   Must maintain 60 FPS target, clean shutdown on SIGINT
agent:   Game Director | 2024-01-15 | Created main game loop with performance monitoring
"""

import sys
import time
import signal
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import game modules
try:
    from gameplay.game import Game
    from integration.performance import PerformanceMonitor
except ImportError as e:
    logger.error(f"Failed to import game modules: {e}")
    logger.error("Please ensure all modules are properly implemented")
    sys.exit(1)


class GameApplication:
    """Main game application coordinating all modules.
    
    Rules: Must handle graceful shutdown and maintain performance targets.
    """
    
    def __init__(self):
        self.game: Optional[Game] = None
        self.monitor: Optional[PerformanceMonitor] = None
        self.running = False
        self.target_fps = 60
        self.target_frame_time = 1.0 / self.target_fps
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
    def initialize(self) -> bool:
        """Initialize all game modules.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing game application...")
            
            # Initialize performance monitor first
            self.monitor = PerformanceMonitor()
            
            # Initialize game
            self.game = Game()
            if not self.game.initialize():
                logger.error("Failed to initialize game")
                return False
                
            logger.info("Game application initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize game application: {e}")
            return False
    
    def run(self) -> int:
        """Run the main game loop.
        
        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        if not self.initialize():
            return 1
            
        self.running = True
        logger.info(f"Starting game loop with target FPS: {self.target_fps}")
        
        try:
            # Main game loop
            while self.running:
                frame_start = time.perf_counter()
                
                # Update game state
                if not self.game.update():
                    logger.warning("Game update returned False, stopping...")
                    break
                
                # Render frame
                self.game.render()
                
                # Calculate frame time and sleep if needed
                frame_time = time.perf_counter() - frame_start
                self.monitor.record_frame(frame_time)
                
                # Maintain target FPS
                if frame_time < self.target_frame_time:
                    sleep_time = self.target_frame_time - frame_time
                    time.sleep(sleep_time)
                else:
                    # Frame took too long - log warning if consistently slow
                    if frame_time > self.target_frame_time * 1.1:  # 10% over budget
                        self.monitor.record_slow_frame(frame_time)
                
                # Check performance warnings
                if self.monitor.should_warn():
                    warnings = self.monitor.get_warnings()
                    for warning in warnings:
                        logger.warning(warning)
                
        except KeyboardInterrupt:
            logger.info("Game interrupted by user")
        except Exception as e:
            logger.error(f"Unexpected error in game loop: {e}")
            return 1
        finally:
            self.shutdown()
            
        return 0
    
    def shutdown(self):
        """Shutdown all game modules gracefully."""
        logger.info("Shutting down game application...")
        
        if self.game:
            self.game.shutdown()
            
        if self.monitor:
            self.monitor.report()
            
        logger.info("Game application shutdown complete")


def main() -> int:
    """Main entry point for the game.
    
    Returns:
        int: Exit code to return to OS
    """
    app = GameApplication()
    return app.run()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)