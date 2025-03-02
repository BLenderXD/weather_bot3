import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from database import create_tables
from middlewares.log_middleware import LoggingMiddleware
from handlers import router
from weather import close_session  # Импортируем функцию закрытия сессии

# Настройки логирования
logging.basicConfig(level=logging.INFO)
load_dotenv()

# Токен бота
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Создание бота с правильным parse_mode для aiogram 3.7+
bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Подключение middleware
dp.update.middleware(LoggingMiddleware(bot))

# Функция обработки завершения работы
async def on_shutdown(dp: Dispatcher):
    """Закрытие сессий при завершении работы бота."""
    logging.info("Бот завершает работу...")
    await close_session()  # Закрываем сессию aiohttp из weather.py
    await bot.session.close()  # Закрываем сессию основного бота
    logging.info("Все сессии закрыты.")

# Функция запуска бота
def main():
    create_tables()  # Создаём таблицы в БД
    dp.include_router(router)  # Подключаем маршруты
    
    # Регистрируем обработчик завершения
    dp.shutdown.register(on_shutdown)
    
    # Запускаем бота в режиме polling
    logging.info("Бот запущен!")
    dp.run_polling(bot, skip_updates=True)

if __name__ == "__main__":
    main()