from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Category, Product, ProductStatus
from keyboards.client import catalog_categories_kb, products_list_kb, product_detail_kb

router = Router(name="catalog")


@router.callback_query(F.data == "catalog")
async def cb_catalog(callback: CallbackQuery, session: AsyncSession, db_user: User):
    result = await session.execute(
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.position, Category.id)
    )
    categories = list(result.scalars().all())

    text = (
        f"📱 <b>Larizinha Store | Catálogo de Serviços</b>\n\n"
        f"💰 Saldo da Carteira: <b>R$ {db_user.balance:.2f}</b>\n\n"
        f"⬇️ Selecione uma categoria abaixo:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=catalog_categories_kb(categories),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("category:"))
async def cb_category(callback: CallbackQuery, session: AsyncSession, db_user: User):
    category_id = int(callback.data.split(":")[1])

    result = await session.execute(
        select(Product)
        .where(
            Product.category_id == category_id,
            Product.status == ProductStatus.ACTIVE,
        )
        .order_by(Product.position, Product.id)
    )
    products = list(result.scalars().all())

    cat = await session.get(Category, category_id)
    cat_name = f"{cat.emoji} {cat.name}" if cat else "Categoria"

    if not products:
        text = f"<b>{cat_name}</b>\n\n❌ Nenhum produto disponível no momento."
        from keyboards.client import back_kb
        await callback.message.edit_text(text, reply_markup=back_kb("catalog"), parse_mode="HTML")
    else:
        text = (
            f"<b>{cat_name}</b>\n\n"
            f"💰 Seu saldo: <b>R$ {db_user.balance:.2f}</b>\n\n"
            f"Escolha um produto:"
        )
        await callback.message.edit_text(
            text,
            reply_markup=products_list_kb(products, category_id),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("product:"))
async def cb_product(callback: CallbackQuery, session: AsyncSession, db_user: User):
    product_id = int(callback.data.split(":")[1])
    product = await session.get(Product, product_id)

    if not product or product.status != ProductStatus.ACTIVE:
        await callback.answer("Produto indisponível.", show_alert=True)
        return

    # Incrementa visualizações
    product.view_count += 1

    has_stock = product.stock_count > 0
    status_emoji = "🟢 DISPONÍVEL AGORA" if has_stock else "🔴 ESGOTADO"

    text = (
        f"🔥 <b>OPORTUNIDADE EXCLUSIVA</b> 🔥\n\n"
        f"{product.emoji} <b>{product.name}</b>\n"
        f"{status_emoji}\n\n"
        f"├ 💵 Preço: <b>R$ {product.price:.2f}</b>\n"
        f"├ 💰 Seu Saldo: <b>R$ {db_user.balance:.2f}</b>\n"
        f"└ 📦 Estoque: <b>{product.stock_count}</b>\n\n"
        f"📝 <b>Descrição:</b>\n"
        f"{product.description or 'Sem descrição.'}\n\n"
        f"📊 <b>Estatísticas:</b>\n"
        f"⚡️ Já foram vendidas <b>{product.sold_count}</b> unidades!\n"
        f"👀 Visualizações: <b>{product.view_count}</b>\n\n"
        f"🛡 Garantia: <b>{product.warranty_days} dias</b>\n"
        f"✅ Compra segura.\n"
        f"Ao adquirir, concorda com /termos"
    )

    await callback.message.edit_text(
        text,
        reply_markup=product_detail_kb(product_id, has_stock),
        parse_mode="HTML"
    )
    await callback.answer()
