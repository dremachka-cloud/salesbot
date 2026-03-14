import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import ReplyKeyboardRemove

from services.calendar_service import refresh_calendar
from services.order_service import get_orders_for_today, format_daily_summary, cleanup_old_orders
from config.loader import get_notify_group_id

logger = logging.getLogger(__name__)


async def job_refresh_calendar():
    refresh_calendar()
    logger.info("Планировщик: календарь обновлён")


async def job_cleanup_orders():
    removed = cleanup_old_orders()
    if removed:
        logger.info("Планировщик: удалено старых заказов: %d", removed)


async def job_daily_summary(bot: Bot):
    orders = get_orders_for_today()
    if not orders:
        return
    summary = format_daily_summary(orders)
    if summary:
        try:
            await bot.send_message(get_notify_group_id(), summary, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
            logger.info("Планировщик: суточный итог отправлен (%d заказов)", len(orders))
        except Exception as e:
            logger.error("Планировщик: ошибка отправки итога: %s", e)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    scheduler.add_job(
        job_refresh_calendar,
        trigger="cron",
        hour=0,
        minute=1,
        id="refresh_calendar",
    )

    scheduler.add_job(
        job_daily_summary,
        trigger="cron",
        hour=21,
        minute=0,
        id="daily_summary",
        kwargs={"bot": bot},
    )

    scheduler.add_job(
        job_cleanup_orders,
        trigger="cron",
        hour=0,
        minute=5,
        id="cleanup_orders",
    )

    return scheduler
