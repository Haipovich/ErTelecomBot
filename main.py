import asyncio
import logging
import os
from aiogram.client.default import DefaultBotProperties

if os.name == 'nt':
    print("Applying WindowsSelectorEventLoopPolicy for asyncio.")
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config

from DataBase import init_db_pool, close_db_pool
from handlers import routers_list

async def main():
    logger.info("Starting bot...")
    await init_db_pool()

    dp = Dispatcher(storage=MemoryStorage())
    default_properties = DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)  # Или ParseMode.HTML
    bot = Bot(token=config.bot.token, default=default_properties)

    for router in routers_list:
        dp.include_router(router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")

async def on_startup(dispatcher: Dispatcher, bot: Bot):
    logger.info("Bot started successfully.")
    await set_bot_commands(bot)

async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
    logger.warning("Shutting down bot...")
    await close_db_pool()
    logger.info("Database pool closed.")

async def set_bot_commands(bot: Bot):
    commands = [
        types.BotCommand(command="/start", description="🚀 Перезапустить бота / Главное меню"),
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Bot commands set successfully.")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually.")
    except Exception as e:
         logger.critical(f"Critical error in main execution: {e}", exc_info=True)
