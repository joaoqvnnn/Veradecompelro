from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from keyboards.client import main_menu_kb
from keyboards.dynamic import build_keyboard_from_buttons
from services.messages import MessageService
from config import settings

router = Router(name="start")


async def get_start_content(session: AsyncSession, user: User):
    tpl = await MessageService.get_rendered(
        session,
        "start",
        store_name=settings.STORE_NAME,
        bot_username=settings.BOT_USERNAME,
        user_id=user.id,
        balance=f"{user.balance:.2f}",
    )
    return tpl


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, session: AsyncSession):
    tpl = await get_start_content(session, db_user)

    # Se o template tiver botões salvos, usa eles. Senão usa o menu padrão.
    if tpl.get("buttons"):
        kb = build_keyboard_from_buttons(tpl["buttons"])
    else:
        kb = main_menu_kb()

    await message.answer(
        tpl["content"],
        reply_markup=kb,
        parse_mode=tpl.get("parse_mode", "HTML")
    )


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, db_user: User, session: AsyncSession):
    tpl = await get_start_content(session, db_user)

    if tpl.get("buttons"):
        kb = build_keyboard_from_buttons(tpl["buttons"])
    else:
        kb = main_menu_kb()

    await callback.message.edit_text(
        tpl["content"],
        reply_markup=kb,
        parse_mode=tpl.get("parse_mode", "HTML")
    )
    await callback.answer()


@router.message(Command("saldo"))
async def cmd_saldo(message: Message, db_user: User):
    await message.answer(
        f"💰 <b>Seu saldo atual:</b> R$ {db_user.balance:.2f}",
        parse_mode="HTML"
    )


@router.message(Command("id"))
async def cmd_id(message: Message, db_user: User):
    await message.answer(f"🆔 Seu ID: <code>{db_user.id}</code>", parse_mode="HTML")


@router.message(Command("termos"))
async def cmd_termos(message: Message, session: AsyncSession):
    tpl = await MessageService.get_rendered(session, "terms")
    await message.answer(tpl["content"], parse_mode=tpl.get("parse_mode", "HTML"))
