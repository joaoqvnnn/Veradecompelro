from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Product
from keyboards.admin import admin_stock_kb, admin_back_kb
from services.stock import StockService
from handlers.admin.panel import is_admin

router = Router(name="admin_stock")


class StockSupply(StatesGroup):
    product_id = State()
    contents = State()


@router.callback_query(F.data == "admin:stock")
async def cb_stock(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    text = "📥 <b>ESTOQUE</b>\n\nGerencie o estoque dos produtos."
    await callback.message.edit_text(text, reply_markup=admin_stock_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:stock_supply")
async def cb_stock_supply(callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    result = await session.execute(select(Product).order_by(Product.id))
    products = list(result.scalars().all())

    if not products:
        await callback.answer("Cadastre um produto primeiro.", show_alert=True)
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    for p in products:
        builder.row(
            InlineKeyboardButton(
                text=f"#{p.id} {p.name} ({p.stock_count})",
                callback_data=f"admin:stock_add:{p.id}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:stock"))

    await callback.message.edit_text(
        "📥 Escolha o produto para abastecer:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:stock_add:"))
async def cb_stock_add(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    product_id = int(callback.data.split(":")[2])
    await state.set_state(StockSupply.contents)
    await state.update_data(product_id=product_id)

    await callback.message.edit_text(
        "📥 <b>Abastecer Estoque</b>\n\n"
        "Envie as contas/linhas (uma por linha):\n\n"
        "<code>email1:senha1\n"
        "email2:senha2\n"
        "codigo123</code>\n\n"
        "Ou envie /cancelar para sair.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(StockSupply.contents)
async def process_stock(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return

    if message.text and message.text.lower() in ("/cancelar", "cancelar"):
        await state.clear()
        await message.answer("❌ Cancelado.", reply_markup=admin_stock_kb())
        return

    data = await state.get_data()
    product_id = data["product_id"]
    lines = [line.strip() for line in message.text.strip().splitlines() if line.strip()]

    if not lines:
        await message.answer("❌ Nenhuma linha válida encontrada.")
        return

    try:
        added = await StockService.add_stock(session, product_id, lines)
        await state.clear()
        await message.answer(
            f"✅ <b>{added}</b> unidades adicionadas ao produto #{product_id}!",
            reply_markup=admin_stock_kb(),
            parse_mode="HTML"
        )
    except ValueError as e:
        await message.answer(f"❌ {e}")


@router.callback_query(F.data == "admin:stock_view")
async def cb_stock_view(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    result = await session.execute(select(Product).order_by(Product.stock_count))
    products = list(result.scalars().all())

    lines = ["📦 <b>ESTOQUE ATUAL</b>\n"]
    for p in products:
        emoji = "⚠️" if p.stock_count <= 5 else "✅"
        lines.append(f"{emoji} #{p.id} {p.name}: <b>{p.stock_count}</b>")

    text = "\n".join(lines) if products else "Nenhum produto."
    await callback.message.edit_text(text, reply_markup=admin_back_kb("admin:stock"), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:stock_low")
async def cb_stock_low(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    from config import settings
    result = await session.execute(
        select(Product).where(Product.stock_count <= settings.LOW_STOCK_THRESHOLD)
    )
    products = list(result.scalars().all())

    if not products:
        text = "✅ Nenhum produto com estoque baixo."
    else:
        lines = ["⚠️ <b>ESTOQUE BAIXO</b>\n"]
        for p in products:
            lines.append(f"🔴 #{p.id} {p.name}: <b>{p.stock_count}</b>")
        text = "\n".join(lines)

    await callback.message.edit_text(text, reply_markup=admin_back_kb("admin:stock"), parse_mode="HTML")
    await callback.answer()
