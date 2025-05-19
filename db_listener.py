import asyncio
import logging
import json
import psycopg
from aiogram import Bot

from notifications import send_application_status_update, process_activity_update_from_db_notify
from DataBase.models import ApplicationStatus
from DataBase.models.application_repo import ApplicationRepository

from DataBase import get_dedicated_db_connection

logger = logging.getLogger(__name__)

APPLICATION_UPDATES_CHANNEL = "application_updates"
ACTIVITY_UPDATES_CHANNEL = "activity_updates"

async def process_application_notification(bot_instance: Bot, payload_str: str, app_repo: ApplicationRepository):
    try:
        payload_data = json.loads(payload_str)
        app_id = int(payload_data.get("id"))
        user_id = int(payload_data.get("user_id"))
        status = payload_data.get("status")
        hr_comment = payload_data.get("hr_comment")

        if not all([app_id, user_id, status]):
            logger.error(f"DB Listener ({APPLICATION_UPDATES_CHANNEL}): Missing required data in payload: {payload_str}")
            return

        try:
            status_enum = ApplicationStatus(status)
        except ValueError:
            logger.error(f"DB Listener ({APPLICATION_UPDATES_CHANNEL}): Invalid status value: {status}")
            return

        app_details = await app_repo.get_application_details_for_notification(app_id)
        if not app_details:
            logger.error(f"DB Listener ({APPLICATION_UPDATES_CHANNEL}): Application {app_id} details not found. Skipping.")
            return
        
        target_title = app_details.get('target_title', 'Неизвестная цель')

        logger.info(f"DB Listener ({APPLICATION_UPDATES_CHANNEL}): Queuing notification for app_id: {app_id}, user_id: {user_id}, status: {status_enum}")
        
        asyncio.create_task(
            send_application_status_update(
                bot=bot_instance,
                user_id=user_id,
                application_id=app_id,
                target_title=target_title,
                new_status=status_enum, 
                hr_comment=hr_comment
            )
        )

    except json.JSONDecodeError:
        logger.error(f"DB Listener ({APPLICATION_UPDATES_CHANNEL}): Failed to decode JSON payload: {payload_str}")
    except (ValueError, TypeError) as e: 
        logger.error(f"DB Listener ({APPLICATION_UPDATES_CHANNEL}): Invalid data in payload '{payload_str}': {e}")
    except Exception as e:
        logger.error(f"DB Listener ({APPLICATION_UPDATES_CHANNEL}): Error processing notification for payload '{payload_str}': {e}", exc_info=True)

async def listen_for_db_notifications(bot_instance: Bot):
    logger.info("Starting PostgreSQL listener for DB notifications...")
    conn = None
    app_repo = ApplicationRepository() 

    while True:
        try:
            conn = await get_dedicated_db_connection() 
            if conn is None:
                logger.error("DB Listener: Failed to get DB connection. Retrying in 30s.")
                await asyncio.sleep(30)
                continue

            async with conn.cursor() as cur:
                await cur.execute(f"LISTEN {APPLICATION_UPDATES_CHANNEL};")
                await cur.execute(f"LISTEN {ACTIVITY_UPDATES_CHANNEL};")
                logger.info(f"DB Listener: Successfully listening on channels: '{APPLICATION_UPDATES_CHANNEL}', '{ACTIVITY_UPDATES_CHANNEL}'.")

                while True:
                    async for notification in conn.notifies():
                        logger.info(f"DB Listener: Received DB notification: PID={notification.pid}, Channel='{notification.channel}', Payload='{notification.payload}'")
                        
                        if notification.channel == APPLICATION_UPDATES_CHANNEL:
                            await process_application_notification(bot_instance, notification.payload, app_repo)
                        elif notification.channel == ACTIVITY_UPDATES_CHANNEL:
                            asyncio.create_task(process_activity_update_from_db_notify(bot_instance, notification.payload))
                        else:
                            logger.warning(f"DB Listener: Received notification on unhandled channel: {notification.channel}")
        
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info("DB Listener: Listener stopped by CancelledError or KeyboardInterrupt.")
            if conn and not conn.closed:
                try: await conn.close()
                except Exception as e: logger.error(f"DB Listener: Error closing DB connection on stop: {e}")
            break
        except Exception as e:
            logger.error(f"DB Listener: Unexpected error: {e}. Retrying in 30 seconds...", exc_info=True)
            if conn and not conn.closed:
                try: await conn.close()
                except Exception as e_close: logger.error(f"DB Listener: Error closing DB connection during generic error handling: {e_close}")
            conn = None
            await asyncio.sleep(30)
