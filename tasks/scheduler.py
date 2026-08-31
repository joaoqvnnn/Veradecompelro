import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.session import AsyncSessionLocal
from database.models import Payment, PaymentStatus
from services.payment import PaymentService

logger = logging.getLogger(__name__)

# Controle das tasks
_tasks: list[asyncio.Task] = []
_running = False


async def expire_pix_payments() -> int:
    """
    Marca como EXPIRED todos os PIX que passaram do prazo.
    Retorna a quantidade de pagamentos expirados.
    """
    payment_service = PaymentService()
    async with AsyncSessionLocal() as session:
        try:
            count = await payment_service.expire_pending(session)
            await session.commit()
            if count > 0:
                logger.info(f"⏳ {count} pagamento(s) PIX expirado(s)")
            return count
        except Exception as e:
            await session.rollback()
            logger.exception(f"Erro ao expirar PIX: {e}")
            return 0


async def cleanup_old_pending_payments(days: int = 7) -> int:
    """
    Remove (ou marca) pagamentos pendentes muito antigos.
    Útil para não acumular lixo no banco.
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Payment).where(
                    Payment.status == PaymentStatus.PENDING,
                    Payment.created_at < cutoff,
                )
            )
            payments = list(result.scalars().all())
            for p in payments:
                p.status = PaymentStatus.EXPIRED

            await session.commit()
            if payments:
                logger.info(f"🧹 {len(payments)} pagamento(s) antigo(s) limpos")
            return len(payments)
        except Exception as e:
            await session.rollback()
            logger.exception(f"Erro na limpeza de pagamentos: {e}")
            return 0


async def _pix_expiration_loop(interval_seconds: int = 60):
    """
    Loop que roda a cada X segundos verificando PIX expirados.
    """
    logger.info(f"Task de expiração de PIX iniciada (intervalo: {interval_seconds}s)")
    while _running:
        try:
            await expire_pix_payments()
        except Exception as e:
            logger.exception(f"Erro no loop de expiração: {e}")
        await asyncio.sleep(interval_seconds)


async def _cleanup_loop(interval_seconds: int = 3600):
    """
    Loop de limpeza mais pesada (a cada 1 hora por padrão).
    """
    logger.info(f"Task de limpeza iniciada (intervalo: {interval_seconds}s)")
    while _running:
        try:
            await cleanup_old_pending_payments(days=7)
        except Exception as e:
            logger.exception(f"Erro no loop de limpeza: {e}")
        await asyncio.sleep(interval_seconds)


async def start_background_tasks():
    """
    Inicia todas as tasks em background.
    Chamar no on_startup do bot.
    """
    global _running, _tasks
    if _running:
        return

    _running = True

    # Expira PIX a cada 60 segundos
    t1 = asyncio.create_task(_pix_expiration_loop(interval_seconds=60))
    # Limpeza pesada a cada 1 hora
    t2 = asyncio.create_task(_cleanup_loop(interval_seconds=3600))

    _tasks = [t1, t2]
    logger.info("✅ Tasks em background iniciadas")


async def stop_background_tasks():
    """
    Para todas as tasks de forma limpa.
    Chamar no on_shutdown.
    """
    global _running, _tasks
    _running = False

    for task in _tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    _tasks = []
    logger.info("🛑 Tasks em background finalizadas")
