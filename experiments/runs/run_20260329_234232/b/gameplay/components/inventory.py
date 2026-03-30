"""
Inventory-related components for the 2D RPG.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from engine.ecs import Component


class ItemType(Enum):
    """Types of items."""
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    MATERIAL = "material"
    QUEST = "quest"
    KEY = "key"
    MISC = "misc"


class ItemRarity(Enum):
    """Item rarity levels."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class EquipmentSlot(Enum):
    """Equipment slots."""
    HEAD = "head"
    CHEST = "chest"
    LEGS = "legs"
    FEET = "feet"
    HANDS = "hands"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    RING_1 = "ring_1"
    RING_2 = "ring_2"
    NECK = "neck"
    BACK = "back"


@dataclass
class InventoryComponent(Component):
    """
    Component for entity inventory management.
    """
    max_slots: int = 20
    items: List[Optional[Dict[str, Any]]] = field(default_factory=list)
    gold: int = 100
    weight_capacity: float = 100.0
    current_weight: float = 0.0
    
    def __post_init__(self):
        """Initialize empty inventory slots."""
        self.items = [None] * self.max_slots
    
    def add_item(self, item_data: Dict[str, Any]) -> Optional[int]:
        """
        Add an item to inventory.
        
        Args:
            item_data: Item data dictionary
            
        Returns:
            Slot number where item was added, or None if failed
        """
        # Check weight
        item_weight = item_data.get('weight', 0.0)
        if self.current_weight + item_weight > self.weight_capacity:
            return None
        
        # Find empty slot
        for slot in range(self.max_slots):
            if self.items[slot] is None:
                self.items[slot] = item_data
                self.current_weight += item_weight
                return slot
        
        return None
    
    def remove_item(self, slot: int) -> Optional[Dict[str, Any]]:
        """
        Remove item from inventory slot.
        
        Args:
            slot: Slot number
            
        Returns:
            Item data if removed, None if slot was empty
        """
        if slot < 0 or slot >= self.max_slots:
            return None
        
        item = self.items[slot]
        if item:
            self.current_weight -= item.get('weight', 0.0)
            self.items[slot] = None
        
        return item
    
    def get_item(self, slot: int) -> Optional[Dict[str, Any]]:
        """
        Get item from inventory slot.
        
        Args:
            slot: Slot number
            
        Returns:
            Item data, or None if slot empty
        """
        if slot < 0 or slot >= self.max_slots:
            return None
        return self.items[slot]
    
    def move_item(self, from_slot: int, to_slot: int) -> bool:
        """
        Move item between slots.
        
        Args:
            from_slot: Source slot
            to_slot: Destination slot
            
        Returns:
            True if move successful
        """
        if (from_slot < 0 or from_slot >= self.max_slots or 
            to_slot < 0 or to_slot >= self.max_slots):
            return False
        
        if self.items[to_slot] is not None:
            return False  # Destination must be empty
        
        self.items[to_slot] = self.items[from_slot]
        self.items[from_slot] = None
        return True
    
    def swap_items(self, slot_a: int, slot_b: int) -> bool:
        """
        Swap items between two slots.
        
        Args:
            slot_a: First slot
            slot_b: Second slot
            
        Returns:
            True if swap successful
        """
        if (slot_a < 0 or slot_a >= self.max_slots or 
            slot_b < 0 or slot_b >= self.max_slots):
            return False
        
        self.items[slot_a], self.items[slot_b] = self.items[slot_b], self.items[slot_a]
        return True
    
    def find_item(self, item_id: str) -> List[int]:
        """
        Find slots containing a specific item.
        
        Args:
            item_id: Item identifier to find
            
        Returns:
            List of slot numbers containing the item
        """
        slots = []
        for slot in range(self.max_slots):
            item = self.items[slot]
            if item and item.get('id') == item_id:
                slots.append(slot)
        return slots
    
    def get_empty_slots(self) -> List[int]:
        """
        Get list of empty slots.
        
        Returns:
            List of empty slot numbers
        """
        return [slot for slot in range(self.max_slots) if self.items[slot] is None]
    
    def get_inventory_data(self) -> Dict[str, Any]:
        """
        Get inventory data for serialization.
        
        Returns:
            Dictionary with inventory data
        """
        return {
            'max_slots': self.max_slots,
            'items': self.items,
            'gold': self.gold,
            'weight_capacity': self.weight_capacity,
            'current_weight': self.current_weight
        }


@dataclass
class ItemComponent(Component):
    """
    Component for item entities.
    """
    item_id: str = ""
    item_type: ItemType = ItemType.MISC
    name: str = "Item"
    description: str = ""
    value: int = 1
    weight: float = 0.1
    stack_size: int = 1
    current_stack: int = 1
    rarity: ItemRarity = ItemRarity.COMMON
    
    # Item properties
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Visual
    sprite_id: str = ""
    icon_id: str = ""
    
    def can_stack_with(self, other: 'ItemComponent') -> bool:
        """
        Check if this item can stack with another.
        
        Args:
            other: Other item component
            
        Returns:
            True if items can stack
        """
        return (self.item_id == other.item_id and 
                self.current_stack < self.stack_size and 
                other.current_stack < other.stack_size)
    
    def merge_stacks(self, other: 'ItemComponent') -> bool:
        """
        Merge stacks with another item.
        
        Args:
            other: Other item component
            
        Returns:
            True if stacks were merged
        """
        if not self.can_stack_with(other):
            return False
        
        total = self.current_stack + other.current_stack
        if total <= self.stack_size:
            self.current_stack = total
            other.current_stack = 0
            return True
        else:
            transfer = self.stack_size - self.current_stack
            self.current_stack = self.stack_size
            other.current_stack -= transfer
            return True
    
    def split_stack(self, amount: int) -> Optional['ItemComponent']:
        """
        Split item stack.
        
        Args:
            amount: Amount to split off
            
        Returns:
            New item component with split amount, or None
        """
        if amount <= 0 or amount >= self.current_stack:
            return None
        
        # Create new item with same properties
        new_item = ItemComponent(
            item_id=self.item_id,
            item_type=self.item_type,
            name=self.name,
            description=self.description,
            value=self.value,
            weight=self.weight,
            stack_size=self.stack_size,
            current_stack=amount,
            rarity=self.rarity,
            properties=self.properties.copy(),
            sprite_id=self.sprite_id,
            icon_id=self.icon_id
        )
        
        # Reduce current stack
        self.current_stack -= amount
        
        return new_item


@dataclass
class EquipmentComponent(Component):
    """
    Component for entity equipment.
    """
    equipped_items: Dict[EquipmentSlot, Optional[Dict[str, Any]]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize empty equipment slots."""
        for slot in EquipmentSlot:
            self.equipped_items[slot] = None
    
    def equip_item(self, slot: EquipmentSlot, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Equip an item.
        
        Args:
            slot: Equipment slot
            item_data: Item data
            
        Returns:
            Previously equipped item if replaced, None otherwise
        """
        previous_item = self.equipped_items[slot]
        self.equipped_items[slot] = item_data
        return previous_item
    
    def unequip_item(self, slot: EquipmentSlot) -> Optional[Dict[str, Any]]:
        """
        Unequip an item.
        
        Args:
            slot: Equipment slot
            
        Returns:
            Unequipped item data, or None if slot was empty
        """
        item = self.equipped_items[slot]
        self.equipped_items[slot] = None
        return item
    
    def get_equipped_item(self, slot: EquipmentSlot) -> Optional[Dict[str, Any]]:
        """
        Get equipped item in slot.
        
        Args:
            slot: Equipment slot
            
        Returns:
            Item data, or None if slot empty
        """
        return self.equipped_items.get(slot)
    
    def get_equipment_stats(self) -> Dict[str, float]:
        """
        Calculate total stats from equipped items.
        
        Returns:
            Dictionary of stat bonuses
        """
        stats = {
            'strength': 0,
            'dexterity': 0,
            'constitution': 0,
            'intelligence': 0,
            'wisdom': 0,
            'charisma': 0,
            'attack_power': 0,
            'spell_power': 0,
            'defense': 0,
            'magic_resist': 0
        }
        
        for item in self.equipped_items.values():
            if item:
                item_stats = item.get('stats', {})
                for stat, value in item_stats.items():
                    if stat in stats:
                        stats[stat] += value
        
        return stats
    
    def is_slot_occupied(self, slot: EquipmentSlot) -> bool:
        """
        Check if equipment slot is occupied.
        
        Args:
            slot: Equipment slot
            
        Returns:
            True if slot has an item equipped
        """
        return self.equipped_items.get(slot) is not None


@dataclass
class CurrencyComponent(Component):
    """
    Component for currency management.
    """
    gold: int = 0
    silver: int = 0
    copper: int = 0
    special_currencies: Dict[str, int] = field(default_factory=dict)
    
    def add_gold(self, amount: int):
        """Add gold."""
        self.gold += amount
    
    def add_silver(self, amount: int):
        """Add silver."""
        self.silver += amount
        # Convert to gold if over 100
        if self.silver >= 100:
            self.gold += self.silver // 100
            self.silver = self.silver % 100
    
    def add_copper(self, amount: int):
        """Add copper."""
        self.copper += amount
        # Convert to silver if over 100
        if self.copper >= 100:
            self.add_silver(self.copper // 100)
            self.copper = self.copper % 100
    
    def add_currency(self, gold: int = 0, silver: int = 0, copper: int = 0):
        """
        Add multiple currency types.
        
        Args:
            gold: Gold amount
            silver: Silver amount
            copper: Copper amount
        """
        self.add_gold(gold)
        self.add_silver(silver)
        self.add_copper(copper)
    
    def get_total_copper(self) -> int:
        """
        Get total value in copper.
        
        Returns:
            Total copper value
        """
        return self.copper + (self.silver * 100) + (self.gold * 10000)
    
    def can_afford(self, gold: int = 0, silver: int = 0, copper: int = 0) -> bool:
        """
        Check if entity can afford an amount.
        
        Args:
            gold: Gold cost
            silver: Silver cost
            copper: Copper cost
            
        Returns:
            True if entity can afford
        """
        total_cost = copper + (silver * 100) + (gold * 10000)
        return self.get_total_copper() >= total_cost
    
    def spend(self, gold: int = 0, silver: int = 0, copper: int = 0) -> bool:
        """
        Spend currency.
        
        Args:
            gold: Gold to spend
            silver: Silver to spend
            copper: Copper to spend
            
        Returns:
            True if spent successfully
        """
        if not self.can_afford(gold, silver, copper):
            return False
        
        total_cost = copper + (silver * 100) + (gold * 10000)
        current_total = self.get_total_copper()
        
        # Calculate new total
        new_total = current_total - total_cost
        
        # Convert back to gold/silver/copper
        self.gold = new_total // 10000
        remaining = new_total % 10000
        self.silver = remaining // 100
        self.copper = remaining % 100
        
        return True


@dataclass
class LootComponent(Component):
    """
    Component for lootable entities.
    """
    loot_table: List[Dict[str, Any]] = field(default_factory=list)
    gold_min: int = 0
    gold_max: int = 10
    experience_value: int = 10
    looted: bool = False
    respawn_time: float = 300.0  # 5 minutes
    respawn_timer: float = 0.0
    
    def generate_loot(self) -> Dict[str, Any]:
        """
        Generate loot from loot table.
        
        Returns:
            Dictionary with generated loot
        """
        if self.looted:
            return {'items': [], 'gold': 0}
        
        items = []
        
        # Generate gold
        import random
        gold = random.randint(self.gold_min, self.gold_max)
        
        # Generate items from loot table
        for loot_entry in self.loot_table:
            chance = loot_entry.get('chance', 1.0)
            if random.random() <= chance:
                item_data = loot_entry.get('item', {}).copy()
                items.append(item_data)
        
        self.looted = True
        self.respawn_timer = self.respawn_time
        
        return {
            'items': items,
            'gold': gold,
            'experience': self.experience_value
        }
    
    def update(self, dt: float):
        """
        Update respawn timer.
        
        Args:
            dt: Delta time in seconds
        """
        if self.looted and self.respawn_time > 0:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.looted = False
                self.respawn_timer = 0.0
    
    def can_be_looted(self) -> bool:
        """
        Check if entity can be looted.
        
        Returns:
            True if lootable and not already looted
        """
        return not self.looted