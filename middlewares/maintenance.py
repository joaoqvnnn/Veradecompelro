from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from config import settings
from database.models import User


class MaintenanceMiddleware(BaseMiddleware):
    """
    Bloqueia usuários comuns quando o modo manutenção está ativo.
    Admins continuam podendo usar o bot.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not settings.MAINTENANCE_MODE:
            return await handler(event, data)

        db_user: User | None = data.get("db_user")
        tg_user = data.get("event_from_user")

        # Admins passam direto
        if db_user and db_user.is_admin:
            return await handler(event, data)

        if tg_user and tg_user.id in settings.ADMIN_IDS:
            return await handler(event, data)

        # Usuário comum → mostra mensagem de manutenção
        text = settings.MAINTENANCE_MESSAGE

        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)

        return  # interrompe
