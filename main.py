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
from db_listener import listen_for_db_notifications
from scheduler import setup_scheduler_jobs, shutdown_scheduler

listener_task = None

async def main():
    global listener_task
    logger.info("Starting bot...")
    await init_db_pool()

    dp = Dispatcher(storage=MemoryStorage())
    default_properties = DefaultBotProperties(parse_mode=ParseMode.HTML)
    bot = Bot(token=config.bot.token, default=default_properties)

    for router in routers_list:
        dp.include_router(router)

    listener_task = asyncio.create_task(listen_for_db_notifications(bot))

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        logger.info("Main function: Finalizing...")
        if listener_task and not listener_task.done():
            logger.info("Main function: Cancelling listener task...")
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                logger.info("Main function: Listener task cancelled successfully.")
        await bot.session.close()
        logger.info("Bot stopped or polling ended.")

async def on_startup(dispatcher: Dispatcher, bot: Bot):
    logger.info("Bot started successfully.")
    await set_bot_commands(bot)
    setup_scheduler_jobs(bot)

async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
    global listener_task
    logger.warning("Shutting down bot...")
    if listener_task and not listener_task.done():
        logger.info("OnShutdown: Cancelling listener task...")
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            logger.info("OnShutdown: Listener task cancelled successfully.")
    await shutdown_scheduler()
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
