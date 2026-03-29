"""component.py — Component base class for ECS data storage.

exports: Component class
used_by: gameplay/components/*.py
rules:   Components must be plain data classes, no logic
agent:   Game Director | 2024-01-15 | Defined Component interface
"""

from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Dict


class Component(ABC):
    """Base class for all ECS components.
    
    Rules:
    - Components are data-only classes (no methods beyond __post_init__)
    - Must be hashable and comparable for archetype matching
    - Should use @dataclass decorator for automatic __init__
    """
    
    def __init_subclass__(cls, **kwargs):
        """Enforce that subclasses are dataclasses."""
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, '__dataclass_fields__'):
            raise TypeError(f"Component subclass {cls.__name__} must be a dataclass")
    
    def __hash__(self) -> int:
        """Default hash based on class and field values.
        
        Rules: Components must be hashable for archetype storage.
        """
        return hash((self.__class__,) + tuple(
            getattr(self, field.name) 
            for field in self.__dataclass_fields__.values()
            if field.compare
        ))
    
    def __eq__(self, other: object) -> bool:
        """Default equality comparison.
        
        Rules: Components must be comparable for archetype matching.
        """
        if not isinstance(other, self.__class__):
            return False
            
        for field in self.__dataclass_fields__.values():
            if field.compare:
                if getattr(self, field.name) != getattr(other, field.name):
                    return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert component to dictionary for serialization.
        
        Returns:
            Dictionary representation of component data
        """
        result = {}
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            # Handle nested dataclasses
            if hasattr(value, 'to_dict'):
                result[field_name] = value.to_dict()
            else:
                result[field_name] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Component':
        """Create component from dictionary.
        
        Args:
            data: Dictionary with component data
            
        Returns:
            New component instance
            
        Rules: Must handle nested component reconstruction.
        """
        processed_data = {}
        for field_name, field_type in cls.__dataclass_fields__.items():
            if field_name in data:
                value = data[field_name]
                
                # Check if field type is a Component subclass
                if hasattr(field_type.type, 'from_dict'):
                    processed_data[field_name] = field_type.type.from_dict(value)
                else:
                    processed_data[field_name] = value
                    
        return cls(**processed_data)