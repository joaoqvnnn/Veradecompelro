from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from keyboards.client import (
    main_menu_kb, gift_card_kb, ranking_kb, support_kb, back_kb
)
from services.giftcard import GiftCardService
from config import settings

router = Router(name="extras")


class GiftStates(StatesGroup):
    waiting_code = State()


@router.callback_query(F.data == "gift_card")
async def cb_gift(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GiftStates.waiting_code)
    await callback.message.edit_text(
        "🎁 <b>RESGATAR GIFT CARD</b>\n\n"
        "Digite o código do seu Gift Card:\n"
        "Exemplo: <code>ABC123XYZ456</code>",
        reply_markup=gift_card_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(GiftStates.waiting_code)
async def process_gift(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    code = message.text.strip() if message.text else ""
    await state.clear()

    try:
        value = await GiftCardService.redeem(session, db_user.id, code)
        await session.refresh(db_user)
        await message.answer(
            f"✅ <b>Gift Card resgatado com sucesso!</b>\n\n"
            f"💰 Valor adicionado: <b>R$ {value:.2f}</b>\n"
            f"💳 Novo saldo: <b>R$ {db_user.balance:.2f}</b>",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    except ValueError as e:
        await message.answer(f"❌ {e}", reply_markup=main_menu_kb())


@router.callback_query(F.data == "ranking")
async def cb_ranking(callback: CallbackQuery):
    text = (
        "🏆 <b>RANKINGS</b>\n\n"
        "Escolha o período:"
    )
    await callback.message.edit_text(text, reply_markup=ranking_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery):
    text = (
        f"🎧 <b>Atendimento</b>\n\n"
        f"Precisa de ajuda? Fale com nosso suporte."
    )
    await callback.message.edit_text(
        text,
        reply_markup=support_kb(settings.SUPPORT_USERNAME),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "about")
async def cb_about(callback: CallbackQuery):
    text = (
        f"ℹ️ <b>Sobre o Bot</b>\n\n"
        f"🏪 Nome: <b>{settings.STORE_NAME}</b>\n"
        f"🤖 Bot: @{settings.BOT_USERNAME}\n"
        f"🛡 Entrega 100% automática\n"
        f"💳 Pagamento via PIX instantâneo\n\n"
        f"Use /termos para ver os termos de uso."
    )
    await callback.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()
