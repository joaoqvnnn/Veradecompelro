from decimal import Decimal
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from keyboards.client import recharge_kb, pix_created_kb, main_menu_kb, back_kb
from services.payment import PaymentService
from config import settings

router = Router(name="wallet")
payment_service = PaymentService()


class PixStates(StatesGroup):
    waiting_custom_value = State()


@router.callback_query(F.data == "recharge")
async def cb_recharge(callback: CallbackQuery, db_user: User):
    text = (
        f"💰 <b>Recarregar Saldo</b>\n\n"
        f"💰 Saldo atual: <b>R$ {db_user.balance:.2f}</b>\n\n"
        f"Escolha um valor ou digite um personalizado:"
    )
    await callback.message.edit_text(text, reply_markup=recharge_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("pix:"))
async def cb_pix_value(callback: CallbackQuery, session: AsyncSession, db_user: User):
    amount = Decimal(callback.data.split(":")[1])
    await _create_pix(callback, session, db_user, amount)


@router.callback_query(F.data == "pix_custom")
async def cb_pix_custom(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PixStates.waiting_custom_value)
    await callback.message.edit_text(
        f"✏️ Digite o valor que deseja recarregar:\n\n"
        f"Mínimo: R$ {settings.PIX_MIN_VALUE:.2f}\n"
        f"Máximo: R$ {settings.PIX_MAX_VALUE:.2f}\n\n"
        f"Exemplo: 15.50",
        reply_markup=back_kb("recharge"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(PixStates.waiting_custom_value)
async def process_custom_pix(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    try:
        amount = Decimal(message.text.strip().replace(",", "."))
    except Exception:
        await message.answer("❌ Valor inválido. Digite um número (ex: 20 ou 15.50)")
        return

    await state.clear()
    # Cria uma mensagem nova pois veio de texto
    fake_callback = type("obj", (object,), {
        "message": message,
        "answer": message.answer,
        "from_user": message.from_user,
    })()
    try:
        payment = await payment_service.create_pix(session, db_user.id, amount)
    except ValueError as e:
        await message.answer(f"❌ {e}")
        return
    except Exception as e:
        await message.answer("❌ Erro ao gerar PIX. Tente novamente.")
        return

    text = _format_pix_message(payment, db_user)
    await message.answer(text, reply_markup=pix_created_kb(payment.uuid), parse_mode="HTML")


async def _create_pix(callback: CallbackQuery, session: AsyncSession, db_user: User, amount: Decimal):
    try:
        payment = await payment_service.create_pix(session, db_user.id, amount)
    except ValueError as e:
        await callback.answer(str(e), show_alert=True)
        return
    except Exception:
        await callback.answer("Erro ao gerar PIX. Tente novamente.", show_alert=True)
        return

    text = _format_pix_message(payment, db_user)
    await callback.message.edit_text(
        text,
        reply_markup=pix_created_kb(payment.uuid),
        parse_mode="HTML"
    )
    await callback.answer()


def _format_pix_message(payment, db_user: User) -> str:
    return (
        f"💰 <b>Comprar Saldo com Pix Automático</b>\n\n"
        f"⏱️ Expira em: <b>{settings.PIX_EXPIRATION_MINUTES} minutos</b>\n"
        f"💵 Valor: <b>R$ {payment.amount:.2f}</b>\n"
        f"🎁 Bônus: <b>R$ {payment.bonus_amount:.2f}</b>\n"
        f"✨ ID da Recarga: <code>{payment.uuid[:8]}...</code>\n\n"
        f"💎 <b>Pix Copia e Cola:</b>\n"
        f"<code>{payment.pix_copy_paste or 'Gerando...'}</code>\n\n"
        f"📊 <b>Dados:</b>\n"
        f"💰 Saldo Atual: <b>R$ {db_user.balance:.2f}</b>\n"
        f"💸 Saldo após pagamento: <b>R$ {db_user.balance + payment.total_credited:.2f}</b>\n\n"
        f"⚠️ O saldo será creditado <b>automaticamente</b> após a confirmação do pagamento."
    )


@router.callback_query(F.data.startswith("check_pix:"))
async def cb_check_pix(callback: CallbackQuery, session: AsyncSession, db_user: User):
    from database.models import Payment, PaymentStatus
    from sqlalchemy import select

    uuid = callback.data.split(":")[1]
    result = await session.execute(select(Payment).where(Payment.uuid == uuid))
    payment = result.scalar_one_or_none()

    if not payment:
        await callback.answer("Pagamento não encontrado.", show_alert=True)
        return

    if payment.status == PaymentStatus.APPROVED:
        await callback.message.edit_text(
            f"✅ <b>PAGAMENTO APROVADO!</b>\n\n"
            f"💰 Valor: R$ {payment.amount:.2f}\n"
            f"🎁 Bônus: R$ {payment.bonus_amount:.2f}\n"
            f"💳 Saldo atual: <b>R$ {db_user.balance:.2f}</b>",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
        await callback.answer("✅ Pagamento confirmado!")
    elif payment.status == PaymentStatus.EXPIRED:
        await callback.answer("⌛️ Este PIX já expirou.", show_alert=True)
    else:
        await callback.answer("⏳ Ainda não recebemos o pagamento. Aguarde alguns segundos e tente novamente.", show_alert=True)
