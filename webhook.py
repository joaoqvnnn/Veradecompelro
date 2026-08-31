import logging
from aiohttp import web
from sqlalchemy import select

from config import settings
from database.session import AsyncSessionLocal
from database.models import Payment, PaymentStatus
from services.payment import PaymentService

logger = logging.getLogger(__name__)
payment_service = PaymentService()


async def mercadopago_webhook(request: web.Request) -> web.Response:
    """
    Endpoint que recebe as notificações do Mercado Pago.
    URL final: https://seudominio.com/webhook/mercadopago
    """
    try:
        # Mercado Pago pode enviar via query string ou body
        data = await request.json()
    except Exception:
        data = dict(request.query)

    logger.info(f"Webhook recebido: {data}")

    # Formato típico do MP:
    # {"action": "payment.updated", "data": {"id": "123456789"}}
    topic = data.get("type") or data.get("topic") or data.get("action", "")
    resource_id = None

    if "data" in data and isinstance(data["data"], dict):
        resource_id = data["data"].get("id")
    elif "id" in data:
        resource_id = data.get("id")
    elif "data.id" in data:
        resource_id = data.get("data.id")

    # Também aceita ?id=xxx&topic=payment
    if not resource_id:
        resource_id = request.query.get("id") or request.query.get("data.id")

    if not resource_id:
        logger.warning("Webhook sem ID de pagamento")
        return web.Response(text="ok", status=200)

    # Só processamos eventos de payment
    if topic and "payment" not in str(topic).lower():
        return web.Response(text="ignored", status=200)

    gateway_id = str(resource_id)

    async with AsyncSessionLocal() as session:
        try:
            payment = await payment_service.process_webhook(session, gateway_id)
            await session.commit()

            if payment and payment.status == PaymentStatus.APPROVED:
                logger.info(
                    f"✅ Pagamento aprovado | User {payment.user_id} | "
                    f"R$ {payment.amount} + bônus R$ {payment.bonus_amount}"
                )
                # Aqui você pode disparar notificação para o usuário via bot
                # (ver função notify_user_payment mais abaixo)
            else:
                logger.info(f"Webhook processado | gateway_id={gateway_id} | status={payment.status if payment else 'not found'}")

        except Exception as e:
            await session.rollback()
            logger.exception(f"Erro ao processar webhook: {e}")
            # Retornamos 200 mesmo em erro para o MP não reenviar infinitamente
            # (ajuste conforme sua necessidade)

    return web.Response(text="ok", status=200)


async def health_check(request: web.Request) -> web.Response:
    return web.Response(text="ok", status=200)


def create_webhook_app() -> web.Application:
    app = web.Application()
    app.router.add_post(settings.WEBHOOK_PATH, mercadopago_webhook)
    app.router.add_get(settings.WEBHOOK_PATH, mercadopago_webhook)  # MP às vezes usa GET
    app.router.add_get("/health", health_check)
    return app


async def start_webhook_server():
    """Inicia o servidor HTTP do webhook."""
    app = create_webhook_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.WEBHOOK_HOST, settings.WEBHOOK_PORT)
    await site.start()
    logger.info(
        f"Webhook rodando em http://{settings.WEBHOOK_HOST}:{settings.WEBHOOK_PORT}{settings.WEBHOOK_PATH}"
    )
    return runner
