from aiogram import Router, F, Bot
from aiogram.types import BotCommand, BotCommandScopeChat
from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter

from database import register_user_if_not_exists, log_query, find_cities_in_db
from user_commands import user_commands
from weather import get_weather_label, get_detailed_weather, check_city_exists, get_weather_label_parallel
from keyboards import main_menu, get_back_keyboard
from states import States

router = Router()

async def set_pagination_state(state: FSMContext, cities: list, page: int = 1):
    await state.update_data(cities=cities, current_page=page)

async def get_pagination_state(state: FSMContext):
    data = await state.get_data()
    return data.get("cities", []), data.get("current_page", 1)

PHOTO_URL = "https://cryptex.games/games_images/5eef5e38abdd2083210192.jpg"

async def show_welcome(update: Message | CallbackQuery, state: FSMContext, bot: Bot):
    """Общая функция для отображения приветственного сообщения."""
    await state.clear()
    
    # Определяем пользователя и тип апдейта
    user = update.from_user
    is_message = isinstance(update, Message)
    
    text = (
        f"<b>👋 Добро пожаловать, {user.first_name}!\n\n"
        "🌦️ В этом боте вы можете узнать погоду в любом городе мира\n\n"
        "👇 Выберите нужный пункт меню:</b>"
    )

    # Если это сообщение, устанавливаем команды и отправляем новое сообщение с фото
    if is_message:
        await bot.set_my_commands(user_commands, scope=BotCommandScopeChat(chat_id=user.id))
        await update.answer_photo(
            photo=PHOTO_URL,
            caption=text,
            reply_markup=main_menu,
            parse_mode="HTML"
        )
    # Если это callback, редактируем сообщение и добавляем фото
    else:
        await update.message.answer_photo(
            photo=PHOTO_URL,
            caption=text,
            reply_markup=main_menu,
            parse_mode="HTML"
        )

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    """Команда /start."""
    register_user_if_not_exists(message.from_user.id)
    await show_welcome(message, state, bot)

@router.callback_query(F.data == "back_to_menu")
async def callback_back(query: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработка возврата в меню."""
    await show_welcome(query, state, bot)



@router.message(F.text == "🌡 Посмотреть температуру городов")
async def handle_view_cities(message: Message, state: FSMContext):
    kb = get_back_keyboard()
    text = (
        "<b>✍️ Введите названия городов через запятую\n\n"
        "👉 Например:</b> <blockquote>Волгоград, Воронеж, Волжский, Пермь</blockquote>"
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(States.waiting_for_cities)




@router.message(F.text == "👤 Мой профиль")
async def handle_my_profile(message: Message, state: FSMContext):
    user = message.from_user
    back_kb = get_back_keyboard()

    username = user.username if user.username else "(нет)"
    language = user.language_code if user.language_code else "(неизвестно)"

    text = (
        "<b>👤 Мой профиль:\n\n"
        f"• Имя: {user.first_name}\n"
        f"• 🆔: <code>{user.id}</code>\n"
        f"• Ваш tg: @{username}\n"
        f"• Язык: {language}</b>"
    )
    await message.answer(text, reply_markup=back_kb)






@router.message(StateFilter(States.waiting_for_cities))
async def process_city_list(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_text = message.text.strip()
    log_query(user_id, user_text)

    if not user_text:
        kb = get_back_keyboard()
        await message.answer("❌ Вы не ввели никаких городов", reply_markup=kb)
        return

    raw_cities = [c.strip() for c in user_text.split(",") if c.strip()]
    cities = list(dict.fromkeys(raw_cities))
    if not cities:
        kb = get_back_keyboard()
        await message.answer("❌ Вы не ввели никаких городов", reply_markup=kb)
        return

    found, not_found = find_cities_in_db(cities)
    additional_found = []
    for city in not_found:
        exists, _lbl = await check_city_exists(city)
        if exists:
            additional_found.append((city, city))

    if additional_found:
        found.extend(additional_found)
        not_found = [c for c in not_found if not any(c == f[0] for f in additional_found)]

    if found:
        await set_pagination_state(state, found, page=1)
        await show_cities_page(message, state)
    else:
        not_found_list = ", ".join(not_found) if not_found else "указанные"
        kb = get_back_keyboard()
        await message.answer(f"❌ Таких городов, как {not_found_list}, нет", reply_markup=kb)


async def show_cities_page(message: Message | CallbackQuery, state: FSMContext):
    cities, current_page = await get_pagination_state(state)
    
    if not cities:
        kb = get_back_keyboard()
        text_out = "❌ Список городов пуст"
        if isinstance(message, Message):
            await message.answer(text_out, reply_markup=kb)
        else:
            await message.message.edit_text(text_out, reply_markup=kb)
        return

    ITEMS_PER_PAGE = 4
    total_pages = (len(cities) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    current_page = max(1, min(current_page, total_pages))

    start_idx = (current_page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_cities = cities[start_idx:end_idx]

    city_official_list = [official for (user_city, official) in page_cities]
    weather_labels = await get_weather_label_parallel(city_official_list)

    weather_buttons = []
    for (user_city, official_city), label in zip(page_cities, weather_labels):
        weather_buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"action=details&city={official_city}&page={current_page}"
            )
        ])

    # Формируем клавиатуру
    keyboard_rows = weather_buttons.copy()

    # Добавляем пагинацию только если больше одной страницы
    if total_pages > 1:
        prev_page = total_pages if current_page == 1 else current_page - 1
        next_page = 1 if current_page == total_pages else current_page + 1
        nav_buttons = [
            InlineKeyboardButton(text="⬅️", callback_data=f"action=page&page={prev_page}"),
            InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="action=none"),
            InlineKeyboardButton(text="➡️", callback_data=f"action=page&page={next_page}"),
        ]
        keyboard_rows.append(nav_buttons)

    # Кнопка "Вернуться" в меню
    keyboard_rows.append([InlineKeyboardButton(text="🔙 Вернуться", callback_data="back_to_menu")])

    weather_kb = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    text_out = "<b>🏙 Вот найденные города по вашему запросу\n\n👇🏻 Нажмите на город, чтобы узнать более подробную информацию</b>"

    if isinstance(message, Message):
        await message.answer(text_out, reply_markup=weather_kb, parse_mode="HTML")
    else:
        await message.message.edit_text(text_out, reply_markup=weather_kb, parse_mode="HTML")


@router.callback_query(StateFilter(States.waiting_for_cities), lambda c: c.data.startswith("action=page"))
async def handle_pagination(query: CallbackQuery, state: FSMContext):
    await query.answer()
    data = dict(param.split("=") for param in query.data.split("&"))
    page = int(data["page"])
    cities, _ = await get_pagination_state(state)
    await set_pagination_state(state, cities, page)
    await show_cities_page(query, state)


@router.callback_query(StateFilter(States.waiting_for_cities), lambda c: c.data.startswith("action=details"))
async def callback_details(query: CallbackQuery, state: FSMContext):
    await query.answer()
    
    data = dict(param.split("=") for param in query.data.split("&"))
    city_name = data["city"]
    return_page = int(data["page"])
    
    info = await get_detailed_weather(city_name)

    # Кнопка "Вернуться" возвращает на страницу пагинации
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔙 Вернуться",
                callback_data=f"action=page&page={return_page}"
            )]
        ]
    )
    await query.message.edit_text(info, reply_markup=kb)

    await query.answer()


@router.callback_query(StateFilter(States.waiting_for_cities), lambda c: c.data.startswith("action=none"))
async def callback_none(query: CallbackQuery):
    await query.answer()  # Просто заглушка для кнопки страницы




@router.message()
async def fallback_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_text = message.text.strip()
    log_query(user_id, user_text)

    await message.answer("Пожалуйста, используйте кнопки или введите /start, чтобы вернуться в меню.")
