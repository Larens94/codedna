"""quest_system.py — Handles quest progression and NPC interactions.

exports: QuestSystem class
used_by: gameplay/main.py → Game._initialize_gameplay
rules:   Manages quest states, objectives, and NPC dialogue
agent:   GameplayDesigner | 2024-01-15 | Created quest system
"""

from typing import Set, Type, Optional, Dict, Any
from engine.system import System
from engine.component import Component
from gameplay.components.quest import (
    Quest, Objective, QuestProgress, QuestState, ObjectiveType
)
from gameplay.components.npc import NPC, Dialogue, Behavior, BehaviorState
from gameplay.components.player import Player
from gameplay.components.inventory import Item, ItemType
from gameplay.components.combat import Enemy


class QuestSystem(System):
    """System for managing quests, objectives, and NPC interactions.
    
    Rules:
    - Tracks quest progress and objectives
    - Handles NPC dialogue trees
    - Awards quest rewards
    - Manages quest state transitions
    """
    
    def __init__(self):
        """Initialize quest system."""
        required_components: Set[Type[Component]] = {QuestProgress}
        super().__init__(required_components)
        self._current_time = 0.0
        
    def update(self, world, delta_time: float) -> None:
        """Update quest states and check objectives.
        
        Args:
            world: World to operate on
            delta_time: Time since last update
        """
        self._current_time += delta_time
        
        # Check all entities with quest progress
        entities = self.query_entities(world)
        for entity in entities:
            quest_progress = entity.get_component(QuestProgress)
            
            # Check time-limited quests
            self._check_time_limits(world, entity, quest_progress)
            
            # Update quest log timestamps
            for entry in quest_progress.quest_log:
                if "timestamp" not in entry or entry["timestamp"] == 0.0:
                    entry["timestamp"] = self._current_time
    
    def start_quest(self, world, entity_id: int, quest_id: str) -> bool:
        """Start a new quest for an entity.
        
        Args:
            world: World reference
            entity_id: ID of entity starting quest
            quest_id: ID of quest to start
            
        Returns:
            bool: True if quest was started successfully
        """
        entity = world.get_entity(entity_id)
        if not entity:
            return False
        
        quest_progress = entity.get_component(QuestProgress)
        if not quest_progress:
            return False
        
        # Check if quest exists in world
        quest_entity = self._find_quest_entity(world, quest_id)
        if not quest_entity:
            return False
        
        quest = quest_entity.get_component(Quest)
        if not quest:
            return False
        
        # Check prerequisites
        if not self._check_prerequisites(world, entity, quest):
            return False
        
        # Start quest
        return quest_progress.start_quest(quest_id)
    
    def update_kill_objective(self, world, entity_id: int, enemy_type: str, 
                             count: int = 1) -> bool:
        """Update kill objective progress.
        
        Args:
            world: World reference
            entity_id: ID of entity to update
            enemy_type: Type of enemy killed
            count: Number killed
            
        Returns:
            bool: True if any objectives were updated
        """
        entity = world.get_entity(entity_id)
        if not entity:
            return False
        
        quest_progress = entity.get_component(QuestProgress)
        if not quest_progress:
            return False
        
        updated = False
        
        # Check all active quests
        for quest_id, state in quest_progress.active_quests.items():
            if state != QuestState.ACTIVE:
                continue
            
            quest_entity = self._find_quest_entity(world, quest_id)
            if not quest_entity:
                continue
            
            quest = quest_entity.get_component(Quest)
            if not quest:
                continue
            
            # Check each objective
            for objective_id in quest.objectives:
                objective_entity = self._find_objective_entity(world, objective_id)
                if not objective_entity:
                    continue
                
                objective = objective_entity.get_component(Objective)
                if not objective:
                    continue
                
                # Check if this is a kill objective for the right enemy type
                if (objective.objective_type == ObjectiveType.KILL and 
                    objective.target == enemy_type):
                    
                    # Update progress
                    quest_progress.update_objective(objective_id, count)
                    updated = True
        
        return updated
    
    def update_collect_objective(self, world, entity_id: int, item_id: str, 
                                count: int = 1) -> bool:
        """Update collect objective progress.
        
        Args:
            world: World reference
            entity_id: ID of entity to update
            item_id: ID of item collected
            count: Number collected
            
        Returns:
            bool: True if any objectives were updated
        """
        # Similar to update_kill_objective but for collect objectives
        entity = world.get_entity(entity_id)
        if not entity:
            return False
        
        quest_progress = entity.get_component(QuestProgress)
        if not quest_progress:
            return False
        
        updated = False
        
        for quest_id, state in quest_progress.active_quests.items():
            if state != QuestState.ACTIVE:
                continue
            
            quest_entity = self._find_quest_entity(world, quest_id)
            if not quest_entity:
                continue
            
            quest = quest_entity.get_component(Quest)
            if not quest:
                continue
            
            for objective_id in quest.objectives:
                objective_entity = self._find_objective_entity(world, objective_id)
                if not objective_entity:
                    continue
                
                objective = objective_entity.get_component(Objective)
                if not objective:
                    continue
                
                if (objective.objective_type == ObjectiveType.COLLECT and 
                    objective.target == item_id):
                    
                    quest_progress.update_objective(objective_id, count)
                    updated = True
        
        return updated
    
    def complete_quest(self, world, entity_id: int, quest_id: str) -> bool:
        """Complete a quest and award rewards.
        
        Args:
            world: World reference
            entity_id: ID of entity completing quest
            quest_id: ID of quest to complete
            
        Returns:
            bool: True if quest was completed successfully
        """
        entity = world.get_entity(entity_id)
        if not entity:
            return False
        
        quest_progress = entity.get_component(QuestProgress)
        if not quest_progress:
            return False
        
        quest_entity = self._find_quest_entity(world, quest_id)
        if not quest_entity:
            return False
        
        quest = quest_entity.get_component(Quest)
        if not quest:
            return False
        
        # Check if all objectives are complete
        if not self._check_objectives_complete(world, quest, quest_progress):
            return False
        
        # Award rewards
        self._award_quest_rewards(world, entity, quest)
        
        # Mark quest as completed
        return quest_progress.complete_quest(quest_id)
    
    def interact_with_npc(self, world, entity_id: int, npc_entity_id: int) -> Dict[str, Any]:
        """Initiate interaction with NPC.
        
        Args:
            world: World reference
            entity_id: ID of entity interacting
            npc_entity_id: ID of NPC entity
            
        Returns:
            Dict[str, Any]: Interaction result with dialogue and options
        """
        entity = world.get_entity(entity_id)
        npc_entity = world.get_entity(npc_entity_id)
        
        if not entity or not npc_entity:
            return {"success": False, "error": "Entity not found"}
        
        npc = npc_entity.get_component(NPC)
        if not npc:
            return {"success": False, "error": "Not an NPC"}
        
        # Update NPC behavior
        behavior = npc_entity.get_component(Behavior)
        if behavior:
            behavior.change_state(BehaviorState.DIALOGUE, self._current_time)
        
        # Get starting dialogue
        dialogue_result = self._get_dialogue(world, npc, entity_id)
        
        # Check for available quests
        available_quests = self._get_available_quests(world, npc, entity_id)
        
        return {
            "success": True,
            "npc_name": npc.name,
            "dialogue": dialogue_result,
            "available_quests": available_quests,
            "is_merchant": npc.is_merchant,
            "shop_inventory": npc.shop_inventory if npc.is_merchant else []
        }
    
    def _check_prerequisites(self, world, entity, quest: Quest) -> bool:
        """Check if entity meets quest prerequisites.
        
        Args:
            world: World reference
            entity: Entity to check
            quest: Quest component
            
        Returns:
            bool: True if prerequisites are met
        """
        # Check level requirement
        player_stats = entity.get_component(PlayerStats)
        if player_stats and player_stats.level < quest.required_level:
            return False
        
        # Check required quests
        quest_progress = entity.get_component(QuestProgress)
        if quest_progress:
            for required_quest_id in quest.required_quests:
                if required_quest_id not in quest_progress.completed_quests:
                    return False
        
        return True
    
    def _check_objectives_complete(self, world, quest: Quest, 
                                 quest_progress: QuestProgress) -> bool:
        """Check if all quest objectives are complete.
        
        Args:
            world: World reference
            quest: Quest component
            quest_progress: QuestProgress component
            
        Returns:
            bool: True if all objectives are complete
        """
        for objective_id in quest.objectives:
            objective_entity = self._find_objective_entity(world, objective_id)
            if not objective_entity:
                continue
            
            objective = objective_entity.get_component(Objective)
            if not objective:
                continue
            
            # Skip optional objectives
            if objective.is_optional:
                continue
            
            # Check progress
            current = quest_progress.objective_progress.get(objective_id, 0)
            if current < objective.required_count:
                return False
        
        return True
    
    def _award_quest_rewards(self, world, entity, quest: Quest) -> None:
        """Award quest rewards to entity.
        
        Args:
            world: World reference
            entity: Entity to reward
            quest: Quest component with rewards
        """
        # Award experience
        experience = entity.get_component(Experience)
        if experience and quest.reward_xp > 0:
            experience.add_xp(quest.reward_xp)
        
        # Award currency
        currency = entity.get_component(Currency)
        if currency and quest.reward_gold > 0:
            currency.add_copper(quest.reward_gold * 10000)  # Convert gold to copper
        
        # TODO: Award items
        # TODO: Award reputation
    
    def _check_time_limits(self, world, entity, quest_progress: QuestProgress) -> None:
        """Check and fail time-limited quests.
        
        Args:
            world: World reference
            entity: Entity to check
            quest_progress: QuestProgress component
        """
        for quest_id, state in list(quest_progress.active_quests.items()):
            if state != QuestState.ACTIVE:
                continue
            
            quest_entity = self._find_quest_entity(world, quest_id)
            if not quest_entity:
                continue
            
            quest = quest_entity.get_component(Quest)
            if not quest or not quest.time_limit:
                continue
            
            # TODO: Check if time limit has expired
            # Would need to track quest start time
    
    def _get_dialogue(self, world, npc: NPC, entity_id: int) -> Dict[str, Any]:
        """Get dialogue for NPC interaction.
        
        Args:
            world: World reference
            npc: NPC component
            entity_id: ID of interacting entity
            
        Returns:
            Dict[str, Any]: Dialogue data
        """
        if not npc.dialogue_tree:
            return {
                "text": f"{npc.name} has nothing to say.",
                "responses": [],
                "node_type": "text"
            }
        
        # TODO: Traverse dialogue tree based on conditions
        # For now, return simple greeting
        return {
            "text": f"Hello, traveler. I am {npc.name}.",
            "responses": [
                {"text": "Do you have any quests?", "action": "show_quests"},
                {"text": "What do you sell?", "action": "show_shop"},
                {"text": "Goodbye.", "action": "end"}
            ],
            "node_type": "question"
        }
    
    def _get_available_quests(self, world, npc: NPC, entity_id: int) -> List[Dict[str, Any]]:
        """Get quests available from NPC.
        
        Args:
            world: World reference
            npc: NPC component
            entity_id: ID of interacting entity
            
        Returns:
            List[Dict[str, Any]]: List of available quests
        """
        available_quests = []
        
        for quest_id in npc.quests_offered:
            quest_entity = self._find_quest_entity(world, quest_id)
            if not quest_entity:
                continue
            
            quest = quest_entity.get_component(Quest)
            if not quest:
                continue
            
            # Check if player already has this quest
            entity = world.get_entity(entity_id)
            if not entity:
                continue
            
            quest_progress = entity.get_component(QuestProgress)
            if not quest_progress:
                continue
            
            if quest_id in quest_progress.active_quests:
                continue
            
            if quest_id in quest_progress.completed_quests and not quest.is_repeatable:
                continue
            
            # Check prerequisites
            if self._check_prerequisites(world, entity, quest):
                available_quests.append({
                    "quest_id": quest_id,
                    "title": quest.title,
                    "description": quest.description,
                    "required_level": quest.required_level,
                    "rewards": {
                        "xp": quest.reward_xp,
                        "gold": quest.reward_gold,
                        "items": quest.reward_items
                    }
                })
        
        return available_quests
    
    def _find_quest_entity(self, world, quest_id: str) -> Optional['Entity']:
        """Find entity with specific quest ID.
        
        Args:
            world: World reference
            quest_id: Quest ID to find
            
        Returns:
            Optional[Entity]: Quest entity if found
        """
        # Query all entities with Quest component
        quest_entities = world.query_entities({Quest})
        for entity in quest_entities:
            quest = entity.get_component(Quest)
            if quest and quest.quest_id == quest_id:
                return entity
        return None
    
    def _find_objective_entity(self, world, objective_id: str) -> Optional['Entity']:
        """Find entity with specific objective ID.
        
        Args:
            world: World reference
            objective_id: Objective ID to find
            
        Returns:
            Optional[Entity]: Objective entity if found
        """
        # Query all entities with Objective component
        objective_entities = world.query_entities({Objective})
        for entity in objective_entities:
            objective = entity.get_component(Objective)
            if objective and objective.objective_id == objective_id:
                return entity
        return None