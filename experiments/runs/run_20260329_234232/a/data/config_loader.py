"""config_loader.py — JSON configuration management with defaults and validation.

exports: load_config(), validate_config(), merge_configs()
used_by: data/main.py → load_config()
rules:   All configs must have defaults, support environment variable substitution
agent:   DataArchitect | 2024-01-15 | Implemented config loading with validation and merging
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union, Type, get_type_hints
from pathlib import Path
from dataclasses import dataclass, field, asdict
import copy

logger = logging.getLogger(__name__)

@dataclass
class ConfigSchema:
    """Configuration schema for validation."""
    fields: Dict[str, Type]
    required: List[str] = field(default_factory=list)
    defaults: Dict[str, Any] = field(default_factory=dict)

class ConfigLoader:
    """Load and manage game configuration files.
    
    Features:
    - JSON configuration loading
    - Default values and validation
    - Environment variable substitution
    - Config merging and inheritance
    - Type conversion and coercion
    """
    
    def __init__(self, config_dir: str = "configs"):
        """Initialize config loader.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self._config_dir = Path(config_dir)
        self._config_dir.mkdir(parents=True, exist_ok=True)
        
        # Schema registry
        self._schemas: Dict[str, ConfigSchema] = {}
        
        # Loaded configs cache
        self._configs: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"ConfigLoader initialized with directory: {config_dir}")
    
    def register_schema(self, config_name: str, schema: ConfigSchema):
        """Register a schema for configuration validation.
        
        Args:
            config_name: Name of configuration
            schema: Configuration schema
        """
        self._schemas[config_name] = schema
        logger.debug(f"Registered schema for: {config_name}")
    
    def _substitute_env_vars(self, value: Any) -> Any:
        """Substitute environment variables in configuration values.
        
        Args:
            value: Configuration value (string, list, or dict)
            
        Returns:
            Value with environment variables substituted
        """
        if isinstance(value, str):
            # Replace ${VAR_NAME} with environment variable
            import re
            def replace_env(match):
                var_name = match.group(1)
                return os.environ.get(var_name, match.group(0))
            
            return re.sub(r'\$\{([^}]+)\}', replace_env, value)
        
        elif isinstance(value, list):
            return [self._substitute_env_vars(item) for item in value]
        
        elif isinstance(value, dict):
            return {k: self._substitute_env_vars(v) for k, v in value.items()}
        
        return value
    
    def _coerce_type(self, value: Any, target_type: Type) -> Any:
        """Coerce value to target type if possible.
        
        Args:
            value: Value to coerce
            target_type: Target type
            
        Returns:
            Coerced value
            
        Raises:
            ValueError: If coercion fails
        """
        # Handle None
        if value is None:
            return None
        
        # Check if already correct type
        if isinstance(value, target_type):
            return value
        
        # Handle special types
        if target_type == bool:
            if isinstance(value, str):
                value_lower = value.lower()
                if value_lower in ('true', 'yes', '1', 'on'):
                    return True
                elif value_lower in ('false', 'no', '0', 'off'):
                    return False
        
        # Try direct conversion
        try:
            return target_type(value)
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert {value!r} to {target_type.__name__}")
    
    def _validate_config(self, config_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration against schema.
        
        Args:
            config_name: Name of configuration
            config: Configuration dictionary
            
        Returns:
            Validated and processed configuration
            
        Raises:
            ValueError: If validation fails
        """
        if config_name not in self._schemas:
            logger.warning(f"No schema registered for {config_name}, skipping validation")
            return config
        
        schema = self._schemas[config_name]
        result = {}
        
        # Check required fields
        for field_name in schema.required:
            if field_name not in config:
                raise ValueError(f"Required field '{field_name}' missing in {config_name}")
        
        # Process all fields
        for field_name, field_type in schema.fields.items():
            # Get value from config or defaults
            if field_name in config:
                value = config[field_name]
            elif field_name in schema.defaults:
                value = schema.defaults[field_name]
            else:
                # Field not in config and no default
                continue
            
            # Substitute environment variables
            value = self._substitute_env_vars(value)
            
            # Coerce to correct type
            try:
                value = self._coerce_type(value, field_type)
            except ValueError as e:
                raise ValueError(f"Field '{field_name}' in {config_name}: {e}")
            
            result[field_name] = value
        
        return result
    
    def load(self, config_name: str, use_cache: bool = True) -> Dict[str, Any]:
        """Load configuration file.
        
        Args:
            config_name: Name of configuration file (without .json)
            use_cache: Use cached version if available
            
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config validation fails
        """
        # Check cache
        if use_cache and config_name in self._configs:
            logger.debug(f"Returning cached config: {config_name}")
            return self._configs[config_name].copy()
        
        # Build file path
        config_path = self._config_dir / f"{config_name}.json"
        
        if not config_path.exists():
            # Try to load default config
            if config_name in self._schemas:
                logger.info(f"Config {config_name} not found, using defaults")
                config = self._schemas[config_name].defaults.copy()
            else:
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
        else:
            # Load from file
            logger.info(f"Loading configuration: {config_path}")
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in {config_path}: {e}")
        
        # Validate and process
        processed_config = self._validate_config(config_name, config)
        
        # Cache result
        self._configs[config_name] = processed_config.copy()
        
        return processed_config
    
    def save(self, config_name: str, config: Dict[str, Any], validate: bool = True):
        """Save configuration to file.
        
        Args:
            config_name: Name of configuration
            config: Configuration dictionary
            validate: Validate before saving
            
        Raises:
            ValueError: If validation fails
        """
        # Validate if requested
        if validate:
            config = self._validate_config(config_name, config)
        
        # Build file path
        config_path = self._config_dir / f"{config_name}.json"
        
        # Save to file
        logger.info(f"Saving configuration: {config_path}")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Update cache
            self._configs[config_name] = config.copy()
            
        except Exception as e:
            raise IOError(f"Failed to save config {config_name}: {e}")
    
    def merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two configurations.
        
        Args:
            base: Base configuration
            override: Override configuration
            
        Returns:
            Merged configuration
        """
        result = copy.deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        
        return result
    
    def load_with_overrides(self, config_name: str, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Load configuration with runtime overrides.
        
        Args:
            config_name: Name of configuration
            overrides: Runtime overrides to apply
            
        Returns:
            Merged configuration
        """
        # Load base config
        base_config = self.load(config_name)
        
        # Merge with overrides
        return self.merge(base_config, overrides)
    
    def get_default_schema(self, config_name: str) -> Optional[ConfigSchema]:
        """Get default schema for a configuration.
        
        Args:
            config_name: Name of configuration
            
        Returns:
            Default schema or None if not registered
        """
        return self._schemas.get(config_name)
    
    def clear_cache(self, config_name: Optional[str] = None):
        """Clear configuration cache.
        
        Args:
            config_name: Specific config to clear, or None for all
        """
        if config_name:
            if config_name in self._configs:
                del self._configs[config_name]
                logger.debug(f"Cleared cache for: {config_name}")
        else:
            self._configs.clear()
            logger.debug("Cleared all config cache")

# Convenience functions
def load_config(config_name: str, config_dir: str = "configs") -> Dict[str, Any]:
    """Load configuration file (convenience function).
    
    Args:
        config_name: Name of configuration file
        config_dir: Directory containing configs
        
    Returns:
        Configuration dictionary
    """
    loader = ConfigLoader(config_dir)
    return loader.load(config_name)

def validate_config(config: Dict[str, Any], schema: ConfigSchema) -> Dict[str, Any]:
    """Validate configuration against schema.
    
    Args:
        config: Configuration to validate
        schema: Validation schema
        
    Returns:
        Validated configuration
        
    Raises:
        ValueError: If validation fails
    """
    # Create temporary loader for validation
    loader = ConfigLoader()
    loader.register_schema("temp", schema)
    return loader._validate_config("temp", config)

def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two configurations.
    
    Args:
        base: Base configuration
        override: Override configuration
        
    Returns:
        Merged configuration
    """
    loader = ConfigLoader()
    return loader.merge(base, override)

# Example schemas
def create_game_config_schema() -> ConfigSchema:
    """Create schema for game configuration."""
    return ConfigSchema(
        fields={
            "window": dict,
            "graphics": dict,
            "audio": dict,
            "controls": dict,
            "gameplay": dict
        },
        required=["window", "graphics"],
        defaults={
            "window": {
                "width": 1280,
                "height": 720,
                "title": "My Game",
                "fullscreen": False
            },
            "graphics": {
                "vsync": True,
                "msaa": 4,
                "texture_quality": "high",
                "shadow_quality": "medium"
            },
            "audio": {
                "master_volume": 1.0,
                "music_volume": 0.8,
                "sfx_volume": 0.9,
                "mute": False
            },
            "controls": {
                "keyboard": {
                    "move_up": "W",
                    "move_down": "S",
                    "move_left": "A",
                    "move_right": "D"
                }
            },
            "gameplay": {
                "difficulty": "normal",
                "autosave_interval": 300
            }
        }
    )

def create_save_config_schema() -> ConfigSchema:
    """Create schema for save configuration."""
    return ConfigSchema(
        fields={
            "max_slots": int,
            "auto_save": bool,
            "auto_save_interval": int,
            "compression": bool,
            "backup_count": int
        },
        required=[],
        defaults={
            "max_slots": 10,
            "auto_save": True,
            "auto_save_interval": 300,
            "compression": True,
            "backup_count": 3
        }
    )

# Example usage
if __name__ == "__main__":
    # Test the config loader
    logging.basicConfig(level=logging.INFO)
    
    # Create test config directory
    test_dir = Path("configs")
    test_dir.mkdir(exist_ok=True)
    
    # Create test config
    test_config = {
        "window": {
            "width": 1920,
            "height": 1080,
            "title": "Test Game",
            "fullscreen": True
        },
        "graphics": {
            "vsync": True,
            "msaa": 8,
            "texture_quality": "ultra"
        }
    }
    
    # Save test config
    loader = ConfigLoader()
    loader.register_schema("game", create_game_config_schema())
    
    try:
        loader.save("game", test_config)
        print("Saved test config")
        
        # Load config
        loaded = loader.load("game")
        print(f"Loaded config: {json.dumps(loaded, indent=2)}")
        
        # Test with overrides
        overrides = {"window": {"fullscreen": False}}
        merged = loader.load_with_overrides("game", overrides)
        print(f"Merged config fullscreen: {merged['window']['fullscreen']}")
        
    except Exception as e:
        print(f"Error: {e}")