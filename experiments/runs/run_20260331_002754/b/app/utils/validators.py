"""Validation utilities for AgentHub."""

from typing import Any, Dict
from marshmallow import Schema, ValidationError


def validate_schema(schema: Schema, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate data against schema.
    
    Args:
        schema: Marshmallow schema instance
        data: Data to validate
        
    Returns:
        Validated data
        
    Raises:
        ValidationError: If validation fails
    """
    if data is None:
        raise ValidationError('No data provided')
    
    result = schema.load(data)
    return result