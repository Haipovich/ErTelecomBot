import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from pydantic import BaseModel, EmailStr, ValidationError

from DataBase.models.user_repo import UserRepository
from DataBase.models import UserUpdate

from keyboards.inline_keyboards import (
    ProfileCallbackData,
    get_profile_view_keyboard,
    get_profile_edit_choices_keyboard,
    format_profile_details,
)
from keyboards.reply_keyboards import get_main_menu_keyboard, get_cancel_keyboard

logger = logging.getLogger(__name__)
router = Router()

class EditProfileStates(StatesGroup):
    choosing_field = State()
    waiting_for_input = State()

async def show_profile(target: types.Message | types.CallbackQuery, user_id: int, state: FSMContext):
    await state.clear()
    user_repo = UserRepository(); user = await user_repo.get_by_id(user_id)
    if not user:
        logger.warning(f"User {user_id} not found when trying to show profile.")
        text = "Не удалось загрузить профиль."; keyboard = get_main_menu_keyboard(); reply_keyboard = True
    else:
        text = format_profile_details(user); keyboard = get_profile_view_keyboard(); reply_keyboard = False

    current_message: types.Message | None = target.message if isinstance(target, types.CallbackQuery) else target
    if not current_message: return
    if reply_keyboard: await current_message.answer(text, reply_markup=keyboard)
    else:
        if isinstance(target, types.CallbackQuery):
             try:
                 if current_message.text == text and current_message.reply_markup == keyboard: await target.answer(); return
                 await current_message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown"); await target.answer()
             except Exception as e:
                 logger.warning(f"Could not edit profile msg for user {user_id}: {e}. Sending new.")
                 try: await current_message.delete()
                 except Exception: pass
                 await current_message.answer(text, reply_markup=keyboard, parse_mode="Markdown"); await target.answer()
        else: await current_message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(StateFilter(None), F.text == "👤 Мой профиль")
async def handle_my_profile_button(message: types.Message, state: FSMContext):
    await show_profile(message, message.from_user.id, state)

@router.message(StateFilter(EditProfileStates), F.text == "❌ Отмена")
async def handle_edit_cancel_text(message: types.Message, state: FSMContext):
    logger.info(f"User {message.from_user.id} canceled profile editing via text button.")
    await state.clear()
    await message.answer("Редактирование отменено.", reply_markup=get_main_menu_keyboard())


@router.message(EditProfileStates.waiting_for_input)
async def handle_profile_field_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await state.get_data()
    field_to_edit = user_data.get('field_to_edit')
    field_name_ru = user_data.get('field_name_ru', 'поля')

    if not field_to_edit:
        logger.error(f"State error for user {user_id}: field_to_edit not found.")
        await state.clear(); await message.answer("Ошибка состояния.", reply_markup=get_main_menu_keyboard()); return

    new_value_str = message.text
    logger.info(f"User {user_id} entered value '{new_value_str}' for field '{field_to_edit}'")
    validated_value: Any = None
    error_message: str | None = None
    try:
        if field_to_edit == 'email':
            class EmailValidatorModel(BaseModel):
                email_field: EmailStr
            try:
                validated_model = EmailValidatorModel(email_field=new_value_str)
                validated_value = validated_model.email_field # Получаем валидированное значение
            except ValidationError as e_val:
                error_detail = "Неверный формат email."
                try:
                    if e_val.errors():
                        first_error = e_val.errors()[0]
                        if first_error.get('msg'):
                             error_detail = first_error['msg']
                except Exception:
                    pass
                raise ValueError(error_detail)
        elif field_to_edit == 'phone':
            if not new_value_str or not new_value_str.replace('+', '').isdigit() or len(new_value_str.replace('+', '')) < 10:
                 raise ValueError("Неверный формат телефона. Пример: +79123456789")
            validated_value = new_value_str
        elif field_to_edit == 'birth_date':
            validated_value = datetime.strptime(new_value_str, '%Y-%m-%d').date()
        elif field_to_edit == 'desired_salary':
            validated_value = Decimal(new_value_str)
            if validated_value < 0: raise ValueError("Зарплата не может быть отрицательной.")
        elif field_to_edit == 'relocation_readiness':
            low_val = new_value_str.lower()
            if low_val in ['да', 'yes', 'true', '1', 'д']: validated_value = True
            elif low_val in ['нет', 'no', 'false', '0', 'н']: validated_value = False
            else: raise ValueError("Ответьте 'Да' или 'Нет'.")
        else:
            validated_value = new_value_str

    except (ValueError, InvalidOperation) as e:
        error_message = f"Ошибка ввода для '{field_name_ru}': {e}\nПожалуйста, попробуйте еще раз или нажмите 'Отмена'."
    except ValidationError as e:
        error_message = f"Ошибка валидации для '{field_name_ru}'. Попробуйте еще раз.\n({e})"
    except Exception as e:
        logger.error(f"Unexpected validation error for field {field_to_edit}, value '{new_value_str}': {e}")
        error_message = "Произошла непредвиденная ошибка при проверке данных. Попробуйте еще раз."
    if error_message:
        await message.reply(error_message, reply_markup=get_cancel_keyboard())
        return
    user_repo = UserRepository()
    update_data = UserUpdate(**{field_to_edit: validated_value})
    updated_user = await user_repo.update(user_id, update_data)
    if updated_user:
        logger.info(f"User {user_id} successfully updated field '{field_to_edit}'.")
        await state.clear()
        await message.answer(f"Поле '{field_name_ru}' успешно обновлено!", reply_markup=get_main_menu_keyboard())
        await show_profile(message, user_id, state)
    else:
        logger.error(f"Failed to update user {user_id} field '{field_to_edit}' in DB.")
        await state.clear()
        await message.answer("Не удалось сохранить изменения. Попробуйте позже.", reply_markup=get_main_menu_keyboard())

@router.callback_query(StateFilter(None), ProfileCallbackData.filter(F.action == "edit_start"))
async def handle_profile_edit_start(query: types.CallbackQuery, state: FSMContext):
    logger.info(f"User {query.from_user.id} started profile editing.")
    await query.message.edit_text("Какое поле вы хотите изменить?", reply_markup=get_profile_edit_choices_keyboard())
    await state.set_state(EditProfileStates.choosing_field); await query.answer()

@router.callback_query(EditProfileStates.choosing_field, ProfileCallbackData.filter(F.action == "edit_field"))
async def handle_profile_edit_field_choice(query: types.CallbackQuery, callback_data: ProfileCallbackData, state: FSMContext):
    field_to_edit = callback_data.field
    if not field_to_edit: logger.error(f"Callback error user {query.from_user.id}: field is None"); await query.answer("Ошибка.", show_alert=True); return
    field_name_ru = "поля"
    if query.message.reply_markup:
         for row in query.message.reply_markup.inline_keyboard:
             for button in row:
                 if button.callback_data == query.data: field_name_ru = button.text.replace("📝 ",""); break
    logger.info(f"User {query.from_user.id} chose to edit field: {field_to_edit}")
    await state.update_data(field_to_edit=field_to_edit, field_name_ru=field_name_ru)
    await state.set_state(EditProfileStates.waiting_for_input)
    await query.message.edit_text(f"Введите новое значение для '{field_name_ru}':", reply_markup=None)
    await query.message.answer("Или нажмите 'Отмена'", reply_markup=get_cancel_keyboard())
    await query.answer()

@router.callback_query(StateFilter(EditProfileStates), ProfileCallbackData.filter(F.action == "edit_cancel"))
async def handle_profile_edit_cancel_callback(query: types.CallbackQuery, state: FSMContext):
    logger.info(f"User {query.from_user.id} canceled profile editing via inline button.")
    await state.clear(); await query.answer("Редактирование отменено.")
    try: await query.message.delete()
    except Exception: pass
    await query.message.answer("Возврат в главное меню.", reply_markup=get_main_menu_keyboard())
    await show_profile(query.message, query.from_user.id, state)