from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# =========================================================
# PAINEL PRINCIPAL ADMIN
# =========================================================

def admin_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📊 Dashboard", callback_data="admin:dashboard")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Produtos", callback_data="admin:products"),
        InlineKeyboardButton(text="🗂 Categorias", callback_data="admin:categories"),
    )
    builder.row(
        InlineKeyboardButton(text="📥 Estoque", callback_data="admin:stock"),
        InlineKeyboardButton(text="🛒 Pedidos", callback_data="admin:orders"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Usuários", callback_data="admin:users"),
        InlineKeyboardButton(text="💰 Carteiras", callback_data="admin:wallets"),
    )
    builder.row(
        InlineKeyboardButton(text="💠 Pagamentos", callback_data="admin:payments"),
        InlineKeyboardButton(text="🤝 Afiliados", callback_data="admin:affiliates"),
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Gift Cards", callback_data="admin:giftcards"),
        InlineKeyboardButton(text="📢 Broadcast", callback_data="admin:broadcast"),
    )
    builder.row(
        InlineKeyboardButton(text="🎨 Mensagens", callback_data="admin:messages"),
        InlineKeyboardButton(text="⚙️ Configurações", callback_data="admin:settings"),
    )
    builder.row(
        InlineKeyboardButton(text="📈 Estatísticas", callback_data="admin:stats"),
        InlineKeyboardButton(text="🧾 Logs", callback_data="admin:logs"),
    )
    builder.row(
        InlineKeyboardButton(text="🚧 Manutenção", callback_data="admin:maintenance"),
        InlineKeyboardButton(text="🔙 Sair do Admin", callback_data="main_menu"),
    )
    return builder.as_markup()


# =========================================================
# PRODUTOS
# =========================================================

def admin_products_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➕ Novo Produto", callback_data="admin:product_create")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Listar Produtos", callback_data="admin:product_list")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:main")
    )
    return builder.as_markup()


def admin_product_actions_kb(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✏️ Editar", callback_data=f"admin:product_edit:{product_id}"),
        InlineKeyboardButton(text="📥 Estoque", callback_data=f"admin:stock_add:{product_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="⏸ Pausar", callback_data=f"admin:product_pause:{product_id}"),
        InlineKeyboardButton(text="🗑 Excluir", callback_data=f"admin:product_delete:{product_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="📄 Duplicar", callback_data=f"admin:product_duplicate:{product_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:products")
    )
    return builder.as_markup()


# =========================================================
# CATEGORIAS
# =========================================================

def admin_categories_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➕ Nova Categoria", callback_data="admin:category_create")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Listar Categorias", callback_data="admin:category_list")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:main")
    )
    return builder.as_markup()


# =========================================================
# ESTOQUE
# =========================================================

def admin_stock_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➕ Abastecer", callback_data="admin:stock_supply")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Ver Estoque", callback_data="admin:stock_view"),
        InlineKeyboardButton(text="⚠️ Estoque Baixo", callback_data="admin:stock_low"),
    )
    builder.row(
        InlineKeyboardButton(text="🧹 Limpar Estoque", callback_data="admin:stock_clear")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:main")
    )
    return builder.as_markup()


# =========================================================
# USUÁRIOS
# =========================================================

def admin_users_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🔎 Buscar Usuário", callback_data="admin:user_search")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:main")
    )
    return builder.as_markup()


def admin_user_actions_kb(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="💰 + Saldo", callback_data=f"admin:user_add_balance:{user_id}"),
        InlineKeyboardButton(text="💸 - Saldo", callback_data=f"admin:user_remove_balance:{user_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Bônus", callback_data=f"admin:user_bonus:{user_id}"),
        InlineKeyboardButton(text="🛑 Bloquear", callback_data=f"admin:user_block:{user_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="📨 Mensagem", callback_data=f"admin:user_message:{user_id}"),
        InlineKeyboardButton(text="📊 Histórico", callback_data=f"admin:user_history:{user_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:users")
    )
    return builder.as_markup()


# =========================================================
# PAGAMENTOS
# =========================================================

def admin_payments_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🟢 Aprovados", callback_data="admin:payments:approved"),
        InlineKeyboardButton(text="🟡 Pendentes", callback_data="admin:payments:pending"),
    )
    builder.row(
        InlineKeyboardButton(text="🔴 Expirados", callback_data="admin:payments:expired"),
        InlineKeyboardButton(text="⚠️ Cancelados", callback_data="admin:payments:cancelled"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:main")
    )
    return builder.as_markup()


# =========================================================
# GIFT CARDS
# =========================================================

def admin_giftcards_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➕ Criar Gift Card", callback_data="admin:gift_create")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Listar Ativos", callback_data="admin:gift_list_active"),
        InlineKeyboardButton(text="✅ Utilizados", callback_data="admin:gift_list_used"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:main")
    )
    return builder.as_markup()


# =========================================================
# AFILIADOS
# =========================================================

def admin_affiliates_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="💸 Saques Pendentes", callback_data="admin:affiliate_withdraws")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Configurações", callback_data="admin:affiliate_settings")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:main")
    )
    return builder.as_markup()


# =========================================================
# BROADCAST
# =========================================================

def admin_broadcast_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📢 Todos", callback_data="admin:broadcast:all")
    )
    builder.row(
        InlineKeyboardButton(text="🟢 Ativos", callback_data="admin:broadcast:active"),
        InlineKeyboardButton(text="🛒 Compradores", callback_data="admin:broadcast:buyers"),
    )
    builder.row(
        InlineKeyboardButton(text="💰 Com Saldo", callback_data="admin:broadcast:balance"),
        InlineKeyboardButton(text="🤝 Afiliados", callback_data="admin:broadcast:affiliates"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:main")
    )
    return builder.as_markup()


# =========================================================
# CONFIGURAÇÕES / MANUTENÇÃO
# =========================================================

def admin_settings_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="🏪 Dados da Loja", callback_data="admin:settings_store")
    )
    builder.row(
        InlineKeyboardButton(text="💠 PIX / Pagamentos", callback_data="admin:settings_pix"),
        InlineKeyboardButton(text="🎁 Bônus", callback_data="admin:settings_bonus"),
    )
    builder.row(
        InlineKeyboardButton(text="🤝 Afiliados", callback_data="admin:settings_affiliate")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:main")
    )
    return builder.as_markup()


def admin_maintenance_kb(is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if is_active:
        builder.row(
            InlineKeyboardButton(text="✅ Desativar Manutenção", callback_data="admin:maintenance_off")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="🔧 Ativar Manutenção", callback_data="admin:maintenance_on")
        )

    builder.row(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:main")
    )
    return builder.as_markup()


def admin_back_kb(callback_data: str = "admin:main") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Voltar", callback_data=callback_data)
    )
    return builder.as_markup()
