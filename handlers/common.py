import logging
from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from keyboards.reply_keyboards import get_main_menu_keyboard
from DataBase.models.user_repo import UserRepository
from DataBase.models import UserCreate

logger = logging.getLogger(__name__)

router = Router()

@router.message(CommandStart())
async def handle_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    user_repo = UserRepository()
    logger.info(f"User {user_id} ({user_name}) started the bot.")
    user = await user_repo.get_by_id(user_id)

    if not user:
        logger.info(f"User {user_id} not found in DB. Creating...")
        username = message.from_user.username
        new_user_data = UserCreate(
            id=user_id,
            full_name=user_name,
            email=None,
            phone=None
        )
        created_user = await user_repo.add(new_user_data)
        if created_user:
            logger.info(f"User {user_id} created in DB.")
            await message.answer(
                f"👋 Добро пожаловать, {user_name}!\n"
                "Я помогу вам найти стажировку, вакансию или интересное мероприятие в нашей компании.\n"
                "Пожалуйста, заполните ваш профиль для удобства откликов.",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            logger.error(f"Failed to create user {user_id} in DB.")
            await message.answer(
                "Произошла ошибка при регистрации. Попробуйте позже или обратитесь в поддержку.",
            )
    else:
        logger.info(f"User {user_id} found in DB.")
        await message.answer(
            f"👋 С возвращением, {user_name}!\n"
            "Выберите интересующий раздел:",
            reply_markup=get_main_menu_keyboard()
        )

@router.message()
async def handle_unknown(message: types.Message):
    await message.reply(
        "Неизвестная команда. Пожалуйста, используйте кнопки меню.",
        reply_markup=get_main_menu_keyboard()
    )
