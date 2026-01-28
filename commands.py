"""
Commands module for Soul Meter bot
Contains /char, /skill commands and character management
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, InputMediaPhoto
from aiogram.enums import ContentType

from storage import (
    get_user, save_user, get_user_characters, get_user_character,
    update_user_character, get_user_skill_slots, set_user_skill_slot
)
from char import (
    CHARACTERS, get_character, calculate_stats_for_level,
    get_upgrade_requirements, RARITY_EMOJI, RARITY_NAME, RARITY_MAX_LEVEL,
    MAX_ABILITY_WEIGHT, MAX_ABILITY_SLOTS
)

router = Router()

CHARS_PER_PAGE = 6


def make_callback(action: str, user_id: int, data: str = "") -> str:
    return f"{action}:{user_id}:{data}"


def parse_callback(callback_data: str) -> tuple:
    parts = callback_data.split(":", 2)
    if len(parts) >= 2:
        return parts[0], int(parts[1]), parts[2] if len(parts) > 2 else ""
    return "", 0, ""


async def check_user_callback(callback: CallbackQuery) -> bool:
    _, user_id, _ = parse_callback(callback.data)
    if callback.from_user.id != user_id:
        await callback.answer("🔴 Эта кнопка не для вас", show_alert=True)
        return False
    return True


# ==================== /char ====================
@router.message(Command("char"))
async def cmd_char(message: Message):
    await show_char_list(message, message.from_user.id, 0)


async def show_char_list(message: Message, user_id: int, page: int, edit: bool = False):
    chars = get_user_characters(user_id)
    
    if not chars:
        text = "🎭 <i>У вас пока нет персонажей</i>\n\nИспользуйте /up для получения сундуков с персонажами"
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return
    
    start = page * CHARS_PER_PAGE
    end = start + CHARS_PER_PAGE
    page_chars = chars[start:end]
    
    lines = ["🎭 <i>Выберете персонажа из следующих</i>\n"]
    
    for i, char_data in enumerate(page_chars, start=1):
        char = get_character(char_data['char_id'])
        if char:
            rarity = RARITY_EMOJI[char['rarity']]
            lines.append(f"{start + i}. <b>{char['name_ru']}</b> <i>{rarity} {char['anime']}</i>")
    
    text = "\n".join(lines)
    
    # Build keyboard
    buttons = []
    row = []
    for i in range(len(page_chars)):
        row.append(InlineKeyboardButton(
            text=str(i + 1),
            callback_data=make_callback("charsel", user_id, f"{page}_{i}")
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    # Navigation
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️Назад", callback_data=make_callback("charpage", user_id, str(page - 1))))
    if end < len(chars):
        nav_row.append(InlineKeyboardButton(text="➡️Далее", callback_data=make_callback("charpage", user_id, str(page + 1))))
    if nav_row:
        buttons.append(nav_row)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if edit:
        if message.content_type == ContentType.TEXT:
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.delete()
            await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("charpage:"))
async def callback_char_page(callback: CallbackQuery):
    if not await check_user_callback(callback):
        return
    _, user_id, page_str = parse_callback(callback.data)
    
    chars = get_user_characters(user_id)
    page = int(page_str)
    max_page = (len(chars) - 1) // CHARS_PER_PAGE
    
    if page > max_page:
        await callback.answer("🔴 Последняя страница", show_alert=True)
        return
    
    await show_char_list(callback.message, user_id, page, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("charsel:"))
async def callback_char_select(callback: CallbackQuery):
    if not await check_user_callback(callback):
        return
    _, user_id, data = parse_callback(callback.data)
    page, idx = map(int, data.split("_"))
    
    chars = get_user_characters(user_id)
    char_idx = page * CHARS_PER_PAGE + idx
    
    if char_idx >= len(chars):
        await callback.answer("🔴 Персонаж не найден", show_alert=True)
        return
    
    char_data = chars[char_idx]
    await show_char_info(callback.message, user_id, char_data['char_id'], page, idx)
    await callback.answer()


async def show_char_info(message: Message, user_id: int, char_id: str, page: int = 0, idx: int = 0):
    char = get_character(char_id)
    user_char = get_user_character(user_id, char_id)
    
    if not char or not user_char:
        await message.edit_text("🔴 Персонаж не найден")
        return
    
    level = user_char.get('level', 1)
    stats = calculate_stats_for_level(char_id, level)
    rarity = RARITY_EMOJI[char['rarity']] + " " + RARITY_NAME[char['rarity']]
    
    text = f"""<b>❕Информация о персонаже {char['name_ru']}</b>

📊 <i>Характеристики:</i>

<blockquote>❤️ <i>Здоровье ›› {stats['hp']}</i>
🗡 <i>Урон ›› {stats['damage'][0]}-{stats['damage'][1]}</i>
🛡 <i>Защита ›› {stats['defense']}</i>
⚔ Крит шанс ›› {stats['crit']}%
🧩 Уровень ›› {level}
🍀 Редкость ›› {rarity}</blockquote>

🏵 <b>Способности:</b>
<blockquote>"""
    
    for i, ability in enumerate(char['abilities'], 1):
        text += f"{i}. {ability['name']} - ⚖{ability['weight']}\n"
    
    text += "</blockquote>"
    
    # Ability buttons
    buttons = []
    abilities = char['abilities']
    row = []
    for i in range(min(4, len(abilities))):
        row.append(InlineKeyboardButton(text=str(i+1), callback_data=make_callback("abilinfo", user_id, f"{char_id}_{i}")))
    if row:
        buttons.append(row)
    
    row = []
    for i in range(4, min(8, len(abilities))):
        row.append(InlineKeyboardButton(text=str(i+1), callback_data=make_callback("abilinfo", user_id, f"{char_id}_{i}")))
    if row:
        buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton(text="📊 Уровень", callback_data=make_callback("charlvl", user_id, f"{char_id}_{page}_{idx}")),
        InlineKeyboardButton(text="🟢 Выбрать", callback_data=make_callback("charuse", user_id, char_id))
    ])
    buttons.append([
        InlineKeyboardButton(text="Выбрать способности", callback_data=make_callback("charskill", user_id, f"{char_id}_{page}_{idx}")),
        InlineKeyboardButton(text="🔙 Назад", callback_data=make_callback("charpage", user_id, str(page)))
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Check for character specific image (Saber)
    if char_id == "Saber":
        photo = FSInputFile("media/saber/saber.jpg")
        if message.content_type == ContentType.PHOTO:
             await message.edit_media(media=InputMediaPhoto(media=photo, caption=text), reply_markup=keyboard)
        else:
             await message.delete()
             await message.answer_photo(photo, caption=text, reply_markup=keyboard)
    else:
        # Standard text display
        if message.content_type == ContentType.TEXT:
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.delete()
            await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("abilinfo:"))
async def callback_ability_info(callback: CallbackQuery):
    if not await check_user_callback(callback):
        return
    _, user_id, data = parse_callback(callback.data)
    char_id, abil_idx = data.rsplit("_", 1)
    abil_idx = int(abil_idx)
    
    char = get_character(char_id)
    if not char or abil_idx >= len(char['abilities']):
        await callback.answer("🔴 Способность не найдена", show_alert=True)
        return
    
    ability = char['abilities'][abil_idx]
    
    text = f"""🏵 {ability['name']}

{ability['description']}

⚖ Вес: {ability['weight']}
⚡ Энергия: -{ability['energy_cost']}"""
    
    if ability.get('energy_restore', 0) > 0:
        text += f" / +{ability['energy_restore']}"
    
    await callback.answer(text[:200], show_alert=True)


@router.callback_query(F.data.startswith("charuse:"))
async def callback_char_use(callback: CallbackQuery):
    if not await check_user_callback(callback):
        return
    _, user_id, char_id = parse_callback(callback.data)
    
    user = get_user(user_id)
    user['active_char'] = char_id
    save_user(user)
    
    char = get_character(char_id)
    await callback.answer(f"🟢 Персонаж {char['name_ru']} выбран!", show_alert=True)


@router.callback_query(F.data.startswith("charlvl:"))
async def callback_char_level(callback: CallbackQuery):
    if not await check_user_callback(callback):
        return
    _, user_id, data = parse_callback(callback.data)
    # data format: char_id_page_idx
    parts = data.split("_")
    char_id = parts[0]
    page = int(parts[1]) if len(parts) > 1 else 0
    idx = int(parts[2]) if len(parts) > 2 else 0
    
    await show_char_level(callback.message, user_id, char_id, page, idx)
    await callback.answer()


async def show_char_level(message: Message, user_id: int, char_id: str, page: int = 0, idx: int = 0):
    char = get_character(char_id)
    user_char = get_user_character(user_id, char_id)
    
    if not char or not user_char:
        return
    
    level = user_char.get('level', 1)
    max_level = RARITY_MAX_LEVEL[char['rarity']]
    next_level = level + 1
    
    if next_level > max_level:
        text = f"""<b>📊 Уровень персонажа</b>

📊 Нынешний уровень ›› {level}

<i>🟢 Максимальный уровень достигнут!</i>"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=make_callback("charsel", user_id, f"{page}_{idx}"))]
        ])
    else:
        souls_req, trophy_souls_req, trophies_req = get_upgrade_requirements(next_level)
        
        text = f"""<b>📊 Уровень персонажа</b>

📊 Нынешний уровень ›› {level}

🆙 Для прокачки:
<blockquote>🧿 Души ›› {souls_req}
🧧 Трофейные души ›› {trophy_souls_req}
🏆 Трофеи ›› {trophies_req}</blockquote>"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🆙 Улучшить", callback_data=make_callback("charupg", user_id, f"{char_id}_{page}_{idx}")),
                InlineKeyboardButton(text="🔙 Назад", callback_data=make_callback("charsel", user_id, f"{page}_{idx}"))
            ]
        ])
    
    if message.content_type == ContentType.TEXT:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.delete()
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("charupg:"))
async def callback_char_upgrade(callback: CallbackQuery):
    if not await check_user_callback(callback):
        return
    _, user_id, data = parse_callback(callback.data)
    parts = data.split("_")
    char_id = parts[0]
    page = int(parts[1]) if len(parts) > 1 else 0
    idx = int(parts[2]) if len(parts) > 2 else 0
    
    user = get_user(user_id)
    user_char = get_user_character(user_id, char_id)
    char = get_character(char_id)
    
    if not char or not user_char:
        return
    
    level = user_char.get('level', 1)
    max_level = RARITY_MAX_LEVEL[char['rarity']]
    next_level = level + 1
    
    if next_level > max_level:
        await callback.answer("🔴 Максимальный уровень!", show_alert=True)
        return
    
    souls_req, trophy_souls_req, trophies_req = get_upgrade_requirements(next_level)
    
    # Check requirements
    if user['souls'] < souls_req or user['trophy_souls'] < trophy_souls_req or user['trophies'] < trophies_req:
        text = "🔴 <i>Вам не хватает материалов для улучшения</i>"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=make_callback("charlvl", user_id, f"{char_id}_{page}_{idx}"))]
        ])
        if callback.message.content_type == ContentType.TEXT:
            await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        return
    
    # Show confirmation
    text = "<i>‼️ Вы действительно хотите улучшить персонажа? Все его характеристики увеличатся и у вас снимут души</i>"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Продолжить", callback_data=make_callback("charupgok", user_id, f"{char_id}_{page}_{idx}")),
            InlineKeyboardButton(text="🔴 Отменить", callback_data=make_callback("charlvl", user_id, f"{char_id}_{page}_{idx}"))
        ]
    ])
    if callback.message.content_type == ContentType.TEXT:
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("charupgok:"))
async def callback_char_upgrade_confirm(callback: CallbackQuery):
    if not await check_user_callback(callback):
        return
    _, user_id, data = parse_callback(callback.data)
    parts = data.split("_")
    char_id = parts[0]
    page = int(parts[1]) if len(parts) > 1 else 0
    idx = int(parts[2]) if len(parts) > 2 else 0
    
    user = get_user(user_id)
    user_char = get_user_character(user_id, char_id)
    char = get_character(char_id)
    
    level = user_char.get('level', 1)
    next_level = level + 1
    souls_req, trophy_souls_req, trophies_req = get_upgrade_requirements(next_level)
    
    # Final check
    if user['souls'] < souls_req or user['trophy_souls'] < trophy_souls_req or user['trophies'] < trophies_req:
        await callback.answer("🔴 Недостаточно ресурсов!", show_alert=True)
        return
    
    # Upgrade
    user['souls'] -= souls_req
    save_user(user)
    update_user_character(user_id, char_id, {'level': next_level})
    
    await callback.answer(f"🟢 Персонаж улучшен до уровня {next_level}!", show_alert=True)
    await callback.answer(f"🟢 Персонаж улучшен до уровня {next_level}!", show_alert=True)
    await show_char_level(callback.message, user_id, char_id, page, idx)


@router.callback_query(F.data.startswith("charskill:"))
async def callback_char_skills(callback: CallbackQuery):
    if not await check_user_callback(callback):
        return
    _, user_id, data = parse_callback(callback.data)
    parts = data.split("_")
    char_id = parts[0]
    page = int(parts[1]) if len(parts) > 1 else 0
    idx = int(parts[2]) if len(parts) > 2 else 0
    
    await show_skill_selection(callback.message, user_id, char_id, page, idx)
    await callback.answer()


async def show_skill_selection(message: Message, user_id: int, char_id: str, page: int = 0, idx: int = 0):
    char = get_character(char_id)
    if not char:
        return
    
    text = f"""<b>Выбор способностей персонажа</b>
Способности:
<i>"""
    
    for i, ability in enumerate(char['abilities'], 1):
        text += f"{i}. {ability['name']} - ⚖{ability['weight']} - ⚡{ability['energy_cost']}\n"
    
    text += f"""</i>
для того чтобы выбрать способность напишите команду <code>/skill {char_id} (номер слота) (номер способности)</code>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=make_callback("charsel", user_id, f"{page}_{idx}"))]
    ])
    
    if message.content_type == ContentType.TEXT:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.delete()
        await message.answer(text, reply_markup=keyboard)


# ==================== /skill ====================
@router.message(Command("skill"))
async def cmd_skill(message: Message):
    args = message.text.split()[1:]
    
    if len(args) < 3:
        await message.answer("Использование: /skill Имя_Персонажа номер_слота номер_способности")
        return
    
    char_id = args[0]
    try:
        slot = int(args[1])
        ability_idx = int(args[2]) - 1
    except ValueError:
        await message.answer("🔴 Неверный формат. Используйте числа для слота и способности")
        return
    
    if slot < 1 or slot > MAX_ABILITY_SLOTS:
        await message.answer(f"🔴 Номер слота должен быть от 1 до {MAX_ABILITY_SLOTS}")
        return
    
    char = get_character(char_id)
    if not char:
        await message.answer("🔴 Персонаж не найден")
        return
    
    user_char = get_user_character(message.from_user.id, char_id)
    if not user_char:
        await message.answer("🔴 У вас нет этого персонажа")
        return
    
    if ability_idx < 0 or ability_idx >= len(char['abilities']):
        await message.answer("🔴 Способность не найдена")
        return
    
    ability = char['abilities'][ability_idx]
    
    # Calculate current total weight
    current_slots = get_user_skill_slots(message.from_user.id, char_id)
    total_weight = 0
    for s, a_idx in current_slots.items():
        if int(s) != slot:  # Don't count the slot we're replacing
            total_weight += char['abilities'][a_idx]['weight']
    
    if total_weight + ability['weight'] > MAX_ABILITY_WEIGHT:
        await message.answer(f"🔴 Вам не хватает максимального веса для добавления этой способности\nТекущий вес: {total_weight}, максимальный: {MAX_ABILITY_WEIGHT}")
        return
    
    set_user_skill_slot(message.from_user.id, char_id, slot, ability_idx)
    
    # Check for 0-energy ability
    updated_slots = get_user_skill_slots(message.from_user.id, char_id)
    has_zero_energy = False
    for s_idx in updated_slots.values():
         if char['abilities'][s_idx]['energy_cost'] == 0:
             has_zero_energy = True
             break
    
    msg = f"🟢 Способность <b>{ability['name']}</b> установлена в слот {slot}"
    if not has_zero_energy:
        msg += "\n\n⚠️ <b>Внимание:</b> У вас не выбрано ни одной способности за 0 энергии! Вы можете не смочь сражаться."
        
    await message.answer(msg)
