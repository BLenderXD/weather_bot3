import logging
import asyncio
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import Update
from aiogram import Bot
from datetime import datetime
import os
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

class LoggingMiddleware(BaseMiddleware):
    _log_bot = None 

    def __init__(self, main_bot: Bot):
        super().__init__()
        self.main_bot = main_bot
        self._init_log_bot()
        logging.info("✅ LoggingMiddleware успешно инициализирована!")
        print("✅ LoggingMiddleware успешно инициализирована!")

    @classmethod
    def _init_log_bot(cls):
        """Инициализация логирующего бота."""
        if cls._log_bot is None:
            token = os.getenv("BOT_LOG_TOKEN")
            logging.info(f"Получен BOT_LOG_TOKEN: {'найден' if token else 'не найден'}")
            if token:
                try:
                    cls._log_bot = Bot(token=token)
                    logging.info("Логирующий бот успешно инициализирован.")
                except Exception as e:
                    logging.error(f"Ошибка инициализации лог-бота: {e}")
            else:
                logging.error("BOT_LOG_TOKEN не найден в .env!")

    async def __call__(self, handler, event: Update, data: dict):
        logging.info("Middleware вызван для события")
        admins = os.getenv("ADMIN")
        logging.info(f"Проверка условий: _log_bot = {self._log_bot is not None}, admins = {admins}")

        if self._log_bot and admins:
            logging.info("Запуск фоновой задачи для обработки события")
            asyncio.create_task(self._process_event(event))
        else:
            logging.warning("Логирование не запущено: отсутствует _log_bot или admins")

        return await handler(event, data)

    async def _process_event(self, event: Update):
        """Формирование логов и отправка в Telegram админу."""
        logging.info("Начало обработки события")
        try:
            user_info = await self._get_user_info(event)
            logging.info(f"Получена информация о пользователе: {user_info}")
            if not user_info or user_info.get("is_bot"):
                logging.info("Событие пропущено: нет пользователя или это бот")
                return

            event_type, event_data = self._get_event_data(event)
            logging.info(f"Тип события: {event_type}, данные: {event_data}")
            if event_type == "unknown":
                logging.info("Неизвестный тип события, пропускаем")
                return

            await self._send_log(user_info, event_type, event_data)
            logging.info("Лог успешно отправлен")
        except Exception as e:
            logging.error(f"Ошибка логирования: {e}", exc_info=True)

    async def _get_user_info(self, event: Update) -> dict | None:
        """Извлекаем информацию о пользователе из события."""
        user = None
        sources = [
            "callback_query",
            "message",
            "inline_query",
            "poll_answer",
            "chat_join_request",
            "my_chat_member",
            "chat_member",
        ]

        for source in sources:
            if obj := getattr(event, source, None):
                user = getattr(obj, "from_user", None)
                if user:
                    logging.info(f"Пользователь найден в источнике: {source}")
                    break

        if not user:
            logging.warning("Пользователь не найден в событии")
            return None

        return {
            "name": user.full_name,
            "username": user.username or "N/A",
            "user_id": user.id,
            "is_bot": user.is_bot,
        }

    def _get_event_data(self, event: Update) -> tuple[str, str]:
        """Определяем тип события и его данные."""
        if event.callback_query:
            data = event.callback_query.data
            return "callback", data[:200] if data else "нет данных"
        if event.message:
            text = event.message.text or event.message.caption
            return "message", text[:200] if text else "нет текста"
        if event.inline_query:
            return "inline", event.inline_query.query[:200]
        return "unknown", ""

    async def _send_log(self, user_info: dict, event_type: str, event_data: str):
        """Отправляем лог админу."""
        try:
            admin_id_str = os.getenv("ADMIN")
            logging.info(f"Получен ADMIN из .env: {admin_id_str}")
            if not admin_id_str:
                raise ValueError("Переменная ADMIN не установлена в .env")
            
            admin_id = int(admin_id_str)
            message = (
                f"👤 <b>{user_info['name']} (@{user_info['username']})</b>\n"
                f"🆔 <code>{user_info['user_id']}</code>\n"
                f"📩 <b>{event_type.capitalize()}</b>\n"
                f"📝 {event_data or 'нет данных'}\n"
                f"⏱ {datetime.now().strftime('%H:%M:%S.%f')[:-3]}"
            )

            logging.info(f"Отправка сообщения админу {admin_id}: {message}")
            await self._log_bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode="HTML",
            )
        except Exception as e:
            logging.error(f"Ошибка отправки лога: {e}", exc_info=True)

    @classmethod
    async def close_log_bot(cls):
        """Закрываем сессию логирующего бота."""
        try:
            if cls._log_bot:
                await cls._log_bot.session.close()
                logging.info("Сессия лог-бота закрыта")
        except Exception as e:
            logging.error(f"Ошибка при закрытии сессии лог-бота: {e}")