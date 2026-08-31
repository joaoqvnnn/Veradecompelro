from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Category, Product, Order, ProductAlert


# =========================================================
# MENU PRINCIPAL
# =========================================================

def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🛍 Comprar Produtos", callback_data="catalog")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Recarregar Saldo", callback_data="recharge"),
        InlineKeyboardButton(text="👤 Meu Perfil", callback_data="profile"),
    )
    builder.row(
        InlineKeyboardButton(text="🤝 Afiliados", callback_data="affiliates"),
        InlineKeyboardButton(text="🏆 Ranking", callback_data="ranking"),
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Gift Card", callback_data="gift_card"),
        InlineKeyboardButton(text="🔎 Pesquisar", callback_data="search"),
    )
    builder.row(
        InlineKeyboardButton(text="📢 Alertas", callback_data="alerts"),
        InlineKeyboardButton(text="🎧 Atendimento", callback_data="support"),
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ Sobre o Bot", callback_data="about")
    )

    return builder.as_markup()


# =========================================================
# CATÁLOGO / CATEGORIAS
# =========================================================

def catalog_categories_kb(categories: List[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for cat in categories:
        if cat.is_active:
            text = f"{cat.emoji} {cat.name}"
            builder.row(
                InlineKeyboardButton(text=text, callback_data=f"category:{cat.id}")
            )

    builder.row(
        InlineKeyboardButton(text="⏮️ Voltar", callback_data="main_menu")
    )
    return builder.as_markup()


def products_list_kb(products: List[Product], category_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for product in products:
        if product.status.value == "active":
            stock_emoji = "🟢" if product.stock_count > 0 else "🔴"
            text = f"{product.emoji} {product.name} — R$ {product.price:.2f} {stock_emoji}"
            builder.row(
                InlineKeyboardButton(text=text, callback_data=f"product:{product.id}")
            )

    builder.row(
        InlineKeyboardButton(text="⏮️ Voltar", callback_data="catalog")
    )
    return builder.as_markup()


# =========================================================
# PÁGINA DO PRODUTO
# =========================================================

def product_detail_kb(product_id: int, has_stock: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if has_stock:
        builder.row(
            InlineKeyboardButton(text="💳 Comprar", callback_data=f"buy:{product_id}:1")
        )
        builder.row(
            InlineKeyboardButton(text="🛒 Comprar mais de um", callback_data=f"buy_multi:{product_id}")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="❌ Sem estoque", callback_data="noop")
        )
        builder.row(
            InlineKeyboardButton(text="📢 Ativar Alerta", callback_data=f"alert_toggle:{product_id}")
        )

    builder.row(
        InlineKeyboardButton(text="⏮️ Voltar", callback_data="catalog")
    )
    return builder.as_markup()


def confirm_purchase_kb(product_id: int, quantity: int = 1) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Confirmar Compra",
            callback_data=f"confirm_buy:{product_id}:{quantity}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="❌ Cancelar", callback_data=f"product:{product_id}")
    )
    return builder.as_markup()


def insufficient_balance_kb(product_id: int, missing_amount: float, quantity: int = 1) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text=f"💠 Gerar PIX R$ {missing_amount:.2f}",
            callback_data=f"pix_for_product:{product_id}:{quantity}:{missing_amount:.2f}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="❌ Cancelar", callback_data=f"product:{product_id}")
    )
    return builder.as_markup()


def quantity_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Cancelar", callback_data="catalog")
    )
    return builder.as_markup()


# =========================================================
# RECARGA / PIX
# =========================================================

def recharge_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    values = [5, 10, 20, 50, 100, 200]
    row = []
    for value in values:
        row.append(
            InlineKeyboardButton(text=f"R$ {value}", callback_data=f"pix:{value}")
        )
        if len(row) == 3:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)

    builder.row(
        InlineKeyboardButton(text="✏️ Outro valor", callback_data="pix_custom")
    )
    builder.row(
        InlineKeyboardButton(text="⏮️ Voltar", callback_data="main_menu")
    )
    return builder.as_markup()


def pix_created_kb(payment_uuid: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Verificar Pagamento", callback_data=f"check_pix:{payment_uuid}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Cancelar", callback_data="recharge")
    )
    return builder.as_markup()


# =========================================================
# PERFIL
# =========================================================

def profile_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🧾 Histórico de Compras", callback_data="history")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Alterar Dados", callback_data="edit_profile"),
        InlineKeyboardButton(text="🎁 Gift Card", callback_data="gift_card"),
    )
    builder.row(
        InlineKeyboardButton(text="⏮️ Voltar", callback_data="main_menu")
    )
    return builder.as_markup()


def order_history_kb(
    current_page: int,
    total_pages: int,
    order_id: Optional[int] = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Navegação
    nav = []
    if current_page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"history_page:{current_page-1}"))
    nav.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"history_page:{current_page+1}"))
    if nav:
        builder.row(*nav)

    if order_id:
        builder.row(
            InlineKeyboardButton(text="📧 E-mail", callback_data=f"order_email:{order_id}"),
            InlineKeyboardButton(text="📲 WhatsApp", callback_data=f"order_whatsapp:{order_id}"),
        )
        builder.row(
            InlineKeyboardButton(text="📄 PDF", callback_data=f"order_pdf:{order_id}")
        )

    builder.row(
        InlineKeyboardButton(text="⏮️ Voltar", callback_data="profile")
    )
    return builder.as_markup()


# =========================================================
# AFILIADOS
# =========================================================

def affiliates_kb(can_withdraw: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if can_withdraw:
        builder.row(
            InlineKeyboardButton(text="💸 Solicitar Saque", callback_data="affiliate_withdraw")
        )

    builder.row(
        InlineKeyboardButton(text="📊 Histórico de Saques", callback_data="affiliate_history")
    )
    builder.row(
        InlineKeyboardButton(text="🔗 Copiar Link", callback_data="affiliate_copy_link")
    )
    builder.row(
        InlineKeyboardButton(text="⏮️ Voltar", callback_data="main_menu")
    )
    return builder.as_markup()


def withdraw_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Cancelar", callback_data="affiliates")
    )
    return builder.as_markup()


# =========================================================
# RANKING
# =========================================================

def ranking_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📅 Hoje", callback_data="ranking:today"),
        InlineKeyboardButton(text="📆 Semana", callback_data="ranking:week"),
    )
    builder.row(
        InlineKeyboardButton(text="🗓 Mês", callback_data="ranking:month"),
        InlineKeyboardButton(text="🏆 Geral", callback_data="ranking:all"),
    )
    builder.row(
        InlineKeyboardButton(text="⏮️ Voltar", callback_data="main_menu")
    )
    return builder.as_markup()


# =========================================================
# ALERTAS
# =========================================================

def alerts_kb(alerts: List[ProductAlert], products_map: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for alert in alerts:
        product = products_map.get(alert.product_id)
        if not product:
            continue
        status = "✅" if alert.is_active else "❌"
        text = f"{status} {product.emoji} {product.name}"
        builder.row(
            InlineKeyboardButton(text=text, callback_data=f"alert_toggle:{product.id}")
        )

    builder.row(
        InlineKeyboardButton(text="⏮️ Voltar", callback_data="main_menu")
    )
    return builder.as_markup()


# =========================================================
# GIFT CARD
# =========================================================

def gift_card_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Cancelar", callback_data="main_menu")
    )
    return builder.as_markup()


# =========================================================
# UTILITÁRIOS
# =========================================================

def back_kb(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏮️ Voltar", callback_data=callback_data)
    )
    return builder.as_markup()


def support_kb(support_username: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💬 Falar com Suporte",
            url=f"https://t.me/{support_username}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="⏮️ Voltar", callback_data="main_menu")
    )
    return builder.as_markup()
