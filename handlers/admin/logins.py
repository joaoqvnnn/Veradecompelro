from decimal import Decimal
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    User, Product, ProductStatus, StockItem, DeliveryType, AdminLog
)
from keyboards.admin import admin_cfg_logins_kb, admin_back_kb
from services.settings_service import SettingsService
from services.stock import StockService
from handlers.admin.panel import is_admin

router = Router(name="admin_logins")


class LoginStates(StatesGroup):
    add_bulk = State()
    remove_one = State()
    remove_platform = State()
    price_one = State()
    price_all = State()


def _parse_login_line(line: str, sep: str) -> dict | None:
    """
    Formato:
    NOME===VALOR===DESCRICAO===EMAIL===SENHA===DURACAO
    Campos mínimos: NOME e pelo menos EMAIL ou conteúdo.
    """
    parts = [p.strip() for p in line.split(sep)]
    if len(parts) < 2:
        return None

    name = parts[0]
    if not name:
        return None

    price = Decimal("0")
    description = ""
    email = ""
    password = ""
    duration = 30

    try:
        if len(parts) >= 2 and parts[1]:
            price = Decimal(parts[1].replace(",", "."))
    except Exception:
        price = Decimal("0")

    if len(parts) >= 3:
        description = parts[2]
    if len(parts) >= 4:
        email = parts[3]
    if len(parts) >= 5:
        password = parts[4]
    if len(parts) >= 6 and parts[5].isdigit():
        duration = int(parts[5])

    if email and password:
        content = f"{email}:{password}"
    elif email:
        content = email
    elif password:
        content = password
    else:
        # linha só com nome + preço + desc → sem unidade de estoque
        content = ""

    return {
        "name": name,
        "price": price,
        "description": description,
        "content": content,
        "duration": duration,
    }


async def _get_or_create_product(
    session: AsyncSession,
    name: str,
    price: Decimal,
    description: str,
    duration: int,
) -> Product:
    result = await session.execute(
        select(Product).where(func.lower(Product.name) == name.lower())
    )
    product = result.scalar_one_or_none()
    if product:
        if price > 0:
            product.price = price
        if description:
            product.description = description
        if duration:
            product.warranty_days = duration
            product.validity_days = duration
        return product

    product = Product(
        name=name,
        emoji="🔥",
        price=price if price > 0 else Decimal("1.00"),
        description=description or None,
        warranty_days=duration or 30,
        validity_days=duration or 30,
        delivery_type="login_password",
        status=ProductStatus.ACTIVE,
        stock_count=0,
    )
    session.add(product)
    await session.flush()
    return product


@router.callback_query(F.data == "admin:cfg_logins")
async def cb_cfg_logins(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    count = (
        await session.execute(
            select(func.count(StockItem.id)).where(StockItem.is_sold.is_(False))
        )
    ).scalar_one() or 0

    sep = await SettingsService.get(session, "separator") or "==="
    text = (
        f"<b>CONFIGURAR LOGINS</b>\n\n"
        f"LOGINS NO ESTOQUE: <b>{count}</b>\n\n"
        f"Formato para adicionar (separador <code>{sep}</code>):\n"
        f"<code>NOME{sep}VALOR{sep}DESCRICAO{sep}EMAIL{sep}SENHA{sep}DURACAO</code>\n\n"
        f"Ex:\n"
        f"<code>NETFLIX{sep}6.00{sep}Tela padrão{sep}email@x.com{sep}senha123{sep}30</code>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_cfg_logins_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:login_add")
@router.callback_query(F.data == "admin:stock_supply")
async def cb_login_add(callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return

    sep = await SettingsService.get(session, "separator") or "==="
    await state.set_state(LoginStates.add_bulk)
    await callback.message.edit_text(
        f"➕ <b>ADICIONAR LOGIN</b>\n\n"
        f"Envie no formato (uma linha por login):\n"
        f"<code>NOME{sep}VALOR{sep}DESCRICAO{sep}EMAIL{sep}SENHA{sep}DURACAO</code>\n\n"
        f"Ex:\n"
        f"<code>NETFLIX{sep}6.00{sep}Tela padrão{sep}a@x.com{sep}senha{sep}30</code>\n\n"
        f"/cancelar para sair.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(LoginStates.add_bulk)
async def process_login_add(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    if message.text and message.text.lower() in ("/cancelar", "cancelar"):
        await state.clear()
        await message.answer("❌ Cancelado.")
        return

    sep = await SettingsService.get(session, "separator") or "==="
    lines = [ln.strip() for ln in (message.text or "").splitlines() if ln.strip()]
    added = 0
    created_products = 0

    for line in lines:
        parsed = _parse_login_line(line, sep)
        if not parsed:
            continue
        product = await _get_or_create_product(
            session,
            parsed["name"],
            parsed["price"],
            parsed["description"],
            parsed["duration"],
        )
        if parsed["content"]:
            session.add(
                StockItem(product_id=product.id, content=parsed["content"])
            )
            product.stock_count = (product.stock_count or 0) + 1
            if product.status == ProductStatus.OUT_OF_STOCK:
                product.status = ProductStatus.ACTIVE
            added += 1
        else:
            created_products += 1

    session.add(AdminLog(
        admin_id=db_user.id,
        action="stock_add_bulk",
        target_type="stock",
        details={"added": added, "lines": len(lines)},
    ))
    await state.clear()

    # Notifica alertas se adicionou estoque
    # (notifica por produto único se só um nome; senão skip detalhado)
    await message.answer(
        f"✅ Processado.\n"
        f"📦 Unidades de estoque: <b>{added}</b>\n"
        f"🆕 Produtos só cadastro: <b>{created_products}</b>",
        parse_mode="HTML",
        reply_markup=admin_cfg_logins_kb(),
    )


@router.callback_query(F.data == "admin:login_remove")
async def cb_login_remove(callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    sep = await SettingsService.get(session, "separator") or "==="
    await state.set_state(LoginStates.remove_one)
    await callback.message.edit_text(
        f"➖ <b>REMOVER LOGIN</b>\n\n"
        f"Envie: <code>SERVICO{sep}EMAIL</code>\n"
        f"Ex: <code>NETFLIX{sep}email@x.com</code>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(LoginStates.remove_one)
async def process_login_remove(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    sep = await SettingsService.get(session, "separator") or "==="
    parts = [p.strip() for p in (message.text or "").split(sep)]
    await state.clear()
    if len(parts) < 2:
        await message.answer(f"❌ Formato: SERVICO{sep}EMAIL")
        return

    name, email = parts[0], parts[1]
    result = await session.execute(
        select(Product).where(func.lower(Product.name) == name.lower())
    )
    product = result.scalar_one_or_none()
    if not product:
        await message.answer("❌ Serviço não encontrado.")
        return

    result = await session.execute(
        select(StockItem).where(
            StockItem.product_id == product.id,
            StockItem.is_sold.is_(False),
            StockItem.content.ilike(f"%{email}%"),
        )
    )
    items = list(result.scalars().all())
    for item in items:
        await session.delete(item)
    product.stock_count = max(0, (product.stock_count or 0) - len(items))

    session.add(AdminLog(
        admin_id=db_user.id,
        action="login_remove",
        target_type="product",
        target_id=str(product.id),
        details={"email": email, "removed": len(items)},
    ))
    await message.answer(
        f"✅ Removido(s): <b>{len(items)}</b> de {product.name}",
        parse_mode="HTML",
        reply_markup=admin_cfg_logins_kb(),
    )


@router.callback_query(F.data == "admin:login_remove_platform")
async def cb_remove_platform(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(LoginStates.remove_platform)
    await callback.message.edit_text(
        "🗑 Envie o <b>nome da plataforma/serviço</b> para remover TODO o estoque não vendido:"
    )
    await callback.answer()


@router.message(LoginStates.remove_platform)
async def process_remove_platform(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    name = (message.text or "").strip()
    await state.clear()
    result = await session.execute(
        select(Product).where(func.lower(Product.name) == name.lower())
    )
    product = result.scalar_one_or_none()
    if not product:
        await message.answer("❌ Plataforma não encontrada.")
        return

    result = await session.execute(
        select(StockItem).where(
            StockItem.product_id == product.id,
            StockItem.is_sold.is_(False),
        )
    )
    items = list(result.scalars().all())
    for item in items:
        await session.delete(item)
    product.stock_count = 0

    session.add(AdminLog(
        admin_id=db_user.id,
        action="login_remove_platform",
        target_type="product",
        target_id=str(product.id),
        details={"removed": len(items)},
    ))
    await message.answer(
        f"✅ Removidos <b>{len(items)}</b> logins de {product.name}.",
        parse_mode="HTML",
        reply_markup=admin_cfg_logins_kb(),
    )


@router.callback_query(F.data == "admin:stock_clear")
async def cb_stock_clear(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    result = await session.execute(
        select(StockItem).where(StockItem.is_sold.is_(False))
    )
    items = list(result.scalars().all())
    for item in items:
        await session.delete(item)

    result = await session.execute(select(Product))
    for p in result.scalars().all():
        p.stock_count = 0

    session.add(AdminLog(
        admin_id=db_user.id,
        action="stock_clear_all",
        details={"removed": len(items)},
    ))
    await callback.message.edit_text(
        f"⚠️ Estoque zerado. Removidos: <b>{len(items)}</b>",
        reply_markup=admin_cfg_logins_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:login_price")
async def cb_login_price(callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    sep = await SettingsService.get(session, "separator") or "==="
    await state.set_state(LoginStates.price_one)
    await callback.message.edit_text(
        f"💰 Envie: <code>SERVICO{sep}VALOR</code>\n"
        f"Ex: <code>NETFLIX{sep}6.00</code>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(LoginStates.price_one)
async def process_price_one(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    sep = await SettingsService.get(session, "separator") or "==="
    parts = [p.strip() for p in (message.text or "").split(sep)]
    await state.clear()
    if len(parts) < 2:
        await message.answer(f"❌ Use: SERVICO{sep}VALOR")
        return
    name, price_s = parts[0], parts[1]
    try:
        price = Decimal(price_s.replace(",", "."))
    except Exception:
        await message.answer("❌ Valor inválido.")
        return

    result = await session.execute(
        select(Product).where(func.lower(Product.name) == name.lower())
    )
    product = result.scalar_one_or_none()
    if not product:
        await message.answer("❌ Serviço não encontrado.")
        return
    product.price = price
    session.add(AdminLog(
        admin_id=db_user.id,
        action="product_price",
        target_type="product",
        target_id=str(product.id),
        details={"price": str(price)},
    ))
    await message.answer(
        f"✅ {product.name} agora custa <b>R$ {price:.2f}</b>",
        parse_mode="HTML",
        reply_markup=admin_cfg_logins_kb(),
    )


@router.callback_query(F.data == "admin:login_price_all")
async def cb_price_all(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(LoginStates.price_all)
    await callback.message.edit_text("🔥 Envie o novo valor para TODOS os produtos (ex: 5.00):")
    await callback.answer()


@router.message(LoginStates.price_all)
async def process_price_all(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    try:
        price = Decimal((message.text or "").strip().replace(",", "."))
    except Exception:
        await message.answer("❌ Valor inválido.")
        return
    await state.clear()
    result = await session.execute(select(Product))
    products = list(result.scalars().all())
    for p in products:
        p.price = price
    session.add(AdminLog(
        admin_id=db_user.id,
        action="product_price_all",
        details={"price": str(price), "count": len(products)},
    ))
    await message.answer(
        f"✅ {len(products)} produtos atualizados para <b>R$ {price:.2f}</b>",
        parse_mode="HTML",
        reply_markup=admin_cfg_logins_kb(),
    )


@router.callback_query(F.data == "admin:stock_view")
async def cb_stock_detailed(callback: CallbackQuery, session: AsyncSession, db_user: User):
    """Reusa visão de estoque."""
    await cb_stock_view(callback, session, db_user)
