import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import ReplyKeyboardRemove

from config.loader import get_token, get_notify_group_id, get_admin_group_id
from services.calendar_service import refresh_calendar
from services.pickle_storage import PickleStorage
from scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(token=get_token())
    dp = Dispatcher(storage=PickleStorage())

    # Регистрация роутеров
    from handlers.user import router as user_router
    from handlers.admin import router as admin_router
    dp.include_router(user_router)
    dp.include_router(admin_router)

    # Обновляем календарь при старте
    refresh_calendar()
    logger.info("Календарь обновлён")

    # Сбрасываем клавиатуру в группах
    for group_id in {get_notify_group_id(), get_admin_group_id()}:
        try:
            msg = await bot.send_message(group_id, "\u200b", reply_markup=ReplyKeyboardRemove())
            await bot.delete_message(group_id, msg.message_id)
        except Exception:
            pass

    # Планировщик
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Планировщик запущен")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
