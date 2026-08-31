from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from database.models import User, Product, ProductStatus, Category, DeliveryType
from keyboards.admin import admin_products_kb, admin_product_actions_kb, admin_back_kb
from handlers.admin.panel import is_admin

router = Router(name="admin_products")


class ProductCreate(StatesGroup):
    name = State()
    price = State()
    description = State()
    category = State()


@router.callback_query(F.data == "admin:products")
async def cb_products(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    text = "📦 <b>PRODUTOS</b>\n\nGerencie o catálogo da loja."
    await callback.message.edit_text(text, reply_markup=admin_products_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:product_list")
async def cb_product_list(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    result = await session.execute(
        select(Product).order_by(Product.id.desc()).limit(20)
    )
    products = list(result.scalars().all())

    if not products:
        text = "Nenhum produto cadastrado ainda."
        await callback.message.edit_text(text, reply_markup=admin_products_kb(), parse_mode="HTML")
        await callback.answer()
        return

    lines = ["📦 <b>LISTA DE PRODUTOS</b>\n"]
    for p in products:
        status = "🟢" if p.status == ProductStatus.ACTIVE else "🔴"
        lines.append(
            f"{status} <b>#{p.id}</b> {p.emoji} {p.name}\n"
            f"   💰 R$ {p.price:.2f} | 📦 {p.stock_count} | 🛒 {p.sold_count}"
        )

    text = "\n".join(lines)
    # Teclado simples com os IDs
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    for p in products[:10]:
        builder.row(
            InlineKeyboardButton(
                text=f"#{p.id} {p.name[:20]}",
                callback_data=f"admin:product_view:{p.id}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:products"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:product_view:"))
async def cb_product_view(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    product_id = int(callback.data.split(":")[2])
    product = await session.get(Product, product_id)
    if not product:
        await callback.answer("Produto não encontrado.", show_alert=True)
        return

    text = (
        f"📦 <b>PRODUTO #{product.id}</b>\n\n"
        f"{product.emoji} <b>{product.name}</b>\n"
        f"💰 Preço: <b>R$ {product.price:.2f}</b>\n"
        f"📦 Estoque: <b>{product.stock_count}</b>\n"
        f"🛒 Vendidos: <b>{product.sold_count}</b>\n"
        f"🛡 Garantia: {product.warranty_days} dias\n"
        f"📊 Status: {product.status.value}\n"
        f"📝 {product.description or 'Sem descrição'}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_product_actions_kb(product.id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:product_create")
async def cb_product_create(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    await state.set_state(ProductCreate.name)
    await callback.message.edit_text(
        "➕ <b>Novo Produto</b>\n\nEnvie o <b>nome</b> do produto:",
        reply_markup=admin_back_kb("admin:products"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(ProductCreate.name)
async def process_name(message: Message, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(ProductCreate.price)
    await message.answer("💰 Agora envie o <b>preço</b> (ex: 6.00 ou 6):", parse_mode="HTML")


@router.message(ProductCreate.price)
async def process_price(message: Message, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    try:
        price = Decimal(message.text.strip().replace(",", "."))
        if price <= 0:
            raise ValueError
    except Exception:
        await message.answer("❌ Preço inválido. Tente novamente.")
        return

    await state.update_data(price=price)
    await state.set_state(ProductCreate.description)
    await message.answer("📝 Envie a <b>descrição</b> do produto (ou envie - para pular):", parse_mode="HTML")


@router.message(ProductCreate.description)
async def process_description(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return

    data = await state.get_data()
    description = None if message.text.strip() == "-" else message.text.strip()

    product = Product(
        name=data["name"],
        price=data["price"],
        description=description,
        emoji="🔥",
        status=ProductStatus.ACTIVE,
        delivery_type=DeliveryType.LOGIN_PASSWORD,
    )
    session.add(product)
    await session.flush()
    await state.clear()

    await message.answer(
        f"✅ Produto criado com sucesso!\n\n"
        f"🆔 ID: <b>{product.id}</b>\n"
        f"📦 {product.name}\n"
        f"💰 R$ {product.price:.2f}\n\n"
        f"Agora abasteça o estoque pelo menu de Estoque.",
        reply_markup=admin_products_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:product_pause:"))
async def cb_product_pause(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    product_id = int(callback.data.split(":")[2])
    product = await session.get(Product, product_id)
    if not product:
        await callback.answer("Não encontrado.", show_alert=True)
        return

    if product.status == ProductStatus.ACTIVE:
        product.status = ProductStatus.PAUSED
        await callback.answer("⏸ Produto pausado")
    else:
        product.status = ProductStatus.ACTIVE
        await callback.answer("▶️ Produto reativado")

    await cb_product_view(callback, session, db_user)
