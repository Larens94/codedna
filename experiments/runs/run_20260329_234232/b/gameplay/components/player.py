"""
Player-related components for the 2D RPG.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from engine.ecs import Component


class PlayerClass(Enum):
    """Player character classes."""
    WARRIOR = "warrior"
    MAGE = "mage"
    ROGUE = "rogue"
    CLERIC = "cleric"
    RANGER = "ranger"


class SkillType(Enum):
    """Types of skills."""
    COMBAT = "combat"
    MAGIC = "magic"
    STEALTH = "stealth"
    CRAFTING = "crafting"
    SOCIAL = "social"


@dataclass
class PlayerComponent(Component):
    """
    Component identifying an entity as a player character.
    """
    player_id: str = "player"
    player_name: str = "Hero"
    player_class: PlayerClass = PlayerClass.WARRIOR
    is_main_player: bool = True
    spawn_point: Tuple[float, float] = (0.0, 0.0)
    last_save_time: float = 0.0
    play_time: float = 0.0  # Total play time in seconds


@dataclass
class StatsComponent(Component):
    """
    Component for character attributes and statistics.
    """
    # Core attributes
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    
    # Derived stats
    max_health: float = 100.0
    max_mana: float = 50.0
    max_stamina: float = 100.0
    
    attack_power: float = 10.0
    spell_power: float = 10.0
    defense: float = 5.0
    magic_resist: float = 5.0
    
    # Movement
    move_speed: float = 5.0
    jump_height: float = 2.0
    sprint_multiplier: float = 1.5
    
    # Combat
    critical_chance: float = 0.05  # 5%
    critical_multiplier: float = 1.5
    dodge_chance: float = 0.05  # 5%
    block_chance: float = 0.1  # 10%
    
    def calculate_derived_stats(self):
        """Calculate derived stats from base attributes."""
        # Health based on constitution
        self.max_health = 50.0 + (self.constitution * 5.0)
        
        # Mana based on intelligence
        self.max_mana = 20.0 + (self.intelligence * 3.0)
        
        # Stamina based on constitution and strength
        self.max_stamina = 50.0 + (self.constitution * 3.0) + (self.strength * 2.0)
        
        # Attack power based on strength
        self.attack_power = self.strength * 1.0
        
        # Spell power based on intelligence
        self.spell_power = self.intelligence * 1.0
        
        # Defense based on constitution and equipment
        self.defense = self.constitution * 0.5
        
        # Magic resist based on wisdom
        self.magic_resist = self.wisdom * 0.5
        
        # Critical chance based on dexterity
        self.critical_chance = 0.05 + (self.dexterity * 0.01)
        
        # Dodge chance based on dexterity
        self.dodge_chance = 0.05 + (self.dexterity * 0.005)


@dataclass
class LevelComponent(Component):
    """
    Component for character level and progression.
    """
    level: int = 1
    experience: int = 0
    experience_to_next_level: int = 100
    skill_points: int = 0
    attribute_points: int = 0
    
    # Level milestones
    max_level: int = 50
    base_exp_required: int = 100
    exp_growth_factor: float = 1.5
    
    def add_experience(self, amount: int) -> bool:
        """
        Add experience and check for level up.
        
        Args:
            amount: Amount of experience to add
            
        Returns:
            True if leveled up
        """
        self.experience += amount
        
        # Check for level up
        leveled_up = False
        while self.experience >= self.experience_to_next_level and self.level < self.max_level:
            self.level_up()
            leveled_up = True
        
        return leveled_up
    
    def level_up(self):
        """Increase level and calculate new experience requirement."""
        self.level += 1
        self.experience -= self.experience_to_next_level
        
        # Calculate new experience requirement
        self.experience_to_next_level = int(
            self.base_exp_required * (self.exp_growth_factor ** (self.level - 1))
        )
        
        # Grant points
        self.skill_points += 2
        self.attribute_points += 5
        
        # Ensure experience doesn't go negative
        if self.experience < 0:
            self.experience = 0
    
    def get_experience_progress(self) -> float:
        """
        Get experience progress to next level.
        
        Returns:
            Progress as percentage (0.0 to 1.0)
        """
        if self.experience_to_next_level == 0:
            return 0.0
        return min(self.experience / self.experience_to_next_level, 1.0)


@dataclass
class ExperienceComponent(Component):
    """
    Component for tracking experience gain sources.
    """
    last_experience_gain: float = 0.0
    experience_sources: Dict[str, int] = field(default_factory=dict)
    bonus_experience: float = 1.0  # Multiplier
    
    def add_experience_source(self, source: str, amount: int):
        """
        Add experience from a source.
        
        Args:
            source: Source of experience (combat, quest, etc.)
            amount: Amount of experience
        """
        if source not in self.experience_sources:
            self.experience_sources[source] = 0
        
        # Apply bonus
        adjusted_amount = int(amount * self.bonus_experience)
        self.experience_sources[source] += adjusted_amount
        self.last_experience_gain = adjusted_amount
    
    def get_total_experience(self) -> int:
        """
        Get total experience from all sources.
        
        Returns:
            Total experience
        """
        return sum(self.experience_sources.values())


@dataclass
class SkillComponent(Component):
    """
    Component for character skills and abilities.
    """
    skills: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    active_skills: List[str] = field(default_factory=list)
    skill_cooldowns: Dict[str, float] = field(default_factory=dict)
    
    def add_skill(self, skill_id: str, skill_data: Dict[str, Any]):
        """
        Add a skill to the character.
        
        Args:
            skill_id: Unique skill identifier
            skill_data: Skill properties
        """
        self.skills[skill_id] = skill_data
    
    def remove_skill(self, skill_id: str):
        """
        Remove a skill from the character.
        
        Args:
            skill_id: Skill identifier to remove
        """
        if skill_id in self.skills:
            del self.skills[skill_id]
        
        if skill_id in self.active_skills:
            self.active_skills.remove(skill_id)
        
        if skill_id in self.skill_cooldowns:
            del self.skill_cooldowns[skill_id]
    
    def activate_skill(self, skill_id: str) -> bool:
        """
        Activate a skill.
        
        Args:
            skill_id: Skill identifier to activate
            
        Returns:
            True if skill was activated
        """
        if skill_id not in self.skills:
            return False
        
        # Check cooldown
        current_time = time.time()
        if skill_id in self.skill_cooldowns:
            cooldown_end = self.skill_cooldowns[skill_id]
            if current_time < cooldown_end:
                return False
        
        # Add to active skills
        if skill_id not in self.active_skills:
            self.active_skills.append(skill_id)
        
        # Set cooldown if skill has one
        skill_data = self.skills[skill_id]
        cooldown = skill_data.get('cooldown', 0)
        if cooldown > 0:
            self.skill_cooldowns[skill_id] = current_time + cooldown
        
        return True
    
    def deactivate_skill(self, skill_id: str):
        """
        Deactivate a skill.
        
        Args:
            skill_id: Skill identifier to deactivate
        """
        if skill_id in self.active_skills:
            self.active_skills.remove(skill_id)
    
    def update_cooldowns(self, current_time: float):
        """
        Update skill cooldowns.
        
        Args:
            current_time: Current game time
        """
        # Remove expired cooldowns
        expired = [skill_id for skill_id, cooldown_end in self.skill_cooldowns.items()
                  if current_time >= cooldown_end]
        
        for skill_id in expired:
            del self.skill_cooldowns[skill_id]
    
    def get_skill_level(self, skill_id: str) -> int:
        """
        Get level of a skill.
        
        Args:
            skill_id: Skill identifier
            
        Returns:
            Skill level, or 0 if skill not found
        """
        if skill_id in self.skills:
            return self.skills[skill_id].get('level', 0)
        return 0
    
    def increase_skill_level(self, skill_id: str, amount: int = 1):
        """
        Increase skill level.
        
        Args:
            skill_id: Skill identifier
            amount: Amount to increase level by
        """
        if skill_id in self.skills:
            current_level = self.skills[skill_id].get('level', 0)
            self.skills[skill_id]['level'] = current_level + amount


# Import time for cooldowns
import time