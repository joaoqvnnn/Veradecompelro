from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Order, Payment, PaymentStatus, OrderStatus, AdminLog
from keyboards.admin import (
    admin_main_kb,
    admin_config_kb,
    admin_cfg_general_kb,
    admin_cfg_admins_kb,
    admin_cfg_affiliate_kb,
    admin_cfg_users_kb,
    admin_cfg_pix_kb,
    admin_cfg_logins_kb,
    admin_back_kb,
)
from services.settings_service import SettingsService
from handlers.admin.panel import is_admin
from config import settings as env_settings
from decimal import Decimal

router = Router(name="admin_config")


class CfgStates(StatesGroup):
    support = State()
    separator = State()
    logs_chat = State()
    adm_add = State()
    adm_remove = State()
    aff_points = State()
    aff_min = State()
    aff_mult = State()
    reg_bonus = State()
    pix_token = State()
    pix_min = State()
    pix_max = State()
    pix_exp = State()
    pix_bonus = State()
    pix_bonus_min = State()


# ========== DASHBOARD REAL ==========

@router.message(F.text == "/admin")
async def cmd_admin(message: Message, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await message.answer("🚫 Acesso negado.")
        return
    await SettingsService.ensure_defaults(session)
    text = await _dashboard_text(session, db_user)
    await message.answer(text, reply_markup=admin_main_kb(), parse_mode="HTML")


@router.callback_query(F.data == "admin:main")
async def cb_admin_main(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    text = await _dashboard_text(session, db_user)
    await callback.message.edit_text(text, reply_markup=admin_main_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:dashboard")
async def cb_dashboard(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    text = await _dashboard_text(session, db_user)
    await callback.message.edit_text(text, reply_markup=admin_main_kb(), parse_mode="HTML")
    await callback.answer()


async def _dashboard_text(session: AsyncSession, db_user: User) -> str:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    users = (await session.execute(select(func.count(User.id)))).scalar_one() or 0

    sales_total = (await session.execute(
        select(func.count(Order.id)).where(Order.status == OrderStatus.DELIVERED)
    )).scalar_one() or 0

    sales_today = (await session.execute(
        select(func.count(Order.id)).where(
            Order.status == OrderStatus.DELIVERED,
            Order.created_at >= today,
        )
    )).scalar_one() or 0

    rev_total = (await session.execute(
        select(func.coalesce(func.sum(Order.total_price), 0)).where(
            Order.status == OrderStatus.DELIVERED
        )
    )).scalar_one() or Decimal("0")

    rev_today = (await session.execute(
        select(func.coalesce(func.sum(Order.total_price), 0)).where(
            Order.status == OrderStatus.DELIVERED,
            Order.created_at >= today,
        )
    )).scalar_one() or Decimal("0")

    # Receita do mês
    month_start = today.replace(day=1)
    rev_month = (await session.execute(
        select(func.coalesce(func.sum(Order.total_price), 0)).where(
            Order.status == OrderStatus.DELIVERED,
            Order.created_at >= month_start,
        )
    )).scalar_one() or Decimal("0")

    store = await SettingsService.get(session, "store_name", env_settings.STORE_NAME)

    return (
        f"📊 <b>DASHBOARD — {store}</b>\n\n"
        f"👥 Users: <b>{users}</b>\n"
        f"💰 Receita total: <b>R$ {rev_total:.2f}</b>\n"
        f"📅 Receita mensal: <b>R$ {rev_month:.2f}</b>\n"
        f"💵 Receita de hoje: <b>R$ {rev_today:.2f}</b>\n"
        f"🛒 Vendas total: <b>{sales_total}</b>\n"
        f"🛒 Vendas hoje: <b>{sales_today}</b>\n\n"
        f"Use os botões abaixo para configurar:"
    )


# ========== MENU CONFIGURAÇÕES ==========

@router.callback_query(F.data == "admin:cfg")
async def cb_cfg(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    text = (
        "<b>MENU DE CONFIGURAÇÕES DO BOT</b>\n\n"
        f"Admin: <b>Sim</b>\n"
        f"Dono: <b>{'Sim' if db_user.id in env_settings.ADMIN_IDS else 'Não'}</b>\n\n"
        "Escolha o que deseja configurar:"
    )
    await callback.message.edit_text(text, reply_markup=admin_config_kb(), parse_mode="HTML")
    await callback.answer()


# ========== CONFIGURAÇÕES GERAIS ==========

@router.callback_query(F.data == "admin:cfg_general")
async def cb_cfg_general(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    logs = await SettingsService.get(session, "logs_chat_id")
    support = await SettingsService.get(session, "support_link")
    sep = await SettingsService.get(session, "separator")
    maint = await SettingsService.get_bool(session, "maintenance_mode")

    text = (
        "<b>CONFIGURAÇÕES GERAIS</b>\n\n"
        f"DESTINO DAS LOG'S: <code>{logs or 'não definido'}</code>\n"
        f"LINK DO SUPORTE: {support}\n"
        f"SEPARADOR: <code>{sep}</code>\n\n"
        "O separador é o caractere usado ao alterar dados em massa.\n"
        "Ex: <code>NOME===VALOR</code>\n\n"
        "Use os botões abaixo:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_cfg_general_kb(maint),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:set_support")
async def cb_set_support(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(CfgStates.support)
    await callback.message.edit_text(
        "🔗 Envie o novo link de suporte (ex: https://t.me/seu_suporte ou https://wa.me/55...):"
    )
    await callback.answer()


@router.message(CfgStates.support)
async def process_support(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    link = (message.text or "").strip()
    await SettingsService.set(session, "support_link", link, db_user.id)
    await state.clear()
    await message.answer(f"✅ Suporte atualizado:\n{link}")


@router.callback_query(F.data == "admin:set_separator")
async def cb_set_sep(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(CfgStates.separator)
    await callback.message.edit_text(
        "📌 Envie o novo separador (ex: === ou |||):\n\n"
        "Escolha algo que você quase não usa em textos normais."
    )
    await callback.answer()


@router.message(CfgStates.separator)
async def process_sep(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    sep = (message.text or "").strip()
    if not sep:
        await message.answer("❌ Separador inválido.")
        return
    await SettingsService.set(session, "separator", sep, db_user.id)
    await state.clear()
    await message.answer(f"✅ Separador atualizado: <code>{sep}</code>", parse_mode="HTML")


@router.callback_query(F.data == "admin:set_logs_chat")
async def cb_set_logs(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(CfgStates.logs_chat)
    await callback.message.edit_text(
        "📨 Envie o ID do chat/canal de logs (ex: -1001234567890):\n\n"
        "O bot precisa ser admin desse canal/grupo."
    )
    await callback.answer()


@router.message(CfgStates.logs_chat)
async def process_logs(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    chat_id = (message.text or "").strip()
    await SettingsService.set(session, "logs_chat_id", chat_id, db_user.id)
    await state.clear()
    await message.answer(f"✅ Destino de logs: <code>{chat_id}</code>", parse_mode="HTML")


@router.callback_query(F.data == "admin:toggle_maintenance")
async def cb_toggle_maint(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    current = await SettingsService.get_bool(session, "maintenance_mode")
    new_val = "false" if current else "true"
    await SettingsService.set(session, "maintenance_mode", new_val, db_user.id)
    # Sincroniza com settings em memória
    env_settings.MAINTENANCE_MODE = new_val == "true"
    await callback.answer(f"Manutenção: {'ON' if new_val == 'true' else 'OFF'}", show_alert=True)
    await cb_cfg_general(callback, session, db_user)


# ========== CONFIGURAR ADMINS ==========

@router.callback_query(F.data == "admin:cfg_admins")
async def cb_cfg_admins(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    result = await session.execute(select(func.count(User.id)).where(User.is_admin.is_(True)))
    count = result.scalar_one() or 0
    text = (
        f"<b>PAINEL CONFIGURAR ADMIN</b>\n\n"
        f"Administradores: <b>{count}</b>\n\n"
        "Use os botões abaixo:"
    )
    await callback.message.edit_text(text, reply_markup=admin_cfg_admins_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:adm_add")
async def cb_adm_add(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(CfgStates.adm_add)
    await callback.message.edit_text("➕ Envie o Telegram ID do novo admin:")
    await callback.answer()


@router.message(CfgStates.adm_add)
async def process_adm_add(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    try:
        uid = int((message.text or "").strip())
    except ValueError:
        await message.answer("❌ ID inválido.")
        return

    user = await session.get(User, uid)
    if not user:
        await message.answer("❌ Usuário não encontrado. Ele precisa ter usado /start antes.")
        await state.clear()
        return

    user.is_admin = True
    user.admin_role = "admin"
    session.add(AdminLog(
        admin_id=db_user.id,
        action="add_admin",
        target_type="user",
        target_id=str(uid),
    ))
    await state.clear()
    await message.answer(f"✅ <code>{uid}</code> agora é admin.", parse_mode="HTML")


@router.callback_query(F.data == "admin:adm_remove")
async def cb_adm_remove(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(CfgStates.adm_remove)
    await callback.message.edit_text("➖ Envie o Telegram ID do admin a remover:")
    await callback.answer()


@router.message(CfgStates.adm_remove)
async def process_adm_remove(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    try:
        uid = int((message.text or "").strip())
    except ValueError:
        await message.answer("❌ ID inválido.")
        return

    if uid in env_settings.ADMIN_IDS:
        await message.answer("❌ Não é possível remover o Owner definido no .env.")
        await state.clear()
        return

    user = await session.get(User, uid)
    if not user:
        await message.answer("❌ Usuário não encontrado.")
        await state.clear()
        return

    user.is_admin = False
    user.admin_role = None
    session.add(AdminLog(
        admin_id=db_user.id,
        action="remove_admin",
        target_type="user",
        target_id=str(uid),
    ))
    await state.clear()
    await message.answer(f"✅ Admin <code>{uid}</code> removido.", parse_mode="HTML")


@router.callback_query(F.data == "admin:adm_list")
async def cb_adm_list(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    result = await session.execute(select(User).where(User.is_admin.is_(True)))
    admins = list(result.scalars().all())
    if not admins:
        text = "Nenhum admin no banco."
    else:
        lines = ["📋 <b>LISTA DE ADMINS</b>\n"]
        for a in admins:
            lines.append(f"• <code>{a.id}</code> — @{a.username or 'N/A'} ({a.admin_role or 'admin'})")
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=admin_cfg_admins_kb(), parse_mode="HTML")
    await callback.answer()


# ========== AFILIADOS ==========

@router.callback_query(F.data == "admin:cfg_affiliate")
async def cb_cfg_aff(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    enabled = await SettingsService.get_bool(session, "affiliate_enabled")
    points = await SettingsService.get(session, "points_per_recharge")
    min_c = await SettingsService.get(session, "points_min_convert")
    mult = await SettingsService.get(session, "points_multiplier")

    text = (
        f"<b>CONFIGURAR AFILIADOS</b>\n\n"
        f"PONTOS MÍNIMO PRA SALDO: <b>{min_c}</b>\n"
        f"MULTIPLICADOR: <b>{mult}</b>\n"
        f"PONTOS POR RECARGA: <b>{points}</b>\n\n"
        f"Sistema: <b>{'ON 🟢' if enabled else 'OFF 🔴'}</b>\n\n"
        "Ex: multiplicador 0.01 e 500 pontos → R$ 5,00"
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_cfg_affiliate_kb(enabled),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:aff_toggle")
async def cb_aff_toggle(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    current = await SettingsService.get_bool(session, "affiliate_enabled")
    await SettingsService.set(session, "affiliate_enabled", "false" if current else "true", db_user.id)
    await callback.answer("Atualizado!", show_alert=False)
    await cb_cfg_aff(callback, session, db_user)


@router.callback_query(F.data == "admin:aff_points_recharge")
async def cb_aff_points(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(CfgStates.aff_points)
    await callback.message.edit_text("⭐ Envie a quantidade de pontos por recarga do afiliado:")
    await callback.answer()


@router.message(CfgStates.aff_points)
async def process_aff_points(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    val = (message.text or "").strip()
    await SettingsService.set(session, "points_per_recharge", val, db_user.id)
    await state.clear()
    await message.answer(f"✅ Pontos por recarga: {val}")


@router.callback_query(F.data == "admin:aff_points_min")
async def cb_aff_min(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(CfgStates.aff_min)
    await callback.message.edit_text("📉 Envie o mínimo de pontos para converter em saldo:")
    await callback.answer()


@router.message(CfgStates.aff_min)
async def process_aff_min(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    val = (message.text or "").strip()
    await SettingsService.set(session, "points_min_convert", val, db_user.id)
    await state.clear()
    await message.answer(f"✅ Mínimo para converter: {val}")


@router.callback_query(F.data == "admin:aff_multiplier")
async def cb_aff_mult(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(CfgStates.aff_mult)
    await callback.message.edit_text("✖️ Envie o multiplicador (ex: 0.01):")
    await callback.answer()


@router.message(CfgStates.aff_mult)
async def process_aff_mult(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    val = (message.text or "").strip().replace(",", ".")
    await SettingsService.set(session, "points_multiplier", val, db_user.id)
    await state.clear()
    await message.answer(f"✅ Multiplicador: {val}")


# ========== USUÁRIOS (bônus registro) ==========

@router.callback_query(F.data == "admin:cfg_users")
async def cb_cfg_users(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    bonus = await SettingsService.get(session, "registration_bonus")
    text = (
        f"<b>CONFIGURAR USUÁRIOS</b>\n\n"
        f"Bônus de registro atual: <b>R$ {bonus}</b>\n\n"
        "Use os botões abaixo:"
    )
    await callback.message.edit_text(text, reply_markup=admin_cfg_users_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:set_reg_bonus")
async def cb_reg_bonus(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(CfgStates.reg_bonus)
    await callback.message.edit_text("🎁 Envie o valor do bônus de registro (ex: 0 ou 1.50):")
    await callback.answer()


@router.message(CfgStates.reg_bonus)
async def process_reg_bonus(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    val = (message.text or "0").strip().replace(",", ".")
    await SettingsService.set(session, "registration_bonus", val, db_user.id)
    await state.clear()
    await message.answer(f"✅ Bônus de registro: R$ {val}")


# ========== PIX ==========

@router.callback_query(F.data == "admin:cfg_pix")
async def cb_cfg_pix(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return

    token = await SettingsService.get(session, "mp_access_token")
    # fallback .env
    if not token:
        token = env_settings.MP_ACCESS_TOKEN or ""
    token_show = (token[:20] + "...") if len(token) > 20 else (token or "não definido")

    pix_min = await SettingsService.get(session, "pix_min")
    pix_max = await SettingsService.get(session, "pix_max")
    exp = await SettingsService.get(session, "pix_expiration_minutes")
    bonus = await SettingsService.get(session, "bonus_percent")
    bonus_min = await SettingsService.get(session, "bonus_min_value")

    text = (
        f"<b>CONFIGURAR PIX</b>\n\n"
        f"TOKEN MERCADO PAGO: <code>{token_show}</code>\n"
        f"DEPÓSITO MÍNIMO: <b>R$ {pix_min}</b>\n"
        f"DEPÓSITO MÁXIMO: <b>R$ {pix_max}</b>\n"
        f"TEMPO DE EXPIRAÇÃO: <b>{exp} min</b>\n"
        f"BÔNUS DE DEPÓSITO: <b>{bonus}%</b>\n"
        f"MÍN PARA BÔNUS: <b>R$ {bonus_min}</b>"
    )
    await callback.message.edit_text(text, reply_markup=admin_cfg_pix_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:pix_token")
async def cb_pix_token(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(CfgStates.pix_token)
    await callback.message.edit_text("🔑 Envie o Access Token do Mercado Pago:")
    await callback.answer()


@router.message(CfgStates.pix_token)
async def process_pix_token(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    token = (message.text or "").strip()
    await SettingsService.set(session, "mp_access_token", token, db_user.id)
    await state.clear()
    # apaga a mensagem com o token por segurança
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer("✅ Token Mercado Pago atualizado.")


@router.callback_query(F.data == "admin:pix_min")
async def cb_pix_min(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(CfgStates.pix_min)
    await callback.message.edit_text("⬇️ Envie o depósito mínimo (ex: 1.00):")
    await callback.answer()


@router.message(CfgStates.pix_min)
async def process_pix_min(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    val = (message.text or "").strip().replace(",", ".")
    await SettingsService.set(session, "pix_min", val, db_user.id)
    await state.clear()
    await message.answer(f"✅ Depósito mínimo: R$ {val}")


@router.callback_query(F.data == "admin:pix_max")
async def cb_pix_max(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(CfgStates.pix_max)
    await callback.message.edit_text("⬆️ Envie o depósito máximo (ex: 150.00):")
    await callback.answer()


@router.message(CfgStates.pix_max)
async def process_pix_max(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    val = (message.text or "").strip().replace(",", ".")
    await SettingsService.set(session, "pix_max", val, db_user.id)
    await state.clear()
    await message.answer(f"✅ Depósito máximo: R$ {val}")


@router.callback_query(F.data == "admin:pix_exp")
async def cb_pix_exp(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(CfgStates.pix_exp)
    await callback.message.edit_text("⏱ Envie o tempo de expiração em minutos (ex: 15):")
    await callback.answer()


@router.message(CfgStates.pix_exp)
async def process_pix_exp(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    val = (message.text or "").strip()
    await SettingsService.set(session, "pix_expiration_minutes", val, db_user.id)
    await state.clear()
    await message.answer(f"✅ Expiração: {val} minutos")


@router.callback_query(F.data == "admin:pix_bonus")
async def cb_pix_bonus(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(CfgStates.pix_bonus)
    await callback.message.edit_text("🎁 Envie a % de bônus (ex: 10):")
    await callback.answer()


@router.message(CfgStates.pix_bonus)
async def process_pix_bonus(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    val = (message.text or "").strip().replace(",", ".")
    await SettingsService.set(session, "bonus_percent", val, db_user.id)
    await state.clear()
    await message.answer(f"✅ Bônus: {val}%")


@router.callback_query(F.data == "admin:pix_bonus_min")
async def cb_pix_bonus_min(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        return
    await state.set_state(CfgStates.pix_bonus_min)
    await callback.message.edit_text("📌 Envie o valor mínimo de depósito para ganhar bônus (ex: 10.00):")
    await callback.answer()


@router.message(CfgStates.pix_bonus_min)
async def process_pix_bonus_min(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    val = (message.text or "").strip().replace(",", ".")
    await SettingsService.set(session, "bonus_min_value", val, db_user.id)
    await state.clear()
    await message.answer(f"✅ Mínimo para bônus: R$ {val}")


# ========== LOGINS (abre o menu de estoque) ==========

@router.callback_query(F.data == "admin:cfg_logins")
async def cb_cfg_logins(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    from database.models import StockItem
    count = (await session.execute(
        select(func.count(StockItem.id)).where(StockItem.is_sold.is_(False))
    )).scalar_one() or 0

    sep = await SettingsService.get(session, "separator")
    text = (
        f"<b>CONFIGURAR LOGINS</b>\n\n"
        f"LOGINS NO ESTOQUE: <b>{count}</b>\n\n"
        f"Formato para adicionar (use o separador <code>{sep}</code>):\n"
        f"<code>NOME{sep}VALOR{sep}DESCRICAO{sep}EMAIL{sep}SENHA{sep}DURACAO</code>"
    )
    await callback.message.edit_text(text, reply_markup=admin_cfg_logins_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:cfg_search")
async def cb_cfg_search(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        return
    text = (
        "<b>PESQUISA DE SERVIÇOS</b>\n\n"
        "A pesquisa já está ativa no bot do cliente.\n"
        "Em breve: imagens por serviço."
    )
    await callback.message.edit_text(text, reply_markup=admin_back_kb("admin:cfg"), parse_mode="HTML")
    await callback.answer()


# Placeholders de seções ainda em construção
@router.callback_query(F.data == "admin:actions")
async def cb_actions(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        return
    from keyboards.admin import admin_giftcards_kb
    text = "🛠 <b>AÇÕES</b>\n\nGift Cards e ações rápidas:"
    await callback.message.edit_text(text, reply_markup=admin_giftcards_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:transactions")
async def cb_transactions(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        return
    from keyboards.admin import admin_payments_kb
    text = "💳 <b>TRANSAÇÕES</b>\n\nFiltre os pagamentos:"
    await callback.message.edit_text(text, reply_markup=admin_payments_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:updates")
async def cb_updates(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        return
    await callback.message.edit_text(
        "🔄 <b>ATUALIZAÇÕES</b>\n\nVersão do bot: <b>1.0.0</b>\n\nEm breve: checagem de update.",
        reply_markup=admin_back_kb(),
        parse_mode="HTML"
    )
    await callback.answer()
