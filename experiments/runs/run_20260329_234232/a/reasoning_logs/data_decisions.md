# Data Module Decisions

## Overview
Implementing the data/ module with:
1. SaveSystem - SQLite-based save/load system
2. AssetManager - Enhanced version with lazy loading and caching
3. ConfigLoader - JSON configuration management
4. Integration with ECS for component serialization

## Key Decisions

### 1. SQLite Schema Design
- **save_slots** table: Manage multiple save slots
- **game_state** table: Core game state (player position, time, etc.)
- **entities** table: ECS entity registry
- **components** table: Component data with JSON serialization
- **inventory** table: Player inventory items
- **quests** table: Active and completed quests
- **world_state** table: World-specific state (NPC states, triggers, etc.)

### 2. Serialization Strategy
- **Components**: Use Component.to_dict()/from_dict() methods
- **Binary data**: Store as BLOB for performance-critical assets
- **JSON data**: Store as TEXT for human-readable configuration
- **Versioning**: Include schema_version in all saves for compatibility

### 3. Asset Management
- **Lazy loading**: Assets loaded on first request
- **Caching**: LRU cache with configurable size limits
- **Reference counting**: Track asset usage for proper cleanup
- **Hot-reloading**: Watch files for changes in development mode

### 4. Configuration Management
- **Defaults**: All configs have sensible defaults
- **Validation**: Validate configs on load
- **Hierarchy**: Support config inheritance/overrides
- **Environment-aware**: Different configs for dev/production

### 5. ECS Integration
- **Entity serialization**: Save/restore entity-component relationships
- **System state**: Optional system state persistence
- **World state**: Save world archetypes and entity mappings

## Implementation Notes

### SaveSystem Features:
- Multiple save slots (auto/manual saves)
- Save metadata (timestamp, playtime, thumbnail)
- Compression for large saves
- Encryption for sensitive data (optional)
- Save validation and repair

### AssetManager Features:
- Texture loading (PNG, JPG, etc.)
- Sound loading (WAV, OGG, MP3)
- Font loading
- Config file loading
- Mesh/3D model loading (future)

### ConfigLoader Features:
- JSON/YAML support
- Environment variable substitution
- Schema validation with JSON Schema
- Type conversion and coercion
- Nested config merging

## Integration Points

1. **Game Engine**: SaveSystem hooks into GameEngine lifecycle
2. **ECS**: Component serialization via existing to_dict/from_dict
3. **Render**: AssetManager provides textures/shaders to renderer
4. **Gameplay**: ConfigLoader provides game balance/config data

## Performance Considerations

1. **SQLite WAL mode**: For concurrent reads during saves
2. **Asset cache limits**: Prevent memory exhaustion
3. **Batch operations**: Group SQL operations where possible
4. **Async loading**: Non-blocking asset loading

## Security Considerations

1. **Save validation**: Prevent corrupted/malicious saves
2. **Asset validation**: Verify asset integrity
3. **Config sanitization**: Prevent injection attacks
4. **Optional encryption**: For sensitive game data

## Testing Strategy

1. **Unit tests**: Each class in isolation
2. **Integration tests**: Save/load cycle with ECS
3. **Performance tests**: Asset loading under load
4. **Compatibility tests**: Save file version upgrades