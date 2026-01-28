"""
Soul Meter - Telegram Bot Main File
Bot for anime character duels
"""
import asyncio
import os
import random
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, InputMediaPhoto, InputMediaVideo, InputMediaAnimation
from aiogram.enums import ParseMode, ContentType
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

import storage
from storage import (
    get_user, save_user, get_user_characters, add_character_to_user,
    get_user_character, update_user_character, get_user_skill_slots,
    set_user_skill_slot, add_to_duel_queue, remove_from_duel_queue,
    get_user_character, update_user_character, get_user_skill_slots,
    set_user_skill_slot, add_to_duel_queue, remove_from_duel_queue,
    get_queue_match, create_duel, get_active_duel, end_duel,
    get_user_by_username
)
from char import (
    CHARACTERS, get_character, get_all_characters, calculate_stats_for_level,
    get_upgrade_requirements, RARITY_EMOJI, RARITY_NAME, RARITY_MAX_LEVEL,
    MAX_ABILITY_WEIGHT, MAX_ABILITY_SLOTS, EFFECT_DAMAGE, EFFECT_HEAL,
    EFFECT_DEFENSE_BUFF, EFFECT_ATTACK_BUFF
)
from utils import (
    format_time_remaining, roll_chest_drop, roll_up_rewards,
    open_chest, calculate_damage, apply_defense
)

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()


class ProfileStates(StatesGroup):
    waiting_for_avatar = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def make_callback(action: str, user_id: int, data: str = "") -> str:
    return f"{action}:{user_id}:{data}"


def parse_callback(callback_data: str) -> tuple:
    parts = callback_data.split(":", 2)
    if len(parts) >= 2:
        return parts[0], int(parts[1]), parts[2] if len(parts) > 2 else ""
    return "", 0, ""


async def check_user_callback(callback: CallbackQuery) -> bool:
    """Check if callback is from the original command sender"""
    _, user_id, _ = parse_callback(callback.data)
    if callback.from_user.id != user_id:
        await callback.answer("🔴 Эта кнопка не для вас", show_alert=True)
        return False
    return True


# ==================== /start ====================
@router.message(CommandStart())
async def cmd_start(message: Message):
    user = get_user(message.from_user.id)
    
    # Update user info
    user['username'] = message.from_user.username
    user['first_name'] = message.from_user.first_name
    save_user(user)
    
    text = """👋 Здравствуй я Soul Meter

<blockquote>Бот в котором вы можете проводить дуэли различных аниме персонажей  
Бот еще в разработке так что функции не все</blockquote>

<i>🌐 Владелец бота @Ev4rnight</i>

🏠 Главное меню:"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data=make_callback("profile", message.from_user.id))],
        [
            InlineKeyboardButton(text="📣 Канал", url="https://t.me/SoulMeterNews"),
            InlineKeyboardButton(text="💬 Чат", url="https://t.me/Par4dis3")
        ],
        [InlineKeyboardButton(text="⁉️ Поддержка", url="https://t.me/Ev4rnight")]
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("profile:"))
async def callback_profile(callback: CallbackQuery):
    if not await check_user_callback(callback):
        return
    if not await check_user_callback(callback):
        return
    await show_profile(callback.message, callback.from_user.id, viewer_id=callback.from_user.id, message_to_edit=callback.message)
    await callback.answer()


@router.message(Command("my_soul", "My_Soul"))
async def cmd_my_soul(message: Message):
    # Update user info
    user = get_user(message.from_user.id)
    user['username'] = message.from_user.username
    user['first_name'] = message.from_user.first_name
    save_user(user)

    await show_profile(message, message.from_user.id, viewer_id=message.from_user.id)


# ==================== /soul ====================
@router.message(Command("soul"))
async def cmd_soul(message: Message):
    args = message.text.split()[1:]
    target_user_id = None
    
    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
    elif args:
        username = args[0].replace("@", "")
        if username.lower() == "me":
            target_user_id = message.from_user.id
        else:
            found_user = get_user_by_username(username)
            if found_user:
                target_user_id = found_user['telegram_id']
            else:
                await message.answer("🔴 Пользователь не найден в базе данных бота")
                return
    else:
        await message.answer("ℹ️ Использование: `/soul @username` или ответом на сообщение пользователя")
        return
        
    if target_user_id:
        await show_profile(message, target_user_id, viewer_id=message.from_user.id)


async def show_profile(message: Message, target_user_id: int, viewer_id: int, message_to_edit: Message = None):
    user_data = get_user(target_user_id)
    user_chars = get_user_characters(target_user_id)
    
    active_char_name = "Не выбран"
    if user_data.get('active_char'):
        char = get_character(user_data['active_char'])
        if char:
            active_char_name = char['name_ru']
    
    name = user_data.get('first_name', "Пользователь")
    
    text = f"""<b>👤 <a href="tg://user?id={target_user_id}">Душа</a></b>

<blockquote>🏷 <i>Ник</i> ›› {name}
  ⤷ <i>SID</i> ›› <code>{user_data['sid']}</code>
  ⤷ <i>Уровень</i> ›› <code>{user_data['level']}</code>

🧿 <i>Души</i> ›› <code>{user_data['souls']}</code>
🧧 <i>Трофейные души</i> ›› <code>{user_data['trophy_souls']}</code>
🏆 <i>Трофеи</i> ›› <code>{user_data['trophies']}</code>

🟢 <i>Активный персонаж</i> ›› <b>{active_char_name}</b></blockquote>"""

    # Settings button (only for own profile)
    keyboard = None
    if target_user_id == viewer_id:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data=make_callback("settings", target_user_id))]
        ])
    
    avatar = user_data.get('avatar')
    
    # Logic for sending/editing
    if message_to_edit:
        # We try to edit the existing message
        try:
            # Case 1: Target has avatar
            if avatar:
                # If message is already media, we can just edit caption/media
                if message_to_edit.content_type in [ContentType.PHOTO, ContentType.ANIMATION, ContentType.VIDEO]:
                    # To be safe and show correct media, we edit media
                    media = None
                    if avatar['type'] == 'photo':
                        media = InputMediaPhoto(media=avatar['file_id'], caption=text)
                    elif avatar['type'] == 'animation':
                        media = InputMediaAnimation(media=avatar['file_id'], caption=text)
                    elif avatar['type'] == 'video':
                        media = InputMediaVideo(media=avatar['file_id'], caption=text)
                    
                    if media:
                        await message_to_edit.edit_media(media=media, reply_markup=keyboard)
                    else:
                        await message_to_edit.edit_caption(caption=text, reply_markup=keyboard)
                else:
                    # Message is text, but we need to show media. Must delete and send new.
                    await message_to_edit.delete()
                    if avatar['type'] == 'photo':
                        await message.answer_photo(avatar['file_id'], caption=text, reply_markup=keyboard)
                    elif avatar['type'] == 'animation':
                        await message.answer_animation(avatar['file_id'], caption=text, reply_markup=keyboard)
                    elif avatar['type'] == 'video':
                        await message.answer_video(avatar['file_id'], caption=text, reply_markup=keyboard)
            
            # Case 2: Target has NO avatar
            else:
                if message_to_edit.content_type == ContentType.TEXT:
                    await message_to_edit.edit_text(text=text, reply_markup=keyboard)
                else:
                    # Message is media, but we need text. Must delete and send new.
                    await message_to_edit.delete()
                    await message.answer(text, reply_markup=keyboard)
                    
        except Exception:
            # Fallback on error (e.g. message too old, types mismatch weirdly)
            await message.answer(text, reply_markup=keyboard)
            
    else:
        # No message to edit, just send new
        if avatar:
            try:
                if avatar['type'] == 'photo':
                    await message.answer_photo(avatar['file_id'], caption=text, reply_markup=keyboard)
                elif avatar['type'] == 'animation':
                    await message.answer_animation(avatar['file_id'], caption=text, reply_markup=keyboard)
                elif avatar['type'] == 'video':
                    await message.answer_video(avatar['file_id'], caption=text, reply_markup=keyboard)
                else:
                    await message.answer(text, reply_markup=keyboard)
            except Exception:
                await message.answer(text, reply_markup=keyboard)
        else:
            await message.answer(text, reply_markup=keyboard)


# ==================== Settings & Avatar ====================
@router.callback_query(F.data.startswith("settings:"))
async def callback_settings(callback: CallbackQuery, state: FSMContext):
    if not await check_user_callback(callback):
        return
    
    # Reset state just in case
    await state.clear()
    
    
    text = "<b>⚙️ Настройка аккаунта</b>"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 Аватарка", callback_data=make_callback("avatar_menu", callback.from_user.id))],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=make_callback("profile", callback.from_user.id))]
    ])
    
    # We want to preserve media if it exists (i.e., we are coming from a profile with avatar)
    # The message is likely a photo/video/animation. We just change caption + Markup.
    
    if callback.message.content_type in [ContentType.PHOTO, ContentType.ANIMATION, ContentType.VIDEO]:
        await callback.message.edit_caption(caption=text, reply_markup=keyboard)
    else:
        # Text to text
        await callback.message.edit_text(text=text, reply_markup=keyboard)
    
    await callback.answer()


@router.callback_query(F.data.startswith("avatar_menu:"))
async def callback_avatar_menu(callback: CallbackQuery, state: FSMContext):
    if not await check_user_callback(callback):
        return
        
    if callback.message.chat.type != 'private':
        await callback.answer("🔴 Изменить аватар можно только в лс", show_alert=True)
        return
        
    text = "❕ Пожалуйста скиньте аватарку (.png, .gif, .mp4)"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Отменить", callback_data=make_callback("cancel_avatar", callback.from_user.id))]
    ])
    
    # Keep media if possible
    if callback.message.content_type in [ContentType.PHOTO, ContentType.ANIMATION, ContentType.VIDEO]:
        await callback.message.edit_caption(caption=text, reply_markup=keyboard)
    else:
        await callback.message.edit_text(text=text, reply_markup=keyboard)
        
    await state.set_state(ProfileStates.waiting_for_avatar)
    await state.update_data(message_id=callback.message.message_id)
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_avatar:"))
async def callback_cancel_avatar(callback: CallbackQuery, state: FSMContext):
    if not await check_user_callback(callback):
        return
    
    await state.clear()
    await callback_settings(callback, state)


@router.message(ProfileStates.waiting_for_avatar, F.content_type.in_([ContentType.PHOTO, ContentType.ANIMATION, ContentType.VIDEO]))
async def process_avatar_upload(message: Message, state: FSMContext):
    data = await state.get_data()
    prompt_msg_id = data.get('message_id')
    
    avatar_data = None
    if message.photo:
        avatar_data = {'type': 'photo', 'file_id': message.photo[-1].file_id}
    elif message.animation:
        avatar_data = {'type': 'animation', 'file_id': message.animation.file_id}
    elif message.video:
        avatar_data = {'type': 'video', 'file_id': message.video.file_id}
    
    if not avatar_data:
        await message.answer("🔴 Неподдерживаемый формат")
        return
        
    user = get_user(message.from_user.id)
    user['avatar'] = avatar_data
    save_user(user)
    
    # Try to delete the prompt message and send new one, or edit if possible.
    # Editing text-to-media is hard. Deleting and sending new is safer.
    if prompt_msg_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_msg_id)
        except Exception:
            pass
            
    success_text = "<i>🟢 Аватарка успешно установлена</i>"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=make_callback("profile", message.from_user.id))]
    ])
    
    if avatar_data['type'] == 'photo':
        await message.answer_photo(avatar_data['file_id'], caption=success_text, reply_markup=keyboard)
    elif avatar_data['type'] == 'animation':
        await message.answer_animation(avatar_data['file_id'], caption=success_text, reply_markup=keyboard)
    elif avatar_data['type'] == 'video':
        await message.answer_video(avatar_data['file_id'], caption=success_text, reply_markup=keyboard)
        
    await state.clear()


# ==================== /up ====================
@router.message(Command("up"))
async def cmd_up(message: Message):
    user = get_user(message.from_user.id)
    
    # Check cooldown
    if user.get('last_up'):
        last_up = datetime.fromisoformat(user['last_up'])
        cooldown_end = last_up + timedelta(minutes=15)
        now = datetime.now()
        
        if now < cooldown_end:
            remaining = int((cooldown_end - now).total_seconds())
            await message.answer(f"<i>💼 Вы ещё не отдохнули, подождите ещё {format_time_remaining(remaining)}</i>")
            return
    
    # Check if first 5 ups (guaranteed positive)
    is_guaranteed = user.get('up_count', 0) < 5
    
    # Roll rewards
    trophy_change, exp = roll_up_rewards(is_guaranteed)
    chest = roll_chest_drop()
    
    # Apply rewards
    user['trophy_souls'] = max(0, user['trophy_souls'] + trophy_change)
    user['exp'] += exp
    user['up_count'] = user.get('up_count', 0) + 1
    user['last_up'] = datetime.now().isoformat()
    
    if chest:
        user['chests'][chest] = user['chests'].get(chest, 0) + 1
    
    save_user(user)
    
    # Format message
    trophy_str = f"+{trophy_change}" if trophy_change >= 0 else str(trophy_change)
    
    text = f"""🏮 <b>Результаты охоты</b>

🧧 <i>Трофейные души</i> ›› <code>{trophy_str}</code>
🎐 <i>Опыт</i> ›› <code>+{exp}</code>

Перед новым использованием команды подождите 15 минут"""
    
    if chest == 'weak_soul':
        text += "\n\n💼 Во время охоты вы нашли <b>Сундук слабой души</b>, немного повезло..."
    elif chest == 'time':
        text += "\n\n🕦 Во время охоты вас благословил бог времени и вы нашли <b>Сундук времени</b>, довольно повезло..."
    elif chest == 'death':
        text += "\n\n☠ Во время охоты вас чуть не настигла смерть и за это сам бог смерти благословил вас и вы получили <b>Сундук смерти</b>, вам сильно повезло..."
    elif chest == 'infinity':
        text += "\n\n🌌 Во время охоты вы были благословлены всей галактикой и в конце нашли <b>Сундук бесконечности</b>, вам очень сильно повезло..."
    
    if user.get('avatar'):
        avatar = user['avatar']
        try:
            if avatar['type'] == 'photo':
                await message.answer_photo(avatar['file_id'], caption=text)
            elif avatar['type'] == 'animation':
                await message.answer_animation(avatar['file_id'], caption=text)
            elif avatar['type'] == 'video':
                await message.answer_video(avatar['file_id'], caption=text)
            else:
                await message.answer(text)
        except Exception:
            await message.answer(text)
    else:
        await message.answer(text)


# ==================== /so ====================
@router.message(Command("so"))
async def cmd_so(message: Message):
    user = get_user(message.from_user.id)
    
    text = f"""💳 <b>Ваш баланс</b>

<blockquote><i>🧿 Души ›› {user['souls']}
🎐 Опыт ›› {user['exp']}
🧧 Трофейные души ›› {user['trophy_souls']}
🏆 Трофеи ›› {user['trophies']}

Сундуки
  ⤷💼 Сундук слабой души ›› {user['chests'].get('weak_soul', 0)}
  ⤷🕦 Сундук времени ›› {user['chests'].get('time', 0)}
  ⤷☠ Сундук смерти ›› {user['chests'].get('death', 0)}
  ⤷🌌 Сундук бесконечности ›› {user['chests'].get('infinity', 0)}</i></blockquote>"""
    
    await message.answer(text)


# ==================== /chests ====================

def get_chests_keyboard(user_id: int, with_back: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="💼Слабой души", callback_data=make_callback("chest", user_id, "weak_soul")),
            InlineKeyboardButton(text="🕦Времени", callback_data=make_callback("chest", user_id, "time"))
        ],
        [
            InlineKeyboardButton(text="☠Смерти", callback_data=make_callback("chest", user_id, "death")),
            InlineKeyboardButton(text="🌌Бесконечности", callback_data=make_callback("chest", user_id, "infinity"))
        ]
    ]
    
    if with_back:
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=make_callback("chests_menu", user_id))])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("chests"))
async def cmd_chests(message: Message):
    user = get_user(message.from_user.id)
    
    text = f"""<blockquote><i>Сундуки
  ⤷💼 Сундук слабой души ›› {user['chests'].get('weak_soul', 0)}
  ⤷🕦 Сундук времени ›› {user['chests'].get('time', 0)}
  ⤷☠ Сундук смерти ›› {user['chests'].get('death', 0)}
  ⤷🌌 Сундук бесконечности ›› {user['chests'].get('infinity', 0)}</i></blockquote>
<i>Для быстрого открытия сундука используйте команды:</i>
<code>💼/open_s</code>, <code>🕦/open_t</code>, <code>☠/open_d</code>, <code>🌌/open_i</code>"""
    
    await message.answer(text, reply_markup=get_chests_keyboard(message.from_user.id))


@router.callback_query(F.data.startswith("chests_menu:"))
async def callback_chests_menu(callback: CallbackQuery):
    if not await check_user_callback(callback):
        return
        
    user = get_user(callback.from_user.id)
    
    text = f"""<blockquote><i>Сундуки
  ⤷💼 Сундук слабой души ›› {user['chests'].get('weak_soul', 0)}
  ⤷🕦 Сундук времени ›› {user['chests'].get('time', 0)}
  ⤷☠ Сундук смерти ›› {user['chests'].get('death', 0)}
  ⤷🌌 Сундук бесконечности ›› {user['chests'].get('infinity', 0)}</i></blockquote>
  Для быстрого открытия сундука используйте команды <code>💼/open_s</code>, <code>🕦/open_t</code>, <code>☠/open_d</code>, <code>🌌/open_i</code>"""
    
    # Check if message type is appropriate for edit_text
    if callback.message.content_type == ContentType.TEXT:
        await callback.message.edit_text(text, reply_markup=get_chests_keyboard(callback.from_user.id))
    else:
        # If for some reason it's not text (unlikely for chests, but safe to handle)
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=get_chests_keyboard(callback.from_user.id))
        
    await callback.answer()


@router.callback_query(F.data.startswith("chest:"))
async def callback_open_chest(callback: CallbackQuery):
    if not await check_user_callback(callback):
        return
    
    _, user_id, chest_type = parse_callback(callback.data)
    
    chest_names = {
        'weak_soul': 'слабой души',
        'time': 'времени', 
        'death': 'смерти',
        'infinity': 'бесконечности'
    }

    result_text = perform_chest_opening(user_id, chest_type)
    
    # If error (starts with red circle), show alert
    if result_text.startswith("🔴"):
        await callback.answer(result_text, show_alert=True)
    else:
        # Success: Show results + buttons + back button
        await callback.message.edit_text(result_text, reply_markup=get_chests_keyboard(user_id, with_back=True))
        await callback.answer()


def perform_chest_opening(user_id: int, chest_type: str) -> str:
    user = get_user(user_id)
    
    chest_names = {
        'weak_soul': 'слабой души',
        'time': 'времени', 
        'death': 'смерти',
        'infinity': 'бесконечности'
    }
    
    if user['chests'].get(chest_type, 0) <= 0:
        return "🔴 У вас нет такого сундука"
    
    # Open chest
    user['chests'][chest_type] -= 1
    
    # Get owned characters to exclude duplicates
    user_chars = get_user_characters(user_id)
    exclude_ids = [c['char_id'] for c in user_chars]
    
    rewards = open_chest(chest_type, exclude_ids)
    
    # Apply rewards
    user['souls'] += rewards['souls']
    user['trophy_souls'] += rewards['trophy_souls']
    user['exp'] += rewards['exp']
    
    if rewards['character']:
        add_character_to_user(user_id, rewards['character'])
    
    save_user(user)
    
    # Format rewards text
    reward_lines = []
    if rewards['souls'] > 0:
        reward_lines.append(f"🧿 Души: +{rewards['souls']}")
    if rewards['trophy_souls'] > 0:
        reward_lines.append(f"🧧 Трофейные души: +{rewards['trophy_souls']}")
    if rewards['exp'] > 0:
        reward_lines.append(f"🎐 Опыт: +{rewards['exp']}")
    if rewards['character']:
        char = get_character(rewards['character'])
        if char:
            reward_lines.append(f"🎭 Персонаж: {char['name_ru']} {RARITY_EMOJI[char['rarity']]}")
    
    if not reward_lines:
        reward_lines.append("Ничего...")
    
    text = f"""🟢 <i>Вы открыли</i> <b>Сундук {chest_names.get(chest_type, chest_type)}</b>

<blockquote>{chr(10).join(reward_lines)}</blockquote>"""
    return text


# ==================== /open_ commands ====================
@router.message(Command("open_s"))
async def cmd_open_weak_soul(message: Message):
    text = perform_chest_opening(message.from_user.id, "weak_soul")
    await message.answer(text)


@router.message(Command("open_t"))
async def cmd_open_time(message: Message):
    text = perform_chest_opening(message.from_user.id, "time")
    await message.answer(text)


@router.message(Command("open_d"))
async def cmd_open_death(message: Message):
    text = perform_chest_opening(message.from_user.id, "death")
    await message.answer(text)


@router.message(Command("open_i"))
async def cmd_open_infinity(message: Message):
    text = perform_chest_opening(message.from_user.id, "infinity")
    await message.answer(text)


# ==================== /chargive (admin) ====================
@router.message(Command("chargive"))
async def cmd_chargive(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("🔴 Команда доступна только администраторам")
        return
    
    args = message.text.split()[1:]
    if len(args) < 2:
        await message.answer("Использование: /chargive @username Имя_Персонажа")
        return
    
    username = args[0].replace("@", "")
    char_id = args[1]
    
    if char_id not in CHARACTERS:
        await message.answer(f"🔴 Персонаж {char_id} не найден")
        return
    
    # We need to find user by username - this requires additional logic
    # For now, we'll use reply or mention
    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                # Can't get user ID from username directly in aiogram
                pass
    
    if not target_user:
        await message.answer("🔴 Ответьте на сообщение пользователя или используйте /chargive в ответ на сообщение")
        return
    
    add_character_to_user(target_user.id, char_id)
    char = get_character(char_id)
    await message.answer(f"🟢 Персонаж <b>{char['name_ru']}</b> выдан пользователю {target_user.first_name}")


# Import additional routers
from commands import router as commands_router
from duel import router as duel_router

dp.include_router(router)
dp.include_router(commands_router)
dp.include_router(duel_router)


from aiogram.types import BotCommand

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="my_soul", description="Профиль"),
        BotCommand(command="up", description="Пойти на охоту"),
        BotCommand(command="so", description="Баланс"),
        BotCommand(command="chests", description="Сундуки"),
        BotCommand(command="char", description="Персонажи"),
        BotCommand(command="skill", description="Настройка способностей"),
        BotCommand(command="duels", description="Дуэли"),
        BotCommand(command="frienduel", description="Дружеская дуэль"),
        BotCommand(command="s", description="Чат в дуэли"),
    ]
    await bot.set_my_commands(commands)


async def main():
    print("Bot starting...")
    await setup_bot_commands(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
