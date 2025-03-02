from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter

from database import register_user_if_not_exists, log_query, find_cities_in_db
from weather import get_weather_label, get_detailed_weather, check_city_exists, get_weather_label_parallel
from keyboards import main_menu, get_back_keyboard
from states import States

router = Router()

async def set_pagination_state(state: FSMContext, cities: list, page: int = 1):
    await state.update_data(cities=cities, current_page=page)

async def get_pagination_state(state: FSMContext):
    data = await state.get_data()
    return data.get("cities", []), data.get("current_page", 1)

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Команда /start."""
    await state.clear()
    register_user_if_not_exists(message.from_user.id)

    text = (
        f"Добро пожаловать в меню, {message.from_user.first_name}!\n\n"
        "Я бот, который покажет погоду.\n"
        "Выберите нужный пункт меню:"
    )
    await message.answer(text, reply_markup=main_menu)

@router.message(F.text == "🌡 Посмотреть температуру городов")
async def handle_view_cities(message: Message, state: FSMContext):
    kb = get_back_keyboard()
    text = (
        "📝 Введите названия городов через запятую.\n\n"
        "Например: «Волгоград, Воронеж, Волжский, Пермь»"
    )
    await message.answer(text, reply_markup=kb)
    await state.set_state(States.waiting_for_cities)

@router.message(F.text == "👤 Мой профиль")
async def handle_my_profile(message: Message, state: FSMContext):
    user = message.from_user
    back_kb = get_back_keyboard()

    username = user.username if user.username else "(нет)"
    language = user.language_code if user.language_code else "(неизвестно)"

    text = (
        "👤 Мой профиль:\n\n"
        f"• Имя: {user.first_name}\n"
        f"• ID: {user.id}\n"
        f"• Ваш tg: @{username}\n"
        f"• Язык: {language}"
    )
    await message.answer(text, reply_markup=back_kb)

@router.callback_query(F.data == "back_to_menu")
async def callback_back(query: CallbackQuery, state: FSMContext):
    await state.clear()  # Очищаем состояние пользователя

    text = (
        "Добро пожаловать в меню!\n\n"
        "Я бот, который покажет погоду.\n"
        "Выберите нужный пункт меню:"
    )

    # 🔹 Используем query.message.edit_text вместо query.edit_text
    await query.message.answer(text, reply_markup=main_menu)

# Важный момент: вместо state=States.waiting_for_cities => StateFilter(States.waiting_for_cities)
@router.message(StateFilter(States.waiting_for_cities))
async def process_city_list(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_text = message.text.strip()
    log_query(user_id, user_text)

    if not user_text:
        kb = get_back_keyboard()
        await message.answer("❌ Вы не ввели никаких городов", reply_markup=kb)
        return

    # Разделяем, убираем дубликаты
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

    # Собираем офиц. названия для параллельного запроса
    city_official_list = [official for (user_city, official) in page_cities]

    # 🔥 Запрашиваем погоду ПАРАЛЛЕЛЬНО
    weather_labels = await get_weather_label_parallel(city_official_list)

    # Формируем кнопки
    weather_buttons = []
    for (user_city, official_city), label in zip(page_cities, weather_labels):
        weather_buttons.append([
            InlineKeyboardButton(text=label, callback_data=f"details|{official_city}")
        ])

    # Кнопки навигации
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"page_{current_page-1}"))

    nav_buttons.append(InlineKeyboardButton(text=f"Страница {current_page}/{total_pages}", callback_data="none"))

    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Следующая", callback_data=f"page_{current_page+1}"))

    # Итоговая клавиатура
    weather_kb = InlineKeyboardMarkup(
        inline_keyboard=weather_buttons + [nav_buttons] + [
            [InlineKeyboardButton(text="🔙 Вернуться", callback_data="back_to_menu")]
        ]
    )

    text_out = "Вот погода по вашим городам (см. кнопки):"

    if isinstance(message, Message):
        await message.answer(text_out, reply_markup=weather_kb)
    else:
        await message.message.edit_text(text_out, reply_markup=weather_kb)


@router.callback_query(StateFilter(States.waiting_for_cities), lambda c: c.data.startswith("page_"))
async def handle_pagination(query: CallbackQuery, state: FSMContext):
    await query.answer()
    _, page_str = query.data.split("_", 1)
    page = int(page_str)
    cities, _ = await get_pagination_state(state)
    await set_pagination_state(state, cities, page)
    await show_cities_page(query, state)

@router.callback_query(lambda c: c.data.startswith("details|"))
async def callback_details(query: CallbackQuery, state: FSMContext):
    await query.answer()
    
    # Разбираем данные из callback
    _, city_name = query.data.split("|", 1)
    info = get_detailed_weather(city_name)

    # Создаём клавиатуру корректным способом
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Вернуться", callback_data="back_to_menu")]
        ]
    )

    # Редактируем сообщение, а не создаём новое
    await query.message.edit_text(info, reply_markup=kb)


@router.message()
async def fallback_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_text = message.text.strip()
    log_query(user_id, user_text)

    await message.answer("Пожалуйста, используйте кнопки или введите /start, чтобы вернуться в меню.")
