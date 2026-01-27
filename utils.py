"""
Utility functions for Soul Meter bot
"""
import random
from typing import Tuple, Optional
from char import CHARACTERS, get_characters_by_rarity, RARITY_HUMAN, RARITY_PLANET, RARITY_UNIVERSE, RARITY_MULTIVERSE


def format_time_remaining(seconds: int) -> str:
    """Format remaining time as MM:SS or HH:MM:SS"""
    if seconds <= 0:
        return "0:00"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def roll_chest_drop() -> Optional[str]:
    """Roll for chest drop from /up command
    Returns chest type or None
    """
    roll = random.random() * 100
    
    if roll < 1:  # 1%
        return 'infinity'
    elif roll < 11:  # 10%
        return 'death'
    elif roll < 31:  # 20%
        return 'time'
    elif roll < 71:  # 40%
        return 'weak_soul'
    
    return None


def roll_up_rewards(is_guaranteed_positive: bool) -> Tuple[int, int]:
    """Roll rewards for /up command
    Returns (trophy_souls_change, exp_gain)
    """
    exp = random.randint(0, 100)
    
    if is_guaranteed_positive:
        trophy_souls = random.randint(1, 30)
    else:
        # 70% win, 30% lose
        if random.random() < 0.7:
            trophy_souls = random.randint(1, 30)
        else:
            trophy_souls = random.randint(-20, -1)
    
    return trophy_souls, exp


def open_chest(chest_type: str, exclude_char_ids: list[str] = None) -> dict:
    """Open a chest and return rewards
    Returns dict with: souls, trophy_souls, exp, character (optional)
    """
    if exclude_char_ids is None:
        exclude_char_ids = []
        
    rewards = {
        'souls': 0,
        'trophy_souls': 0,
        'exp': 0,
        'character': None
    }
    
    if chest_type == 'weak_soul':
        # Сундук слабой души
        if random.random() < 0.80:
            rewards['souls'] = random.randint(50, 200)
        if random.random() < 0.55:
            rewards['trophy_souls'] = random.randint(20, 50)
        if random.random() < 0.40:
            rewards['exp'] = random.randint(100, 200)
        
        # Character drops
        roll = random.random()
        rarity_to_check = None
        
        if roll < 0.0000001:  # 0.00001%
            rarity_to_check = RARITY_MULTIVERSE
        elif roll < 0.0001:  # 0.01%
            rarity_to_check = RARITY_UNIVERSE
        elif roll < 0.01:  # 1%
            rarity_to_check = RARITY_PLANET
        elif roll < 0.20:  # 20%
            rarity_to_check = RARITY_HUMAN
            
        if rarity_to_check:
            chars = get_characters_by_rarity(rarity_to_check)
            # Filter out owned characters
            available_chars = [c for c in chars if c not in exclude_char_ids]
            if available_chars:
                rewards['character'] = random.choice(available_chars)
    
    elif chest_type == 'time':
        # Сундук времени
        if random.random() < 0.90:
            rewards['souls'] = random.randint(200, 500)
        if random.random() < 0.80:
            rewards['trophy_souls'] = random.randint(50, 75)
        if random.random() < 0.70:
            rewards['exp'] = random.randint(200, 500)
        
        roll = random.random()
        rarity_to_check = None
        
        if roll < 0.0001:  # 0.01%
            rarity_to_check = RARITY_MULTIVERSE
        elif roll < 0.005:  # 0.5%
            rarity_to_check = RARITY_UNIVERSE
        elif roll < 0.20:  # 20%
            rarity_to_check = RARITY_PLANET
            
        if rarity_to_check:
            chars = get_characters_by_rarity(rarity_to_check)
            # Filter out owned characters
            available_chars = [c for c in chars if c not in exclude_char_ids]
            if available_chars:
                rewards['character'] = random.choice(available_chars)
    
    elif chest_type == 'death':
        # Сундук смерти
        if random.random() < 0.99:
            rewards['souls'] = random.randint(500, 1000)
        if random.random() < 0.89:
            rewards['trophy_souls'] = random.randint(100, 150)
        if random.random() < 0.79:
            rewards['exp'] = random.randint(500, 1000)
        
        roll = random.random()
        rarity_to_check = None
        
        if roll < 0.01:  # 1%
            rarity_to_check = RARITY_MULTIVERSE
        elif roll < 0.20:  # 20%
            rarity_to_check = RARITY_UNIVERSE
            
        if rarity_to_check:
            chars = get_characters_by_rarity(rarity_to_check)
            # Filter out owned characters
            available_chars = [c for c in chars if c not in exclude_char_ids]
            if available_chars:
                rewards['character'] = random.choice(available_chars)
    
    elif chest_type == 'infinity':
        # Сундук бесконечности
        rewards['souls'] = random.randint(1000, 10000)
        rewards['trophy_souls'] = random.randint(150, 200)
        rewards['exp'] = random.randint(1000, 10000)
        
        if random.random() < 0.20:  # 20%
            chars = get_characters_by_rarity(RARITY_MULTIVERSE)
            # Filter out owned characters
            available_chars = [c for c in chars if c not in exclude_char_ids]
            if available_chars:
                rewards['character'] = random.choice(available_chars)
    
    return rewards


def calculate_damage(base_damage: list, crit_chance: int, attacker_buff: int = 0) -> Tuple[int, bool]:
    """Calculate damage with crit chance
    Returns (damage, is_crit)
    """
    damage = random.randint(base_damage[0], base_damage[1])
    
    # Apply attack buff
    if attacker_buff > 0:
        damage = int(damage * (1 + attacker_buff / 100))
    
    is_crit = random.randint(1, 100) <= crit_chance
    if is_crit:
        damage *= 2
    
    return damage, is_crit


def apply_defense(damage: int, defense: int, defense_debuff: int = 0) -> int:
    """Apply defense reduction to damage"""
    effective_defense = defense
    if defense_debuff < 0:  # Negative means debuff
        effective_defense = int(defense * (1 + defense_debuff / 100))
    
    final_damage = max(1, damage - effective_defense)
    return final_damage
