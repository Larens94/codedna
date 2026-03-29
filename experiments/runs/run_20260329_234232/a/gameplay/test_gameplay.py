"""test_gameplay.py — Test gameplay systems and components.

exports: test_gameplay() function
used_by: Manual testing
rules:   Tests all gameplay systems integration
agent:   GameplayDesigner | 2024-01-15 | Created gameplay tests
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import World
from gameplay.components import *
from gameplay.systems import *


def test_components():
    """Test that all components can be created and serialized."""
    print("Testing gameplay components...")
    
    # Test player components
    player = Player()
    assert player.entity_id > 0
    print(f"✓ Player component: {player}")
    
    stats = PlayerStats(level=5, strength=15)
    assert stats.level == 5
    print(f"✓ PlayerStats component: {stats}")
    
    xp = Experience(current_xp=150, next_level_xp=200)
    assert xp.current_xp == 150
    print(f"✓ Experience component: {xp}")
    
    # Test combat components
    health = Health(current=75, maximum=100)
    assert health.is_alive()
    print(f"✓ Health component: {health}")
    
    damage = Damage(base_damage=20.0, critical_chance=0.1)
    assert damage.base_damage == 20.0
    print(f"✓ Damage component: {damage}")
    
    enemy = Enemy(enemy_type="goblin", experience_value=25)
    assert enemy.enemy_type == "goblin"
    print(f"✓ Enemy component: {enemy}")
    
    # Test movement components
    position = Position(x=10.5, y=5.2, z=0.0)
    assert position.x == 10.5
    print(f"✓ Position component: {position}")
    
    velocity = Velocity(x=2.0, y=0.0, z=0.0, max_speed=5.0)
    assert velocity.speed() == 2.0
    print(f"✓ Velocity component: {velocity}")
    
    input_state = InputState(move_forward=True, move_right=True)
    assert input_state.move_forward
    print(f"✓ InputState component: {input_state}")
    
    # Test inventory components
    item = Item(
        item_id="health_potion",
        name="Health Potion",
        item_type=ItemType.CONSUMABLE,
        stack_size=5,
        value=25
    )
    assert item.item_id == "health_potion"
    print(f"✓ Item component: {item}")
    
    inventory = Inventory(max_slots=10, weight_capacity=30.0)
    assert inventory.max_slots == 10
    print(f"✓ Inventory component: {inventory}")
    
    currency = Currency(gold=50, silver=25, copper=10)
    assert currency.total_copper_value() == 50*10000 + 25*100 + 10
    print(f"✓ Currency component: {currency}")
    
    # Test quest components
    objective = Objective(
        objective_id="kill_goblins",
        description="Kill 10 Goblins",
        objective_type=ObjectiveType.KILL,
        target="goblin",
        required_count=10
    )
    assert objective.objective_type == ObjectiveType.KILL
    print(f"✓ Objective component: {objective}")
    
    quest = Quest(
        quest_id="goblin_menace",
        title="Goblin Menace",
        description="Clear the goblins from the forest",
        reward_xp=500,
        reward_gold=100
    )
    assert quest.quest_id == "goblin_menace"
    print(f"✓ Quest component: {quest}")
    
    quest_progress = QuestProgress()
    assert len(quest_progress.active_quests) == 0
    print(f"✓ QuestProgress component: {quest_progress}")
    
    # Test NPC components
    npc = NPC(
        npc_id="merchant",
        name="Merchant",
        npc_type=NPCType.VENDOR,
        is_merchant=True
    )
    assert npc.is_merchant
    print(f"✓ NPC component: {npc}")
    
    behavior = Behavior(current_state=BehaviorState.IDLE)
    assert behavior.current_state == BehaviorState.IDLE
    print(f"✓ Behavior component: {behavior}")
    
    print("✓ All components tested successfully!")


def test_systems():
    """Test that systems can be created and initialized."""
    print("\nTesting gameplay systems...")
    
    world = World()
    
    # Test movement system
    movement_system = MovementSystem()
    movement_system.initialize(world)
    assert movement_system.initialized
    print(f"✓ MovementSystem: {movement_system}")
    
    # Test combat system
    combat_system = CombatSystem()
    combat_system.initialize(world)
    assert combat_system.initialized
    print(f"✓ CombatSystem: {combat_system}")
    
    # Test inventory system
    inventory_system = InventorySystem()
    inventory_system.initialize(world)
    assert inventory_system.initialized
    print(f"✓ InventorySystem: {inventory_system}")
    
    # Test quest system
    quest_system = QuestSystem()
    quest_system.initialize(world)
    assert quest_system.initialized
    print(f"✓ QuestSystem: {quest_system}")
    
    # Note: PlayerSystem requires GLFW window, so we skip it in this test
    print("✓ PlayerSystem skipped (requires GLFW window)")
    
    print("✓ All systems tested successfully!")


def test_entity_creation():
    """Test creating entities with gameplay components."""
    print("\nTesting entity creation...")
    
    world = World()
    
    # Create player entity
    player = world.create_entity()
    player.add_component(Player())
    player.add_component(PlayerStats())
    player.add_component(Health(current=100, maximum=100))
    player.add_component(Position(x=0, y=0, z=0))
    player.add_component(Inventory())
    player.add_component(QuestProgress())
    
    assert player.has_component(Player)
    assert player.has_component(Health)
    assert player.has_component(Position)
    print(f"✓ Created player entity: {player.entity_id}")
    
    # Create enemy entity
    enemy = world.create_entity()
    enemy.add_component(Enemy(enemy_type="goblin"))
    enemy.add_component(Health(current=50, maximum=50))
    enemy.add_component(Position(x=5, y=0, z=0))
    enemy.add_component(CombatState())
    
    assert enemy.has_component(Enemy)
    assert enemy.has_component(CombatState)
    print(f"✓ Created enemy entity: {enemy.entity_id}")
    
    # Query entities
    player_entities = world.query_entities({Player})
    assert len(player_entities) == 1
    print(f"✓ Found {len(player_entities)} player entity")
    
    enemy_entities = world.query_entities({Enemy})
    assert len(enemy_entities) == 1
    print(f"✓ Found {len(enemy_entities)} enemy entity")
    
    print("✓ Entity creation tested successfully!")


def test_component_interactions():
    """Test interactions between components."""
    print("\nTesting component interactions...")
    
    # Test health damage
    health = Health(current=100, maximum=100)
    damage_taken = health.take_damage(30)
    assert damage_taken == 30
    assert health.current == 70
    print(f"✓ Health damage: {health.current}/{health.maximum}")
    
    # Test health healing
    healing_done = health.heal(20)
    assert healing_done == 20
    assert health.current == 90
    print(f"✓ Health healing: {health.current}/{health.maximum}")
    
    # Test experience level up
    xp = Experience(current_xp=150, next_level_xp=100)
    assert xp.level_up()
    print(f"✓ Experience level up check: {xp.level_up()}")
    
    # Test input movement vector
    input_state = InputState(move_forward=True, move_right=True)
    x, y = input_state.get_movement_vector()
    # Diagonal should be normalized
    assert abs((x*x + y*y) ** 0.5 - 1.0) < 0.001
    print(f"✓ Input movement vector: ({x:.2f}, {y:.2f})")
    
    # Test currency conversion
    currency = Currency(gold=2, silver=3, copper=4)
    total_copper = currency.total_copper_value()
    assert total_copper == 2*10000 + 3*100 + 4
    print(f"✓ Currency conversion: {total_copper} copper")
    
    # Test objective progress
    objective = Objective(required_count=10, current_count=3)
    progress = objective.progress()
    assert progress == 30.0  # 3/10 = 30%
    print(f"✓ Objective progress: {progress:.1f}%")
    
    print("✓ Component interactions tested successfully!")


def main():
    """Run all gameplay tests."""
    print("=" * 60)
    print("Gameplay Module Tests")
    print("=" * 60)
    
    try:
        test_components()
        test_systems()
        test_entity_creation()
        test_component_interactions()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())