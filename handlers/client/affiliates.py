from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from keyboards.client import affiliates_kb, main_menu_kb
from config import settings

router = Router(name="affiliates")


@router.callback_query(F.data == "affiliates")
async def cb_affiliates(callback: CallbackQuery, db_user: User):
    can_withdraw = db_user.affiliate_balance >= settings.AFFILIATE_MIN_WITHDRAW

    link = f"https://t.me/{settings.BOT_USERNAME}?start={db_user.id}"

    text = (
        f"💰 <b>PROGRAMA DE AFILIADOS</b>\n\n"
        f"⚙️ Status: <b>{'Ativo' if settings.AFFILIATE_ENABLED else 'Desativado'}</b>\n"
        f"🧲 Comissão: <b>{settings.AFFILIATE_COMMISSION_PERCENT}%</b>\n"
        f"👥 Indicações: <b>{db_user.total_referrals}</b>\n"
        f"🪙 Total ganho: <b>R$ {db_user.total_commission_earned:.2f}</b>\n"
        f"💰 Saque mínimo: <b>R$ {settings.AFFILIATE_MIN_WITHDRAW:.2f}</b>\n"
        f"🔥 Saldo de comissões: <b>R$ {db_user.affiliate_balance:.2f}</b>\n\n"
        f"🔗 <b>Seu link:</b>\n"
        f"<code>{link}</code>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=affiliates_kb(can_withdraw),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "affiliate_copy_link")
async def cb_copy_link(callback: CallbackQuery, db_user: User):
    link = f"https://t.me/{settings.BOT_USERNAME}?start={db_user.id}"
    await callback.answer(f"Link: {link}", show_alert=True)
