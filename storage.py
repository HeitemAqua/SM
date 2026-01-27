"""
Storage module for Soul Meter bot
Handles all JSON file operations for user data, characters, etc.
"""
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime

STORAGE_DIR = os.path.join(os.path.dirname(__file__), 'storage')

# Ensure storage directory exists
os.makedirs(STORAGE_DIR, exist_ok=True)


def _load_json(filename: str) -> Dict:
    """Load JSON file from storage directory"""
    filepath = os.path.join(STORAGE_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def _save_json(filename: str, data: Dict) -> None:
    """Save data to JSON file in storage directory"""
    filepath = os.path.join(STORAGE_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(telegram_id: int) -> Dict[str, Any]:
    """Get user profile or create new one if doesn't exist"""
    data = _load_json('profile.json')
    
    if 'users' not in data:
        data['users'] = {}
    if 'next_sid' not in data:
        data['next_sid'] = 1
    
    str_id = str(telegram_id)
    
    if str_id not in data['users']:
        # Create new user
        new_user = {
            'telegram_id': telegram_id,
            'sid': data['next_sid'],
            'level': 1,
            'souls': 0,
            'exp': 0,
            'trophy_souls': 0,
            'trophies': 0,
            'chests': {
                'weak_soul': 0,
                'time': 0,
                'death': 0,
                'infinity': 0
            },
            'active_char': None,
            'last_up': None,
            'up_count': 0,  # Counter for first 5 guaranteed positive ups
            'skill_slots': {},  # {char_id: {slot_num: ability_index}}
            'avatar': None  # {type: 'photo'|'animation'|'video', file_id: str}
        }
        data['users'][str_id] = new_user
        data['next_sid'] += 1
        _save_json('profile.json', data)
    
    return data['users'][str_id]


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Find user by username (case-insensitive)"""
    data = _load_json('profile.json')
    if 'users' not in data:
        return None
        
    target_username = username.lstrip('@').lower()
    
    for user in data['users'].values():
        user_username = user.get('username', '').lower()
        if user_username == target_username:
            return user
            
    return None


def save_user(user_data: Dict[str, Any]) -> None:
    """Save user profile data"""
    data = _load_json('profile.json')
    
    if 'users' not in data:
        data['users'] = {}
    
    str_id = str(user_data['telegram_id'])
    data['users'][str_id] = user_data
    _save_json('profile.json', data)


def get_user_characters(telegram_id: int) -> list:
    """Get list of characters owned by user"""
    data = _load_json('userchar.json')
    
    if 'user_chars' not in data:
        data['user_chars'] = {}
    
    str_id = str(telegram_id)
    return data['user_chars'].get(str_id, [])


def add_character_to_user(telegram_id: int, char_id: str) -> None:
    """Add a character to user's collection"""
    data = _load_json('userchar.json')
    
    if 'user_chars' not in data:
        data['user_chars'] = {}
    
    str_id = str(telegram_id)
    
    if str_id not in data['user_chars']:
        data['user_chars'][str_id] = []
    
    # Add character with default level 1
    char_entry = {
        'char_id': char_id,
        'level': 1
    }
    data['user_chars'][str_id].append(char_entry)
    _save_json('userchar.json', data)


def get_user_character(telegram_id: int, char_id: str) -> Optional[Dict]:
    """Get specific character data for user"""
    chars = get_user_characters(telegram_id)
    for char in chars:
        if char['char_id'] == char_id:
            return char
    return None


def update_user_character(telegram_id: int, char_id: str, updates: Dict) -> None:
    """Update specific character for user"""
    data = _load_json('userchar.json')
    
    if 'user_chars' not in data:
        return
    
    str_id = str(telegram_id)
    
    if str_id not in data['user_chars']:
        return
    
    for char in data['user_chars'][str_id]:
        if char['char_id'] == char_id:
            char.update(updates)
            break
    
    _save_json('userchar.json', data)


def get_user_skill_slots(telegram_id: int, char_id: str) -> Dict[int, int]:
    """Get skill slot assignments for a character"""
    user = get_user(telegram_id)
    skill_slots = user.get('skill_slots', {})
    return skill_slots.get(char_id, {})


def set_user_skill_slot(telegram_id: int, char_id: str, slot: int, ability_index: int) -> None:
    """Set ability in skill slot"""
    user = get_user(telegram_id)
    
    if 'skill_slots' not in user:
        user['skill_slots'] = {}
    
    if char_id not in user['skill_slots']:
        user['skill_slots'][char_id] = {}
    
    user['skill_slots'][char_id][str(slot)] = ability_index
    save_user(user)


# Duel state storage (in-memory for active duels)
active_duels = {}  # {user_id: duel_data}
duel_queue = []  # List of user_ids waiting for match


def add_to_duel_queue(user_id: int) -> None:
    """Add user to duel matchmaking queue"""
    if user_id not in duel_queue:
        duel_queue.append(user_id)


def remove_from_duel_queue(user_id: int) -> None:
    """Remove user from duel queue"""
    if user_id in duel_queue:
        duel_queue.remove(user_id)


def get_queue_match(user_id: int) -> Optional[int]:
    """Try to find a match in queue, returns opponent_id or None"""
    for opponent_id in duel_queue:
        if opponent_id != user_id:
            return opponent_id
    return None


def create_duel(user1_id: int, user2_id: int, is_friendly: bool = False) -> Dict:
    """Create a new duel between two users"""
    duel_data = {
        'user1_id': user1_id,
        'user2_id': user2_id,
        'is_friendly': is_friendly,
        'current_turn': user1_id,
        'user1_hp': 0,  # Will be set when duel starts
        'user2_hp': 0,
        'user1_energy': 10,
        'user2_energy': 10,
        'user1_char': None,
        'user2_char': None,
        'status': 'pending',  # pending, accepted, active, finished
        'last_damage': {user1_id: 0, user2_id: 0},
        'last_energy_change': {user1_id: 0, user2_id: 0},
        'last_action_log': None
    }
    active_duels[user1_id] = duel_data
    active_duels[user2_id] = duel_data
    return duel_data


def get_active_duel(user_id: int) -> Optional[Dict]:
    """Get active duel for user"""
    return active_duels.get(user_id)


def end_duel(user_id: int) -> None:
    """End duel and clean up"""
    duel = active_duels.get(user_id)
    if duel:
        user1_id = duel['user1_id']
        user2_id = duel['user2_id']
        if user1_id in active_duels:
            del active_duels[user1_id]
        if user2_id in active_duels:
            del active_duels[user2_id]
