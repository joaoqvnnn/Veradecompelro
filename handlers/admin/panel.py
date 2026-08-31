from datetime import datetime, timedelta, timezone
from decimal import Decimal

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Order, Payment, PaymentStatus, OrderStatus, Product
from keyboards.admin import admin_main_kb, admin_maintenance_kb, admin_back_kb
from config import settings

router = Router(name="admin_panel")


def is_admin(user: User) -> bool:
    return user.is_admin or user.id in settings.ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message, db_user: User):
    if not is_admin(db_user):
        await message.answer("🚫 Acesso negado.")
        return

    text = (
        f"👑 <b>PAINEL ADMINISTRATIVO</b>\n\n"
        f"Olá, <b>{db_user.first_name or 'Admin'}</b>!\n"
        f"Escolha uma opção abaixo:"
    )
    await message.answer(text, reply_markup=admin_main_kb(), parse_mode="HTML")


@router.callback_query(F.data == "admin:main")
async def cb_admin_main(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    text = (
        f"👑 <b>PAINEL ADMINISTRATIVO</b>\n\n"
        f"Escolha uma opção:"
    )
    await callback.message.edit_text(text, reply_markup=admin_main_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:dashboard")
async def cb_dashboard(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Usuários
    total_users = (await session.execute(select(func.count(User.id)))).scalar_one() or 0
    active_today = (await session.execute(
        select(func.count(User.id)).where(User.last_activity >= today_start)
    )).scalar_one() or 0

    # Vendas hoje
    sales_today = (await session.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.total_price), 0))
        .where(Order.status == OrderStatus.DELIVERED, Order.created_at >= today_start)
    )).one()
    sales_count, sales_amount = sales_today[0] or 0, sales_today[1] or Decimal("0")

    # PIX hoje
    pix_today = (await session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.status == PaymentStatus.APPROVED, Payment.paid_at >= today_start)
    )).scalar_one() or Decimal("0")

    # Pagamentos pendentes / expirados
    pending = (await session.execute(
        select(func.count(Payment.id)).where(Payment.status == PaymentStatus.PENDING)
    )).scalar_one() or 0
    expired = (await session.execute(
        select(func.count(Payment.id)).where(Payment.status == PaymentStatus.EXPIRED)
    )).scalar_one() or 0

    text = (
        f"📊 <b>DASHBOARD</b>\n\n"
        f"👥 Usuários: <b>{total_users}</b>\n"
        f"🟢 Ativos hoje: <b>{active_today}</b>\n\n"
        f"🛒 Vendas hoje: <b>{sales_count}</b>\n"
        f"💰 Faturamento hoje: <b>R$ {sales_amount:.2f}</b>\n"
        f"💠 Pix hoje: <b>R$ {pix_today:.2f}</b>\n\n"
        f"⚠️ Pagamentos pendentes: <b>{pending}</b>\n"
        f"❌ Pagamentos expirados: <b>{expired}</b>"
    )
    await callback.message.edit_text(text, reply_markup=admin_back_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:maintenance")
async def cb_maintenance(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    status = "🔧 ATIVO" if settings.MAINTENANCE_MODE else "✅ Desativado"
    text = (
        f"🚧 <b>MODO MANUTENÇÃO</b>\n\n"
        f"Status atual: <b>{status}</b>\n\n"
        f"Quando ativo, apenas administradores conseguem usar o bot."
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_maintenance_kb(settings.MAINTENANCE_MODE),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:maintenance_on")
async def cb_maintenance_on(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    # Nota: para persistir de verdade, salve no banco (SystemSetting).
    # Aqui alteramos em memória para o processo atual.
    settings.MAINTENANCE_MODE = True
    await callback.answer("🔧 Manutenção ATIVADA", show_alert=True)
    await cb_maintenance(callback, db_user)


@router.callback_query(F.data == "admin:maintenance_off")
async def cb_maintenance_off(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    settings.MAINTENANCE_MODE = False
    await callback.answer("✅ Manutenção DESATIVADA", show_alert=True)
    await cb_maintenance(callback, db_user)
