from decimal import Decimal
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Product
from keyboards.client import (
    confirm_purchase_kb,
    insufficient_balance_kb,
    quantity_cancel_kb,
    product_detail_kb,
    main_menu_kb,
)
from services.purchase import PurchaseService

router = Router(name="purchase")


class BuyStates(StatesGroup):
    waiting_quantity = State()


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy_one(callback: CallbackQuery, session: AsyncSession, db_user: User):
    _, product_id, qty = callback.data.split(":")
    product_id = int(product_id)
    quantity = int(qty)

    can, msg, missing = await PurchaseService.check_can_buy(
        session, db_user.id, product_id, quantity
    )

    product = await session.get(Product, product_id)
    if not product:
        await callback.answer("Produto não encontrado.", show_alert=True)
        return

    if can:
        text = (
            f"💳 <b>Confirmar Compra</b>\n\n"
            f"📦 Produto: <b>{product.name}</b>\n"
            f"🔢 Quantidade: <b>{quantity}</b>\n"
            f"💵 Valor: <b>R$ {product.price * quantity:.2f}</b>\n"
            f"💰 Seu saldo: <b>R$ {db_user.balance:.2f}</b>\n"
            f"💳 Saldo após compra: <b>R$ {db_user.balance - (product.price * quantity):.2f}</b>\n\n"
            f"Deseja confirmar?"
        )
        await callback.message.edit_text(
            text,
            reply_markup=confirm_purchase_kb(product_id, quantity),
            parse_mode="HTML"
        )
    else:
        if "Estoque" in msg:
            await callback.answer(msg, show_alert=True)
            return

        text = (
            f"❌ <b>Saldo insuficiente!</b>\n\n"
            f"💰 Seu saldo: <b>R$ {db_user.balance:.2f}</b>\n"
            f"💵 Valor do produto: <b>R$ {product.price * quantity:.2f}</b>\n"
            f"📉 Faltam: <b>R$ {missing:.2f}</b>\n\n"
            f"💡 Deseja gerar um PIX de <b>R$ {missing:.2f}</b> para completar a compra?"
        )
        await callback.message.edit_text(
            text,
            reply_markup=insufficient_balance_kb(product_id, float(missing), quantity),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_buy:"))
async def cb_confirm_buy(callback: CallbackQuery, session: AsyncSession, db_user: User):
    _, product_id, qty = callback.data.split(":")
    product_id = int(product_id)
    quantity = int(qty)

    try:
        order, contents = await PurchaseService.buy_with_balance(
            session, db_user.id, product_id, quantity
        )
    except ValueError as e:
        await callback.answer(str(e), show_alert=True)
        return

    product = await session.get(Product, product_id)
    delivery_text = "\n".join(contents)

    text = (
        f"✅ <b>COMPRA APROVADA!</b>\n\n"
        f"🎬 Produto: <b>{product.name}</b>\n"
        f"💰 Valor: <b>R$ {order.total_price:.2f}</b>\n"
        f"📅 Data: {order.created_at.strftime('%d/%m/%Y %H:%M')}\n"
        f"💳 Pagamento: Saldo\n"
        f"📦 Sua entrega está pronta:\n\n"
        f"<code>{delivery_text}</code>\n\n"
        f"🛡 Guarde esses dados com segurança!"
    )
    await callback.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")
    await callback.answer("✅ Compra realizada com sucesso!")


@router.callback_query(F.data.startswith("buy_multi:"))
async def cb_buy_multi(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    await state.set_state(BuyStates.waiting_quantity)
    await state.update_data(product_id=product_id)

    await callback.message.edit_text(
        "📦 <b>Quantos deseja comprar?</b>\n\n"
        "Digite a quantidade (número).\n"
        "💡 Digite /cancelar a qualquer momento para sair.",
        reply_markup=quantity_cancel_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(BuyStates.waiting_quantity)
async def process_quantity(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if message.text and message.text.lower() in ("/cancelar", "cancelar"):
        await state.clear()
        await message.answer("❌ Compra cancelada.", reply_markup=main_menu_kb())
        return

    try:
        quantity = int(message.text.strip())
        if quantity < 1:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("❌ Digite um número válido maior que zero.")
        return

    data = await state.get_data()
    product_id = data["product_id"]
    await state.clear()

    can, msg, missing = await PurchaseService.check_can_buy(
        session, db_user.id, product_id, quantity
    )
    product = await session.get(Product, product_id)

    if not can:
        if "Estoque" in msg:
            await message.answer(f"❌ {msg}")
            return

        text = (
            f"❌ <b>Saldo insuficiente!</b>\n\n"
            f"💰 Seu saldo: <b>R$ {db_user.balance:.2f}</b>\n"
            f"💵 Valor total: <b>R$ {product.price * quantity:.2f}</b>\n"
            f"📉 Faltam: <b>R$ {missing:.2f}</b>"
        )
        await message.answer(
            text,
            reply_markup=insufficient_balance_kb(product_id, float(missing), quantity),
            parse_mode="HTML"
        )
        return

    text = (
        f"💳 <b>Confirmar Compra</b>\n\n"
        f"📦 Produto: <b>{product.name}</b>\n"
        f"🔢 Quantidade: <b>{quantity}</b>\n"
        f"💵 Valor total: <b>R$ {product.price * quantity:.2f}</b>\n"
        f"💰 Seu saldo: <b>R$ {db_user.balance:.2f}</b>\n"
        f"💳 Saldo após: <b>R$ {db_user.balance - (product.price * quantity):.2f}</b>"
    )
    await message.answer(
        text,
        reply_markup=confirm_purchase_kb(product_id, quantity),
        parse_mode="HTML"
    )
