"""inventory_system.py — Handles item management and equipment.

exports: InventorySystem class
used_by: gameplay/main.py → Game._initialize_gameplay
rules:   Manages inventory slots, equipment, and item interactions
agent:   GameplayDesigner | 2024-01-15 | Created inventory system
"""

from typing import Set, Type, Optional, List
from engine.system import System
from engine.component import Component
from gameplay.components.inventory import (
    Inventory, Item, Equipment, Currency, EquipmentSlot
)
from gameplay.components.player import Player


class InventorySystem(System):
    """System for managing entity inventories and equipment.
    
    Rules:
    - Handles item pickup and dropping
    - Manages equipment slots
    - Processes item stacking
    - Handles currency transactions
    """
    
    def __init__(self):
        """Initialize inventory system."""
        required_components: Set[Type[Component]] = {Inventory}
        super().__init__(required_components)
        
    def update(self, world, delta_time: float) -> None:
        """Update inventory states.
        
        Args:
            world: World to operate on
            delta_time: Time since last update
        """
        # Inventory system doesn't need per-frame updates
        # Most operations are event-driven
        pass
    
    def pick_up_item(self, world, entity_id: int, item_entity_id: int) -> bool:
        """Pick up an item and add to inventory.
        
        Args:
            world: World reference
            entity_id: ID of entity picking up item
            item_entity_id: ID of item entity to pick up
            
        Returns:
            bool: True if item was picked up successfully
        """
        entity = world.get_entity(entity_id)
        item_entity = world.get_entity(item_entity_id)
        
        if not entity or not item_entity:
            return False
        
        inventory = entity.get_component(Inventory)
        item = item_entity.get_component(Item)
        
        if not inventory or not item:
            return False
        
        # Check weight capacity
        item_weight = item.weight * item.current_stack
        if inventory.current_weight + item_weight > inventory.weight_capacity:
            return False
        
        # Add to inventory
        if inventory.add_item(item_entity_id, world):
            # Item successfully added, remove from world or hide
            # TODO: Hide item entity or mark as collected
            return True
        
        return False
    
    def drop_item(self, world, entity_id: int, slot_index: int) -> Optional[int]:
        """Drop item from inventory slot.
        
        Args:
            world: World reference
            entity_id: ID of entity dropping item
            slot_index: Inventory slot index
            
        Returns:
            Optional[int]: Entity ID of dropped item, or None
        """
        entity = world.get_entity(entity_id)
        if not entity:
            return None
        
        inventory = entity.get_component(Inventory)
        if not inventory:
            return None
        
        # Remove item from inventory
        item_entity_id = inventory.remove_item(slot_index, world)
        if item_entity_id:
            # TODO: Create dropped item entity in world at entity's position
            # For now, just return the entity ID
            return item_entity_id
        
        return None
    
    def equip_item(self, world, entity_id: int, slot_index: int) -> bool:
        """Equip item from inventory slot.
        
        Args:
            world: World reference
            entity_id: ID of entity equipping item
            slot_index: Inventory slot index
            
        Returns:
            bool: True if item was equipped successfully
        """
        entity = world.get_entity(entity_id)
        if not entity:
            return False
        
        inventory = entity.get_component(Inventory)
        if not inventory:
            return False
        
        # Get item from inventory
        if slot_index < 0 or slot_index >= len(inventory.slots):
            return False
        
        item_entity_id = inventory.slots[slot_index]
        if item_entity_id is None:
            return False
        
        item_entity = world.get_entity(item_entity_id)
        if not item_entity:
            return False
        
        item = item_entity.get_component(Item)
        equipment = item_entity.get_component(Equipment)
        
        if not item or not equipment:
            return False
        
        # Check if slot is already occupied
        if inventory.equipped.get(equipment.slot) is not None:
            # Unequip current item first
            self.unequip_item(world, entity_id, equipment.slot)
        
        # Equip the item
        inventory.equipped[equipment.slot] = item_entity_id
        equipment.is_equipped = True
        equipment.equipped_by = entity_id
        
        # Remove from inventory slots
        inventory.slots[slot_index] = None
        
        # TODO: Apply item stat bonuses to entity
        
        return True
    
    def unequip_item(self, world, entity_id: int, slot: EquipmentSlot) -> bool:
        """Unequip item from equipment slot.
        
        Args:
            world: World reference
            entity_id: ID of entity unequipping item
            slot: Equipment slot to unequip from
            
        Returns:
            bool: True if item was unequipped successfully
        """
        entity = world.get_entity(entity_id)
        if not entity:
            return False
        
        inventory = entity.get_component(Inventory)
        if not inventory:
            return False
        
        # Get equipped item
        item_entity_id = inventory.equipped.get(slot)
        if item_entity_id is None:
            return False
        
        item_entity = world.get_entity(item_entity_id)
        if not item_entity:
            return False
        
        equipment = item_entity.get_component(Equipment)
        if not equipment:
            return False
        
        # Find empty inventory slot
        empty_slot = None
        for i, slot_item_id in enumerate(inventory.slots):
            if slot_item_id is None:
                empty_slot = i
                break
        
        if empty_slot is None:
            return False  # No space in inventory
        
        # Move to inventory
        inventory.slots[empty_slot] = item_entity_id
        inventory.equipped[slot] = None
        equipment.is_equipped = False
        equipment.equipped_by = None
        
        # TODO: Remove item stat bonuses from entity
        
        return True
    
    def use_item(self, world, entity_id: int, slot_index: int) -> bool:
        """Use consumable item from inventory.
        
        Args:
            world: World reference
            entity_id: ID of entity using item
            slot_index: Inventory slot index
            
        Returns:
            bool: True if item was used successfully
        """
        entity = world.get_entity(entity_id)
        if not entity:
            return False
        
        inventory = entity.get_component(Inventory)
        if not inventory:
            return False
        
        # Get item from inventory
        if slot_index < 0 or slot_index >= len(inventory.slots):
            return False
        
        item_entity_id = inventory.slots[slot_index]
        if item_entity_id is None:
            return False
        
        item_entity = world.get_entity(item_entity_id)
        if not item_entity:
            return False
        
        item = item_entity.get_component(Item)
        if not item:
            return False
        
        # Check if item is consumable
        from gameplay.components.inventory import ItemType
        if item.item_type != ItemType.CONSUMABLE:
            return False
        
        # TODO: Apply consumable effects (healing, buffs, etc.)
        
        # Reduce stack size
        item.current_stack -= 1
        
        # Remove item if stack is empty
        if item.current_stack <= 0:
            inventory.remove_item(slot_index, world)
            world.destroy_entity(item_entity_id)
        
        return True
    
    def transfer_currency(self, world, from_entity_id: int, to_entity_id: int, 
                         amount: int) -> bool:
        """Transfer currency between entities.
        
        Args:
            world: World reference
            from_entity_id: ID of entity giving currency
            to_entity_id: ID of entity receiving currency
            amount: Amount to transfer in copper
            
        Returns:
            bool: True if transfer was successful
        """
        from_entity = world.get_entity(from_entity_id)
        to_entity = world.get_entity(to_entity_id)
        
        if not from_entity or not to_entity:
            return False
        
        from_currency = from_entity.get_component(Currency)
        to_currency = to_entity.get_component(Currency)
        
        if not from_currency or not to_currency:
            return False
        
        # Check if sender has enough
        if from_currency.total_copper_value() < amount:
            return False
        
        # Remove from sender
        total_from = from_currency.total_copper_value() - amount
        from_currency.gold = total_from // 10000
        total_from %= 10000
        from_currency.silver = total_from // 100
        from_currency.copper = total_from % 100
        
        # Add to receiver
        to_currency.add_copper(amount)
        
        return True
    
    def get_player_inventory(self, world) -> Optional[Inventory]:
        """Get player inventory component.
        
        Args:
            world: World reference
            
        Returns:
            Optional[Inventory]: Player inventory if found
        """
        # Query for player entity
        player_entities = world.query_entities({Player})
        if not player_entities:
            return None
        
        player_entity = player_entities[0]
        return player_entity.get_component(Inventory)