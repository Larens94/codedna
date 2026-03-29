"""quest.py — Quest and objective components.

exports: Quest, Objective, QuestProgress
used_by: gameplay/systems/quest_system.py
rules:   Quest component defines quest data, QuestProgress tracks state
agent:   GameplayDesigner | 2024-01-15 | Created quest components
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from engine.component import Component


class ObjectiveType(Enum):
    """Types of quest objectives."""
    KILL = "kill"
    COLLECT = "collect"
    DELIVER = "deliver"
    TALK = "talk"
    EXPLORE = "explore"
    CRAFT = "craft"
    ESCORT = "escort"


class QuestState(Enum):
    """States a quest can be in."""
    NOT_STARTED = "not_started"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    TURNED_IN = "turned_in"


@dataclass
class Objective(Component):
    """Individual quest objective.
    
    Attributes:
        objective_id: Unique objective identifier
        description: Objective description
        objective_type: Type of objective
        target: Target entity/item/NPC ID
        required_count: Number required for completion
        current_count: Current progress count
        location: Optional location hint
        is_optional: Whether objective is optional
    """
    objective_id: str = ""
    description: str = ""
    objective_type: ObjectiveType = ObjectiveType.KILL
    target: str = ""
    required_count: int = 1
    current_count: int = 0
    location: Optional[str] = None
    is_optional: bool = False
    
    def is_complete(self) -> bool:
        """Check if objective is complete.
        
        Returns:
            bool: True if current_count >= required_count
        """
        return self.current_count >= self.required_count
    
    def progress(self) -> float:
        """Get progress as percentage.
        
        Returns:
            float: Progress percentage (0-100)
        """
        if self.required_count == 0:
            return 100.0
        return min(100.0, (self.current_count / self.required_count) * 100.0)


@dataclass
class Quest(Component):
    """Quest definition and metadata.
    
    Attributes:
        quest_id: Unique quest identifier
        title: Quest title
        description: Quest description
        giver_id: Entity ID of quest giver NPC
        receiver_id: Entity ID of quest turn-in NPC
        objectives: List of objective IDs
        required_level: Minimum level to accept
        required_quests: List of prerequisite quest IDs
        reward_xp: Experience reward
        reward_gold: Gold reward
        reward_items: List of reward item IDs
        reward_reputation: Reputation rewards
        time_limit: Optional time limit in seconds
        is_repeatable: Whether quest can be repeated
        category: Quest category (main, side, daily, etc.)
    """
    quest_id: str = ""
    title: str = "Quest"
    description: str = ""
    giver_id: Optional[int] = None
    receiver_id: Optional[int] = None
    objectives: List[str] = field(default_factory=list)
    required_level: int = 1
    required_quests: List[str] = field(default_factory=list)
    reward_xp: int = 100
    reward_gold: int = 10
    reward_items: List[str] = field(default_factory=list)
    reward_reputation: Dict[str, int] = field(default_factory=dict)
    time_limit: Optional[float] = None
    is_repeatable: bool = False
    category: str = "side"


@dataclass
class QuestProgress(Component):
    """Quest progress tracking for an entity.
    
    Attributes:
        active_quests: Dictionary of quest_id -> quest state
        completed_quests: List of completed quest IDs
        failed_quests: List of failed quest IDs
        objective_progress: Dictionary of objective_id -> current_count
        quest_log: List of recent quest events
        selected_quest: Currently selected/focused quest ID
    """
    active_quests: Dict[str, QuestState] = field(default_factory=dict)
    completed_quests: List[str] = field(default_factory=list)
    failed_quests: List[str] = field(default_factory=list)
    objective_progress: Dict[str, int] = field(default_factory=dict)
    quest_log: List[Dict[str, Any]] = field(default_factory=list)
    selected_quest: Optional[str] = None
    
    def start_quest(self, quest_id: str) -> bool:
        """Start a new quest.
        
        Args:
            quest_id: ID of quest to start
            
        Returns:
            bool: True if quest started successfully
        """
        if quest_id not in self.active_quests:
            self.active_quests[quest_id] = QuestState.ACTIVE
            self._log_event(quest_id, "quest_started", "Quest started")
            return True
        return False
    
    def update_objective(self, objective_id: str, amount: int = 1) -> bool:
        """Update objective progress.
        
        Args:
            objective_id: ID of objective to update
            amount: Amount to add to progress
            
        Returns:
            bool: True if objective exists and was updated
        """
        current = self.objective_progress.get(objective_id, 0)
        self.objective_progress[objective_id] = current + amount
        return True
    
    def complete_quest(self, quest_id: str) -> bool:
        """Mark quest as completed.
        
        Args:
            quest_id: ID of quest to complete
            
        Returns:
            bool: True if quest was active and is now completed
        """
        if quest_id in self.active_quests:
            self.active_quests[quest_id] = QuestState.COMPLETED
            self.completed_quests.append(quest_id)
            self._log_event(quest_id, "quest_completed", "Quest completed!")
            return True
        return False
    
    def fail_quest(self, quest_id: str) -> bool:
        """Mark quest as failed.
        
        Args:
            quest_id: ID of quest to fail
            
        Returns:
            bool: True if quest was active and is now failed
        """
        if quest_id in self.active_quests:
            self.active_quests[quest_id] = QuestState.FAILED
            self.failed_quests.append(quest_id)
            self._log_event(quest_id, "quest_failed", "Quest failed")
            return True
        return False
    
    def _log_event(self, quest_id: str, event_type: str, message: str) -> None:
        """Add event to quest log.
        
        Args:
            quest_id: Quest ID
            event_type: Type of event
            message: Event message
        """
        self.quest_log.append({
            "quest_id": quest_id,
            "event_type": event_type,
            "message": message,
            "timestamp": 0.0  # Would be set by system with current time
        })
        # Keep only last 100 entries
        if len(self.quest_log) > 100:
            self.quest_log.pop(0)