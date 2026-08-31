from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Product, ProductStatus, ProductAlert
from keyboards.client import alerts_kb, back_kb, product_detail_kb
from services.alerts import AlertService

router = Router(name="alerts")


@router.callback_query(F.data == "alerts")
async def cb_alerts(callback: CallbackQuery, session: AsyncSession, db_user: User):
    """Lista produtos com status do alerta do usuário."""

    # Busca produtos ativos
    result = await session.execute(
        select(Product)
        .where(Product.status == ProductStatus.ACTIVE)
        .order_by(Product.name)
        .limit(30)
    )
    products = list(result.scalars().all())

    # Alertas do usuário
    user_alerts = await AlertService.get_user_alerts(session, db_user.id)
    active_map = {a.product_id: a.is_active for a in user_alerts}

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()

    if not products:
        text = (
            "📢 <b>Sistema de Alertas</b>\n\n"
            "Nenhum produto disponível no momento."
        )
        builder.row(InlineKeyboardButton(text="⏮️ Voltar", callback_data="main_menu"))
    else:
        text = (
            "📢 <b>Sistema de Alertas</b>\n\n"
            "Seja notificado quando seu serviço favorito for abastecido.\n\n"
            "✅ = alerta ativo | ❌ = desativado\n"
            "Toque para ativar/desativar:"
        )
        for p in products:
            is_on = active_map.get(p.id, False)
            status = "✅" if is_on else "❌"
            stock_info = f"({p.stock_count})" if p.stock_count > 0 else "(esgotado)"
            builder.row(
                InlineKeyboardButton(
                    text=f"{status} {p.emoji} {p.name} {stock_info}",
                    callback_data=f"alert_toggle:{p.id}"
                )
            )
        builder.row(InlineKeyboardButton(text="⏮️ Voltar", callback_data="main_menu"))

    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("alert_toggle:"))
async def cb_alert_toggle(callback: CallbackQuery, session: AsyncSession, db_user: User):
    product_id = int(callback.data.split(":")[1])
    product = await session.get(Product, product_id)

    if not product:
        await callback.answer("Produto não encontrado.", show_alert=True)
        return

    is_active = await AlertService.toggle_alert(session, db_user.id, product_id)

    if is_active:
        await callback.answer(f"✅ Alerta ativado para {product.name}", show_alert=False)
    else:
        await callback.answer(f"❌ Alerta desativado para {product.name}", show_alert=False)

    # Atualiza a lista
    await cb_alerts(callback, session, db_user)
