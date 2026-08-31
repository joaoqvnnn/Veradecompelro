import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from config import settings


class AntiFloodMiddleware(BaseMiddleware):
    """
    Anti-flood simples em memória (por processo).
    Para produção com vários workers use Redis.
    """

    def __init__(self) -> None:
        # user_id -> lista de timestamps
        self._commands: Dict[int, list[float]] = {}
        self._callbacks: Dict[int, list[float]] = {}
        self._pix: Dict[int, list[float]] = {}
        self._gift: Dict[int, list[float]] = {}

    def _clean(self, data: Dict[int, list[float]], user_id: int, window: float) -> list[float]:
        now = time.time()
        timestamps = [t for t in data.get(user_id, []) if now - t < window]
        data[user_id] = timestamps
        return timestamps

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if not tg_user:
            return await handler(event, data)

        user_id = tg_user.id
        now = time.time()

        # ========== COMANDOS ==========
        if isinstance(event, Message) and event.text and event.text.startswith("/"):
            timestamps = self._clean(self._commands, user_id, settings.RATE_LIMIT_WINDOW)
            if len(timestamps) >= settings.RATE_LIMIT_COMMANDS:
                await event.answer("⏳ Você está enviando comandos muito rápido. Aguarde alguns segundos.")
                return
            self._commands.setdefault(user_id, []).append(now)

        # ========== CALLBACKS (botões) ==========
        if isinstance(event, CallbackQuery):
            timestamps = self._clean(self._callbacks, user_id, 1.0)  # 1 segundo
            if len(timestamps) >= settings.CALLBACK_RATE_LIMIT:
                await event.answer("⏳ Calma! Clique mais devagar.", show_alert=False)
                return
            self._callbacks.setdefault(user_id, []).append(now)

            # Limite especial para geração de PIX
            if event.data and event.data.startswith("pix:"):
                pix_ts = self._clean(self._pix, user_id, 3600)  # 1 hora
                if len(pix_ts) >= settings.MAX_PIX_PER_HOUR:
                    await event.answer(
                        f"❌ Limite de {settings.MAX_PIX_PER_HOUR} PIX por hora atingido. Tente mais tarde.",
                        show_alert=True,
                    )
                    return
                self._pix.setdefault(user_id, []).append(now)

            # Limite de tentativas de Gift Card
            if event.data and event.data.startswith("gift:"):
                gift_ts = self._clean(self._gift, user_id, 3600)
                if len(gift_ts) >= settings.MAX_GIFT_ATTEMPTS:
                    await event.answer(
                        f"❌ Muitas tentativas de Gift Card. Aguarde 1 hora.",
                        show_alert=True,
                    )
                    return
                self._gift.setdefault(user_id, []).append(now)

        return await handler(event, data)
