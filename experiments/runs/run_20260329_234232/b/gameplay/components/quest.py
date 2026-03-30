"""
Quest-related components for the 2D RPG.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from engine.ecs import Component


class QuestState(Enum):
    """Quest states."""
    NOT_STARTED = "not_started"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class ObjectiveType(Enum):
    """Types of quest objectives."""
    KILL = "kill"
    COLLECT = "collect"
    TALK = "talk"
    GO_TO = "go_to"
    INTERACT = "interact"
    ESCORT = "escort"
    DEFEND = "defend"


class DialogueNodeType(Enum):
    """Types of dialogue nodes."""
    TEXT = "text"
    QUESTION = "question"
    BRANCH = "branch"
    ACTION = "action"
    END = "end"


@dataclass
class QuestComponent(Component):
    """
    Component for quest tracking.
    """
    quest_id: str = ""
    quest_name: str = "Quest"
    description: str = ""
    quest_giver: str = ""  # NPC ID
    quest_state: QuestState = QuestState.NOT_STARTED
    objectives: List[Dict[str, Any]] = field(default_factory=list)
    rewards: Dict[str, Any] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)  # Quest IDs
    level_requirement: int = 1
    time_limit: float = 0.0  # 0 = no time limit
    start_time: float = 0.0
    completion_time: float = 0.0
    
    # Progress tracking
    current_objective: int = 0
    objective_progress: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    
    def start_quest(self):
        """Start the quest."""
        if self.quest_state == QuestState.NOT_STARTED:
            self.quest_state = QuestState.ACTIVE
            self.start_time = time.time()
            
            # Initialize objective progress
            for i, objective in enumerate(self.objectives):
                self.objective_progress[i] = {
                    'completed': False,
                    'current': 0,
                    'required': objective.get('required', 1)
                }
    
    def update_objective(self, objective_type: ObjectiveType, target: str, amount: int = 1) -> bool:
        """
        Update quest objective progress.
        
        Args:
            objective_type: Type of objective
            target: Target identifier
            amount: Amount to add
            
        Returns:
            True if objective was updated
        """
        if self.quest_state != QuestState.ACTIVE:
            return False
        
        # Find matching objective
        for i, objective in enumerate(self.objectives):
            if (objective.get('type') == objective_type and 
                objective.get('target') == target and
                not self.objective_progress[i]['completed']):
                
                # Update progress
                self.objective_progress[i]['current'] += amount
                
                # Check if objective completed
                if self.objective_progress[i]['current'] >= self.objective_progress[i]['required']:
                    self.objective_progress[i]['completed'] = True
                    self.objective_progress[i]['current'] = self.objective_progress[i]['required']
                    
                    # Move to next objective if this one is complete
                    if i == self.current_objective:
                        self._advance_to_next_objective()
                
                return True
        
        return False
    
    def _advance_to_next_objective(self):
        """Advance to the next objective."""
        # Find next incomplete objective
        for i in range(self.current_objective + 1, len(self.objectives)):
            if not self.objective_progress[i]['completed']:
                self.current_objective = i
                return
        
        # All objectives complete
        self.complete_quest()
    
    def complete_quest(self):
        """Complete the quest."""
        if self.quest_state == QuestState.ACTIVE:
            self.quest_state = QuestState.COMPLETED
            self.completion_time = time.time()
    
    def fail_quest(self):
        """Fail the quest."""
        if self.quest_state == QuestState.ACTIVE:
            self.quest_state = QuestState.FAILED
    
    def get_current_objective(self) -> Optional[Dict[str, Any]]:
        """
        Get current objective.
        
        Returns:
            Current objective data, or None if no objectives
        """
        if not self.objectives or self.current_objective >= len(self.objectives):
            return None
        
        objective = self.objectives[self.current_objective].copy()
        progress = self.objective_progress.get(self.current_objective, {})
        
        objective['progress'] = progress.get('current', 0)
        objective['required'] = progress.get('required', 1)
        objective['completed'] = progress.get('completed', False)
        
        return objective
    
    def get_progress_percentage(self) -> float:
        """
        Get quest completion percentage.
        
        Returns:
            Percentage complete (0.0 to 1.0)
        """
        if not self.objectives:
            return 0.0
        
        completed = sum(1 for prog in self.objective_progress.values() if prog.get('completed', False))
        return completed / len(self.objectives)
    
    def check_time_limit(self) -> bool:
        """
        Check if quest has exceeded time limit.
        
        Returns:
            True if quest failed due to time limit
        """
        if self.time_limit > 0 and self.quest_state == QuestState.ACTIVE:
            elapsed = time.time() - self.start_time
            if elapsed > self.time_limit:
                self.fail_quest()
                return True
        return False
    
    def get_rewards(self) -> Dict[str, Any]:
        """
        Get quest rewards.
        
        Returns:
            Dictionary of rewards
        """
        return self.rewards.copy()


@dataclass
class NPCComponent(Component):
    """
    Component for NPC entities.
    """
    npc_id: str = ""
    npc_name: str = "NPC"
    npc_type: str = "villager"  # merchant, quest_giver, guard, etc.
    dialogue_id: str = ""
    default_dialogue: str = "Hello there!"
    faction: str = "neutral"
    attitude: int = 50  # 0-100, higher = more friendly
    
    # Quest-related
    available_quests: List[str] = field(default_factory=list)  # Quest IDs
    completed_quests: List[str] = field(default_factory=list)
    
    # Merchant-related
    is_merchant: bool = False
    shop_inventory: List[Dict[str, Any]] = field(default_factory=list)
    buy_multiplier: float = 0.5  # Buys items at 50% value
    sell_multiplier: float = 1.5  # Sells items at 150% value
    
    def start_dialogue(self) -> str:
        """
        Start dialogue with NPC.
        
        Returns:
            Initial dialogue text
        """
        return self.default_dialogue
    
    def get_available_quests(self) -> List[str]:
        """
        Get quests available from this NPC.
        
        Returns:
            List of available quest IDs
        """
        return [q for q in self.available_quests if q not in self.completed_quests]
    
    def complete_quest(self, quest_id: str):
        """
        Mark a quest as completed with this NPC.
        
        Args:
            quest_id: Quest ID to mark as completed
        """
        if quest_id in self.available_quests and quest_id not in self.completed_quests:
            self.completed_quests.append(quest_id)
    
    def buy_item(self, item_data: Dict[str, Any]) -> int:
        """
        Calculate buy price for an item.
        
        Args:
            item_data: Item data
            
        Returns:
            Buy price in gold
        """
        value = item_data.get('value', 0)
        return int(value * self.buy_multiplier)
    
    def sell_item(self, item_data: Dict[str, Any]) -> int:
        """
        Calculate sell price for an item.
        
        Args:
            item_data: Item data
            
        Returns:
            Sell price in gold
        """
        value = item_data.get('value', 0)
        return int(value * self.sell_multiplier)
    
    def update_attitude(self, change: int):
        """
        Update NPC attitude.
        
        Args:
            change: Amount to change attitude by (can be negative)
        """
        self.attitude = max(0, min(100, self.attitude + change))


@dataclass
class DialogueComponent(Component):
    """
    Component for dialogue trees.
    """
    dialogue_id: str = ""
    current_node: str = "start"
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    dialogue_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_node(self, node_id: str, node_data: Dict[str, Any]):
        """
        Add a dialogue node.
        
        Args:
            node_id: Node identifier
            node_data: Node data
        """
        self.nodes[node_id] = node_data
    
    def get_current_node(self) -> Optional[Dict[str, Any]]:
        """
        Get current dialogue node.
        
        Returns:
            Current node data, or None
        """
        return self.nodes.get(self.current_node)
    
    def select_option(self, option_index: int) -> Optional[Dict[str, Any]]:
        """
        Select a dialogue option.
        
        Args:
            option_index: Index of selected option
            
        Returns:
            Next node data, or None if invalid
        """
        current_node = self.get_current_node()
        if not current_node:
            return None
        
        if current_node.get('type') != DialogueNodeType.QUESTION:
            return None
        
        options = current_node.get('options', [])
        if option_index < 0 or option_index >= len(options):
            return None
        
        option = options[option_index]
        
        # Record dialogue choice
        self.dialogue_history.append({
            'node': self.current_node,
            'option': option.get('text', ''),
            'timestamp': time.time()
        })
        
        # Move to next node
        next_node_id = option.get('next_node')
        if next_node_id in self.nodes:
            self.current_node = next_node_id
            return self.nodes[next_node_id]
        
        return None
    
    def advance(self) -> Optional[Dict[str, Any]]:
        """
        Advance to next dialogue node.
        
        Returns:
            Next node data, or None if at end
        """
        current_node = self.get_current_node()
        if not current_node:
            return None
        
        # Record dialogue
        if current_node.get('type') == DialogueNodeType.TEXT:
            self.dialogue_history.append({
                'node': self.current_node,
                'text': current_node.get('text', ''),
                'timestamp': time.time()
            })
        
        # Get next node
        next_node_id = current_node.get('next_node')
        if next_node_id in self.nodes:
            self.current_node = next_node_id
            return self.nodes[next_node_id]
        
        # End of dialogue
        if current_node.get('type') == DialogueNodeType.END:
            return None
        
        return None
    
    def reset(self):
        """Reset dialogue to start."""
        self.current_node = "start"
    
    def get_dialogue_text(self) -> str:
        """
        Get text from current node.
        
        Returns:
            Dialogue text
        """
        node = self.get_current_node()
        if not node:
            return ""
        
        if node.get('type') == DialogueNodeType.TEXT:
            return node.get('text', '')
        elif node.get('type') == DialogueNodeType.QUESTION:
            return node.get('question', '')
        
        return ""


@dataclass
class ObjectiveComponent(Component):
    """
    Component for tracking specific objectives.
    """
    objective_id: str = ""
    objective_type: ObjectiveType = ObjectiveType.KILL
    target: str = ""  # Entity ID or item ID
    required: int = 1
    current: int = 0
    completed: bool = False
    parent_quest: str = ""  # Quest ID
    
    def update(self, amount: int = 1) -> bool:
        """
        Update objective progress.
        
        Args:
            amount: Amount to add
            
        Returns:
            True if objective completed
        """
        if self.completed:
            return False
        
        self.current += amount
        
        if self.current >= self.required:
            self.current = self.required
            self.completed = True
            return True
        
        return False
    
    def get_progress(self) -> Dict[str, Any]:
        """
        Get objective progress.
        
        Returns:
            Dictionary with progress information
        """
        return {
            'current': self.current,
            'required': self.required,
            'completed': self.completed,
            'percentage': min(1.0, self.current / self.required) if self.required > 0 else 0.0
        }


# Import required modules
import time