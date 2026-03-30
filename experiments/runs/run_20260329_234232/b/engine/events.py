"""
Event system for decoupled communication between game systems.
Implements a publish-subscribe pattern with event queuing and prioritization.
"""

from typing import Dict, List, Set, Callable, Any, Optional, Type, Union
from enum import Enum, IntEnum
import time
from dataclasses import dataclass, field
from weakref import WeakMethod


class EventPriority(IntEnum):
    """Priority levels for event processing."""
    LOWEST = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    HIGHEST = 4
    MONITOR = 5  # For monitoring only, shouldn't modify events


@dataclass
class Event:
    """Base class for all game events."""
    
    # Event metadata
    timestamp: float = field(default_factory=time.time)
    cancelled: bool = False
    propagation_stopped: bool = False
    
    def cancel(self):
        """Cancel this event."""
        self.cancelled = True
    
    def stop_propagation(self):
        """Stop further propagation of this event."""
        self.propagation_stopped = True
    
    def is_cancelled(self) -> bool:
        """
        Check if event is cancelled.
        
        Returns:
            True if cancelled
        """
        return self.cancelled
    
    def is_propagation_stopped(self) -> bool:
        """
        Check if event propagation is stopped.
        
        Returns:
            True if propagation stopped
        """
        return self.propagation_stopped


# Common event types

@dataclass
class InputEvent(Event):
    """Base class for input events."""
    device: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class KeyEvent(InputEvent):
    """Keyboard event."""
    key: int = 0
    scancode: int = 0
    action: int = 0  # PRESS, RELEASE, REPEAT
    mods: int = 0


@dataclass
class MouseEvent(InputEvent):
    """Mouse event."""
    button: int = 0
    action: int = 0  # PRESS, RELEASE
    mods: int = 0
    x: float = 0.0
    y: float = 0.0


@dataclass
class MouseMoveEvent(InputEvent):
    """Mouse movement event."""
    x: float = 0.0
    y: float = 0.0
    dx: float = 0.0
    dy: float = 0.0


@dataclass
class MouseScrollEvent(InputEvent):
    """Mouse scroll event."""
    xoffset: float = 0.0
    yoffset: float = 0.0


@dataclass
class WindowEvent(Event):
    """Window-related event."""
    window_id: int = 0
    width: int = 0
    height: int = 0


@dataclass
class SceneEvent(Event):
    """Scene-related event."""
    scene_name: str = ""
    previous_scene: str = ""


@dataclass
class EntityEvent(Event):
    """Entity-related event."""
    entity_id: int = 0
    component_type: Optional[Type] = None


@dataclass
class CollisionEvent(Event):
    """Collision event."""
    entity_a: int = 0
    entity_b: int = 0
    normal_x: float = 0.0
    normal_y: float = 0.0
    penetration: float = 0.0


@dataclass
class GameEvent(Event):
    """Game-specific event."""
    event_type: str = ""
    data: Any = None


class EventListener:
    """Wrapper for event listener callbacks."""
    
    def __init__(self, callback: Callable[[Event], Any], priority: EventPriority = EventPriority.NORMAL):
        """
        Initialize an event listener.
        
        Args:
            callback: Function to call when event is triggered
            priority: Priority of this listener
        """
        self.callback = self._wrap_callback(callback)
        self.priority = priority
        self.is_weak = False
    
    def _wrap_callback(self, callback: Callable[[Event], Any]) -> Callable[[Event], Any]:
        """Wrap callback to handle weak references."""
        if hasattr(callback, '__self__') and hasattr(callback, '__func__'):
            # It's a bound method, use WeakMethod
            self.is_weak = True
            return WeakMethod(callback)
        return callback
    
    def __call__(self, event: Event) -> Any:
        """Call the listener with an event."""
        if self.is_weak:
            method = self.callback()
            if method is not None:
                return method(event)
            return None
        else:
            return self.callback(event)
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, EventListener):
            return False
        
        if self.is_weak and other.is_weak:
            self_method = self.callback()
            other_method = other.callback()
            return self_method == other_method
        else:
            return self.callback == other.callback


class EventManager:
    """
    Manages event dispatch and subscription.
    Supports event queuing, prioritization, and filtering.
    """
    
    def __init__(self):
        """Initialize the event manager."""
        self.listeners: Dict[Type[Event], List[EventListener]] = {}
        self.event_queue: List[Event] = []
        self.max_queue_size = 1000
        
        # Statistics
        self.events_processed = 0
        self.events_dropped = 0
        self.listeners_called = 0
        
        # Filtering
        self.event_filters: Dict[Type[Event], List[Callable[[Event], bool]]] = {}
        
        # Delayed events
        self.delayed_events: List[tuple[float, Event]] = []  # (trigger_time, event)
    
    def subscribe(self, event_type: Type[Event], callback: Callable[[Event], Any], 
                  priority: EventPriority = EventPriority.NORMAL) -> EventListener:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
            priority: Priority of this listener
            
        Returns:
            EventListener object that can be used to unsubscribe
        """
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        
        listener = EventListener(callback, priority)
        self.listeners[event_type].append(listener)
        
        # Sort by priority (highest first)
        self.listeners[event_type].sort(key=lambda l: l.priority, reverse=True)
        
        return listener
    
    def unsubscribe(self, event_type: Type[Event], listener: EventListener):
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            listener: Listener to remove
        """
        if event_type in self.listeners:
            if listener in self.listeners[event_type]:
                self.listeners[event_type].remove(listener)
    
    def unsubscribe_all(self, event_type: Type[Event]):
        """
        Unsubscribe all listeners from an event type.
        
        Args:
            event_type: Type of event to clear listeners for
        """
        if event_type in self.listeners:
            self.listeners[event_type].clear()
    
    def publish(self, event: Event, immediate: bool = False):
        """
        Publish an event.
        
        Args:
            event: The event to publish
            immediate: If True, process immediately instead of queuing
        """
        if immediate:
            self._process_event(event)
        else:
            if len(self.event_queue) < self.max_queue_size:
                self.event_queue.append(event)
            else:
                self.events_dropped += 1
                print(f"Warning: Event queue full, dropping event: {type(event).__name__}")
    
    def publish_delayed(self, event: Event, delay: float):
        """
        Publish an event with a delay.
        
        Args:
            event: The event to publish
            delay: Delay in seconds
        """
        trigger_time = time.time() + delay
        self.delayed_events.append((trigger_time, event))
    
    def add_filter(self, event_type: Type[Event], filter_func: Callable[[Event], bool]):
        """
        Add a filter for events of a specific type.
        
        Args:
            event_type: Type of event to filter
            filter_func: Function that returns True if event should be processed
        """
        if event_type not in self.event_filters:
            self.event_filters[event_type] = []
        
        self.event_filters[event_type].append(filter_func)
    
    def remove_filter(self, event_type: Type[Event], filter_func: Callable[[Event], bool]):
        """
        Remove a filter for events of a specific type.
        
        Args:
            event_type: Type of event
            filter_func: Filter function to remove
        """
        if event_type in self.event_filters:
            if filter_func in self.event_filters[event_type]:
                self.event_filters[event_type].remove(filter_func)
    
    def update(self, dt: float):
        """
        Update the event manager.
        
        Args:
            dt: Delta time in seconds
        """
        # Process delayed events
        current_time = time.time()
        ready_events = []
        remaining_events = []
        
        for trigger_time, event in self.delayed_events:
            if current_time >= trigger_time:
                ready_events.append(event)
            else:
                remaining_events.append((trigger_time, event))
        
        self.delayed_events = remaining_events
        
        # Add ready delayed events to queue
        for event in ready_events:
            if len(self.event_queue) < self.max_queue_size:
                self.event_queue.append(event)
            else:
                self.events_dropped += 1
        
        # Process event queue
        events_to_process = self.event_queue.copy()
        self.event_queue.clear()
        
        for event in events_to_process:
            self._process_event(event)
    
    def _process_event(self, event: Event):
        """
        Process a single event.
        
        Args:
            event: The event to process
        """
        event_type = type(event)
        
        # Check filters
        if event_type in self.event_filters:
            for filter_func in self.event_filters[event_type]:
                if not filter_func(event):
                    return  # Event filtered out
        
        # Get listeners for this event type and all parent types
        listeners = []
        
        # Check for listeners of exact type
        if event_type in self.listeners:
            listeners.extend(self.listeners[event_type])
        
        # Check for listeners of parent types
        for listener_type, type_listeners in self.listeners.items():
            if listener_type != event_type and issubclass(event_type, listener_type):
                listeners.extend(type_listeners)
        
        # Sort all listeners by priority
        listeners.sort(key=lambda l: l.priority, reverse=True)
        
        # Call listeners
        for listener in listeners:
            if event.is_propagation_stopped():
                break
            
            try:
                listener(event)
                self.listeners_called += 1
            except Exception as e:
                print(f"Error in event listener for {event_type.__name__}: {e}")
        
        self.events_processed += 1
    
    def clear_queue(self):
        """Clear all queued events."""
        self.event_queue.clear()
    
    def clear_delayed_events(self):
        """Clear all delayed events."""
        self.delayed_events.clear()
    
    def get_statistics(self) -> dict:
        """
        Get event system statistics.
        
        Returns:
            Dictionary with statistics
        """
        total_listeners = sum(len(listeners) for listeners in self.listeners.values())
        
        return {
            'events_processed': self.events_processed,
            'events_dropped': self.events_dropped,
            'listeners_called': self.listeners_called,
            'total_listeners': total_listeners,
            'queued_events': len(self.event_queue),
            'delayed_events': len(self.delayed_events),
            'event_types_registered': len(self.listeners)
        }
    
    def reset_statistics(self):
        """Reset all statistics."""
        self.events_processed = 0
        self.events_dropped = 0
        self.listeners_called = 0
    
    def shutdown(self):
        """Shutdown the event manager."""
        self.listeners.clear()
        self.event_queue.clear()
        self.delayed_events.clear()
        self.event_filters.clear()
        self.reset_statistics()


# Convenience functions for common event patterns

def subscribe_to(event_type: Type[Event], priority: EventPriority = EventPriority.NORMAL):
    """
    Decorator for subscribing to events.
    
    Args:
        event_type: Type of event to subscribe to
        priority: Priority of the listener
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[[Event], Any]):
        # Store subscription info on the function
        if not hasattr(func, '_event_subscriptions'):
            func._event_subscriptions = []
        func._event_subscriptions.append((event_type, priority))
        return func
    return decorator


class EventBus:
    """
    Singleton event bus for global event handling.
    """
    
    _instance: Optional['EventBus'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.manager = EventManager()
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'EventBus':
        """
        Get the singleton instance.
        
        Returns:
            EventBus instance
        """
        if cls._instance is None:
            cls._instance = EventBus()
        return cls._instance
    
    def subscribe(self, event_type: Type[Event], callback: Callable[[Event], Any], 
                  priority: EventPriority = EventPriority.NORMAL) -> EventListener:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
            priority: Priority of this listener
            
        Returns:
            EventListener object
        """
        return self.manager.subscribe(event_type, callback, priority)
    
    def publish(self, event: Event, immediate: bool = False):
        """
        Publish an event.
        
        Args:
            event: The event to publish
            immediate: If True, process immediately
        """
        self.manager.publish(event, immediate)
    
    def update(self, dt: float):
        """
        Update the event bus.
        
        Args:
            dt: Delta time in seconds
        """
        self.manager.update(dt)
    
    def shutdown(self):
        """Shutdown the event bus."""
        self.manager.shutdown()