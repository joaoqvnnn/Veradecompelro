from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser, Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, UserStatus
from config import settings


class UserMiddleware(BaseMiddleware):
    """
    Garante que o usuário existe no banco.
    Atualiza username, nome e last_activity.
    Injeta o objeto User como data["db_user"]
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        session: AsyncSession | None = data.get("session")

        if not tg_user or not session:
            return await handler(event, data)

        # Busca usuário
        result = await session.execute(
            select(User).where(User.id == tg_user.id)
        )
        db_user = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if db_user is None:
            # Cria novo usuário
            referred_by = None

            # Captura afiliado se veio de /start REF_ID
            if isinstance(event, Message) and event.text and event.text.startswith("/start "):
                parts = event.text.split(maxsplit=1)
                if len(parts) == 2 and parts[1].isdigit():
                    ref_id = int(parts[1])
                    if ref_id != tg_user.id:
                        # Verifica se o indicador existe
                        ref_result = await session.execute(
                            select(User).where(User.id == ref_id)
                        )
                        if ref_result.scalar_one_or_none():
                            referred_by = ref_id

            db_user = User(
                id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                language_code=tg_user.language_code,
                referred_by=referred_by,
                is_admin=tg_user.id in settings.ADMIN_IDS,
                admin_role="owner" if tg_user.id in settings.ADMIN_IDS else None,
                last_activity=now,
            )
            session.add(db_user)

            # Atualiza contador de indicações do afiliado
            if referred_by:
                ref_user = await session.get(User, referred_by)
                if ref_user:
                    ref_user.total_referrals += 1

            await session.flush()
        else:
            # Atualiza dados básicos
            db_user.username = tg_user.username
            db_user.first_name = tg_user.first_name
            db_user.last_name = tg_user.last_name
            db_user.language_code = tg_user.language_code
            db_user.last_activity = now

            # Garante que admins configurados no .env tenham permissão
            if tg_user.id in settings.ADMIN_IDS and not db_user.is_admin:
                db_user.is_admin = True
                db_user.admin_role = "owner"

        # Bloqueia usuários banidos
        if db_user.status in (UserStatus.BLOCKED, UserStatus.BANNED):
            if isinstance(event, Message):
                await event.answer("🚫 Você está bloqueado e não pode usar este bot.")
            elif isinstance(event, CallbackQuery):
                await event.answer("🚫 Você está bloqueado.", show_alert=True)
            return  # interrompe o fluxo

        data["db_user"] = db_user
        return await handler(event, data)
