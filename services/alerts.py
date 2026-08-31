from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot

from database.models import ProductAlert, Product, User


class AlertService:

    @staticmethod
    async def toggle_alert(
        session: AsyncSession,
        user_id: int,
        product_id: int,
    ) -> bool:
        """
        Ativa ou desativa o alerta.
        Retorna True se ficou ativo, False se desativou.
        """
        result = await session.execute(
            select(ProductAlert).where(
                ProductAlert.user_id == user_id,
                ProductAlert.product_id == product_id,
            )
        )
        alert = result.scalar_one_or_none()

        if alert:
            alert.is_active = not alert.is_active
            if alert.is_active:
                alert.notified_at = None
            await session.flush()
            return alert.is_active

        # Cria novo alerta ativo
        alert = ProductAlert(
            user_id=user_id,
            product_id=product_id,
            is_active=True,
        )
        session.add(alert)
        await session.flush()
        return True

    @staticmethod
    async def get_user_alerts(
        session: AsyncSession,
        user_id: int,
    ) -> List[ProductAlert]:
        result = await session.execute(
            select(ProductAlert)
            .where(ProductAlert.user_id == user_id)
            .order_by(ProductAlert.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_active_subscribers(
        session: AsyncSession,
        product_id: int,
    ) -> List[int]:
        """Retorna lista de user_ids inscritos e ativos nesse produto."""
        result = await session.execute(
            select(ProductAlert.user_id).where(
                ProductAlert.product_id == product_id,
                ProductAlert.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def notify_restock(
        session: AsyncSession,
        bot: Bot,
        product_id: int,
        added_quantity: int,
    ) -> int:
        """
        Notifica todos os usuários que ativaram alerta deste produto.
        Retorna quantos foram notificados.
        """
        product = await session.get(Product, product_id)
        if not product:
            return 0

        user_ids = await AlertService.get_active_subscribers(session, product_id)
        if not user_ids:
            return 0

        text = (
            f"🔥 <b>PRODUTO REABASTECIDO!</b>\n\n"
            f"{product.emoji} <b>{product.name}</b>\n"
            f"📦 Novas unidades disponíveis: <b>{added_quantity}</b>\n"
            f"📦 Estoque atual: <b>{product.stock_count}</b>\n\n"
            f"Corra antes que acabe!"
        )

        notified = 0
        now = datetime.now(timezone.utc)

        for user_id in user_ids:
            try:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="💳 Ver Produto",
                        callback_data=f"product:{product_id}"
                    )]
                ])
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=kb,
                    parse_mode="HTML",
                )
                notified += 1

                # Atualiza notified_at
                result = await session.execute(
                    select(ProductAlert).where(
                        ProductAlert.user_id == user_id,
                        ProductAlert.product_id == product_id,
                    )
                )
                alert = result.scalar_one_or_none()
                if alert:
                    alert.notified_at = now

            except Exception:
                # Usuário bloqueou o bot ou outro erro — ignora
                continue

        await session.flush()
        return notified
