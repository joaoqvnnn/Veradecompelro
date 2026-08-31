import logging
from sqlalchemy import select
from aiogram import Bot

from config import settings
from database.session import AsyncSessionLocal
from database.models import Product, ProductStatus

logger = logging.getLogger(__name__)


async def check_low_stock_and_notify(bot: Bot) -> None:
    """
    Verifica produtos com estoque baixo e avisa os admins.
    Pode ser chamado periodicamente.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Product).where(
                Product.stock_count <= settings.LOW_STOCK_THRESHOLD,
                Product.status == ProductStatus.ACTIVE,
            )
        )
        products = list(result.scalars().all())

    if not products:
        return

    lines = ["⚠️ <b>ALERTA DE ESTOQUE BAIXO</b>\n"]
    for p in products:
        lines.append(f"🔴 {p.emoji} <b>{p.name}</b> — restam <b>{p.stock_count}</b>")

    text = "\n".join(lines)

    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Falha ao notificar admin {admin_id}: {e}")
