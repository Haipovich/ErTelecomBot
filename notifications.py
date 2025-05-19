import logging
from typing import Optional
from aiogram import Bot
from aiogram.utils.markdown import hbold, hitalic
from DataBase.models import ApplicationStatus, Application, Activity 
from DataBase.models.application_repo import ApplicationRepository
from DataBase.models.activity_repo import ActivityRepository
from datetime import datetime
import json

logger = logging.getLogger(__name__)

STATUS_TRANSLATIONS = {
    ApplicationStatus.PENDING: "Рассматривается",
    ApplicationStatus.UNDER_REVIEW: "На рассмотрении",
    ApplicationStatus.INTERVIEW: "Назначено собеседование",
    ApplicationStatus.OFFER: "Предложение о работе",
    ApplicationStatus.HIRED: "Вы приняты!",
    ApplicationStatus.REJECTED: "Отклонена",
    ApplicationStatus.WITHDRAWN: "Отозвана вами"
}

async def send_application_status_update(
    bot: Bot,
    user_id: int,
    application_id: int,
    target_title: str,
    new_status: ApplicationStatus,
    hr_comment: Optional[str]
):
    status_text = STATUS_TRANSLATIONS.get(new_status, str(new_status.value))

    main_message_parts = [
        f"🔔 Обновление статуса вашей заявки!",
        f"Заявка на: {hbold(target_title)} (ID: {application_id})",
        f"Новый статус: {hbold(status_text)}"
    ]
    
    message_text = "\\n".join(main_message_parts) 

    if hr_comment: 
        message_text += f"\\n\\nКомментарий от HR:\\n{hitalic(hr_comment)}"

    try:
        await bot.send_message(user_id, message_text)
        logger.info(f"Sent status update to user {user_id} for application {application_id} (new status: {new_status}).")
    except Exception as e:
        logger.error(f"Failed to send status update to user {user_id} for application {application_id}: {e}")
        
async def process_status_change_and_notify(
    bot_instance: Bot,
    application_id_to_update: int,
    new_status_for_app: ApplicationStatus,
    hr_comment_for_app: Optional[str]
):
    app_repo = ApplicationRepository()

    app_details = await app_repo.get_application_details_for_notification(application_id_to_update)

    if not app_details:
        logger.error(f"Application {application_id_to_update} not found. Cannot send notification.")
        return

    user_id_to_notify = app_details.get('user_id')
    target_title = app_details.get('target_title', 'Неизвестная цель')

    if not user_id_to_notify:
        logger.error(f"User ID not found for application {application_id_to_update}. Cannot send notification.")
        return

    update_successful = await app_repo.update_status_and_comment(
        application_id=application_id_to_update,
        new_status=new_status_for_app,
        hr_comment=hr_comment_for_app
    )

    if update_successful:
        logger.info(f"(Via process_status_change_and_notify) Application {application_id_to_update} status successfully updated to {new_status_for_app}.")
        await send_application_status_update(
            bot=bot_instance,
            user_id=user_id_to_notify,
            application_id=application_id_to_update,
            target_title=target_title,
            new_status=new_status_for_app,
            hr_comment=hr_comment_for_app
        )
    else:
        logger.error(f"(Via process_status_change_and_notify) Failed to update status for application {application_id_to_update}.")

async def process_application_update_from_db_notify(
    bot_instance: Bot,
    application_id: int
):
    app_repo = ApplicationRepository()
    logger.info(f"DB Notify: Processing update for application_id: {application_id}")

    app_details = await app_repo.get_application_details_for_notification(application_id)

    if not app_details:
        logger.error(f"DB Notify: Application {application_id} not found. Cannot send notification.")
        return

    user_id_to_notify = app_details.get('user_id')
    target_title = app_details.get('target_title', 'Неизвестная цель')
    actual_new_status: Optional[ApplicationStatus] = app_details.get('status') 
    actual_hr_comment: Optional[str] = app_details.get('hr_comment')

    if not user_id_to_notify:
        logger.error(f"DB Notify: User ID not found for application {application_id}. Cannot send notification.")
        return
    
    if not actual_new_status:
        logger.error(f"DB Notify: Status not found for application {application_id} after fetching details. Cannot send notification.")
        return

    logger.info(f"DB Notify: Sending notification for application {application_id}, new status {actual_new_status}.")
    await send_application_status_update(
        bot=bot_instance,
        user_id=user_id_to_notify,
        application_id=application_id,
        target_title=target_title,
        new_status=actual_new_status,
        hr_comment=actual_hr_comment
    )

async def send_activity_time_change_notification(
    bot: Bot,
    user_id: int,
    activity_title: str,
    activity_id: int,
    new_start_time: datetime,
    new_end_time: datetime
):
    message_text = (
        f"🔔 Важное обновление по активности!\\n\\n"
        f"Время проведения мероприятия {hbold(activity_title)} (ID: {activity_id}) было изменено.\\n\\n"
        f"Новое время:\\n"
        f"▶️ Начало: {hbold(new_start_time.strftime('%d.%m.%Y в %H:%M %Z'))}\\n"
        f"⏹️ Окончание: {hbold(new_end_time.strftime('%d.%m.%Y в %H:%M %Z'))}\\n\\n"
        f"Пожалуйста, проверьте актуальное расписание."
    )
    try:
        await bot.send_message(user_id, message_text)
        logger.info(f"Sent activity time change notification to user {user_id} for activity {activity_id}.")
    except Exception as e:
        logger.error(f"Failed to send activity time change notification to user {user_id} for activity {activity_id}: {e}")

async def process_activity_update_from_db_notify(bot_instance: Bot, payload_str: str):
    logger.info(f"DB Notify: Processing activity update with payload: {payload_str}")
    try:
        payload = json.loads(payload_str)
        activity_id = payload.get('id')
        if activity_id is None:
            logger.error(f"DB Notify: 'id' (for activity_id) not found in payload: {payload_str}")
            return
        
    except json.JSONDecodeError:
        logger.error(f"DB Notify: Invalid JSON payload for activity update: {payload_str}")
        try:
            activity_id = int(payload_str)
            logger.warning(f"DB Notify: Payload was not JSON, attempting to parse as int activity_id: {activity_id}")
        except ValueError:
            logger.error(f"DB Notify: Payload is not valid JSON and not a simple activity_id: {payload_str}")
            return
    
    if not isinstance(activity_id, int):
        logger.error(f"DB Notify: Extracted activity_id is not an integer: {activity_id}. Payload was: {payload_str}")
        return

    activity_repo = ActivityRepository()
    app_repo = ApplicationRepository()

    activity_details = await activity_repo.get_activity_details_for_notification(activity_id)

    if not activity_details:
        logger.error(f"DB Notify: Activity {activity_id} not found. Cannot send notifications.")
        return

    if not activity_details.start_time or not activity_details.end_time:
        logger.error(f"DB Notify: Activity {activity_id} fetched, but start_time or end_time is missing. Title: {activity_details.title}. Cannot send notifications.")
        return

    user_ids_to_notify = await app_repo.get_user_ids_for_activity(activity_id)

    if not user_ids_to_notify:
        logger.info(f"DB Notify: No users found for activity {activity_id}. No notifications to send.")
        return

    logger.info(f"DB Notify: Sending activity time change notifications for activity {activity_id} (Title: {activity_details.title}) to users: {user_ids_to_notify}")

    for user_id in user_ids_to_notify:
        await send_activity_time_change_notification(
            bot=bot_instance,
            user_id=user_id,
            activity_title=activity_details.title,
            activity_id=activity_id,
            new_start_time=activity_details.start_time,
            new_end_time=activity_details.end_time
        )
