"""
Character definitions for Soul Meter bot
Each character has Russian name (in bot), English name (in code)
"""
from typing import Dict, Any, List

# Rarity constants
RARITY_HUMAN = "human"           # ⚪️ Человеческая - max 3 levels
RARITY_PLANET = "planet"         # 🟣 Планетарная - max 5 levels
RARITY_UNIVERSE = "universe"     # 🟠 Вселенская - max 7 levels
RARITY_MULTIVERSE = "multiverse" # 🔴 Межвселенская - max 10 levels

RARITY_EMOJI = {
    RARITY_HUMAN: "⚪️",
    RARITY_PLANET: "🟣",
    RARITY_UNIVERSE: "🟠",
    RARITY_MULTIVERSE: "🔴"
}

RARITY_NAME = {
    RARITY_HUMAN: "Человеческая",
    RARITY_PLANET: "Планетарная",
    RARITY_UNIVERSE: "Вселенская",
    RARITY_MULTIVERSE: "Межвселенская"
}

RARITY_MAX_LEVEL = {
    RARITY_HUMAN: 3,
    RARITY_PLANET: 5,
    RARITY_UNIVERSE: 7,
    RARITY_MULTIVERSE: 10
}

# Upgrade requirements: level -> (souls_cost, trophy_souls_req, trophies_req)
# Only souls are spent, trophy_souls and trophies are requirements
UPGRADE_REQUIREMENTS = {
    2: (750, 100, 50),
    3: (1500, 250, 150),
    4: (3000, 750, 500),
    5: (5000, 1000, 750),
    6: (7500, 1250, 1000),
    7: (10000, 2000, 1500),
    8: (20000, 4000, 2000),
    9: (35000, 5000, 3500),
    10: (50000, 7500, 5000)
}

# Maximum weight for abilities (currently 10 for everyone)
MAX_ABILITY_WEIGHT = 10

# Maximum ability slots
MAX_ABILITY_SLOTS = 12

# Ability effect types
EFFECT_DAMAGE = "damage"           # Deal damage
EFFECT_HEAL = "heal"               # Restore HP
EFFECT_DEFENSE_BUFF = "def_buff"   # Increase defense
EFFECT_ATTACK_BUFF = "atk_buff"    # Increase attack
EFFECT_ENERGY_RESTORE = "energy"   # Restore energy (already in energy_restore field)


def create_ability(
    name: str,
    description: str,
    weight: int,
    energy_cost: int,
    energy_restore: int = 0,
    effect_type: str = EFFECT_DAMAGE,
    effect_value: int = 0,
    effect_percent: int = 0,  # For percentage-based effects
    gif: str = None  # Path to GIF file
) -> Dict[str, Any]:
    """Create an ability definition"""
    return {
        "name": name,
        "description": description,
        "weight": weight,
        "energy_cost": energy_cost,
        "energy_restore": energy_restore,
        "effect_type": effect_type,
        "effect_value": effect_value,
        "effect_percent": effect_percent,
        "gif": gif
    }


# Character definitions
CHARACTERS: Dict[str, Dict[str, Any]] = {
    "Yuichi_Katagiri": {
        "name_ru": "Юичи Катагири",
        "name_en": "Yuichi Katagiri",
        "anime": "Tomodachi Game",
        "rarity": RARITY_HUMAN,
        "base_hp": 750,
        "base_damage": [75, 125],  # Damage range
        "base_defense": 75,
        "base_crit": 10,  # Crit chance %
        "abilities": [
            create_ability(
                name="Психологический анализ",
                description="Юичи анализирует слабости противника и наносит точный удар. Урон: 120",
                weight=2,
                energy_cost=2,
                effect_type=EFFECT_DAMAGE,
                effect_value=120
            ),
            create_ability(
                name="Манипуляция",
                description="Юичи манипулирует противником, снижая его защиту. Снижает защиту на 15%",
                weight=3,
                energy_cost=3,
                effect_type=EFFECT_DEFENSE_BUFF,
                effect_percent=-15
            ),
            create_ability(
                name="Блеф",
                description="Юичи отвлекает противника блефом. Восстанавливает 3 энергии",
                weight=1,
                energy_cost=0,
                energy_restore=3
            ),
            create_ability(
                name="Предательство",
                description="Юичи использует доверие против врага. Критический урон: 200",
                weight=4,
                energy_cost=5,
                effect_type=EFFECT_DAMAGE,
                effect_value=200
            ),
            create_ability(
                name="Холодный расчёт",
                description="Юичи рассчитывает каждый шаг. Урон: 80, восстанавливает 1 энергию",
                weight=2,
                energy_cost=1,
                energy_restore=1,
                effect_type=EFFECT_DAMAGE,
                effect_value=80
            ),
            create_ability(
                name="Ложная дружба",
                description="Юичи притворяется другом и наносит удар исподтишка. Урон: 150",
                weight=3,
                energy_cost=4,
                effect_type=EFFECT_DAMAGE,
                effect_value=150
            ),
            create_ability(
                name="Быстрое мышление",
                description="Юичи быстро оценивает ситуацию. Восстанавливает 4 энергии",
                weight=2,
                energy_cost=0,
                energy_restore=4
            ),
            create_ability(
                name="Игра на доверии",
                description="Юичи использует доверие противника. Лечение: 100 HP",
                weight=2,
                energy_cost=3,
                effect_type=EFFECT_HEAL,
                effect_value=100
            )
        ]
    },
    
    "Ayanokoji_Kiyotaka": {
        "name_ru": "Аянокоджи Киётака",
        "name_en": "Ayanokoji Kiyotaka",
        "anime": "Classroom of the Elite",
        "rarity": RARITY_HUMAN,
        "base_hp": 1000,
        "base_damage": [120, 180],  # Damage range 
        "base_defense": 100,
        "base_crit": 7,  # Crit chance %
        "abilities": [
            create_ability(
                name="Белая комната",
                description="Навыки из Белой комнаты. Мощный удар: 180 урона",
                weight=4,
                energy_cost=5,
                effect_type=EFFECT_DAMAGE,
                effect_value=180
            ),
            create_ability(
                name="Манипуляция разумом",
                description="Аянокоджи манипулирует мыслями противника. Урон: 100",
                weight=2,
                energy_cost=2,
                effect_type=EFFECT_DAMAGE,
                effect_value=100
            ),
            create_ability(
                name="Скрытая сила",
                description="Аянокоджи раскрывает часть своей силы. Повышает атаку на 20%",
                weight=3,
                energy_cost=3,
                effect_type=EFFECT_ATTACK_BUFF,
                effect_percent=20
            ),
            create_ability(
                name="Идеальный расчёт",
                description="Расчёт каждого действия. Урон: 120, восстанавливает 2 энергии",
                weight=3,
                energy_cost=2,
                energy_restore=2,
                effect_type=EFFECT_DAMAGE,
                effect_value=120
            ),
            create_ability(
                name="Тень",
                description="Аянокоджи уклоняется и восстанавливает силы. Лечение: 150 HP",
                weight=3,
                energy_cost=4,
                effect_type=EFFECT_HEAL,
                effect_value=150
            ),
            create_ability(
                name="Анализ слабостей",
                description="Аянокоджи находит слабости противника. Снижает защиту на 20%",
                weight=3,
                energy_cost=3,
                effect_type=EFFECT_DEFENSE_BUFF,
                effect_percent=-20
            ),
            create_ability(
                name="Восстановление",
                description="Аянокоджи восстанавливает энергию. +5 энергии",
                weight=2,
                energy_cost=0,
                energy_restore=5
            ),
            create_ability(
                name="Точный удар",
                description="Рассчитанный точный удар. Урон: 90",
                weight=1,
                energy_cost=1,
                effect_type=EFFECT_DAMAGE,
                effect_value=90
            ),
            create_ability(
                name="Абсолютное превосходство",
                description="Аянокоджи показывает истинную силу. Урон: 250",
                weight=5,
                energy_cost=7,
                effect_type=EFFECT_DAMAGE,
                effect_value=250
            ),
            create_ability(
                name="Контратака",
                description="Аянокоджи контратакует после уклонения. Урон: 130",
                weight=2,
                energy_cost=2,
                effect_type=EFFECT_DAMAGE,
                effect_value=130
            )
        ]
    },
    
    "Saber": {
        "name_ru": "Сэйбер",
        "name_en": "Saber",
        "anime": "Fate/Stay Night",
        "rarity": RARITY_PLANET,
        "base_hp": 8500,
        "base_damage": [700, 1000],
        "base_defense": 500,
        "base_crit": 15,
        "abilities": [
            create_ability(
                name="Удар",
                description="Сэйбер наносит быстрый удар мечом. Урон: 700-1000",
                weight=1,
                energy_cost=0,
                energy_restore=3,
                effect_type=EFFECT_DAMAGE,
                effect_value=850,  # Average of 700-1000 for calculation base
                gif="gifs/saber/attack.gif"
            )
        ]
    }
}


def get_character(char_id: str) -> Dict[str, Any]:
    """Get character definition by ID"""
    return CHARACTERS.get(char_id)


def get_all_characters() -> Dict[str, Dict[str, Any]]:
    """Get all character definitions"""
    return CHARACTERS


def get_characters_by_rarity(rarity: str) -> List[str]:
    """Get list of character IDs by rarity"""
    return [char_id for char_id, char in CHARACTERS.items() if char['rarity'] == rarity]


def calculate_stats_for_level(char_id: str, level: int) -> Dict[str, Any]:
    """Calculate character stats for given level"""
    char = CHARACTERS.get(char_id)
    if not char:
        return None
    
    # Base stats at level 1
    hp = char['base_hp']
    damage_min = char['base_damage'][0]
    damage_max = char['base_damage'][1]
    defense = char['base_defense']
    crit = char['base_crit']
    
    # Apply level scaling: divide by 0.9 for each level above 1
    for _ in range(1, level):
        hp = int(hp / 0.9)
        damage_min = int(damage_min / 0.9)
        damage_max = int(damage_max / 0.9)
        defense = int(defense / 0.9)
        crit = int(crit / 0.9)
    
    return {
        'hp': hp,
        'damage': [damage_min, damage_max],
        'defense': defense,
        'crit': crit
    }


def get_upgrade_requirements(target_level: int) -> tuple:
    """Get upgrade requirements for target level"""
    return UPGRADE_REQUIREMENTS.get(target_level, (0, 0, 0))
