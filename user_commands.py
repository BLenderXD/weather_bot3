from aiogram.types import BotCommand, BotCommandScopeChat
from aiogram import Bot

# Команды для обычного пользователя
user_commands = [
    BotCommand(command="/start", description="🚀 Запустить бота"),
]