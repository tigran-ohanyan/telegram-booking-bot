import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from bot.config import load_settings
from bot.db import connect
from bot.handlers import admin, booking, my_bookings, start
from bot.repository import Repository
from bot.services.reminders import CHECK_EVERY_MIN, send_due_reminders


async def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    settings = load_settings()

    db = await connect(settings.db_path)
    repo = Repository(db)

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp["repo"] = repo
    dp["settings"] = settings
    dp.include_routers(start.router, booking.router, my_bookings.router, admin.router)

    scheduler = AsyncIOScheduler(timezone=settings.tz)
    scheduler.add_job(
        send_due_reminders, "interval", minutes=CHECK_EVERY_MIN, args=[bot, repo, settings]
    )
    scheduler.start()

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
