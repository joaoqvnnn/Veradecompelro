from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from services.messages import MessageService, DEFAULT_TEMPLATES
from keyboards.admin import admin_back_kb
from keyboards.dynamic import build_keyboard_from_buttons
from handlers.admin.panel import is_admin
from config import settings

router = Router(name="admin_messages")


class EditMessage(StatesGroup):
    waiting_content = State()


# =========================================================
# MENU PRINCIPAL DO EDITOR
# =========================================================

@router.callback_query(F.data == "admin:messages")
async def cb_messages_menu(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    templates = await MessageService.list_templates(session)

    builder = InlineKeyboardBuilder()
    for tpl in templates:
        source = "🗄" if tpl["source"] == "database" else "📄"
        builder.row(
            InlineKeyboardButton(
                text=f"{source} {tpl['title']}",
                callback_data=f"admin:msg_view:{tpl['key']}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:main"))

    text = (
        "🎨 <b>EDITOR DE MENSAGENS</b>\n\n"
        "📄 = padrão do sistema\n"
        "🗄 = personalizado (salvo no banco)\n\n"
        "Escolha uma mensagem para editar:"
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


# =========================================================
# VISUALIZAR TEMPLATE
# =========================================================

@router.callback_query(F.data.startswith("admin:msg_view:"))
async def cb_msg_view(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    key = callback.data.split(":")[2]
    tpl = await MessageService.get_template(session, key)

    # Preview com dados de exemplo
    preview = MessageService.render(
        tpl["content"],
        store_name=settings.STORE_NAME,
        bot_username=settings.BOT_USERNAME,
        user_id=db_user.id,
        balance=f"{db_user.balance:.2f}",
        product_name="COMBATE",
        emoji="🔥",
        status_text="🟢 DISPONÍVEL AGORA",
        price="6.00",
        stock="2",
        description="Tela Combate\nAcesso no app oficial",
        sold="4",
        views="8",
        warranty="30",
        product_price="6.00",
        missing="1.00",
        expiration=str(settings.PIX_EXPIRATION_MINUTES),
        amount="10.00",
        bonus="1.00",
        payment_id="e58db1...",
        pix_code="000201...",
        balance_after="10.00",
        total="11.00",
        date="31/08/2026 15:00",
        delivery="email@teste.com:senha123",
        whatsapp="Não informado",
        email="Não informado",
        orders="2",
        total_spent="12.00",
        total_deposited="20.00",
        total_bonus="2.00",
        status="Ativo",
        commission=str(settings.AFFILIATE_COMMISSION_PERCENT),
        referrals="0",
        total_earned="0.00",
        min_withdraw=f"{settings.AFFILIATE_MIN_WITHDRAW:.2f}",
        affiliate_balance="0.00",
        link=f"https://t.me/{settings.BOT_USERNAME}?start={db_user.id}",
    )

    # Limita preview para não estourar limite do Telegram
    if len(preview) > 3500:
        preview = preview[:3500] + "\n\n... (cortado)"

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Editar Texto", callback_data=f"admin:msg_edit:{key}")
    )
    builder.row(
        InlineKeyboardButton(text="👁 Pré-visualizar", callback_data=f"admin:msg_preview:{key}")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Restaurar Padrão", callback_data=f"admin:msg_reset:{key}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Voltar", callback_data="admin:messages")
    )

    text = (
        f"🎨 <b>{tpl.get('title') or key}</b>\n"
        f"🔑 Key: <code>{key}</code>\n\n"
        f"📝 <b>Conteúdo atual:</b>\n"
        f"———————————————\n"
        f"{preview}\n"
        f"———————————————"
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


# =========================================================
# EDITAR TEXTO
# =========================================================

@router.callback_query(F.data.startswith("admin:msg_edit:"))
async def cb_msg_edit(callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    key = callback.data.split(":")[2]
    tpl = await MessageService.get_template(session, key)

    await state.set_state(EditMessage.waiting_content)
    await state.update_data(msg_key=key)

    await callback.message.edit_text(
        f"✏️ <b>Editando: {tpl.get('title') or key}</b>\n\n"
        f"Envie o novo texto da mensagem.\n\n"
        f"<b>Variáveis disponíveis</b> (use com chaves):\n"
        f"<code>{{store_name}}</code> {{user_id}} {{balance}}\n"
        f"<code>{{product_name}}</code> {{price}} {{stock}} {{sold}}\n"
        f"<code>{{amount}}</code> {{bonus}} {{pix_code}} etc.\n\n"
        f"Suporta HTML: &lt;b&gt; &lt;i&gt; &lt;code&gt;\n\n"
        f"Ou envie /cancelar para sair.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(EditMessage.waiting_content)
async def process_msg_edit(message: Message, state: FSMContext, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        return

    if message.text and message.text.lower() in ("/cancelar", "cancelar"):
        await state.clear()
        await message.answer("❌ Edição cancelada.")
        return

    data = await state.get_data()
    key = data["msg_key"]
    content = message.text or message.caption or ""

    if not content.strip():
        await message.answer("❌ Texto vazio. Tente novamente.")
        return

    default = DEFAULT_TEMPLATES.get(key, {})
    await MessageService.save_template(
        session=session,
        key=key,
        content=content,
        title=default.get("title", key),
        parse_mode="HTML",
        buttons=default.get("buttons"),
        admin_id=db_user.id,
    )
    await state.clear()

    await message.answer(
        f"✅ Mensagem <b>{key}</b> atualizada com sucesso!\n\n"
        f"As alterações já valem para os próximos envios.",
        parse_mode="HTML"
    )


# =========================================================
# PRÉ-VISUALIZAR
# =========================================================

@router.callback_query(F.data.startswith("admin:msg_preview:"))
async def cb_msg_preview(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    key = callback.data.split(":")[2]
    tpl = await MessageService.get_rendered(
        session,
        key,
        store_name=settings.STORE_NAME,
        bot_username=settings.BOT_USERNAME,
        user_id=db_user.id,
        balance=f"{db_user.balance:.2f}",
        product_name="COMBATE",
        emoji="🔥",
        status_text="🟢 DISPONÍVEL AGORA",
        price="6.00",
        stock="2",
        description="Tela Combate\nAcesso no app oficial",
        sold="4",
        views="8",
        warranty="30",
        product_price="6.00",
        missing="1.00",
        expiration=str(settings.PIX_EXPIRATION_MINUTES),
        amount="10.00",
        bonus="1.00",
        payment_id="e58db1ab",
        pix_code="00020126...",
        balance_after="11.00",
        total="11.00",
        date="31/08/2026 15:00",
        delivery="email@teste.com:senha123",
        whatsapp="Não informado",
        email="Não informado",
        orders="2",
        total_spent="12.00",
        total_deposited="20.00",
        total_bonus="2.00",
        status="Ativo",
        commission=str(settings.AFFILIATE_COMMISSION_PERCENT),
        referrals="0",
        total_earned="0.00",
        min_withdraw=f"{settings.AFFILIATE_MIN_WITHDRAW:.2f}",
        affiliate_balance="0.00",
        link=f"https://t.me/{settings.BOT_USERNAME}?start={db_user.id}",
    )

    kb = build_keyboard_from_buttons(tpl.get("buttons") or [])
    # Adiciona botão de voltar
    builder = InlineKeyboardBuilder()
    if tpl.get("buttons"):
        for row in tpl["buttons"]:
            row_btns = []
            for btn in row:
                row_btns.append(
                    InlineKeyboardButton(
                        text=btn.get("text", "Botão"),
                        callback_data="noop"
                    )
                )
            builder.row(*row_btns)
    builder.row(InlineKeyboardButton(text="🔙 Voltar ao editor", callback_data=f"admin:msg_view:{key}"))

    await callback.message.edit_text(
        tpl["content"],
        reply_markup=builder.as_markup(),
        parse_mode=tpl.get("parse_mode", "HTML")
    )
    await callback.answer("Pré-visualização")


# =========================================================
# RESTAURAR PADRÃO
# =========================================================

@router.callback_query(F.data.startswith("admin:msg_reset:"))
async def cb_msg_reset(callback: CallbackQuery, session: AsyncSession, db_user: User):
    if not is_admin(db_user):
        await callback.answer("Acesso negado.", show_alert=True)
        return

    key = callback.data.split(":")[2]
    deleted = await MessageService.reset_template(session, key)

    if deleted:
        await callback.answer("↩️ Restaurado para o padrão!", show_alert=True)
    else:
        await callback.answer("Já estava no padrão.", show_alert=True)

    # Volta para a visualização
    callback.data = f"admin:msg_view:{key}"
    await cb_msg_view(callback, session, db_user)
