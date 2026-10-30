from datetime import datetime
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot import texts
from bot.config import Settings
from bot.keyboards import CancelCb, MenuCb, main_menu, my_bookings_kb
from bot.repository import Repository

router = Router(name="my_bookings")


def _render(bookings) -> str:
    if not bookings:
        return texts.MY_BOOKINGS_EMPTY
    lines = [texts.MY_BOOKINGS, ""]
    for b in bookings:
        lines.append(
            f"• {b.starts_at.strftime('%a %d %b, %H:%M')} — <b>{escape(b.service_name)}</b>"
        )
    lines += ["", "Tap a booking to cancel it."]
    return "\n".join(lines)


async def _show(target: Message, user_id: int, repo: Repository, settings: Settings) -> None:
    bookings = await repo.user_bookings(user_id, datetime.now(settings.tz))
    markup = my_bookings_kb(bookings) if bookings else main_menu()
    await target.edit_text(_render(bookings), reply_markup=markup)


@router.message(Command("my"))
async def cmd_my(message: Message, repo: Repository, settings: Settings) -> None:
    bookings = await repo.user_bookings(message.from_user.id, datetime.now(settings.tz))
    markup = my_bookings_kb(bookings) if bookings else main_menu()
    await message.answer(_render(bookings), reply_markup=markup)


@router.callback_query(MenuCb.filter(F.action == "mine"))
async def menu_mine(query: CallbackQuery, repo: Repository, settings: Settings) -> None:
    await _show(query.message, query.from_user.id, repo, settings)
    await query.answer()


@router.callback_query(CancelCb.filter())
async def cancel_booking(
    query: CallbackQuery, callback_data: CancelCb, repo: Repository, settings: Settings
) -> None:
    ok = await repo.cancel_booking(callback_data.id, user_id=query.from_user.id)
    await query.answer(texts.BOOKING_CANCELLED if ok else texts.BOOKING_NOT_FOUND)
    await _show(query.message, query.from_user.id, repo, settings)
