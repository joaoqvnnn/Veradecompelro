import logging
from aiohttp import web

from config import settings
from database.session import AsyncSessionLocal
from database.models import PaymentStatus
from services.payment import PaymentService

logger = logging.getLogger(__name__)
payment_service = PaymentService()

# Bot será injetado depois
_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


async def mercadopago_webhook(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        data = dict(request.query)

    logger.info(f"Webhook recebido: {data}")

    topic = data.get("type") or data.get("topic") or data.get("action", "")
    resource_id = None

    if "data" in data and isinstance(data["data"], dict):
        resource_id = data["data"].get("id")
    elif "id" in data:
        resource_id = data.get("id")

    if not resource_id:
        resource_id = request.query.get("id") or request.query.get("data.id")

    if not resource_id:
        logger.warning("Webhook sem ID de pagamento")
        return web.Response(text="ok", status=200)

    if topic and "payment" not in str(topic).lower():
        return web.Response(text="ignored", status=200)

    gateway_id = str(resource_id)

    async with AsyncSessionLocal() as session:
        try:
            payment = await payment_service.process_webhook(session, gateway_id)
            await session.commit()

            if payment and payment.status == PaymentStatus.APPROVED and _bot:
                from utils.notify import notify_user_payment_approved
                await notify_user_payment_approved(_bot, payment)
                logger.info(
                    f"✅ Pagamento aprovado e usuário notificado | "
                    f"User {payment.user_id} | R$ {payment.amount}"
                )

        except Exception as e:
            await session.rollback()
            logger.exception(f"Erro ao processar webhook: {e}")

    return web.Response(text="ok", status=200)


async def health_check(request: web.Request) -> web.Response:
    return web.Response(text="ok", status=200)


def create_webhook_app() -> web.Application:
    app = web.Application()
    app.router.add_post(settings.WEBHOOK_PATH, mercadopago_webhook)
    app.router.add_get(settings.WEBHOOK_PATH, mercadopago_webhook)
    app.router.add_get("/health", health_check)
    return app


async def start_webhook_server():
    app = create_webhook_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.WEBHOOK_HOST, settings.WEBHOOK_PORT)
    await site.start()
    logger.info(
        f"Webhook rodando em http://{settings.WEBHOOK_HOST}:{settings.WEBHOOK_PORT}{settings.WEBHOOK_PATH}"
    )
    return runner
