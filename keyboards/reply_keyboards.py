from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📚 Стажировки"),
        KeyboardButton(text="💼 Вакансии")
    )
    builder.row(KeyboardButton(text="🎯 Активности"))
    builder.row(
        KeyboardButton(text="📄 Мои заявки"),
        KeyboardButton(text="👤 Мой профиль")
    )
    builder.row(KeyboardButton(text="🆘 Поддержка / FAQ"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False, input_field_placeholder=True)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)