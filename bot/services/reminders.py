import logging
from datetime import datetime, timedelta
from html import escape

from aiogram import Bot

from bot import texts
from bot.config import Settings
from bot.repository import Repository

log = logging.getLogger(__name__)

REMIND_BEFORE = timedelta(hours=1)
CHECK_EVERY_MIN = 5


async def send_due_reminders(bot: Bot, repo: Repository, settings: Settings) -> int:
    """Send a reminder for bookings starting in about one hour. Returns how many were sent."""
    now = datetime.now(settings.tz)
    window_start = now + REMIND_BEFORE - timedelta(minutes=CHECK_EVERY_MIN)
    window_end = now + REMIND_BEFORE + timedelta(minutes=CHECK_EVERY_MIN)

    sent = 0
    for booking in await repo.due_reminders(window_start, window_end):
        try:
            await bot.send_message(
                booking.user_id,
                texts.REMINDER.format(
                    service=escape(booking.service_name),
                    when=booking.starts_at.strftime("%H:%M"),
                ),
            )
            sent += 1
        except Exception:
            log.warning("Reminder for booking %s failed", booking.id, exc_info=True)
        finally:
            await repo.mark_reminded(booking.id)
    return sent
