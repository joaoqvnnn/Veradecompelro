import asyncio
import logging
import sys

from aiogram.types import BotCommand

from bot import create_bot, create_dispatcher
from config import settings
from database.session import init_db, close_db


logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def set_commands(bot):
    commands = [
        BotCommand(command="start", description="Iniciar o bot"),
        BotCommand(command="saldo", description="Ver meu saldo"),
        BotCommand(command="id", description="Ver meu ID"),
        BotCommand(command="termos", description="Termos de uso"),
        BotCommand(command="cancelar", description="Cancelar operação atual"),
    ]
    await bot.set_my_commands(commands)


async def on_startup(bot):
    logger.info("Iniciando banco de dados...")
    await init_db()
    await set_commands(bot)
    logger.info(f"Bot @{settings.BOT_USERNAME} iniciado com sucesso!")


async def on_shutdown(bot):
    logger.info("Encerrando conexões...")
    await close_db()
    await bot.session.close()
    logger.info("Bot finalizado.")


async def main():
    bot = create_bot()
    dp = create_dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Remove webhook caso exista e inicia polling
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Iniciando polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot interrompido pelo usuário.")
