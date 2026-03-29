"""npc.py — NPC and dialogue components.

exports: NPC, Dialogue, Behavior
used_by: gameplay/systems/quest_system.py, gameplay/systems/npc_system.py
rules:   NPC component marks entity as non-player character
agent:   GameplayDesigner | 2024-01-15 | Created NPC components
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from engine.component import Component


class NPCType(Enum):
    """Types of NPCs."""
    VENDOR = "vendor"
    QUEST_GIVER = "quest_giver"
    GUARD = "guard"
    CIVILIAN = "civilian"
    MONSTER = "monster"
    BOSS = "boss"
    COMPANION = "companion"


class DialogueNodeType(Enum):
    """Types of dialogue nodes."""
    TEXT = "text"
    QUESTION = "question"
    BRANCH = "branch"
    ACTION = "action"
    END = "end"


class BehaviorState(Enum):
    """NPC behavior states."""
    IDLE = "idle"
    PATROL = "patrol"
    FOLLOW = "follow"
    FLEE = "flee"
    ATTACK = "attack"
    DIALOGUE = "dialogue"
    TRADING = "trading"


@dataclass
class NPC(Component):
    """Non-player character definition.
    
    Attributes:
        npc_id: Unique NPC identifier
        name: NPC name
        npc_type: Type of NPC
        faction: NPC faction alignment
        reputation: Dictionary of faction -> reputation value
        is_merchant: Whether NPC can trade
        shop_inventory: List of item IDs for sale
        buy_multiplier: Price multiplier when buying from player
        sell_multiplier: Price multiplier when selling to player
        quests_offered: List of quest IDs this NPC offers
        quests_received: List of quest IDs this NPC receives
        dialogue_tree: Root dialogue node ID
    """
    npc_id: str = ""
    name: str = "NPC"
    npc_type: NPCType = NPCType.CIVILIAN
    faction: str = "neutral"
    reputation: Dict[str, int] = field(default_factory=dict)
    is_merchant: bool = False
    shop_inventory: List[str] = field(default_factory=list)
    buy_multiplier: float = 0.5  # Buys from player at 50% value
    sell_multiplier: float = 1.5  # Sells to player at 150% value
    quests_offered: List[str] = field(default_factory=list)
    quests_received: List[str] = field(default_factory=list)
    dialogue_tree: Optional[str] = None


@dataclass
class Dialogue(Component):
    """Dialogue tree node.
    
    Attributes:
        node_id: Unique node identifier
        text: Dialogue text
        node_type: Type of dialogue node
        responses: List of response node IDs
        conditions: Conditions required to show this node
        actions: Actions to execute when node is reached
        next_node: Next node ID (for linear dialogue)
        speaker: Entity ID of speaker
        listener: Entity ID of listener
    """
    node_id: str = ""
    text: str = ""
    node_type: DialogueNodeType = DialogueNodeType.TEXT
    responses: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    next_node: Optional[str] = None
    speaker: Optional[int] = None
    listener: Optional[int] = None


@dataclass
class Behavior(Component):
    """NPC behavior and state machine.
    
    Attributes:
        current_state: Current behavior state
        target_entity: Entity ID of current target
        patrol_route: List of patrol points
        current_patrol_index: Current patrol point index
        idle_time: Time to remain idle
        aggression_level: How aggressive NPC is (0-100)
        fear_level: How fearful NPC is (0-100)
        last_state_change: Time of last state change
        state_duration: How long in current state
        custom_behaviors: Custom behavior definitions
    """
    current_state: BehaviorState = BehaviorState.IDLE
    target_entity: Optional[int] = None
    patrol_route: List[Dict[str, float]] = field(default_factory=list)  # [{x, y, z}, ...]
    current_patrol_index: int = 0
    idle_time: float = 5.0
    aggression_level: int = 50
    fear_level: int = 10
    last_state_change: float = 0.0
    state_duration: float = 0.0
    custom_behaviors: Dict[str, Any] = field(default_factory=dict)
    
    def change_state(self, new_state: BehaviorState, current_time: float) -> None:
        """Change to a new behavior state.
        
        Args:
            new_state: New state to transition to
            current_time: Current game time
        """
        if self.current_state != new_state:
            self.current_state = new_state
            self.last_state_change = current_time
            self.state_duration = 0.0
    
    def update_duration(self, delta_time: float) -> None:
        """Update state duration.
        
        Args:
            delta_time: Time since last update
        """
        self.state_duration += delta_time