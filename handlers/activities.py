import logging
from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from DataBase.models.activity_repo import ActivityRepository
from DataBase.models.application_repo import ApplicationRepository
from DataBase.models.user_repo import UserRepository
from DataBase.models import ApplicationCreate

from keyboards.inline_keyboards import (
    ActivityCallbackData,
    get_list_keyboard,
    get_item_details_keyboard,
    format_activity_details,
)

logger = logging.getLogger(__name__)
router = Router()

LIST_LIMIT = 5

@router.message(StateFilter(None), F.text == "🎯 Активности")
async def handle_activities(message: types.Message, state: FSMContext):
    await show_activities_list(message)

async def show_activities_list(message: types.Message, page: int = 0):
    activity_repo = ActivityRepository()
    offset = page * LIST_LIMIT
    activities = await activity_repo.get_active_activities(upcoming_only=True, limit=LIST_LIMIT, offset=offset)
    if not activities: await message.answer("Актуальных активностей пока нет."); return
    await message.answer(
        text=f"Найдено {len(activities)} активностей. Выберите для просмотра:",
        reply_markup=get_list_keyboard(items=activities, data_fabric=ActivityCallbackData)
    )

@router.callback_query(ActivityCallbackData.filter(F.action == "view"))
async def handle_view_activity(query: types.CallbackQuery, callback_data: ActivityCallbackData):
    activity_id = callback_data.item_id; user_id = query.from_user.id
    logger.info(f"User {user_id} viewing activity {activity_id}")
    activity_repo = ActivityRepository(); app_repo = ApplicationRepository()
    activity = await activity_repo.get_by_id(activity_id)
    if not activity:
        await query.answer("Активность недоступна.", show_alert=True)
        try: await query.message.delete()
        except Exception: pass
        return
    existing_application = await app_repo.get_by_user_and_target(user_id=user_id, activity_id=activity_id)
    details_text = format_activity_details(activity)
    keyboard = get_item_details_keyboard(item_id=activity.id, data_fabric=ActivityCallbackData, already_applied=(existing_application is not None))
    try:
        await query.answer()
        await query.message.edit_text(text=details_text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e: logger.error(f"Error editing message for activity {activity_id}: {e}")


@router.callback_query(ActivityCallbackData.filter(F.action == "apply"))
async def handle_apply_activity(query: types.CallbackQuery, callback_data: ActivityCallbackData):
    activity_id = callback_data.item_id
    user_id = query.from_user.id
    logger.info(f"User {user_id} attempting to apply for activity {activity_id}")
    user_repo = UserRepository()
    user = await user_repo.get_by_id(user_id)
    if not user or not user.phone or user.phone == "unknown" or not user.email or "@telegram.user" in user.email:
        logger.warning(f"User {user_id} profile is incomplete. Denying application for activity {activity_id}.")
        await query.answer(
            "Пожалуйста, сначала заполните ваш Профиль.\n"
            "Обязательно укажите корректные Телефон и Email.",
            show_alert=True
        )
        return
    logger.info(f"User {user_id} profile is complete. Proceeding with application for activity {activity_id}.")
    app_repo = ApplicationRepository()
    app_data = ApplicationCreate(user_id=user_id, activity_id=activity_id)
    created_app = await app_repo.add(app_data)
    if created_app:
        await query.answer("Вы успешно зарегистрировались на активность!", show_alert=True)
        logger.info(f"Application {created_app.id} created/found for user {user_id}, activity {activity_id}")
        try:
            activity_repo_inner = ActivityRepository()
            activity = await activity_repo_inner.get_by_id(activity_id)
            if activity:
                details_text = format_activity_details(activity)
                keyboard = get_item_details_keyboard(
                    item_id=activity_id,
                    data_fabric=ActivityCallbackData,
                    already_applied=True
                )
                await query.message.edit_text(text=details_text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Could not edit message after applying for activity {activity_id}: {e}")
    else:
        existing_app = await app_repo.get_by_user_and_target(user_id=user_id, activity_id=activity_id)
        if existing_app:
             await query.answer("Вы уже регистрировались на эту активность.", show_alert=True)
        else:
            await query.answer("Не удалось зарегистрироваться. Попробуйте позже.", show_alert=True)
            logger.error(f"Failed to process application for user {user_id} and activity {activity_id}")