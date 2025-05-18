import logging
from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from DataBase.models.job_repo import JobRepository
from DataBase.models.application_repo import ApplicationRepository
from DataBase.models.user_repo import UserRepository
from DataBase.models import JobType, ApplicationCreate

from keyboards.inline_keyboards import (
    JobCallbackData,
    get_list_keyboard,
    get_item_details_keyboard,
    format_job_details,
)

logger = logging.getLogger(__name__)
router = Router()

LIST_LIMIT = 5

@router.message(StateFilter(None), F.text == "📚 Стажировки")
async def handle_internships(message: types.Message, state: FSMContext):
    await show_jobs_list(message, job_type=JobType.INTERNSHIP)

@router.message(StateFilter(None), F.text == "💼 Вакансии")
async def handle_vacancies(message: types.Message, state: FSMContext):
    await show_jobs_list(message, job_type=JobType.VACANCY)

async def show_jobs_list(message: types.Message, job_type: JobType, page: int = 0):
    job_repo = JobRepository()
    offset = page * LIST_LIMIT
    jobs = await job_repo.get_active_jobs(job_type=job_type, limit=LIST_LIMIT, offset=offset)
    type_text = "стажировок" if job_type == JobType.INTERNSHIP else "вакансий"
    if not jobs: await message.answer(f"Активных {type_text} пока нет."); return
    await message.answer(
        text=f"Найдено {len(jobs)} {type_text}. Выберите для просмотра:",
        reply_markup=get_list_keyboard(items=jobs, data_fabric=JobCallbackData)
    )

@router.callback_query(JobCallbackData.filter(F.action == "view"))
async def handle_view_job(query: types.CallbackQuery, callback_data: JobCallbackData):
    job_id = callback_data.item_id; user_id = query.from_user.id
    logger.info(f"User {user_id} viewing job {job_id}")
    job_repo = JobRepository(); app_repo = ApplicationRepository()
    job = await job_repo.get_by_id(job_id)
    if not job:
        await query.answer("Вакансия/стажировка недоступна.", show_alert=True)
        try: await query.message.delete()
        except Exception: pass
        return
    existing_application = await app_repo.get_by_user_and_target(user_id=user_id, job_id=job_id)
    details_text = format_job_details(job)
    keyboard = get_item_details_keyboard(item_id=job.id, data_fabric=JobCallbackData, already_applied=(existing_application is not None))
    try:
        await query.answer()
        await query.message.edit_text(text=details_text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e: logger.error(f"Error editing message for job {job_id}: {e}")


@router.callback_query(JobCallbackData.filter(F.action == "apply"))
async def handle_apply_job(query: types.CallbackQuery, callback_data: JobCallbackData):
    job_id = callback_data.item_id
    user_id = query.from_user.id
    logger.info(f"User {user_id} attempting to apply for job {job_id}")
    user_repo = UserRepository()
    user = await user_repo.get_by_id(user_id)
    if not user or not user.phone or user.phone == "unknown" or not user.email or "@telegram.user" in user.email:
        logger.warning(f"User {user_id} profile is incomplete. Denying application for job {job_id}.")
        await query.answer(
            "Пожалуйста, сначала заполните ваш Профиль.\n"
            "Обязательно укажите корректные Телефон и Email.",
            show_alert=True
        )
        return

    logger.info(f"User {user_id} profile is complete. Proceeding with application for job {job_id}.")
    app_repo = ApplicationRepository()
    app_data = ApplicationCreate(user_id=user_id, job_id=job_id)

    created_app = await app_repo.add(app_data)

    if created_app:
        await query.answer("Ваш отклик успешно отправлен!", show_alert=True)
        logger.info(f"Application {created_app.id} created/found for user {user_id}, job {job_id}")
        try:
            job_repo_inner = JobRepository()
            job = await job_repo_inner.get_by_id(job_id)
            if job:
                details_text = format_job_details(job)
                keyboard = get_item_details_keyboard(
                    item_id=job_id,
                    data_fabric=JobCallbackData,
                    already_applied=True
                )
                await query.message.edit_text(
                    text=details_text, reply_markup=keyboard, parse_mode="Markdown"
                )
        except Exception as e:
            logger.warning(f"Could not edit message after applying for job {job_id}: {e}")

    else:
        existing_app = await app_repo.get_by_user_and_target(user_id=user_id, job_id=job_id)
        if existing_app:
             await query.answer("Вы уже откликались на эту вакансию/стажировку.", show_alert=True)
        else:
            await query.answer("Не удалось отправить отклик. Попробуйте позже.", show_alert=True)
            logger.error(f"Failed to process application for user {user_id} and job {job_id}")