from datetime import date, datetime

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.models import Booking, Service


class MenuCb(CallbackData, prefix="menu"):
    action: str  # book | mine


class ServiceCb(CallbackData, prefix="svc"):
    id: int


class DayCb(CallbackData, prefix="day"):
    iso: str  # YYYY-MM-DD


class SlotCb(CallbackData, prefix="slot"):
    ts: int  # unix timestamp


class ConfirmCb(CallbackData, prefix="ok"):
    yes: bool


class CancelCb(CallbackData, prefix="cancel"):
    id: int


class BackCb(CallbackData, prefix="back"):
    to: str  # services | days


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Book an appointment", callback_data=MenuCb(action="book"))
    kb.button(text="🗒 My bookings", callback_data=MenuCb(action="mine"))
    kb.adjust(1)
    return kb.as_markup()


def services_kb(services: list[Service]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in services:
        label = f"{s.name} · {s.duration_min} min"
        if s.price:
            label += f" · {s.price}"
        kb.button(text=label, callback_data=ServiceCb(id=s.id))
    kb.adjust(1)
    return kb.as_markup()


def days_kb(days: list[date]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for d in days:
        kb.button(text=d.strftime("%a %d %b"), callback_data=DayCb(iso=d.isoformat()))
    kb.adjust(2)
    kb.row(_back_button("services"))
    return kb.as_markup()


def slots_kb(slots: list[datetime]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in slots:
        kb.button(text=s.strftime("%H:%M"), callback_data=SlotCb(ts=int(s.timestamp())))
    kb.adjust(3)
    kb.row(_back_button("days"))
    return kb.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Confirm", callback_data=ConfirmCb(yes=True))
    kb.button(text="❌ Cancel", callback_data=ConfirmCb(yes=False))
    kb.adjust(2)
    return kb.as_markup()


def my_bookings_kb(bookings: list[Booking]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for b in bookings:
        label = f"❌ {b.starts_at.strftime('%d %b %H:%M')} · {b.service_name}"
        kb.button(text=label, callback_data=CancelCb(id=b.id))
    kb.adjust(1)
    kb.row(
        InlineKeyboardBuilder()
        .button(text="« Menu", callback_data=MenuCb(action="menu"))
        .buttons[0]
    )
    return kb.as_markup()


def _back_button(to: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text="« Back", callback_data=BackCb(to=to).pack())
