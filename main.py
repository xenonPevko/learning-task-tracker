import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import Database
from handlers import router, set_service
from repositories import TaskRepository, SubjectRepository, UserRepository
from services import TaskService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


async def main():
    # --- 1. База данных ---
    db = Database()
    await db.connect()

    # --- 2. Слои: репозитории → сервис ---
    user_repo = UserRepository(db)
    subject_repo = SubjectRepository(db)
    task_repo = TaskRepository(db)

    service = TaskService(
        tasks=task_repo,
        subjects=subject_repo,
        users=user_repo,
    )

    # Прокидываем сервис в хендлеры
    set_service(service)

    # --- 3. Бот и диспетчер ---
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    # --- 4. Запуск ---
    log.info("Бот запущен")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()
        log.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass