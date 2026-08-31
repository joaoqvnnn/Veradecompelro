from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from keyboards.client import main_menu_kb
from config import settings

router = Router(name="start")


def format_start_text(user: User) -> str:
    return (
        f"🎬 <b>Bem-vindo à {settings.STORE_NAME}!</b> ✨\n\n"
        f"A sua central de streamings com entrega <b>100% automática</b>.\n"
        f"Pagou, recebeu. Sem filas, sem precisar falar com atendente, 24 horas por dia! ⚡️\n\n"
        f"🛡 <b>Segurança e Suporte:</b>\n"
        f"Mais de 12.000 clientes já passaram por aqui.\n"
        f"Participe da nossa comunidade e veja as referências.\n\n"
        f"💠 <b>Seus Dados:</b>\n"
        f"├ 👤 ID: <code>{user.id}</code>\n"
        f"└ 💰 Saldo Atual: <b>R$ {user.balance:.2f}</b>\n\n"
        f"👇 <b>COMO COMEÇAR:</b>\n"
        f"Clique em <b>\"🛍 Comprar Produtos\"</b> para acessar nosso catálogo."
    )


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, session: AsyncSession):
    text = format_start_text(db_user)
    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, db_user: User):
    text = format_start_text(db_user)
    await callback.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")
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
