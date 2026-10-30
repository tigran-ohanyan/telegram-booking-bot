import logging
from datetime import date, datetime, time, timedelta
from html import escape

from aiogram import Bot, Router
from aiogram.filters import BaseFilter, Command, CommandObject
from aiogram.types import Message

from bot import texts
from bot.config import Settings
from bot.repository import Repository

log = logging.getLogger(__name__)
router = Router(name="admin")

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

HELP = """<b>Admin commands</b>

/services — list all services with ids
/addservice Name | minutes | price — add a service
/hideservice id · /showservice id — hide or show a service
/hours mon 09:00-18:00 — set working hours for a weekday
/hours mon off — remove a working day
/bookings [YYYY-MM-DD] — bookings for a day (default: today)
/cancel id — cancel a booking and notify the client
"""


class IsAdmin(BaseFilter):
    async def __call__(self, message: Message, settings: Settings) -> bool:
        return bool(message.from_user and message.from_user.id in settings.admin_ids)


router.message.filter(IsAdmin())


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    await message.answer(HELP)


@router.message(Command("services"))
async def cmd_services(message: Message, repo: Repository) -> None:
    services = await repo.list_services(active_only=False)
    if not services:
        await message.answer("No services yet. Add one with /addservice Name | 30 | 5000")
        return
    lines = []
    for s in services:
        flag = "" if s.active else " (hidden)"
        lines.append(f"#{s.id} <b>{escape(s.name)}</b> · {s.duration_min} min · {s.price}{flag}")
    await message.answer("\n".join(lines))


@router.message(Command("addservice"))
async def cmd_addservice(message: Message, command: CommandObject, repo: Repository) -> None:
    parts = [p.strip() for p in (command.args or "").split("|")]
    if len(parts) < 2 or not parts[0] or not parts[1].isdigit():
        await message.answer("Usage: /addservice Name | minutes | price")
        return
    price = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    service = await repo.add_service(parts[0], int(parts[1]), price)
    await message.answer(f"Added #{service.id} <b>{escape(service.name)}</b>")


@router.message(Command("hideservice", "showservice"))
async def cmd_toggle_service(message: Message, command: CommandObject, repo: Repository) -> None:
    if not (command.args or "").strip().isdigit():
        await message.answer(f"Usage: /{command.command} id")
        return
    active = command.command == "showservice"
    ok = await repo.set_service_active(int(command.args), active)
    await message.answer("Done." if ok else "Service not found.")


@router.message(Command("hours"))
async def cmd_hours(message: Message, command: CommandObject, repo: Repository) -> None:
    args = (command.args or "").lower().split()
    if len(args) != 2 or args[0] not in WEEKDAYS:
        await message.answer("Usage: /hours mon 09:00-18:00  or  /hours mon off")
        return
    weekday = WEEKDAYS.index(args[0])
    if args[1] == "off":
        await repo.clear_working_hours(weekday)
        await message.answer(f"{args[0].title()} is now a day off.")
        return
    try:
        start_raw, end_raw = args[1].split("-")
        start, end = time.fromisoformat(start_raw), time.fromisoformat(end_raw)
    except ValueError:
        await message.answer("Time must look like 09:00-18:00")
        return
    if start >= end:
        await message.answer("Start must be before end.")
        return
    await repo.set_working_hours(weekday, start, end)
    await message.answer(f"{args[0].title()}: {start:%H:%M}–{end:%H:%M}")


@router.message(Command("bookings"))
async def cmd_bookings(
    message: Message, command: CommandObject, repo: Repository, settings: Settings
) -> None:
    raw = (command.args or "").strip()
    try:
        day = date.fromisoformat(raw) if raw else datetime.now(settings.tz).date()
    except ValueError:
        await message.answer("Date must look like 2030-01-07")
        return
    start = datetime.combine(day, time.min, tzinfo=settings.tz)
    bookings = await repo.bookings_between(start, start + timedelta(days=1))
    if not bookings:
        await message.answer(f"No bookings on {day:%a %d %b}.")
        return
    lines = [f"<b>{day:%a %d %b}</b>", ""]
    for b in bookings:
        lines.append(
            f"#{b.id} {b.starts_at:%H:%M}–{b.ends_at:%H:%M} "
            f"<b>{escape(b.service_name)}</b> — {escape(b.user_name)}"
        )
    await message.answer("\n".join(lines))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, command: CommandObject, repo: Repository, bot: Bot) -> None:
    if not (command.args or "").strip().isdigit():
        await message.answer("Usage: /cancel id")
        return
    booking = await repo.get_booking(int(command.args))
    if booking is None or not await repo.cancel_booking(booking.id):
        await message.answer("Booking not found or already cancelled.")
        return
    await message.answer(f"Booking #{booking.id} cancelled.")
    try:
        await bot.send_message(
            booking.user_id,
            texts.ADMIN_CANCELLED_USER.format(
                service=escape(booking.service_name),
                when=booking.starts_at.strftime("%a %d %b, %H:%M"),
            ),
        )
    except Exception:  # user may have blocked the bot
        log.warning("Could not notify user %s about cancellation", booking.user_id)
