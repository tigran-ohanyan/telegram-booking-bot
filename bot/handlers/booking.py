from datetime import date, datetime, timedelta
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot import texts
from bot.config import Settings
from bot.keyboards import (
    BackCb,
    ConfirmCb,
    DayCb,
    MenuCb,
    ServiceCb,
    SlotCb,
    confirm_kb,
    days_kb,
    main_menu,
    services_kb,
    slots_kb,
)
from bot.repository import Repository
from bot.services.slots import free_slots, upcoming_days

router = Router(name="booking")


class BookingFlow(StatesGroup):
    service = State()
    day = State()
    slot = State()
    confirm = State()


def _when(dt: datetime) -> str:
    return dt.strftime("%a %d %b, %H:%M")


async def _show_services(target: Message, repo: Repository, state: FSMContext) -> None:
    services = await repo.list_services()
    await state.set_state(BookingFlow.service)
    await target.edit_text(texts.CHOOSE_SERVICE, reply_markup=services_kb(services))


async def _show_days(
    target: Message, repo: Repository, settings: Settings, state: FSMContext
) -> None:
    data = await state.get_data()
    service = await repo.get_service(data["service_id"])
    hours = await repo.get_working_hours()
    today = datetime.now(settings.tz).date()
    days = upcoming_days(today, hours, settings.days_ahead)
    if not days:
        await target.edit_text(texts.NO_DAYS, reply_markup=main_menu())
        await state.clear()
        return
    await state.set_state(BookingFlow.day)
    await target.edit_text(
        texts.CHOOSE_DAY.format(service=escape(service.name), duration=service.duration_min),
        reply_markup=days_kb(days),
    )


@router.message(Command("book"))
async def cmd_book(message: Message, repo: Repository, state: FSMContext) -> None:
    services = await repo.list_services()
    await state.set_state(BookingFlow.service)
    await message.answer(texts.CHOOSE_SERVICE, reply_markup=services_kb(services))


@router.callback_query(MenuCb.filter(F.action == "book"))
async def menu_book(query: CallbackQuery, repo: Repository, state: FSMContext) -> None:
    await _show_services(query.message, repo, state)
    await query.answer()


@router.callback_query(BackCb.filter(F.to == "services"))
async def back_to_services(query: CallbackQuery, repo: Repository, state: FSMContext) -> None:
    await _show_services(query.message, repo, state)
    await query.answer()


@router.callback_query(BookingFlow.service, ServiceCb.filter())
async def pick_service(
    query: CallbackQuery,
    callback_data: ServiceCb,
    repo: Repository,
    settings: Settings,
    state: FSMContext,
) -> None:
    await state.update_data(service_id=callback_data.id)
    await _show_days(query.message, repo, settings, state)
    await query.answer()


@router.callback_query(BackCb.filter(F.to == "days"))
async def back_to_days(
    query: CallbackQuery, repo: Repository, settings: Settings, state: FSMContext
) -> None:
    await _show_days(query.message, repo, settings, state)
    await query.answer()


@router.callback_query(BookingFlow.day, DayCb.filter())
async def pick_day(
    query: CallbackQuery,
    callback_data: DayCb,
    repo: Repository,
    settings: Settings,
    state: FSMContext,
) -> None:
    day = date.fromisoformat(callback_data.iso)
    data = await state.get_data()
    service = await repo.get_service(data["service_id"])
    hours = (await repo.get_working_hours()).get(day.weekday())

    day_start = datetime.combine(day, datetime.min.time(), tzinfo=settings.tz)
    busy = [
        (b.starts_at, b.ends_at)
        for b in await repo.bookings_between(day_start, day_start + timedelta(days=1))
    ]
    slots = free_slots(
        day,
        hours,
        service.duration_min,
        settings.slot_step_min,
        busy,
        now=datetime.now(settings.tz),
        tz=settings.tz,
    )
    if not slots:
        await query.answer(texts.NO_SLOTS.format(day=day.strftime("%a %d %b")), show_alert=True)
        return

    await state.update_data(day=callback_data.iso)
    await state.set_state(BookingFlow.slot)
    await query.message.edit_text(
        texts.CHOOSE_SLOT.format(service=escape(service.name), day=day.strftime("%a %d %b")),
        reply_markup=slots_kb(slots),
    )
    await query.answer()


@router.callback_query(BookingFlow.slot, SlotCb.filter())
async def pick_slot(
    query: CallbackQuery,
    callback_data: SlotCb,
    repo: Repository,
    settings: Settings,
    state: FSMContext,
) -> None:
    starts_at = datetime.fromtimestamp(callback_data.ts, tz=settings.tz)
    data = await state.get_data()
    service = await repo.get_service(data["service_id"])

    await state.update_data(ts=callback_data.ts)
    await state.set_state(BookingFlow.confirm)
    price_line = texts.PRICE_LINE.format(price=service.price) if service.price else ""
    await query.message.edit_text(
        texts.CONFIRM.format(
            service=escape(service.name),
            when=_when(starts_at),
            duration=service.duration_min,
            price_line=price_line,
        ),
        reply_markup=confirm_kb(),
    )
    await query.answer()


@router.callback_query(BookingFlow.confirm, ConfirmCb.filter())
async def confirm(
    query: CallbackQuery,
    callback_data: ConfirmCb,
    repo: Repository,
    settings: Settings,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    await state.clear()

    if not callback_data.yes:
        await query.message.edit_text(texts.CANCELLED_FLOW, reply_markup=main_menu())
        await query.answer()
        return

    service = await repo.get_service(data["service_id"])
    starts_at = datetime.fromtimestamp(data["ts"], tz=settings.tz)
    user = query.from_user
    booking = await repo.create_booking(user.id, user.full_name, service, starts_at)

    if booking is None:
        await query.message.edit_text(texts.SLOT_TAKEN, reply_markup=main_menu())
    else:
        await query.message.edit_text(
            texts.BOOKED.format(service=escape(service.name), when=_when(starts_at)),
            reply_markup=main_menu(),
        )
    await query.answer()
