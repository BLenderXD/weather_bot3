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

logging.basicConfig(level=logging.INFO)
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

dp.update.middleware(LoggingMiddleware(bot))


async def on_shutdown(dp: Dispatcher):
    """Закрытие сессий при завершении работы бота."""
    logging.info("Бот завершает работу...")
    await close_session()  
    await bot.session.close()  
    logging.info("Все сессии закрыты.")

# запуск бота
def main():
    create_tables()  # cоздаём таблицы в БД
    dp.include_router(router)  # подключаем маршруты
    
    # регистрируем обработчик завершения
    dp.shutdown.register(on_shutdown)
    
    # запускаем бота в режиме polling
    logging.info("Бот запущен!")
    dp.run_polling(bot, skip_updates=True)

if __name__ == "__main__":
    main()