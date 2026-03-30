"""
Complete UI rendering system for 2D RPG.
"""

import pygame
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass
import math


@dataclass
class UIComponent:
    """Base class for UI components."""
    position: Tuple[float, float] = (0, 0)
    size: Tuple[float, float] = (100, 50)
    visible: bool = True
    enabled: bool = True
    z_index: int = 0
    parent: Optional[Any] = None
    children: List[Any] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    def update(self, delta_time: float):
        """Update component state."""
        for child in self.children:
            child.update(delta_time)
    
    def render(self, surface: pygame.Surface):
        """Render component to surface."""
        if not self.visible:
            return
        for child in self.children:
            child.render(surface)
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input event."""
        if not self.enabled or not self.visible:
            return False
        for child in reversed(self.children):
            if child.handle_event(event):
                return True
        return False
    
    def add_child(self, child):
        """Add a child component."""
        child.parent = self
        self.children.append(child)
    
    def get_absolute_position(self) -> Tuple[float, float]:
        """Get absolute screen position."""
        if self.parent:
            parent_pos = self.parent.get_absolute_position()
            return (parent_pos[0] + self.position[0],
                    parent_pos[1] + self.position[1])
        return self.position
    
    def get_global_rect(self) -> pygame.Rect:
        """Get global rectangle for hit testing."""
        pos = self.get_absolute_position()
        return pygame.Rect(pos[0], pos[1], self.size[0], self.size[1])


class Panel(UIComponent):
    """Container panel."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (50, 50, 50, 200)
        self.border_color = (100, 100, 100, 255)
        self.border_width = 2
        self.corner_radius = 5
    
    def render(self, surface: pygame.Surface):
        """Render panel."""
        if not self.visible:
            return
        
        pos = self.get_absolute_position()
        rect = pygame.Rect(pos[0], pos[1], self.size[0], self.size[1])
        
        # Draw background
        if self.background_color[3] < 255:
            bg_surface = pygame.Surface(self.size, pygame.SRCALPHA)
            pygame.draw.rect(bg_surface, self.background_color, 
                           (0, 0, self.size[0], self.size[1]),
                           border_radius=self.corner_radius)
            surface.blit(bg_surface, pos)
        else:
            pygame.draw.rect(surface, self.background_color, rect,
                           border_radius=self.corner_radius)
        
        # Draw border
        if self.border_width > 0:
            pygame.draw.rect(surface, self.border_color, rect,
                           self.border_width, border_radius=self.corner_radius)
        
        # Render children
        super().render(surface)


class HealthBar(UIComponent):
    """Health bar component."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.max_health = 100
        self.current_health = 100
        self.background_color = (30, 30, 30, 255)
        self.health_color = (0, 200, 0, 255)
        self.damage_color = (200, 0, 0, 255)
        self.border_color = (255, 255, 255, 255)
        self.border_width = 1
        self.show_text = True
        self.font = None
        self.text_color = (255, 255, 255, 255)
        
        # Animation
        self.display_health = 100.0
        self.health_change_speed = 50.0
    
    def update(self, delta_time: float):
        """Animate health bar."""
        if self.display_health != self.current_health:
            diff = self.current_health - self.display_health
            max_change = self.health_change_speed * delta_time
            
            if abs(diff) <= max_change:
                self.display_health = self.current_health
            else:
                self.display_health += math.copysign(max_change, diff)
        
        super().update(delta_time)
    
    def render(self, surface: pygame.Surface):
        """Render health bar."""
        if not self.visible:
            return
        
        pos = self.get_absolute_position()
        rect = pygame.Rect(pos[0], pos[1], self.size[0], self.size[1])
        
        # Draw background
        pygame.draw.rect(surface, self.background_color, rect)
        
        # Calculate health width
        health_ratio = max(0, min(1, self.display_health / max(1, self.max_health)))
        health_width = int(self.size[0] * health_ratio)
        
        if health_width > 0:
            health_rect = pygame.Rect(pos[0], pos[1], health_width, self.size[1])
            
            # Choose color based on health
            if health_ratio > 0.5:
                color = self.health_color
            elif health_ratio > 0.25:
                t = (health_ratio - 0.25) / 0.25
                color = (
                    int(self.health_color[0] * t + self.damage_color[0] * (1 - t)),
                    int(self.health_color[1] * t + self.damage_color[1] * (1 - t)),
                    int(self.health_color[2] * t + self.damage_color[2] * (1 - t)),
                    255
                )
            else:
                color = self.damage_color
            
            pygame.draw.rect(surface, color, health_rect)
        
        # Draw border
        if self.border_width > 0:
            pygame.draw.rect(surface, self.border_color, rect, self.border_width)
        
        # Draw text
        if self.show_text:
            if self.font is None:
                self.font = pygame.font.Font(None, 20)
            
            health_text = f"{int(self.current_health)}/{self.max_health}"
            text_surface = self.font.render(health_text, True, self.text_color)
            text_rect = text_surface.get_rect(center=rect.center)
            surface.blit(text_surface, text_rect)
        
        super().render(surface)
    
    def set_health(self, current: float, max_health: Optional[float] = None):
        """Set health values."""
        self.current_health = max(0, current)
        if max_health is not None:
            self.max_health = max(1, max_health)


class Button(UIComponent):
    """Interactive button."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = "Button"
        self.normal_color = (70, 70, 70, 255)
        self.hover_color = (100, 100, 100, 255)
        self.pressed_color = (50, 50, 50, 255)
        self.text_color = (255, 255, 255, 255)
        self.border_color = (150, 150, 150, 255)
        self.border_width = 2
        self.corner_radius = 5
        self.font = None
        
        # State
        self.is_hovered = False
        self.is_pressed = False
        self.on_click = None
    
    def update(self, delta_time: float):
        """Update button state."""
        super().update(delta_time)
    
    def render(self, surface: pygame.Surface):
        """Render button."""
        if not self.visible:
            return
        
        pos = self.get_absolute_position()
        rect = pygame.Rect(pos[0], pos[1], self.size[0], self.size[1])
        
        # Choose color based on state
        if self.is_pressed:
            color = self.pressed_color
        elif self.is_hovered:
            color = self.hover_color
        else:
            color = self.normal_color
        
        # Draw button
        pygame.draw.rect(surface, color, rect, border_radius=self.corner_radius)
        
        # Draw border
        if self.border_width > 0:
            pygame.draw.rect(surface, self.border_color, rect,
                           self.border_width, border_radius=self.corner_radius)
        
        # Draw text
        if self.font is None:
            self.font = pygame.font.Font(None, 24)
        
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=rect.center)
        surface.blit(text_surface, text_rect)
        
        super().render(surface)
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle button events."""
        if not self.enabled or not self.visible:
            return False
        
        rect = self.get_global_rect()
        
        if event.type == pygame.MOUSEMOTION:
            # Check hover
            was_hovered = self.is_hovered
            self.is_hovered = rect.collidepoint(event.pos)
            return self.is_hovered
        
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check click start
            if rect.collidepoint(event.pos):
                self.is_pressed = True
                return True
        
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # Check click release
            if self.is_pressed and rect.collidepoint(event.pos):
                self.is_pressed = False
                if self.on_click:
                    self.on_click()
                return True
            self.is_pressed = False
        
        return super().handle_event(event)


class TextLabel(UIComponent):
    """Text label component."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = "Label"
        self.text_color = (255, 255, 255, 255)
        self.font_size = 24
        self.font = None
        self.alignment = "center"  # "left", "center", "right"
    
    def render(self, surface: pygame.Surface):
        """Render text label."""
        if not self.visible:
            return
        
        pos = self.get_absolute_position()
        rect = pygame.Rect(pos[0], pos[1], self.size[0], self.size[1])
        
        # Create font if needed
        if self.font is None:
            self.font = pygame.font.Font(None, self.font_size)
        
        # Render text
        text_surface = self.font.render(self.text, True, self.text_color)
        
        # Calculate text position based on alignment
        if self.alignment == "left":
            text_rect = text_surface.get_rect(midleft=rect.midleft)
        elif self.alignment == "right":
            text_rect = text_surface.get_rect(midright=rect.midright)
        else:  # center
            text_rect = text_surface.get_rect(center=rect.center)
        
        surface.blit(text_surface, text_rect)
        
        super().render(surface)


class UIRenderer:
    """
    Main UI rendering system.
    Manages UI components and rendering.
    """
    
    def __init__(self, screen: pygame.Surface):
        """
        Initialize UI renderer.
        
        Args:
            screen: Pygame surface to render to
        """
        self.screen = screen
        self.root = Panel(position=(0, 0), size=screen.get_size())
        self.components: Dict[str, UIComponent] = {}
        
        # Performance tracking
        self.components_rendered = 0
        self.events_processed = 0
    
    def add_component(self, component_id: str, component: UIComponent,
                     parent_id: Optional[str] = None) -> bool:
        """
        Add UI component.
        
        Args:
            component_id: Unique ID for component
            component: UIComponent instance
            parent_id: Optional parent component ID
            
        Returns:
            True if successful
        """
        if component_id in self.components:
            return False
        
        self.components[component_id] = component
        
        # Add to parent or root
        if parent_id and parent_id in self.components:
            self.components[parent_id].add_child(component)
        else:
            self.root.add_child(component)
        
        return True
    
    def get_component(self, component_id: str) -> Optional[UIComponent]:
        """
        Get component by ID.
        
        Args:
            component_id: Component ID
            
        Returns:
            UIComponent or None
        """
        return self.components.get(component_id)
    
    def remove_component(self, component_id: str):
        """
        Remove component.
        
        Args:
            component_id: Component ID to remove
        """
        if component_id in self.components:
            # Note: This doesn't remove from parent's children list
            # In a full implementation, you'd need to handle that
            del self.components[component_id]
    
    def update(self, delta_time: float):
        """
        Update all UI components.
        
        Args:
            delta_time: Time since last update
        """
        self.root.update(delta_time)
    
    def render(self):
        """Render all UI components."""
        self.components_rendered = len(self.components)
        self.root.render(self.screen)
    
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle input event.
        
        Args:
            event: Pygame event
            
        Returns:
            True if event was consumed
        """
        self.events_processed += 1
        return self.root.handle_event(event)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get UI statistics.
        
        Returns:
            Dictionary with UI metrics
        """
        return {
            'total_components': len(self.components),
            'components_rendered': self.components_rendered,
            'events_processed': self.events_processed
        }
    
    def cleanup(self):
        """Clean up UI resources."""
        self.components.clear()
        self.root.children.clear()
        print("UIRenderer cleaned up")


def draw_ui(screen: pygame.Surface, ui_elements: List[Dict[str, Any]]):
    """
    Simple UI drawing function for basic elements.
    
    Args:
        screen: Pygame surface
        ui_elements: List of UI element dictionaries
    """
    for element in ui_elements:
        element_type = element.get('type', 'text')
        
        if element_type == 'text':
            # Draw text
            text = element.get('text', '')
            position = element.get('position', (0, 0))
            color = element.get('color', (255, 255, 255))
            font_size = element.get('font_size', 24)
            
            font = pygame.font.Font(None, font_size)
            text_surface = font.render(text, True, color)
            screen.blit(text_surface, position)
        
        elif element_type == 'rect':
            # Draw rectangle
            rect = element.get('rect', pygame.Rect(0, 0, 100, 50))
            color = element.get('color', (255, 255, 255))
            width = element.get('width', 0)  # 0 for filled
            
            pygame.draw.rect(screen, color, rect, width)
        
        elif element_type == 'health_bar':
            # Draw health bar
            position = element.get('position', (0, 0))
            size = element.get('size', (100, 20))
            current = element.get('current', 50)
            maximum = element.get('max', 100)
            
            # Background
            bg_rect = pygame.Rect(position[0], position[1], size[0], size[1])
            pygame.draw.rect(screen, (30, 30, 30), bg_rect)
            
            # Health
            health_width = int(size[0] * (current / max(1, maximum)))
            if health_width > 0:
                health_rect = pygame.Rect(position[0], position[1], health_width, size[1])
                health_color = (0, 200, 0) if current / maximum > 0.5 else (200, 0, 0)
                pygame.draw.rect(screen, health_color, health_rect)
            
            # Border
            pygame.draw.rect(screen, (255, 255, 255), bg_rect, 1)