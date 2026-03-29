"""inventory.py — Inventory and item management components.

exports: Inventory, Item, Equipment, Currency
used_by: gameplay/systems/inventory_system.py
rules:   Inventory component required for item-carrying entities
agent:   GameplayDesigner | 2024-01-15 | Created inventory components
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from engine.component import Component


class ItemType(Enum):
    """Types of items in the game."""
    CONSUMABLE = "consumable"
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    MATERIAL = "material"
    QUEST = "quest"
    KEY = "key"


class EquipmentSlot(Enum):
    """Equipment slots for character."""
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    HEAD = "head"
    CHEST = "chest"
    LEGS = "legs"
    FEET = "feet"
    HANDS = "hands"
    RING = "ring"
    NECK = "neck"
    BACK = "back"


@dataclass
class Item(Component):
    """Base item definition.
    
    Attributes:
        item_id: Unique item identifier
        name: Display name
        description: Item description
        item_type: Type of item
        stack_size: Maximum stack size
        current_stack: Current stack count
        weight: Item weight
        value: Base gold value
        icon: Icon asset ID
        mesh: 3D mesh asset ID
        stats: Dictionary of stat bonuses
        requirements: Dictionary of stat requirements
    """
    item_id: str = ""
    name: str = "Item"
    description: str = ""
    item_type: ItemType = ItemType.CONSUMABLE
    stack_size: int = 1
    current_stack: int = 1
    weight: float = 0.1
    value: int = 1
    icon: str = ""
    mesh: str = ""
    stats: Dict[str, float] = field(default_factory=dict)
    requirements: Dict[str, int] = field(default_factory=dict)
    
    def can_stack_with(self, other: 'Item') -> bool:
        """Check if this item can stack with another.
        
        Args:
            other: Other item to check
            
        Returns:
            bool: True if items can stack
        """
        return (self.item_id == other.item_id and 
                self.current_stack < self.stack_size)


@dataclass
class Inventory(Component):
    """Entity inventory container.
    
    Attributes:
        slots: List of item entity IDs in inventory
        max_slots: Maximum number of inventory slots
        equipped: Dictionary of equipment slot to item entity ID
        weight_capacity: Maximum carry weight
        current_weight: Current total weight
        is_open: Whether inventory UI is open
    """
    slots: List[Optional[int]] = field(default_factory=list)
    max_slots: int = 20
    equipped: Dict[EquipmentSlot, Optional[int]] = field(default_factory=dict)
    weight_capacity: float = 50.0
    current_weight: float = 0.0
    is_open: bool = False
    
    def __post_init__(self):
        """Initialize equipment slots."""
        if not self.equipped:
            for slot in EquipmentSlot:
                self.equipped[slot] = None
        if not self.slots:
            self.slots = [None] * self.max_slots
    
    def add_item(self, item_entity_id: int, world) -> bool:
        """Add item to inventory.
        
        Args:
            item_entity_id: Entity ID of item to add
            world: World reference to get item component
            
        Returns:
            bool: True if item was added successfully
        """
        # Check for existing stack
        item_entity = world.get_entity(item_entity_id)
        if not item_entity:
            return False
            
        item_component = item_entity.get_component(Item)
        if not item_component:
            return False
        
        # Try to stack with existing items
        for i, slot_item_id in enumerate(self.slots):
            if slot_item_id is not None:
                slot_item = world.get_entity(slot_item_id)
                if slot_item:
                    slot_item_component = slot_item.get_component(Item)
                    if slot_item_component and slot_item_component.can_stack_with(item_component):
                        # Add to stack
                        available_space = slot_item_component.stack_size - slot_item_component.current_stack
                        if available_space > 0:
                            transfer_amount = min(item_component.current_stack, available_space)
                            slot_item_component.current_stack += transfer_amount
                            item_component.current_stack -= transfer_amount
                            
                            if item_component.current_stack == 0:
                                world.destroy_entity(item_entity_id)
                                return True
        
        # Find empty slot
        for i, slot_item_id in enumerate(self.slots):
            if slot_item_id is None:
                self.slots[i] = item_entity_id
                self.current_weight += item_component.weight * item_component.current_stack
                return True
        
        return False
    
    def remove_item(self, slot_index: int, world) -> Optional[int]:
        """Remove item from inventory slot.
        
        Args:
            slot_index: Index of slot to remove from
            world: World reference
            
        Returns:
            Optional[int]: Entity ID of removed item, or None
        """
        if 0 <= slot_index < len(self.slots):
            item_entity_id = self.slots[slot_index]
            if item_entity_id is not None:
                item_entity = world.get_entity(item_entity_id)
                if item_entity:
                    item_component = item_entity.get_component(Item)
                    if item_component:
                        self.current_weight -= item_component.weight * item_component.current_stack
                self.slots[slot_index] = None
                return item_entity_id
        return None


@dataclass
class Equipment(Component):
    """Equipment state for an entity.
    
    Attributes:
        slot: Equipment slot this item occupies
        is_equipped: Whether currently equipped
        equipped_by: Entity ID of wearer
        durability: Current durability
        max_durability: Maximum durability
    """
    slot: EquipmentSlot = EquipmentSlot.MAIN_HAND
    is_equipped: bool = False
    equipped_by: Optional[int] = None
    durability: float = 100.0
    max_durability: float = 100.0


@dataclass
class Currency(Component):
    """Currency and wealth component.
    
    Attributes:
        gold: Amount of gold
        silver: Amount of silver
        copper: Amount of copper
        gems: Dictionary of gem types and counts
    """
    gold: int = 0
    silver: int = 0
    copper: int = 0
    gems: Dict[str, int] = field(default_factory=dict)
    
    def total_copper_value(self) -> int:
        """Calculate total value in copper coins.
        
        Returns:
            int: Total value in copper
        """
        return self.copper + (self.silver * 100) + (self.gold * 10000)
    
    def add_copper(self, amount: int) -> None:
        """Add copper coins, converting to higher denominations.
        
        Args:
            amount: Copper coins to add
        """
        total = self.total_copper_value() + amount
        self.gold = total // 10000
        total %= 10000
        self.silver = total // 100
        self.copper = total % 100