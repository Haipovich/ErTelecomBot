import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError

from DataBase.models import ReminderType, Activity 
from DataBase.models.activity_repo import ActivityRepository 
from DataBase.models.activity_reminder_repo import ActivityReminderRepository

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Europe/Moscow") 

async def send_actual_reminder_message(
    bot: Bot, 
    user_id: int, 
    activity_id: int, 
    activity_title: str, 
    activity_start_time_str: str 
):
    message_text = (
        f"👋 Напоминание!\\n\\n"
        f"Мероприятие '{activity_title}' (ID: {activity_id}), на которое вы записаны, "
        f"начнется примерно через 24 часа - {activity_start_time_str}.\\n\\n"
        f"Не пропустите!"
    )
    try:
        await bot.send_message(user_id, message_text)
        logger.info(f"Successfully sent 24h reminder to user {user_id} for activity {activity_id} ('{activity_title}').")
    except Exception as e:
        logger.error(f"Failed to send 24h reminder message to user {user_id} for activity {activity_id}: {e}")
        
async def schedule_reminder_for_activity(
    bot: Bot, 
    user_id: int, 
    activity: Activity 
):
    reminder_repo = ActivityReminderRepository()
    
    activity_id = activity.id
    activity_title = activity.title
    activity_start_time = activity.start_time

    already_handled = await reminder_repo.has_reminder_been_sent(user_id, activity_id, ReminderType.H24)
    if already_handled:
        logger.info(f"Reminder for user {user_id}, activity {activity_id} (type {ReminderType.H24.value}) already handled (scheduled/sent). Skipping.")
        return

    run_date = activity_start_time - timedelta(hours=24)
    now_in_scheduler_tz = datetime.now(scheduler.timezone)

    if run_date <= now_in_scheduler_tz:
        logger.info(f"Cannot schedule 24h reminder for activity {activity_id} for user {user_id}. Calculated run_date {run_date} is in the past or too soon.")
        return

    job_id = f"activity_reminder_user{user_id}_activity{activity_id}_type{ReminderType.H24.value}"
    
    start_time_for_message = activity_start_time.strftime("%d.%m.%Y в %H:%M")
    if activity_start_time.tzinfo:
        start_time_for_message += f" {activity_start_time.tzinfo}"
    else: 
        start_time_for_message += f" ({scheduler.timezone})" 

    try:
        existing_job = scheduler.get_job(job_id)
        if existing_job:
            logger.warning(f"Job {job_id} already exists in scheduler. Skipping add. This case should ideally be caught by has_reminder_been_sent.")
            if not await reminder_repo.has_reminder_been_sent(user_id, activity_id, ReminderType.H24):
                 await reminder_repo.add_reminder_sent(user_id, activity_id, ReminderType.H24)
            return

        scheduler.add_job(
            send_actual_reminder_message, 
            'date', 
            run_date=run_date, 
            args=[bot, user_id, activity_id, activity_title, start_time_for_message],
            id=job_id,
            replace_existing=True 
        )
        await reminder_repo.add_reminder_sent(user_id, activity_id, ReminderType.H24)
        logger.info(f"Scheduled 24h reminder job {job_id} for activity {activity_id} to user {user_id} at {run_date}.")
    except Exception as e:
        logger.error(f"Failed to schedule 24h reminder job for activity {activity_id} to user {user_id}: {e}", exc_info=True)

async def cancel_scheduled_reminder(user_id: int, activity_id: int, reminder_type: ReminderType = ReminderType.H24):
    job_id = f"activity_reminder_user{user_id}_activity{activity_id}_type{reminder_type.value}"
    reminder_repo = ActivityReminderRepository()
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Successfully removed job {job_id} from scheduler.")
    except JobLookupError:
        logger.info(f"Job {job_id} not found in scheduler, could not remove (might have already run or never existed).")
    except Exception as e:
        logger.error(f"Error removing job {job_id} from scheduler: {e}", exc_info=True)
    
    deleted_from_db = await reminder_repo.delete_reminder(user_id, activity_id, reminder_type)
    if not deleted_from_db:
        logger.warning(f"Could not delete reminder from DB for user {user_id}, activity {activity_id}, type {reminder_type.value} (it might not have existed).")


def setup_scheduler_jobs(bot: Bot): 
    try:
        if not scheduler.running:
            scheduler.start()
            logger.info("Scheduler started.")
        else:
            logger.info("Scheduler already running.")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}", exc_info=True)

async def shutdown_scheduler():
    if scheduler and scheduler.running:
        logger.info("Scheduler: Shutting down...")
        scheduler.shutdown(wait=False)
        logger.info("Scheduler: Shutdown complete.") 
