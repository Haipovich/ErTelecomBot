import logging
from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from DataBase.models.application_repo import ApplicationRepository
from DataBase.models.job_repo import JobRepository
from DataBase.models.activity_repo import ActivityRepository
from DataBase.models import Job, Activity

from keyboards.inline_keyboards import (
    ApplicationCallbackData,
    get_my_applications_keyboard,
    get_application_details_keyboard,
    format_application_details,
)

logger = logging.getLogger(__name__)
router = Router()

LIST_LIMIT = 10

@router.message(StateFilter(None), F.text == "📄 Мои заявки")
async def handle_my_applications_button(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested their applications list via button.")
    await show_my_applications(message, user_id, is_new_message=True)

async def show_my_applications(target: types.Message | types.CallbackQuery, user_id: int, page: int = 0, is_new_message: bool = False):
    app_repo = ApplicationRepository()
    offset = page * LIST_LIMIT
    applications_data = await app_repo.get_user_applications_with_details(
        user_id=user_id, limit=LIST_LIMIT, offset=offset
    )
    if not applications_data:
        text = "У вас пока нет отправленных заявок."
        keyboard = None
    else:
        text = "Ваши заявки (нажмите для просмотра деталей):"
        keyboard = get_my_applications_keyboard(applications_data)
    current_message: types.Message | None = None
    if isinstance(target, types.CallbackQuery):
        current_message = target.message
    elif isinstance(target, types.Message):
        current_message = target
    if not current_message:
         logger.error("Target for show_my_applications is neither Message nor CallbackQuery")
         return
    if is_new_message:
        if isinstance(target, types.CallbackQuery):
             try:
                 await target.message.delete()
             except Exception as e:
                 logger.warning(f"Could not delete previous message for user {user_id} on back action: {e}")
             await current_message.answer(text=text, reply_markup=keyboard)
        else:
            await current_message.answer(text=text, reply_markup=keyboard)
        if isinstance(target, types.CallbackQuery) and ApplicationCallbackData.unpack(target.data).action != "delete":
            await target.answer()
    else:
         if current_message.text == text and current_message.reply_markup == keyboard:
             if isinstance(target, types.CallbackQuery): await target.answer("Список заявок не изменился.")
             return
         try:
             await current_message.edit_text(text=text, reply_markup=keyboard)
             if isinstance(target, types.CallbackQuery): await target.answer()
         except Exception as e:
             logger.error(f"Error editing message for my_applications for user {user_id}: {e}")
             try: await current_message.delete()
             except Exception as del_e: logger.warning(f"Could not delete msg for user {user_id} after edit error: {del_e}")
             await current_message.answer(text=text, reply_markup=keyboard) 
             if isinstance(target, types.CallbackQuery):
                 await target.answer("Не удалось обновить предыдущее сообщение. Показан актуальный список.", show_alert=True)

@router.callback_query(ApplicationCallbackData.filter(F.action == "view_details"))
async def handle_view_application_details(query: types.CallbackQuery, callback_data: ApplicationCallbackData):
    app_id = callback_data.item_id
    user_id = query.from_user.id
    logger.info(f"User {user_id} viewing details for application {app_id}")
    app_repo = ApplicationRepository()
    application = await app_repo.get_by_id_and_user(app_id, user_id)
    if not application:
        await query.answer("Не удалось найти информацию по этой заявке.", show_alert=True)
        try: await query.message.delete()
        except Exception: pass
        return
    target_details: Job | Activity | None = None
    if application.job_id:
        job_repo = JobRepository(); target_details = await job_repo.get_by_id(application.job_id)
    elif application.activity_id:
        activity_repo = ActivityRepository(); target_details = await activity_repo.get_by_id(application.activity_id)
    details_text = format_application_details(application, target_details)
    keyboard = get_application_details_keyboard(application)
    try:
        await query.message.edit_text(text=details_text, reply_markup=keyboard, parse_mode="Markdown")
        await query.answer()
    except Exception as e:
        logger.error(f"Error editing message for application details {app_id}: {e}")
        await query.answer("Не удалось обновить сообщение.", show_alert=True)

@router.callback_query(ApplicationCallbackData.filter(F.action == "delete"))
async def handle_delete_application(query: types.CallbackQuery, callback_data: ApplicationCallbackData):
    app_id = callback_data.item_id
    user_id = query.from_user.id
    logger.info(f"User {user_id} attempting to delete application {app_id}.")
    app_repo = ApplicationRepository()
    deleted = await app_repo.delete_by_user(app_id=app_id, user_id=user_id)
    if deleted:
        logger.info(f"Application {app_id} successfully deleted by user {user_id}.")
        await query.answer("Заявка успешно удалена.", show_alert=False)
        await show_my_applications(query, user_id, is_new_message=True)
    else:
        logger.warning(f"Failed to delete application {app_id} for user {user_id} or deletion not allowed.")
        await query.answer(
            "Не удалось удалить заявку.\\nВозможно, ее статус уже изменился или произошла ошибка.",
            show_alert=True
        )
        application = await app_repo.get_by_id_and_user(app_id, user_id)
        if application:
             target_details: Job | Activity | None = None
             if application.job_id: job_repo = JobRepository(); target_details = await job_repo.get_by_id(application.job_id)
             elif application.activity_id: activity_repo = ActivityRepository(); target_details = await activity_repo.get_by_id(application.activity_id)
             details_text = format_application_details(application, target_details)
             keyboard = get_application_details_keyboard(application)
             try:
                 await query.message.edit_text(text=details_text, reply_markup=keyboard, parse_mode="Markdown")
             except Exception: pass
        else:
             await show_my_applications(query, user_id, is_new_message=True)

@router.callback_query(ApplicationCallbackData.filter(F.action == "back_to_list"))
async def handle_back_to_applications_list(query: types.CallbackQuery, callback_data: ApplicationCallbackData):
    user_id = query.from_user.id
    logger.info(f"User {user_id} going back to applications list.")
    await show_my_applications(query, user_id, is_new_message=True)
