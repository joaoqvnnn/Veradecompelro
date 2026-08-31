from decimal import Decimal
from datetime import datetime, timedelta, timezone
import secrets
import string

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, GiftCard, GiftCardStatus, Payment, PaymentStatus
from keyboards.admin import (
    admin_giftcards_kb, admin_payments_kb, admin_affiliates_kb,
    admin_settings_kb, admin_back_kb, admin_broadcast_kb
)
from handlers.admin.panel import is_admin

router = Router(name="admin_others")


class GiftCreate(StatesGroup):
    value = State()
    quantity = State()


# ========== GIFT CARDS ==========

@router.callback_query(F.data == "admin:giftcards")
async def cb_giftcards(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    text = "🎁 <b>GIFT CARDS</b>\n\nCrie e gerencie códigos."
    await callback.message.edit_text(text, reply_markup=admin_giftcards_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:gift_create")
async def cb_gift_create(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    await state.set_state(GiftCreate.value)
    await callback.message.edit_text(
        "🎁 Envie o <b>valor</b> do Gift Card (ex: 20):",
        reply_markup=admin_back_kb("admin:giftcards"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(GiftCreate.value)
async def process_gift_value(message: Message, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    try:
        value = Decimal(message.text.strip().replace(",", "."))
        if value <= 0:
            raise ValueError
    except Exception:
        await message.answer("❌ Valor inválido.")
        return
    await state.update_data(value=value)
    await state.set_state(GiftCreate.quantity)
    await message.answer("🔢 Quantos códigos deseja gerar? (ex: 5)")


@router.message(GiftCreate.quantity)
async def process_gift_qty(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    try:
        qty = int(message.text.strip())
        if qty < 1 or qty > 50:
            raise ValueError
    except Exception:
        await message.answer("❌ Quantidade inválida (1 a 50).")
        return

    data = await state.get_data()
    value = data["value"]
    await state.clear()

    codes = []
    for _ in range(qty):
        code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))
        gift = GiftCard(
            code=code,
            value=value,
            status=GiftCardStatus.ACTIVE,
            created_by_admin_id=db_user.id,
        )
        session.add(gift)
        codes.append(code)

    await session.flush()
    codes_text = "\n".join(f"<code>{c}</code>" for c in codes)
    await message.answer(
        f"✅ <b>{qty}</b> Gift Cards de <b>R$ {value:.2f}</b> criados:\n\n{codes_text}",
        reply_markup=admin_giftcards_kb(),
        parse_mode="HTML"
    )


# ========== PAGAMENTOS ==========

@router.callback_query(F.data == "admin:payments")
async def cb_payments(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    text = "💠 <b>PAGAMENTOS</b>\n\nFiltre por status:"
    await callback.message.edit_text(text, reply_markup=admin_payments_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:payments:"))
async def cb_payments_filter(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    status_map = {
        "approved": PaymentStatus.APPROVED,
        "pending": PaymentStatus.PENDING,
        "expired": PaymentStatus.EXPIRED,
        "cancelled": PaymentStatus.CANCELLED,
    }
    key = callback.data.split(":")[2]
    status = status_map.get(key)
    if not status:
        await callback.answer("Filtro inválido.")
        return

    result = await session.execute(
        select(Payment)
        .where(Payment.status == status)
        .order_by(Payment.created_at.desc())
        .limit(15)
    )
    payments = list(result.scalars().all())

    if not payments:
        text = f"Nenhum pagamento com status <b>{key}</b>."
    else:
        lines = [f"💠 <b>Pagamentos — {key.upper()}</b>\n"]
        for p in payments:
            lines.append(
                f"#{p.id} | R$ {p.amount:.2f} | User {p.user_id} | {p.created_at.strftime('%d/%m %H:%M')}"
            )
        text = "\n".join(lines)

    await callback.message.edit_text(text, reply_markup=admin_back_kb("admin:payments"), parse_mode="HTML")
    await callback.answer()


# ========== AFILIADOS / SETTINGS / BROADCAST (placeholders funcionais) ==========

@router.callback_query(F.data == "admin:affiliates")
async def cb_affiliates_admin(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    text = "🤝 <b>AFILIADOS</b>\n\nGerencie saques e configurações."
    await callback.message.edit_text(text, reply_markup=admin_affiliates_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:settings")
async def cb_settings(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    text = "⚙️ <b>CONFIGURAÇÕES</b>\n\nAjustes gerais da loja."
    await callback.message.edit_text(text, reply_markup=admin_settings_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:broadcast")
async def cb_broadcast(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    text = "📢 <b>BROADCAST</b>\n\nEm breve você poderá disparar mensagens em massa."
    await callback.message.edit_text(text, reply_markup=admin_broadcast_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
@router.callback_query(F.data == "admin:logs")
@router.callback_query(F.data == "admin:orders")
@router.callback_query(F.data == "admin:wallets")
@router.callback_query(F.data == "admin:categories")
@router.callback_query(F.data == "admin:messages")
async def cb_placeholder(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    await callback.answer("Em desenvolvimento — próxima etapa.", show_alert=True)
