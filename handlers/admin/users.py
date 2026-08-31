from decimal import Decimal
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, UserStatus, TransactionType, AdminLog
from keyboards.admin import admin_users_kb, admin_user_actions_kb, admin_back_kb
from services.balance import BalanceService
from handlers.admin.panel import is_admin

router = Router(name="admin_users")


class UserSearch(StatesGroup):
    waiting_id = State()


class BalanceAction(StatesGroup):
    waiting_amount = State()


@router.callback_query(F.data == "admin:users")
async def cb_users(callback: CallbackQuery, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    text = "👥 <b>USUÁRIOS</b>\n\nBusque e gerencie usuários."
    await callback.message.edit_text(text, reply_markup=admin_users_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:user_search")
async def cb_user_search(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    await state.set_state(UserSearch.waiting_id)
    await callback.message.edit_text(
        "🔎 Envie o <b>Telegram ID</b> do usuário:",
        reply_markup=admin_back_kb("admin:users"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(UserSearch.waiting_id)
async def process_user_search(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID inválido.")
        return

    user = await session.get(User, user_id)
    await state.clear()

    if not user:
        await message.answer("❌ Usuário não encontrado.", reply_markup=admin_users_kb())
        return

    text = (
        f"👤 <b>USUÁRIO</b>\n\n"
        f"ID: <code>{user.id}</code>\n"
        f"Username: @{user.username or 'N/A'}\n"
        f"Nome: {user.first_name or ''} {user.last_name or ''}\n"
        f"💰 Saldo: <b>R$ {user.balance:.2f}</b>\n"
        f"🛒 Total gasto: R$ {user.total_spent:.2f}\n"
        f"💠 Depositado: R$ {user.total_deposited:.2f}\n"
        f"🤝 Indicações: {user.total_referrals}\n"
        f"🪙 Comissão: R$ {user.affiliate_balance:.2f}\n"
        f"📌 Status: {user.status.value}"
    )
    await message.answer(text, reply_markup=admin_user_actions_kb(user.id), parse_mode="HTML")


@router.callback_query(F.data.startswith("admin:user_add_balance:"))
async def cb_add_balance(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    user_id = int(callback.data.split(":")[2])
    await state.set_state(BalanceAction.waiting_amount)
    await state.update_data(target_user_id=user_id, action="add")
    await callback.message.edit_text(
        f"💰 Envie o valor para <b>adicionar</b> ao usuário <code>{user_id}</code>:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:user_remove_balance:"))
async def cb_remove_balance(callback: CallbackQuery, state: FSMContext, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return
    user_id = int(callback.data.split(":")[2])
    await state.set_state(BalanceAction.waiting_amount)
    await state.update_data(target_user_id=user_id, action="remove")
    await callback.message.edit_text(
        f"💸 Envie o valor para <b>remover</b> do usuário <code>{user_id}</code>:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(BalanceAction.waiting_amount)
async def process_balance_action(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return
    try:
        amount = Decimal(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except Exception:
        await message.answer("❌ Valor inválido.")
        return

    data = await state.get_data()
    target_id = data["target_user_id"]
    action = data["action"]
    await state.clear()

    try:
        if action == "add":
            await BalanceService.add_balance(
                session, target_id, amount,
                TransactionType.ADMIN_ADD,
                description=f"Crédito admin por {db_user.id}",
                admin_id=db_user.id,
            )
            msg = f"✅ R$ {amount:.2f} adicionados ao usuário {target_id}"
        else:
            await BalanceService.remove_balance(
                session, target_id, amount,
                TransactionType.ADMIN_REMOVE,
                description=f"Débito admin por {db_user.id}",
                admin_id=db_user.id,
            )
            msg = f"✅ R$ {amount:.2f} removidos do usuário {target_id}"

        # Log
        session.add(AdminLog(
            admin_id=db_user.id,
            action=f"balance_{action}",
            target_type="user",
            target_id=str(target_id),
            details={"amount": str(amount)},
        ))
        await message.answer(msg, reply_markup=admin_users_kb())
    except ValueError as e:
        await message.answer(f"❌ {e}")


@router.callback_query(F.data.startswith("admin:user_block:"))
async def cb_block_user(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    user_id = int(callback.data.split(":")[2])
    user = await session.get(User, user_id)
    if not user:
        await callback.answer("Usuário não encontrado.", show_alert=True)
        return

    if user.status == UserStatus.BLOCKED:
        user.status = UserStatus.ACTIVE
        await callback.answer("🔓 Usuário desbloqueado")
    else:
        user.status = UserStatus.BLOCKED
        await callback.answer("🛑 Usuário bloqueado")

    session.add(AdminLog(
        admin_id=db_user.id,
        action="toggle_block",
        target_type="user",
        target_id=str(user_id),
        details={"new_status": user.status.value},
    ))
