"""ui.py — UI rendering functions.

exports: draw_ui() -> None
used_by: render/main.py → draw_ui
rules:   Must render health bars, inventory, quest log
agent:   GraphicsSpecialist | 2024-03-29 | Created UI rendering functions
"""

import pygame
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class UIRenderer:
    """UI renderer for game HUD elements."""
    
    def __init__(self, renderer: Any):
        """Initialize UI renderer.
        
        Args:
            renderer: PygameRenderer instance
        """
        self._renderer = renderer
        self._fonts: Dict[int, pygame.font.Font] = {}
        self._ui_elements: Dict[str, Dict[str, Any]] = {}
        
    def draw_health_bar(self, position: tuple, size: tuple, 
                       current_health: float, max_health: float,
                       color: tuple = (0, 255, 0, 255),
                       background_color: tuple = (255, 0, 0, 255),
                       border_color: tuple = (255, 255, 255, 255)) -> None:
        """Draw a health bar.
        
        Args:
            position: (x, y) screen position
            size: (width, height) of health bar
            current_health: Current health value
            max_health: Maximum health value
            color: Health fill color (RGBA)
            background_color: Background color (RGBA)
            border_color: Border color (RGBA)
        """
        if not self._renderer.initialized or not self._renderer.screen:
            return
        
        screen = self._renderer.screen
        
        # Calculate health ratio
        health_ratio = max(0.0, min(1.0, current_health / max_health))
        
        # Draw background
        bg_rect = pygame.Rect(position[0], position[1], size[0], size[1])
        pygame.draw.rect(screen, background_color, bg_rect)
        
        # Draw health fill
        fill_width = int(size[0] * health_ratio)
        if fill_width > 0:
            fill_rect = pygame.Rect(position[0], position[1], fill_width, size[1])
            pygame.draw.rect(screen, color, fill_rect)
        
        # Draw border
        pygame.draw.rect(screen, border_color, bg_rect, 2)
        
        # Draw health text
        health_text = f"{int(current_health)}/{int(max_health)}"
        font = self._get_font(20)
        if font:
            text_surface = font.render(health_text, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=bg_rect.center)
            screen.blit(text_surface, text_rect)
    
    def draw_inventory(self, position: tuple, items: list, 
                      selected_index: int = 0) -> None:
        """Draw inventory overlay.
        
        Args:
            position: (x, y) screen position
            items: List of item names or icons
            selected_index: Currently selected item index
        """
        if not self._renderer.initialized or not self._renderer.screen:
            return
        
        screen = self._renderer.screen
        font = self._get_font(18)
        
        # Draw inventory background
        bg_width = 200
        bg_height = 40 + len(items) * 40
        bg_rect = pygame.Rect(position[0], position[1], bg_width, bg_height)
        pygame.draw.rect(screen, (30, 30, 40, 220), bg_rect)
        pygame.draw.rect(screen, (100, 100, 120, 255), bg_rect, 2)
        
        # Draw title
        if font:
            title = font.render("INVENTORY", True, (255, 255, 255))
            title_rect = title.get_rect(centerx=bg_rect.centerx, top=bg_rect.top + 10)
            screen.blit(title, title_rect)
        
        # Draw items
        for i, item in enumerate(items):
            item_y = bg_rect.top + 50 + i * 40
            
            # Draw item background (highlight if selected)
            item_color = (60, 60, 80, 200) if i != selected_index else (80, 100, 120, 200)
            item_rect = pygame.Rect(bg_rect.left + 10, item_y, bg_width - 20, 30)
            pygame.draw.rect(screen, item_color, item_rect)
            
            # Draw item text
            if font:
                item_text = font.render(str(item), True, (255, 255, 255))
                item_text_rect = item_text.get_rect(center=item_rect.center)
                screen.blit(item_text, item_text_rect)
    
    def draw_quest_log(self, position: tuple, quests: list) -> None:
        """Draw quest log panel.
        
        Args:
            position: (x, y) screen position
            quests: List of quest dictionaries with 'title', 'description', 'progress'
        """
        if not self._renderer.initialized or not self._renderer.screen:
            return
        
        screen = self._renderer.screen
        font_title = self._get_font(20)
        font_desc = self._get_font(16)
        
        # Calculate panel size
        panel_width = 300
        panel_height = 100 + len(quests) * 120
        
        # Draw panel background
        panel_rect = pygame.Rect(position[0], position[1], panel_width, panel_height)
        pygame.draw.rect(screen, (40, 40, 60, 220), panel_rect)
        pygame.draw.rect(screen, (120, 120, 140, 255), panel_rect, 2)
        
        # Draw title
        if font_title:
            title = font_title.render("QUEST LOG", True, (255, 255, 200))
            title_rect = title.get_rect(centerx=panel_rect.centerx, top=panel_rect.top + 10)
            screen.blit(title, title_rect)
        
        # Draw quests
        y_offset = 50
        for quest in quests:
            quest_y = panel_rect.top + y_offset
            
            # Draw quest background
            quest_rect = pygame.Rect(panel_rect.left + 10, quest_y, panel_width - 20, 100)
            pygame.draw.rect(screen, (60, 60, 80, 180), quest_rect)
            pygame.draw.rect(screen, (100, 100, 120, 255), quest_rect, 1)
            
            # Draw quest title
            if font_title and 'title' in quest:
                title_text = font_title.render(quest['title'], True, (255, 255, 150))
                title_rect = title_text.get_rect(left=quest_rect.left + 10, top=quest_rect.top + 10)
                screen.blit(title_text, title_rect)
            
            # Draw quest description
            if font_desc and 'description' in quest:
                # Wrap text
                desc = quest['description']
                words = desc.split()
                lines = []
                current_line = []
                
                for word in words:
                    current_line.append(word)
                    test_line = ' '.join(current_line)
                    if font_desc.size(test_line)[0] > quest_rect.width - 20:
                        current_line.pop()
                        lines.append(' '.join(current_line))
                        current_line = [word]
                
                if current_line:
                    lines.append(' '.join(current_line))
                
                # Draw lines
                line_y = quest_rect.top + 40
                for line in lines[:2]:  # Limit to 2 lines
                    line_text = font_desc.render(line, True, (220, 220, 220))
                    line_rect = line_text.get_rect(left=quest_rect.left + 10, top=line_y)
                    screen.blit(line_text, line_rect)
                    line_y += 20
            
            # Draw quest progress
            if 'progress' in quest:
                progress = max(0.0, min(1.0, quest['progress']))
                progress_width = int((quest_rect.width - 20) * progress)
                
                progress_rect = pygame.Rect(
                    quest_rect.left + 10,
                    quest_rect.bottom - 25,
                    progress_width,
                    15
                )
                pygame.draw.rect(screen, (0, 200, 0, 200), progress_rect)
                
                # Draw progress text
                if font_desc:
                    progress_text = f"{int(progress * 100)}%"
                    text_surface = font_desc.render(progress_text, True, (255, 255, 255))
                    text_rect = text_surface.get_rect(center=progress_rect.center)
                    screen.blit(text_surface, text_rect)
            
            y_offset += 120
    
    def draw_minimap(self, position: tuple, size: tuple, 
                    player_pos: tuple, world_size: tuple,
                    points_of_interest: list = None) -> None:
        """Draw minimap.
        
        Args:
            position: (x, y) screen position
            size: (width, height) of minimap
            player_pos: (x, y) player position in world
            world_size: (width, height) of world
            points_of_interest: List of POI dicts with 'pos', 'color', 'type'
        """
        if not self._renderer.initialized or not self._renderer.screen:
            return
        
        screen = self._renderer.screen
        points_of_interest = points_of_interest or []
        
        # Draw minimap background
        map_rect = pygame.Rect(position[0], position[1], size[0], size[1])
        pygame.draw.rect(screen, (20, 20, 40, 200), map_rect)
        pygame.draw.rect(screen, (80, 80, 100, 255), map_rect, 2)
        
        # Calculate scale
        scale_x = size[0] / world_size[0]
        scale_y = size[1] / world_size[1]
        
        # Draw points of interest
        for poi in points_of_interest:
            if 'pos' in poi and 'color' in poi:
                poi_x = position[0] + poi['pos'][0] * scale_x
                poi_y = position[1] + poi['pos'][1] * scale_y
                
                # Draw different shapes based on type
                if poi.get('type') == 'enemy':
                    pygame.draw.circle(screen, poi['color'], (int(poi_x), int(poi_y)), 3)
                elif poi.get('type') == 'item':
                    pygame.draw.rect(screen, poi['color'], 
                                   pygame.Rect(poi_x - 2, poi_y - 2, 4, 4))
                else:
                    pygame.draw.circle(screen, poi['color'], (int(poi_x), int(poi_y)), 2)
        
        # Draw player
        player_x = position[0] + player_pos[0] * scale_x
        player_y = position[1] + player_pos[1] * scale_y
        pygame.draw.circle(screen, (0, 255, 0), (int(player_x), int(player_y)), 4)
        
        # Draw player direction (simple triangle)
        # In a real implementation, this would use player rotation
    
    def _get_font(self, size: int) -> Optional[pygame.font.Font]:
        """Get or create font of specified size.
        
        Args:
            size: Font size
            
        Returns:
            pygame.font.Font or None if failed
        """
        if size not in self._fonts:
            try:
                self._fonts[size] = pygame.font.Font(None, size)
            except:
                logger.warning(f"Failed to create font size {size}")
                return None
        
        return self._fonts[size]


# Global UI renderer instance
_ui_renderer: Optional[UIRenderer] = None


def draw_ui(renderer: Any = None) -> None:
    """Draw UI elements.
    
    Args:
        renderer: PygameRenderer instance (optional if already initialized)
    """
    global _ui_renderer
    
    if renderer and _ui_renderer is None:
        _ui_renderer = UIRenderer(renderer)
    
    if _ui_renderer is None:
        logger.warning("UI renderer not initialized")
        return
    
    # Example usage - in a real game, this would be called with actual game data
    # _ui_renderer.draw_health_bar((20, 20), (200, 30), 75, 100)
    # _ui_renderer.draw_inventory((20, 70), ["Sword", "Shield", "Potion", "Key"])
    # _ui_renderer.draw_quest_log((20, 250), [
    #     {"title": "Find the Artifact", "description": "Locate the ancient artifact in the ruins", "progress": 0.3},
    #     {"title": "Defeat the Dragon", "description": "Slay the dragon terrorizing the village", "progress": 0.8}
    # ])