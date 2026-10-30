from html import escape

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from bot import texts
from bot.keyboards import MenuCb, main_menu

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    name = escape(message.from_user.first_name if message.from_user else "there")
    await message.answer(texts.WELCOME.format(name=name), reply_markup=main_menu())


@router.callback_query(MenuCb.filter())
async def back_to_menu(query: CallbackQuery, callback_data: MenuCb) -> None:
    if callback_data.action != "menu":
        return  # handled by other routers
    name = escape(query.from_user.first_name)
    await query.message.edit_text(texts.WELCOME.format(name=name), reply_markup=main_menu())
    await query.answer()
