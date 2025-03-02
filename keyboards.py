from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# В aiogram 3.x нужно явно передать keyboard=[...]
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🌡 Посмотреть температуру городов"),
            KeyboardButton(text="👤 Мой профиль")
        ]
    ],
    resize_keyboard=True
)

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_back_keyboard():
    # Для aiogram 3.x просто указываем inline_keyboard как список списков кнопок.
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Вернуться", callback_data="back_to_menu")]
        ]
    )
