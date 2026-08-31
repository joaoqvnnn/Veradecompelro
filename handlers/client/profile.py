from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Order, OrderStatus
from keyboards.client import profile_kb, order_history_kb, main_menu_kb

router = Router(name="profile")


@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery, session: AsyncSession, db_user: User):
    # Estatísticas rápidas
    result = await session.execute(
        select(func.count(Order.id)).where(
            Order.user_id == db_user.id,
            Order.status == OrderStatus.DELIVERED
        )
    )
    total_orders = result.scalar_one() or 0

    text = (
        f"👤 <b>Meu Perfil</b>\n\n"
        f"🔍 Veja os detalhes da sua conta:\n\n"
        f"👤 <b>Informações:</b>\n"
        f"🆔 ID da Carteira: <code>{db_user.id}</code>\n"
        f"💰 Saldo Atual: <b>R$ {db_user.balance:.2f}</b>\n"
        f"📲 WhatsApp: {db_user.whatsapp or 'Não informado'}\n"
        f"📧 E-mail: {db_user.email or 'Não informado'}\n\n"
        f"📊 <b>Suas Movimentações:</b>\n"
        f"🛒 Compras Realizadas: <b>{total_orders}</b>\n"
        f"💰 Total Gasto: <b>R$ {db_user.total_spent:.2f}</b>\n"
        f"💠 Pix Inseridos: <b>R$ {db_user.total_deposited:.2f}</b>\n"
        f"🎁 Bônus Recebidos: <b>R$ {db_user.total_bonus:.2f}</b>"
    )
    await callback.message.edit_text(text, reply_markup=profile_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "history")
@router.callback_query(F.data.startswith("history_page:"))
async def cb_history(callback: CallbackQuery, session: AsyncSession, db_user: User):
    page = 1
    if callback.data.startswith("history_page:"):
        page = int(callback.data.split(":")[1])

    per_page = 1  # Uma compra por vez (como no exemplo da spec)
    offset = (page - 1) * per_page

    result = await session.execute(
        select(Order)
        .where(Order.user_id == db_user.id, Order.status == OrderStatus.DELIVERED)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    orders = list(result.scalars().all())

    count_result = await session.execute(
        select(func.count(Order.id)).where(
            Order.user_id == db_user.id,
            Order.status == OrderStatus.DELIVERED
        )
    )
    total = count_result.scalar_one() or 0
    total_pages = max(1, (total + per_page - 1) // per_page)

    if not orders:
        text = "Você ainda não possui compras no bot."
        await callback.message.edit_text(text, reply_markup=profile_kb(), parse_mode="HTML")
        await callback.answer()
        return

    order = orders[0]
    product_name = order.product.name if order.product else "Produto"

    text = (
        f"🛍 <b>Compra #{order.id}</b>\n\n"
        f"⏰ Data: {order.created_at.strftime('%d/%m/%Y %H:%M')}\n"
        f"📆 Vencimento: {order.expires_at.strftime('%d/%m/%Y') if order.expires_at else 'Sem validade'}\n"
        f"💰 Valor: <b>R$ {order.total_price:.2f}</b>\n"
        f"🎫 ID: <code>{order.uuid}</code>\n"
        f"⚜️ Serviço: <b>{product_name}</b>\n\n"
        f"📦 <b>Entrega:</b>\n"
        f"<code>{order.delivery_content or 'N/A'}</code>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=order_history_kb(page, total_pages, order.id),
        parse_mode="HTML"
    )
    await callback.answer()
