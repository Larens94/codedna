"""
Serializer module for game data serialization.
Handles serialization and deserialization of game entities, components, and state.
"""

import json
import pickle
import zlib
import base64
import logging
from typing import Dict, List, Optional, Any, Tuple, Union, Type, TypeVar
from dataclasses import dataclass, field, asdict, is_dataclass
from enum import Enum
import inspect
from datetime import datetime, date
from decimal import Decimal
import numpy as np

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SerializationError(Exception):
    """Serialization error."""
    pass


class DeserializationError(Exception):
    """Deserialization error."""
    pass


class Serializer:
    """
    Handles serialization and deserialization of game data.
    Supports dataclasses, enums, and custom types.
    """
    
    def __init__(self, compress: bool = True, pretty_print: bool = False):
        """
        Initialize serializer.
        
        Args:
            compress: Whether to compress serialized data
            pretty_print: Whether to pretty-print JSON output
        """
        self.compress = compress
        self.pretty_print = pretty_print
        
        # Type registry for custom serialization
        self._type_registry: Dict[str, Type] = {}
        self._reverse_registry: Dict[Type, str] = {}
        
        # Custom serializers
        self._custom_serializers: Dict[Type, callable] = {}
        self._custom_deserializers: Dict[str, callable] = {}
        
        # Register built-in types
        self._register_builtin_types()
    
    def _register_builtin_types(self):
        """Register built-in types for serialization."""
        # Register common types
        self.register_type(datetime, "datetime")
        self.register_type(date, "date")
        self.register_type(Decimal, "decimal")
        
        # Register numpy types if available
        try:
            self.register_type(np.ndarray, "numpy.ndarray")
            self.register_type(np.float32, "numpy.float32")
            self.register_type(np.float64, "numpy.float64")
            self.register_type(np.int32, "numpy.int32")
            self.register_type(np.int64, "numpy.int64")
        except ImportError:
            pass
    
    def register_type(self, type_class: Type, type_name: str):
        """
        Register a type for serialization.
        
        Args:
            type_class: Type class
            type_name: Unique name for the type
        """
        self._type_registry[type_name] = type_class
        self._reverse_registry[type_class] = type_name
    
    def register_custom_serializer(self, type_class: Type, serializer: callable, deserializer: callable):
        """
        Register custom serializer for a type.
        
        Args:
            type_class: Type class
            serializer: Function that converts object to serializable form
            deserializer: Function that converts serialized form back to object
        """
        type_name = self._reverse_registry.get(type_class)
        if not type_name:
            type_name = type_class.__name__
            self.register_type(type_class, type_name)
        
        self._custom_serializers[type_class] = serializer
        self._custom_deserializers[type_name] = deserializer
    
    def serialize(self, obj: Any) -> str:
        """
        Serialize an object to string.
        
        Args:
            obj: Object to serialize
            
        Returns:
            Serialized string
        """
        try:
            # Convert object to serializable form
            serializable = self._to_serializable(obj)
            
            # Convert to JSON
            if self.pretty_print:
                json_str = json.dumps(serializable, indent=2, default=self._json_default)
            else:
                json_str = json.dumps(serializable, default=self._json_default)
            
            # Compress if requested
            if self.compress:
                compressed = zlib.compress(json_str.encode('utf-8'))
                return base64.b64encode(compressed).decode('ascii')
            else:
                return json_str
                
        except Exception as e:
            logger.error(f"Serialization failed: {e}")
            raise SerializationError(f"Failed to serialize object: {e}")
    
    def deserialize(self, data: str, target_type: Optional[Type[T]] = None) -> Any:
        """
        Deserialize string to object.
        
        Args:
            data: Serialized string
            target_type: Expected type of deserialized object
            
        Returns:
            Deserialized object
        """
        try:
            # Decompress if needed
            if self.compress and len(data) > 0 and not data.startswith('{'):
                try:
                    compressed = base64.b64decode(data.encode('ascii'))
                    json_str = zlib.decompress(compressed).decode('utf-8')
                except:
                    # Not compressed, use as-is
                    json_str = data
            else:
                json_str = data
            
            # Parse JSON
            parsed = json.loads(json_str)
            
            # Convert from serializable form
            result = self._from_serializable(parsed, target_type)
            
            return result
            
        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            raise DeserializationError(f"Failed to deserialize data: {e}")
    
    def _to_serializable(self, obj: Any) -> Any:
        """
        Convert object to serializable form.
        
        Args:
            obj: Object to convert
            
        Returns:
            Serializable representation
        """
        # Handle None
        if obj is None:
            return None
        
        # Handle basic types
        if isinstance(obj, (str, int, float, bool)):
            return obj
        
        # Handle lists and tuples
        if isinstance(obj, (list, tuple)):
            return [self._to_serializable(item) for item in obj]
        
        # Handle dictionaries
        if isinstance(obj, dict):
            return {key: self._to_serializable(value) for key, value in obj.items()}
        
        # Handle enums
        if isinstance(obj, Enum):
            return {
                '__type__': 'enum',
                'enum_class': obj.__class__.__name__,
                'value': obj.value
            }
        
        # Handle dataclasses
        if is_dataclass(obj) and not isinstance(obj, type):
            result = {
                '__type__': 'dataclass',
                'class_name': obj.__class__.__name__,
                'module': obj.__class__.__module__,
                'fields': {}
            }
            
            for field_name, field_value in asdict(obj).items():
                result['fields'][field_name] = self._to_serializable(field_value)
            
            return result
        
        # Handle custom serializers
        obj_type = type(obj)
        if obj_type in self._custom_serializers:
            custom_data = self._custom_serializers[obj_type](obj)
            return {
                '__type__': 'custom',
                'type_name': self._reverse_registry.get(obj_type, obj_type.__name__),
                'data': self._to_serializable(custom_data)
            }
        
        # Handle registered types
        if obj_type in self._reverse_registry:
            type_name = self._reverse_registry[obj_type]
            return {
                '__type__': 'registered',
                'type_name': type_name,
                'data': self._to_serializable(obj.__dict__)
            }
        
        # Try to use object's __dict__
        if hasattr(obj, '__dict__'):
            return {
                '__type__': 'object',
                'class_name': obj.__class__.__name__,
                'module': obj.__class__.__module__,
                'attributes': self._to_serializable(obj.__dict__)
            }
        
        # Fallback to string representation
        logger.warning(f"Using string representation for unserializable type: {type(obj)}")
        return str(obj)
    
    def _from_serializable(self, data: Any, target_type: Optional[Type] = None) -> Any:
        """
        Convert from serializable form to object.
        
        Args:
            data: Serializable data
            target_type: Expected type
            
        Returns:
            Deserialized object
        """
        # Handle basic types
        if not isinstance(data, dict) or '__type__' not in data:
            return data
        
        type_info = data['__type__']
        
        # Handle enums
        if type_info == 'enum':
            enum_class_name = data['enum_class']
            value = data['value']
            
            # Try to find enum class
            if target_type and issubclass(target_type, Enum):
                enum_class = target_type
            else:
                # Search in registered types
                enum_class = self._find_class(enum_class_name)
            
            if enum_class and issubclass(enum_class, Enum):
                return enum_class(value)
            else:
                raise DeserializationError(f"Enum class not found: {enum_class_name}")
        
        # Handle dataclasses
        elif type_info == 'dataclass':
            class_name = data['class_name']
            module = data['module']
            fields_data = data['fields']
            
            # Try to find dataclass
            if target_type and is_dataclass(target_type):
                dataclass_type = target_type
            else:
                dataclass_type = self._find_class(class_name, module)
            
            if dataclass_type and is_dataclass(dataclass_type):
                # Deserialize fields
                field_values = {}
                for field_name, field_value in fields_data.items():
                    # Get field type hint if available
                    field_type = None
                    if hasattr(dataclass_type, '__annotations__'):
                        field_type = dataclass_type.__annotations__.get(field_name)
                    
                    field_values[field_name] = self._from_serializable(field_value, field_type)
                
                # Create dataclass instance
                return dataclass_type(**field_values)
            else:
                raise DeserializationError(f"Dataclass not found: {class_name}")
        
        # Handle custom types
        elif type_info == 'custom':
            type_name = data['type_name']
            custom_data = data['data']
            
            if type_name in self._custom_deserializers:
                deserialized_data = self._from_serializable(custom_data)
                return self._custom_deserializers[type_name](deserialized_data)
            else:
                raise DeserializationError(f"Custom deserializer not found: {type_name}")
        
        # Handle registered types
        elif type_info == 'registered':
            type_name = data['type_name']
            type_data = data['data']
            
            if type_name in self._type_registry:
                type_class = self._type_registry[type_name]
                attributes = self._from_serializable(type_data)
                
                # Create instance
                instance = type_class.__new__(type_class)
                if isinstance(attributes, dict):
                    instance.__dict__.update(attributes)
                return instance
            else:
                raise DeserializationError(f"Registered type not found: {type_name}")
        
        # Handle generic objects
        elif type_info == 'object':
            class_name = data['class_name']
            module = data['module']
            attributes = data['attributes']
            
            # Try to find class
            obj_class = self._find_class(class_name, module)
            if obj_class:
                instance = obj_class.__new__(obj_class)
                instance.__dict__.update(self._from_serializable(attributes))
                return instance
            else:
                # Return as dictionary
                return self._from_serializable(attributes)
        
        else:
            raise DeserializationError(f"Unknown type info: {type_info}")
    
    def _find_class(self, class_name: str, module: Optional[str] = None) -> Optional[Type]:
        """
        Find class by name.
        
        Args:
            class_name: Name of the class
            module: Module name (optional)
            
        Returns:
            Class if found, None otherwise
        """
        # Check registered types first
        if class_name in self._type_registry:
            return self._type_registry[class_name]
        
        # Try to import from module
        if module:
            try:
                imported_module = __import__(module, fromlist=[class_name])
                if hasattr(imported_module, class_name):
                    return getattr(imported_module, class_name)
            except ImportError:
                pass
        
        # Try to find in globals
        import sys
        for module_name, module_obj in sys.modules.items():
            if hasattr(module_obj, class_name):
                return getattr(module_obj, class_name)
        
        return None
    
    def _json_default(self, obj: Any) -> Any:
        """
        Default JSON encoder for non-serializable types.
        
        Args:
            obj: Object to encode
            
        Returns:
            JSON-serializable representation
        """
        # Handle datetime
        if isinstance(obj, datetime):
            return {
                '__type__': 'datetime',
                'isoformat': obj.isoformat()
            }
        
        # Handle date
        if isinstance(obj, date):
            return {
                '__type__': 'date',
                'isoformat': obj.isoformat()
            }
        
        # Handle Decimal
        if isinstance(obj, Decimal):
            return {
                '__type__': 'decimal',
                'value': str(obj)
            }
        
        # Handle numpy arrays
        if isinstance(obj, np.ndarray):
            return {
                '__type__': 'numpy.ndarray',
                'dtype': str(obj.dtype),
                'shape': obj.shape,
                'data': obj.tolist()
            }
        
        # Handle numpy scalars
        if isinstance(obj, (np.float32, np.float64, np.int32, np.int64)):
            return {
                '__type__': type(obj).__name__,
                'value': obj.item()
            }
        
        # Try to serialize using our method
        try:
            return self._to_serializable(obj)
        except:
            pass
        
        # Fallback to string
        return str(obj)
    
    def serialize_to_file(self, obj: Any, file_path: str):
        """
        Serialize object to file.
        
        Args:
            obj: Object to serialize
            file_path: Path to output file
        """
        serialized = self.serialize(obj)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(serialized)
            logger.debug(f"Serialized object to file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to write serialized data to file: {e}")
            raise SerializationError(f"Failed to write to file: {e}")
    
    def deserialize_from_file(self, file_path: str, target_type: Optional[Type[T]] = None) -> Any:
        """
        Deserialize object from file.
        
        Args:
            file_path: Path to input file
            target_type: Expected type of deserialized object
            
        Returns:
            Deserialized object
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = f.read()
            
            return self.deserialize(data, target_type)
            
        except Exception as e:
            logger.error(f"Failed to read or deserialize from file: {e}")
            raise DeserializationError(f"Failed to read from file: {e}")
    
    def clone(self, obj: Any) -> Any:
        """
        Create a deep copy of an object using serialization.
        
        Args:
            obj: Object to clone
            
        Returns:
            Cloned object
        """
        return self.deserialize(self.serialize(obj), type(obj))


# Default serializer instance
default_serializer = Serializer()


def serialize(obj: Any, compress: bool = True, pretty_print: bool = False) -> str:
    """
    Convenience function to serialize an object.
    
    Args:
        obj: Object to serialize
        compress: Whether to compress
        pretty_print: Whether to pretty-print
        
    Returns:
        Serialized string
    """
    serializer = Serializer(compress=compress, pretty_print=pretty_print)
    return serializer.serialize(obj)


def deserialize(data: str, target_type: Optional[Type[T]] = None, 
                compress: bool = True) -> Any:
    """
    Convenience function to deserialize data.
    
    Args:
        data: Serialized string
        target_type: Expected type
        compress: Whether data is compressed
        
    Returns:
        Deserialized object
    """
    serializer = Serializer(compress=compress)
    return serializer.deserialize(data, target_type)