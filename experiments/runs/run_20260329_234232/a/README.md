# 2D RPG Game - Professional Architecture

A complete 2D RPG game demonstrating professional game architecture with Entity-Component-System (ECS) pattern, designed for 60 FPS performance target.

## 🎮 Features

- **Pure ECS Architecture**: Data-oriented design for maximum performance
- **60 FPS Target**: Real-time performance monitoring with automatic warnings
- **Complete Demo Scene**: Player, enemies, NPCs, items, and quests
- **Modular Design**: Clean separation between engine, render, gameplay, and data
- **Asset Management**: Centralized loading, caching, and lifecycle management
- **Professional Standards**: In-source annotation protocol, semantic naming, comprehensive logging

## 🏗️ Architecture Overview

```
├── engine/           # ECS core: World, Entity, Component, System
├── render/           # OpenGL/GLFW rendering system
├── gameplay/         # Game-specific logic and systems
├── data/            # Asset management and serialization
├── integration/      # Performance monitoring and tests
├── assets/          # Game assets (configs, textures, sounds)
├── reasoning_logs/  # Architectural decisions
├── main.py          # Game entry point with performance monitoring
├── requirements.txt # Dependencies
└── README.md        # This file
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Game
```bash
python main.py
```

### 3. Controls
- **ESC**: Quit game
- **Real-time FPS display** in terminal
- **Performance warnings** automatically logged

## 📊 Performance Monitoring

The game includes comprehensive performance monitoring:
- **60 FPS target** with adaptive frame timing
- **Slow frame detection** with warnings
- **Memory usage tracking**
- **Real-time FPS display** in terminal
- **Performance reports** on shutdown

## 🎯 Demo Scene

The game creates a complete demo scene with:

### Entities Created:
1. **Player Entity** (ID: 0)
   - Health: 100/100
   - Damage: 15.0
   - Inventory: 20 slots, 50.0 weight capacity
   - Gold: 10
   - Position: (0, 0, 0)

2. **Enemy Entity** (ID: 1) - Goblin
   - Health: 50/50
   - Damage: 5.0
   - Aggression range: 5.0
   - Experience value: 25
   - Position: (5, 0, 0)

3. **NPC Entity** (ID: 2) - Merchant
   - Dialogue: "Welcome traveler!"
   - Available quest: "find_lost_ring"
   - Position: (-5, 0, 0)

4. **Item Entity** (ID: 3) - Health Potion
   - Restores 50 health
   - Weight: 0.5
   - Value: 25 gold
   - Position: (2, 2, 0)

5. **Quest Entity** (ID: 4) - Find the Lost Ring
   - Objective: Find merchant's lost ring
   - Rewards: 100 XP + 50 gold

### Gameplay Systems:
- **Movement System** (Priority: 0) - Handles entity movement
- **Player System** (Priority: 10) - Handles player input
- **Combat System** (Priority: 20) - Manages combat logic
- **Inventory System** (Priority: 30) - Manages items and equipment
- **Quest System** (Priority: 40) - Handles quests and NPC interactions

## 🛠️ Module Responsibilities

### Engine Module (`engine/`)
- **Entity-Component-System** core implementation
- **Archetype-based** component storage for cache efficiency
- **System scheduling** with fixed/variable timestep support
- **Entity lifecycle** management with ID recycling

### Render Module (`render/`)
- **OpenGL 3.3+** and **GLFW** window management
- **Shader**, **mesh**, and **texture** management
- **Camera** and viewport control
- **Batched rendering** for performance

### Gameplay Module (`gameplay/`)
- **Game-specific components** (Position, Velocity, Health, Inventory, etc.)
- **Game-specific systems** (Movement, Combat, Player, Quest, etc.)
- **Game state** management
- **Input handling** integration

### Data Module (`data/`)
- **Asset loading** (textures, meshes, sounds, configs)
- **Resource caching** with LRU eviction
- **Reference counting** for proper cleanup
- **Hot-reloading** support for development
- **Configuration management**

### Integration Module (`integration/`)
- **Performance monitoring** and FPS tracking
- **Frame time analysis** with warning system
- **Memory usage** tracking
- **Benchmarking** and profiling

## 📈 Performance Targets

- **60 FPS**: 16.67ms per frame budget
- **Memory**: Efficient archetype storage with LRU caching
- **Scalability**: Support for 10,000+ entities
- **Stability**: Graceful shutdown and error handling

## 👥 Team Coordination

Each specialist works on their module with clear interfaces:

1. **Engine Specialist**: ECS optimization, entity queries, system scheduling
2. **Render Specialist**: OpenGL implementation, shaders, rendering pipeline
3. **Gameplay Specialist**: Game logic, components, systems
4. **Data Specialist**: Asset loading, serialization, configuration
5. **Integration Specialist**: Testing, performance validation, benchmarks

## 📝 Code Standards

### In-source Annotation Protocol
Every Python file opens with this exact header:
```python
"""filename.py — <purpose, max 15 words>.

exports: <function(arg) -> return_type>
used_by: <consumer_file.py → consumer_function>
rules:   <hard architectural constraints>
agent:   <YourName> | <YYYY-MM-DD> | <what you implemented>
"""
```

### Semantic Naming
Data-carrying variables use `<type>_<shape>_<domain>_<origin>`:
```python
list_dict_entities_from_engine = engine.get_entities()  # correct
data = engine.get_entities()                            # avoid
```

### Comprehensive Documentation
- **Type hints** for all function signatures
- **Rules sections** in docstrings for domain constraints
- **Logging** at appropriate levels (ERROR, WARNING, INFO, DEBUG)

## 🔧 Development Workflow

1. **Define Components** (in `gameplay/components/`):
   ```python
   @dataclass
   class Position(Component):
       x: float = 0.0
       y: float = 0.0
       z: float = 0.0
   ```

2. **Create Systems** (in `gameplay/systems/`):
   ```python
   class MovementSystem(System):
       def __init__(self):
           super().__init__(required_components={Position, Velocity})
       
       def update(self, world, delta_time):
           for entity in self.query_entities(world):
               pos = entity.get_component(Position)
               vel = entity.get_component(Velocity)
               pos.x += vel.x * delta_time
               pos.y += vel.y * delta_time
   ```

3. **Add Assets** (in `assets/` directory):
   ```
   assets/
   ├── textures/      # .png, .jpg images
   ├── configs/       # .json configuration files
   ├── sounds/        # .wav, .ogg audio files
   └── shaders/       # GLSL shader files
   ```

4. **Monitor Performance**:
   - Automatic FPS tracking in terminal
   - Frame time analysis with warnings
   - Performance reports on shutdown

## 🧪 Testing

### Run Structure Validation
```bash
python test_structure.py
```

### Run Gameplay Tests
```bash
python gameplay/test_gameplay.py
```

### Run Engine Tests
```bash
python engine/test_ecs.py
```

## 📋 Requirements

See `requirements.txt` for complete list:
- **pygame>=2.5.0** - 2D rendering and input
- **PyOpenGL>=3.1.0** - 3D rendering (optional)
- **glfw>=2.5.0** - Window management for OpenGL
- **PyGLM>=2.6.0** - Math library
- **Pillow>=9.0.0** - Image processing

## 🚨 Troubleshooting

### Common Issues:

1. **GLFW initialization failed**
   - Ensure you have OpenGL 3.3+ compatible graphics drivers
   - Try updating graphics drivers

2. **Import errors**
   - Run `pip install -r requirements.txt`
   - Check Python version (requires 3.8+)

3. **Performance issues**
   - Check terminal for performance warnings
   - Reduce window size in `main.py`
   - Disable vsync in renderer initialization

### Getting Help:
- Check `reasoning_logs/` for architectural decisions
- Review module interfaces in `__init__.py` files
- Examine performance reports in terminal output

## 📄 License

Professional game development architecture - for educational and professional use.

## 🙏 Acknowledgments

- **Entity-Component-System** pattern based on modern game engine design
- **Performance monitoring** inspired by professional game development practices
- **Modular architecture** following industry best practices
- **Code standards** based on professional software engineering principles

---

**🎮 Happy Gaming!** The complete 2D RPG architecture is now running. Press ESC to quit and see the performance report.