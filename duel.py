"""
Duel system for Soul Meter bot
Contains /duels, /frienduel, /s commands and battle logic
"""
import asyncio
import random
from typing import Dict, Optional
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, InputMediaAnimation
from aiogram.enums import ContentType

from storage import (
    get_user, save_user, get_user_characters, get_user_character,
    get_user_skill_slots, add_to_duel_queue, remove_from_duel_queue,
    get_queue_match, create_duel, get_active_duel, end_duel, active_duels
)
from char import (
    CHARACTERS, get_character, calculate_stats_for_level,
    EFFECT_DAMAGE, EFFECT_HEAL, EFFECT_DEFENSE_BUFF, EFFECT_ATTACK_BUFF
)
from utils import calculate_damage, apply_defense

router = Router()
    
def has_zero_energy_ability(user_id: int, char_id: str) -> bool:
    """Check if user has at least one 0-energy ability equipped"""
    slots = get_user_skill_slots(user_id, char_id)
    char = get_character(char_id)
    if not char or not slots:
        return False
        
    for s_idx in slots.values():
        # s_idx is int index in abilities list
        if 0 <= s_idx < len(char['abilities']):
            if char['abilities'][s_idx]['energy_cost'] == 0:
                return True
    return False

# Pending duels (for friendly duels)
pending_friendly_duels: Dict[int, dict] = {}


def make_callback(action: str, user_id: int, data: str = "") -> str:
    return f"{action}:{user_id}:{data}"


def parse_callback(callback_data: str) -> tuple:
    parts = callback_data.split(":", 2)
    if len(parts) >= 2:
        return parts[0], int(parts[1]), parts[2] if len(parts) > 2 else ""
    return "", 0, ""


async def check_duel_callback(callback: CallbackQuery, duel: dict) -> bool:
    """Check if user is participant of duel"""
    user_id = callback.from_user.id
    if user_id != duel['user1_id'] and user_id != duel['user2_id']:
        await callback.answer("🔴 Вы не участник этой дуэли", show_alert=True)
        return False
    return True


def get_duel_message(duel: dict, user_id: int = None, bot_instance: Bot = None) -> str:
    """Generate duel status message for a user"""
    is_friendly = duel.get('is_friendly', False)
    
    # For friendly duels, show both players' stats without "my/opponent" perspective
    if is_friendly:
        user1_hp = duel['user1_hp']
        user1_energy = duel['user1_energy']
        user1_char_id = duel['user1_char']
        user1_slots = duel['user1_slots']
        
        user2_hp = duel['user2_hp']
        user2_energy = duel['user2_energy']
        user2_char_id = duel['user2_char']
        user2_slots = duel['user2_slots']
        
        char1 = get_character(user1_char_id)
        char2 = get_character(user2_char_id)
        
        # Damage/energy change indicators
        user1_dmg = duel['last_damage'].get(duel['user1_id'], 0)
        user2_dmg = duel['last_damage'].get(duel['user2_id'], 0)
        user1_eng_change = duel['last_energy_change'].get(duel['user1_id'], 0)
        user2_eng_change = duel['last_energy_change'].get(duel['user2_id'], 0)
        
        user1_dmg_str = f" <code>{user1_dmg:+d}</code>" if user1_dmg != 0 else ""
        user2_dmg_str = f" <code>{user2_dmg:+d}</code>" if user2_dmg != 0 else ""
        user1_eng_str = f" <code>{user1_eng_change:+d}</code>" if user1_eng_change != 0 else ""
        user2_eng_str = f" <code>{user2_eng_change:+d}</code>" if user2_eng_change != 0 else ""
        
        # User1 abilities
        user1_abilities_text = ""
        if char1 and user1_slots:
            abilities = []
            for slot, abil_idx in sorted(user1_slots.items(), key=lambda x: int(x[0])):
                abil = char1['abilities'][abil_idx]
                abilities.append(f"{slot}. {abil['name']}")
            user1_abilities_text = " ".join(abilities)
        
        # User2 abilities
        user2_abilities_text = ""
        if char2 and user2_slots:
            abilities = []
            for slot, abil_idx in sorted(user2_slots.items(), key=lambda x: int(x[0])):
                abil = char2['abilities'][abil_idx]
                abilities.append(f"{slot}. {abil['name']}")
            user2_abilities_text = " ".join(abilities)
        
        is_user1_turn = duel['current_turn'] == duel['user1_id']
        turn_text = "<b><i>❗Ход игрока 1</i></b>" if is_user1_turn else "<b><i>❗Ход игрока 2</i></b>"
        
        log_text = f"{duel['last_action_log']}" if duel.get('last_action_log') else ""
        
        text = f"""<blockquote><b>|——————|
| ⚔Дуэль |
|——————|</b></blockquote>

<blockquote><b>Игрок 1
🟢 Активный персонаж ›› {char1['name_ru']}
❤️ Здоровье ›› {user1_hp}{user1_dmg_str}
⚡️ Энергия ›› {user1_energy}/10{user1_eng_str}

✨ Способности
{user1_abilities_text}</b></blockquote>

<blockquote><i>Игрок 2
🟢 Активный персонаж ›› {char2['name_ru']}
❤️ Здоровье ›› {user2_hp}{user2_dmg_str}
⚡️ Энергия ›› {user2_energy}/10{user2_eng_str}

✨ Способности
{user2_abilities_text}</i></blockquote>

{log_text}
{turn_text}"""
        
        return text
    
    # Regular duel - show from user's perspective
    is_user1 = user_id == duel['user1_id']
    
    my_hp = duel['user1_hp'] if is_user1 else duel['user2_hp']
    my_energy = duel['user1_energy'] if is_user1 else duel['user2_energy']
    my_char_id = duel['user1_char'] if is_user1 else duel['user2_char']
    my_slots = duel['user1_slots'] if is_user1 else duel['user2_slots']
    
    opp_hp = duel['user2_hp'] if is_user1 else duel['user1_hp']
    opp_energy = duel['user2_energy'] if is_user1 else duel['user1_energy']
    opp_char_id = duel['user2_char'] if is_user1 else duel['user1_char']
    opp_slots = duel['user2_slots'] if is_user1 else duel['user1_slots']
    
    my_char = get_character(my_char_id)
    opp_char = get_character(opp_char_id)
    
    # Damage/energy change indicators
    my_dmg = duel['last_damage'].get(user_id, 0)
    opp_id = duel['user2_id'] if is_user1 else duel['user1_id']
    opp_dmg = duel['last_damage'].get(opp_id, 0)
    my_eng_change = duel['last_energy_change'].get(user_id, 0)
    opp_eng_change = duel['last_energy_change'].get(opp_id, 0)
    
    my_dmg_str = f" <code>{my_dmg:+d}</code>" if my_dmg != 0 else ""
    opp_dmg_str = f" <code>{opp_dmg:+d}</code>" if opp_dmg != 0 else ""
    my_eng_str = f" <code>{my_eng_change:+d}</code>" if my_eng_change != 0 else ""
    opp_eng_str = f" <code>{opp_eng_change:+d}</code>" if opp_eng_change != 0 else ""
    
    # My abilities
    my_abilities_text = ""
    if my_char and my_slots:
        abilities = []
        for slot, abil_idx in sorted(my_slots.items(), key=lambda x: int(x[0])):
            abil = my_char['abilities'][abil_idx]
            abilities.append(f"{slot}. {abil['name']}")
        my_abilities_text = " ".join(abilities)
    
    # Opponent abilities
    opp_abilities_text = ""
    if opp_char and opp_slots:
        abilities = []
        for slot, abil_idx in sorted(opp_slots.items(), key=lambda x: int(x[0])):
            abil = opp_char['abilities'][abil_idx]
            abilities.append(f"{slot}. {abil['name']}")
        opp_abilities_text = " ".join(abilities)
    
    is_my_turn = duel['current_turn'] == user_id
    turn_text = "<b><i>❗Ваш ход</i></b>" if is_my_turn else "<b><i>❗Ход противника</i></b>"
    
    log_text = f"\n\n{duel['last_action_log']}" if duel.get('last_action_log') else ""
    
    text = f"""<blockquote><b>|——————|
| ⚔Дуэль |
|——————|</b></blockquote>

<blockquote><b>Вы
🟢 Активный персонаж ›› {my_char['name_ru']}
❤️ Здоровье ›› {my_hp}{my_dmg_str}
⚡️ Энергия ›› {my_energy}/10{my_eng_str}

✨ Способности
{my_abilities_text}</b></blockquote>

<blockquote><i>Ваш противник
🟢 Активный персонаж ›› {opp_char['name_ru']}
❤️ Здоровье ›› {opp_hp}{opp_dmg_str}
⚡️ Энергия ›› {opp_energy}/10{opp_eng_str}

✨ Способности
{opp_abilities_text}</i></blockquote>

{log_text}
{turn_text}"""
    
    return text


def get_duel_keyboard(duel: dict, user_id: int = None) -> InlineKeyboardMarkup:
    """Generate ability buttons for duel"""
    is_friendly = duel.get('is_friendly', False)
    
    if is_friendly:
        # For friendly duels, show buttons for current turn player
        # Use special callback format that allows any participant to click
        current_turn_id = duel['current_turn']
        is_user1_turn = current_turn_id == duel['user1_id']
        
        char_id = duel['user1_char'] if is_user1_turn else duel['user2_char']
        slots = duel['user1_slots'] if is_user1_turn else duel['user2_slots']
        
        char = get_character(char_id)
        if not char or not slots:
            return InlineKeyboardMarkup(inline_keyboard=[])
        
        buttons = []
        row = []
        
        sorted_slots = sorted(slots.items(), key=lambda x: int(x[0]))
        
        for i, (slot, abil_idx) in enumerate(sorted_slots):
            abil = char['abilities'][abil_idx]
            btn_text = f"{slot}⚡{abil['energy_cost']}"
            # Use "fduelact" callback for friendly duels - checks turn, not user_id
            row.append(InlineKeyboardButton(
                text=btn_text,
                callback_data=f"fduelact:{duel['user1_id']}:{slot}"
            ))
            if len(row) == 3:
                buttons.append(row)
                row = []
        
        if row:
            buttons.append(row)
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Regular duel
    is_user1 = user_id == duel['user1_id']
    my_char_id = duel['user1_char'] if is_user1 else duel['user2_char']
    my_slots = duel['user1_slots'] if is_user1 else duel['user2_slots']
    
    char = get_character(my_char_id)
    if not char or not my_slots:
        return InlineKeyboardMarkup(inline_keyboard=[])
    
    buttons = []
    row = []
    
    sorted_slots = sorted(my_slots.items(), key=lambda x: int(x[0]))
    
    for i, (slot, abil_idx) in enumerate(sorted_slots):
        abil = char['abilities'][abil_idx]
        btn_text = f"{slot}⚡{abil['energy_cost']}"
        row.append(InlineKeyboardButton(
            text=btn_text,
            callback_data=make_callback("duelact", user_id, f"{slot}")
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def update_duel_interface(callback: CallbackQuery, text: str, keyboard: InlineKeyboardMarkup, gif_path: str = None):
    """Helper to handle Text <-> Animation transitions in duel interface"""
    try:
        # Determine if we need to show animation or text
        if gif_path:
             # We want to show Animation
             media = InputMediaAnimation(media=FSInputFile(gif_path), caption=text)
             
             if callback.message.content_type == ContentType.ANIMATION:
                 # Animation -> Animation: Edit media
                 await callback.message.edit_media(media=media, reply_markup=keyboard)
             else:
                 # Text/Photo/Video -> Animation: Delete and Send
                 # (Photo/Video -> Animation *might* work with edit_media but Delete/Send is safer for aspect ratios etc)
                 # Actually edit_media works fine between visual types usually, but let's be safe if coming from Text
                 if callback.message.content_type in [ContentType.PHOTO, ContentType.VIDEO]:
                      await callback.message.edit_media(media=media, reply_markup=keyboard)
                 else:
                      await callback.message.delete()
                      await callback.message.answer_animation(animation=FSInputFile(gif_path), caption=text, reply_markup=keyboard)
        else:
             # We want to show Text
             if callback.message.content_type == ContentType.TEXT:
                 # Text -> Text: Edit text
                 await callback.message.edit_text(text, reply_markup=keyboard)
             else:
                 # Animation/Photo/Video -> Text: Delete and Send
                 await callback.message.delete()
                 await callback.message.answer(text, reply_markup=keyboard)
                 
    except Exception as e:
        print(f"Error updating duel interface: {e}")
        # Fallback to simple answer if something breaks
        try:
            await callback.message.answer(text, reply_markup=keyboard)
        except:
            pass


# ==================== /duels ====================
@router.message(Command("duels"))
async def cmd_duels(message: Message):
    text = """❗<b>Информация о дуэлях</b>

<blockquote><i>Дуэли это сражения 1 на 1 с игроками, победы в дуэлях дают кубки, души, и сундуки</i></blockquote>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Начать подбор", callback_data=make_callback("duelstart", message.from_user.id))]
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("duelstart:"))
async def callback_duel_start(callback: CallbackQuery):
    _, user_id, _ = parse_callback(callback.data)
    
    if callback.from_user.id != user_id:
        await callback.answer("🔴 Эта кнопка не для вас", show_alert=True)
        return
    
    # Check if in DM
    if callback.message.chat.type != "private":
        await callback.answer("🔴 Рейтинговые дуэли доступны только в личных сообщениях", show_alert=True)
        return
    
    # Check if user has active character
    user = get_user(user_id)
    if not user.get('active_char'):
        await callback.answer("🔴 Сначала выберите персонажа командой /char", show_alert=True)
        return
    
    # Check if user has skills equipped
    slots = get_user_skill_slots(user_id, user['active_char'])
    if not slots:
        await callback.answer("🔴 Сначала выберите способности командой /skill", show_alert=True)
        return
    
    if not has_zero_energy_ability(user_id, user['active_char']):
         await callback.answer("🔴 Выберите хотя бы одну способность за 0 энергии", show_alert=True)
         return
    
    # Check for existing duel
    if get_active_duel(user_id):
        await callback.answer("🔴 Вы уже в дуэли", show_alert=True)
        return
    
    # Try to find opponent
    opponent_id = get_queue_match(user_id)
    
    if opponent_id:
        # Match found
        remove_from_duel_queue(opponent_id)
        duel = create_duel(user_id, opponent_id)
        
        # Get opponent info
        opponent_user = get_user(opponent_id)
        
        text = f"<i>⚔️ Противник найден!</i>"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Принять", callback_data=make_callback("duelaccept", user_id)),
                InlineKeyboardButton(text="🔴 Отклонить", callback_data=make_callback("duelreject", user_id))
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
        # Notify opponent as well
        try:
            opponent_text = f"<i>⚔️ Противник найден!</i>"
            opponent_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🟢 Принять", callback_data=make_callback("duelaccept", opponent_id)),
                    InlineKeyboardButton(text="🔴 Отклонить", callback_data=make_callback("duelreject", opponent_id))
                ]
            ])
            await callback.bot.send_message(opponent_id, opponent_text, reply_markup=opponent_keyboard)
        except Exception:
            pass  # Opponent may have blocked the bot
    else:
        # Add to queue
        add_to_duel_queue(user_id)
        
        text = "🗡️ <i>Идёт подбор противника</i>"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=make_callback("duelcancel", user_id))]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    await callback.answer()


@router.callback_query(F.data.startswith("duelcancel:"))
async def callback_duel_cancel(callback: CallbackQuery):
    _, user_id, _ = parse_callback(callback.data)
    
    if callback.from_user.id != user_id:
        await callback.answer("🔴 Эта кнопка не для вас", show_alert=True)
        return
    
    remove_from_duel_queue(user_id)
    
    # Return to duels menu
    text = """❗<b>Информация о дуэлях</b>

<blockquote><i>Дуэли это сражения 1 на 1 с игроками, победы в дуэлях дают кубки, души, и сундуки</i></blockquote>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Начать подбор", callback_data=make_callback("duelstart", user_id))]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("duelaccept:"))
async def callback_duel_accept(callback: CallbackQuery):
    _, original_user_id, _ = parse_callback(callback.data)
    
    duel = get_active_duel(callback.from_user.id)
    if not duel:
        await callback.answer("🔴 Дуэль не найдена", show_alert=True)
        return
    
    if not await check_duel_callback(callback, duel):
        return
    
    # Initialize duel
    user1 = get_user(duel['user1_id'])
    user2 = get_user(duel['user2_id'])
    
    char1 = get_character(user1['active_char'])
    char2 = get_character(user2['active_char'])
    
    user1_char = get_user_character(duel['user1_id'], user1['active_char'])
    user2_char = get_user_character(duel['user2_id'], user2['active_char'])
    
    stats1 = calculate_stats_for_level(user1['active_char'], user1_char.get('level', 1))
    stats2 = calculate_stats_for_level(user2['active_char'], user2_char.get('level', 1))
    
    duel['user1_hp'] = stats1['hp']
    duel['user2_hp'] = stats2['hp']
    duel['user1_energy'] = 10
    duel['user2_energy'] = 10
    duel['user1_char'] = user1['active_char']
    duel['user2_char'] = user2['active_char']
    duel['user1_slots'] = get_user_skill_slots(duel['user1_id'], user1['active_char'])
    duel['user2_slots'] = get_user_skill_slots(duel['user2_id'], user2['active_char'])
    duel['user1_stats'] = stats1
    duel['user2_stats'] = stats2
    duel['user1_buffs'] = {'attack': 0, 'defense': 0}
    duel['user2_buffs'] = {'attack': 0, 'defense': 0}
    duel['status'] = 'active'
    duel['current_turn'] = duel['user1_id']  # User1 goes first
    duel['user1_level'] = user1_char.get('level', 1)
    duel['user2_level'] = user2_char.get('level', 1)
    
    # Show duel interface
    text = get_duel_message(duel, callback.from_user.id)
    keyboard = get_duel_keyboard(duel, callback.from_user.id)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer("⚔️ Дуэль началась!")


@router.callback_query(F.data.startswith("duelreject:"))
async def callback_duel_reject(callback: CallbackQuery):
    _, original_user_id, _ = parse_callback(callback.data)
    
    duel = get_active_duel(callback.from_user.id)
    if duel:
        end_duel(callback.from_user.id)
    
    # Return to duels menu
    text = """❗<b>Информация о дуэлях</b>

<blockquote><i>Дуэли это сражения 1 на 1 с игроками, победы в дуэлях дают кубки, души, и сундуки</i></blockquote>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Начать подбор", callback_data=make_callback("duelstart", callback.from_user.id))]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("duelact:"))
async def callback_duel_action(callback: CallbackQuery):
    _, user_id, slot_str = parse_callback(callback.data)
    
    if callback.from_user.id != user_id:
        await callback.answer("🔴 Эта кнопка не для вас", show_alert=True)
        return
    
    duel = get_active_duel(user_id)
    if not duel or duel['status'] != 'active':
        await callback.answer("🔴 Дуэль не активна", show_alert=True)
        return
    
    if duel['current_turn'] != user_id:
        await callback.answer("🔴 Сейчас не ваш ход", show_alert=True)
        return
    
    is_user1 = user_id == duel['user1_id']
    my_char_id = duel['user1_char'] if is_user1 else duel['user2_char']
    my_slots = duel['user1_slots'] if is_user1 else duel['user2_slots']
    my_energy_key = 'user1_energy' if is_user1 else 'user2_energy'
    opp_hp_key = 'user2_hp' if is_user1 else 'user1_hp'
    my_hp_key = 'user1_hp' if is_user1 else 'user2_hp'
    my_buffs_key = 'user1_buffs' if is_user1 else 'user2_buffs'
    opp_buffs_key = 'user2_buffs' if is_user1 else 'user1_buffs'
    my_stats_key = 'user1_stats' if is_user1 else 'user2_stats'
    opp_stats_key = 'user2_stats' if is_user1 else 'user1_stats'
    opp_id = duel['user2_id'] if is_user1 else duel['user1_id']
    
    char = get_character(my_char_id)
    if not char:
        return
    
    slot = slot_str
    if slot not in my_slots:
        await callback.answer("🔴 Способность не найдена", show_alert=True)
        return
    
    abil_idx = my_slots[slot]
    ability = char['abilities'][abil_idx]
    
    # Check energy
    if duel[my_energy_key] < ability['energy_cost']:
        await callback.answer("🔴 Недостаточно энергии", show_alert=True)
        return
    
    # Reset last changes
    duel['last_damage'] = {user_id: 0, opp_id: 0}
    duel['last_energy_change'] = {user_id: 0, opp_id: 0}
    
    # Apply ability
    duel[my_energy_key] -= ability['energy_cost']
    duel['last_energy_change'][user_id] = -ability['energy_cost']
    
    if ability.get('energy_restore', 0) > 0:
        restore = ability['energy_restore']
        duel[my_energy_key] = min(10, duel[my_energy_key] + restore)
        duel['last_energy_change'][user_id] += restore
    
    effect_type = ability.get('effect_type', '')
    
    action_log = ""
    
    if effect_type == EFFECT_DAMAGE:
        base_dmg = ability['effect_value']
        
        # Apply level scaling
        my_level_key = 'user1_level' if is_user1 else 'user2_level'
        level = duel.get(my_level_key, 1)
        for _ in range(1, level):
            base_dmg = int(base_dmg / 0.9)
            
        attack_buff = duel[my_buffs_key]['attack']
        defense_debuff = duel[opp_buffs_key]['defense']
        opp_defense = duel[opp_stats_key]['defense']
        
        # Apply buffs
        if attack_buff > 0:
            base_dmg = int(base_dmg * (1 + attack_buff / 100))
        
        final_dmg = apply_defense(base_dmg, opp_defense, defense_debuff)
        duel[opp_hp_key] -= final_dmg
        duel['last_damage'][opp_id] = -final_dmg
        
        action_log = f"<i>{callback.from_user.first_name} использовал {ability['name']} -{ability['energy_cost']}⚡ и нанес {final_dmg} урона</i>"
        
    elif effect_type == EFFECT_HEAL:
        heal = ability['effect_value']
        max_hp = duel[my_stats_key]['hp']
        old_hp = duel[my_hp_key]
        duel[my_hp_key] = min(max_hp, duel[my_hp_key] + heal)
        actual_heal = duel[my_hp_key] - old_hp
        duel['last_damage'][user_id] = actual_heal
        
        action_log = f"<i>{callback.from_user.first_name} использовал {ability['name']} -{ability['energy_cost']}⚡ и восстановил {actual_heal} здоровья</i>"
        
    elif effect_type == EFFECT_DEFENSE_BUFF:
        duel[opp_buffs_key]['defense'] += ability['effect_percent']
        action_log = f"<i>{callback.from_user.first_name} использовал {ability['name']} -{ability['energy_cost']}⚡</i>"
        
    elif effect_type == EFFECT_ATTACK_BUFF:
        duel[my_buffs_key]['attack'] += ability['effect_percent']
        action_log = f"<i>{callback.from_user.first_name} использовал {ability['name']} -{ability['energy_cost']}⚡</i>"
        
    duel['last_action_log'] = action_log
    
    # Check win condition
    if duel[opp_hp_key] <= 0:
        duel['status'] = 'finished'
        duel['winner'] = user_id
        
        # Award trophies
        if not duel.get('is_friendly', False):
            winner = get_user(user_id)
            loser = get_user(opp_id)
            
            trophy_gain = random.randint(10, 30)
            trophy_loss = random.randint(5, 15)
            soul_reward = random.randint(50, 150)
            
            winner['trophies'] += trophy_gain
            winner['souls'] += soul_reward
            loser['trophies'] = max(0, loser['trophies'] - trophy_loss)
            
            save_user(winner)
            save_user(loser)
        
        text = f"""🏆 <b>Дуэль окончена!</b>

<i>Победитель: {callback.from_user.first_name}</i>"""
        
        if not duel.get('is_friendly', False):
            text += f"\n\n🏆 +{trophy_gain} трофеев\n🧿 +{soul_reward} душ"
        
        end_duel(user_id)
        await callback.message.edit_text(text)
        await callback.answer("🏆 Победа!")
        return
    
    # Switch turn
    duel['current_turn'] = opp_id
    
    # Update message
    text = get_duel_message(duel, user_id)
    keyboard = get_duel_keyboard(duel, user_id)
    
    gif_path = ability.get('gif')
    await update_duel_interface(callback, text, keyboard, gif_path)
    
    await callback.answer(f"✨ {ability['name']}")


# ==================== /frienduel ====================
@router.message(Command("frienduel"))
async def cmd_frienduel(message: Message):
    if not message.reply_to_message:
        await message.answer("🔴 Ответьте на сообщение пользователя, которому хотите бросить вызов")
        return
    
    target = message.reply_to_message.from_user
    
    if target.id == message.from_user.id:
        await message.answer("🔴 Нельзя вызвать себя на дуэль")
        return
    
    if target.is_bot:
        await message.answer("🔴 Нельзя вызвать бота на дуэль")
        return
    
    # Check if challenger has character
    user = get_user(message.from_user.id)
    if not user.get('active_char'):
        await message.answer("🔴 Сначала выберите персонажа командой /char")
        return
    
    slots = get_user_skill_slots(message.from_user.id, user['active_char'])
    if not slots:
        await message.answer("🔴 Сначала выберите способности командой /skill")
        return
        
    if not has_zero_energy_ability(message.from_user.id, user['active_char']):
        await message.answer("🔴 Вы не можете начать дуэль, так как у вас нет способности с 0 энергии")
        return
    
    # Store pending duel
    pending_friendly_duels[target.id] = {
        'challenger_id': message.from_user.id,
        'challenger_name': message.from_user.first_name,
        'created_at': datetime.now()
    }
    
    target_link = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
    
    text = f"<b>⚔️ {target_link}, вам бросили вызов, хотите его принять?</b>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Принять", callback_data=make_callback("friendaccept", target.id)),
            InlineKeyboardButton(text="🔴 Отклонить", callback_data=make_callback("friendreject", target.id))
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("friendaccept:"))
async def callback_friend_accept(callback: CallbackQuery):
    _, target_id, _ = parse_callback(callback.data)
    
    if callback.from_user.id != target_id:
        await callback.answer("🔴 Этот вызов не для вас", show_alert=True)
        return
    
    if target_id not in pending_friendly_duels:
        await callback.answer("🔴 Вызов истёк", show_alert=True)
        return
    
    pending = pending_friendly_duels.pop(target_id)
    challenger_id = pending['challenger_id']
    
    # Check if target has character
    user = get_user(target_id)
    if not user.get('active_char'):
        await callback.answer("🔴 Сначала выберите персонажа командой /char", show_alert=True)
        return
    
    slots = get_user_skill_slots(target_id, user['active_char'])
    if not slots:
        await callback.answer("🔴 Сначала выберите способности командой /skill", show_alert=True)
        return

    if not has_zero_energy_ability(target_id, user['active_char']):
        await callback.answer("🔴 Вы не можете принять дуэль, так как у вас нет способности с 0 энергии", show_alert=True)
        return
    
    # Create friendly duel
    duel = create_duel(challenger_id, target_id, is_friendly=True)
    
    # Initialize duel
    user1 = get_user(challenger_id)
    user2 = get_user(target_id)
    
    user1_char = get_user_character(challenger_id, user1['active_char'])
    user2_char = get_user_character(target_id, user2['active_char'])
    
    stats1 = calculate_stats_for_level(user1['active_char'], user1_char.get('level', 1))
    stats2 = calculate_stats_for_level(user2['active_char'], user2_char.get('level', 1))
    
    duel['user1_hp'] = stats1['hp']
    duel['user2_hp'] = stats2['hp']
    duel['user1_energy'] = 10
    duel['user2_energy'] = 10
    duel['user1_char'] = user1['active_char']
    duel['user2_char'] = user2['active_char']
    duel['user1_slots'] = get_user_skill_slots(challenger_id, user1['active_char'])
    duel['user2_slots'] = get_user_skill_slots(target_id, user2['active_char'])
    duel['user1_stats'] = stats1
    duel['user2_stats'] = stats2
    duel['user1_buffs'] = {'attack': 0, 'defense': 0}
    duel['user2_buffs'] = {'attack': 0, 'defense': 0}
    duel['status'] = 'active'
    duel['current_turn'] = challenger_id
    duel['user1_level'] = user1_char.get('level', 1)
    duel['user2_level'] = user2_char.get('level', 1)
    duel['message'] = callback.message
    
    text = get_duel_message(duel, target_id)
    keyboard = get_duel_keyboard(duel, target_id)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer("⚔️ Дружеская дуэль началась!")


@router.callback_query(F.data.startswith("fduelact:"))
async def callback_friendly_duel_action(callback: CallbackQuery):
    """Handle friendly duel action - anyone can click, but only current turn player can act"""
    _, user1_id, slot_str = parse_callback(callback.data)
    
    # Get the duel - use user1_id from callback to find it
    duel = get_active_duel(user1_id)
    if not duel:
        # Try to find duel where callback user is a participant
        duel = get_active_duel(callback.from_user.id)
    
    if not duel or duel['status'] != 'active':
        await callback.answer("🔴 Дуэль не активна", show_alert=True)
        return
    
    # Check if it's actually a friendly duel
    if not duel.get('is_friendly', False):
        await callback.answer("🔴 Это не дружеская дуэль", show_alert=True)
        return
    
    # Check if user is a participant
    if callback.from_user.id != duel['user1_id'] and callback.from_user.id != duel['user2_id']:
        await callback.answer("🔴 Вы не участник этой дуэли", show_alert=True)
        return
    
    # Check if it's the current player's turn (not specific user)
    if duel['current_turn'] != callback.from_user.id:
        await callback.answer("🔴 Сейчас не ваш ход", show_alert=True)
        return
    
    user_id = callback.from_user.id
    is_user1 = user_id == duel['user1_id']
    my_char_id = duel['user1_char'] if is_user1 else duel['user2_char']
    my_slots = duel['user1_slots'] if is_user1 else duel['user2_slots']
    my_energy_key = 'user1_energy' if is_user1 else 'user2_energy'
    opp_hp_key = 'user2_hp' if is_user1 else 'user1_hp'
    my_hp_key = 'user1_hp' if is_user1 else 'user2_hp'
    my_buffs_key = 'user1_buffs' if is_user1 else 'user2_buffs'
    opp_buffs_key = 'user2_buffs' if is_user1 else 'user1_buffs'
    my_stats_key = 'user1_stats' if is_user1 else 'user2_stats'
    opp_stats_key = 'user2_stats' if is_user1 else 'user1_stats'
    opp_id = duel['user2_id'] if is_user1 else duel['user1_id']
    
    char = get_character(my_char_id)
    if not char:
        return
    
    slot = slot_str
    if slot not in my_slots:
        await callback.answer("🔴 Способность не найдена", show_alert=True)
        return
    
    abil_idx = my_slots[slot]
    ability = char['abilities'][abil_idx]
    
    # Check energy
    if duel[my_energy_key] < ability['energy_cost']:
        await callback.answer("🔴 Недостаточно энергии", show_alert=True)
        return
    
    # Reset last changes
    duel['last_damage'] = {duel['user1_id']: 0, duel['user2_id']: 0}
    duel['last_energy_change'] = {duel['user1_id']: 0, duel['user2_id']: 0}
    
    # Apply ability
    duel[my_energy_key] -= ability['energy_cost']
    duel['last_energy_change'][user_id] = -ability['energy_cost']
    
    if ability.get('energy_restore', 0) > 0:
        restore = ability['energy_restore']
        duel[my_energy_key] = min(10, duel[my_energy_key] + restore)
        duel['last_energy_change'][user_id] += restore
    
    effect_type = ability.get('effect_type', '')
    
    action_log = ""
    
    if effect_type == EFFECT_DAMAGE:
        base_dmg = ability['effect_value']
        attack_buff = duel[my_buffs_key]['attack']
        defense_debuff = duel[opp_buffs_key]['defense']
        opp_defense = duel[opp_stats_key]['defense']
        
        # Apply buffs
        if attack_buff > 0:
            base_dmg = int(base_dmg * (1 + attack_buff / 100))
        
        final_dmg = apply_defense(base_dmg, opp_defense, defense_debuff)
        duel[opp_hp_key] -= final_dmg
        duel['last_damage'][opp_id] = -final_dmg
        
        action_log = f"<i>{callback.from_user.first_name} использовал {ability['name']} -{ability['energy_cost']}⚡ и нанес {final_dmg} урона</i>"
        
    elif effect_type == EFFECT_HEAL:
        heal = ability['effect_value']
        max_hp = duel[my_stats_key]['hp']
        old_hp = duel[my_hp_key]
        duel[my_hp_key] = min(max_hp, duel[my_hp_key] + heal)
        actual_heal = duel[my_hp_key] - old_hp
        duel['last_damage'][user_id] = actual_heal
        
        action_log = f"<i>{callback.from_user.first_name} использовал {ability['name']} -{ability['energy_cost']}⚡ и восстановил {actual_heal} здоровья</i>"
        
    elif effect_type == EFFECT_DEFENSE_BUFF:
        duel[opp_buffs_key]['defense'] += ability['effect_percent']
        action_log = f"<i>{callback.from_user.first_name} использовал {ability['name']} -{ability['energy_cost']}⚡</i>"
        
    elif effect_type == EFFECT_ATTACK_BUFF:
        duel[my_buffs_key]['attack'] += ability['effect_percent']
        action_log = f"<i>{callback.from_user.first_name} использовал {ability['name']} -{ability['energy_cost']}⚡</i>"

    duel['last_action_log'] = action_log
    
    # Check win condition
    if duel[opp_hp_key] <= 0:
        duel['status'] = 'finished'
        duel['winner'] = user_id
        
        text = f"⚔️ <b>Дуэль закончилась, победил {callback.from_user.first_name}</b>"
        
        end_duel(user_id)
        await callback.message.edit_text(text)
        await callback.answer("🏆 Победа!")
        return
    
    # Switch turn
    duel['current_turn'] = opp_id
    
    # Update message for both players (since it's the same message in group chat)
    text = get_duel_message(duel, None)  # Pass None for friendly duels
    keyboard = get_duel_keyboard(duel, None)
    
    gif_path = ability.get('gif')
    await update_duel_interface(callback, text, keyboard, gif_path)
    
    await callback.answer(f"✨ {ability['name']}")


@router.callback_query(F.data.startswith("friendreject:"))
async def callback_friend_reject(callback: CallbackQuery):
    _, target_id, _ = parse_callback(callback.data)
    
    if callback.from_user.id != target_id:
        await callback.answer("🔴 Этот вызов не для вас", show_alert=True)
        return
    
    if target_id in pending_friendly_duels:
        pending_friendly_duels.pop(target_id)
    
    await callback.message.edit_text("<i>🔴 Вызов отклонён</i>")
    await callback.answer()


# ==================== /s (duel chat) ====================
@router.message(Command("s"))
async def cmd_duel_chat(message: Message):
    duel = get_active_duel(message.from_user.id)
    
    if not duel or duel['status'] != 'active':
        await message.answer("<i>🔴 Сейчас не идёт дуэль</i>")
        return
    
    # Get message text after /s
    text = message.text[2:].strip() if len(message.text) > 2 else ""
    
    if not text:
        return
    
    # Find opponent
    is_user1 = message.from_user.id == duel['user1_id']
    opp_id = duel['user2_id'] if is_user1 else duel['user1_id']
    
    # Send message to opponent
    chat_text = f"<b>{message.from_user.first_name}:</b>\n<i>{text}</i>"
    
    try:
        await message.bot.send_message(opp_id, chat_text)
    except Exception:
        pass  # Opponent may have blocked the bot
