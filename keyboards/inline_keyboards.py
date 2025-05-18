from typing import List, Dict, Any
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from DataBase.models import User, Job, Activity, Application, JobType, ApplicationStatus # Добавили User

class JobCallbackData(CallbackData, prefix="job"):
    action: str
    item_id: int

class ActivityCallbackData(CallbackData, prefix="activity"):
    action: str
    item_id: int

class ApplicationCallbackData(CallbackData, prefix="app"):
    action: str
    item_id: int

class ProfileCallbackData(CallbackData, prefix="profile"):
    action: str
    field: str | None = None

def get_list_keyboard(items: List[Job | Activity], data_fabric: type[CallbackData]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(text=f"🔎 {item.title[:40]}...", callback_data=data_fabric(action="view", item_id=item.id))
    builder.adjust(1)
    return builder.as_markup()

def get_item_details_keyboard(item_id: int, data_fabric: type[CallbackData], already_applied: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not already_applied:
         builder.button(text="✅ Откликнуться / Участвовать", callback_data=data_fabric(action="apply", item_id=item_id))
    else:
         builder.button(text="✔️ Вы уже откликнулись", callback_data="dummy_already_applied")
    builder.adjust(1)
    return builder.as_markup()

def get_my_applications_keyboard(applications: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not applications: return builder.as_markup()
    for app_data in applications:
        app_id = app_data.get('id'); target_title = app_data.get('target_title', '?'); status = app_data.get('status')
        if app_id is None: continue
        status_text = status.value if isinstance(status, ApplicationStatus) else str(status)
        button_text = f"📄 {target_title[:35]}... ({status_text})"
        builder.button(text=button_text, callback_data=ApplicationCallbackData(action="view_details", item_id=app_id))
    builder.adjust(1)
    return builder.as_markup()

def get_application_details_keyboard(application: Application) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    deletable_statuses = [ApplicationStatus.PENDING, ApplicationStatus.UNDER_REVIEW]
    if application.status in deletable_statuses:
        builder.button(text="🗑️ Удалить заявку", callback_data=ApplicationCallbackData(action="delete", item_id=application.id))
    builder.button(text="◀️ К списку заявок", callback_data=ApplicationCallbackData(action="back_to_list", item_id=0))
    builder.adjust(1)
    return builder.as_markup()

def get_profile_view_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✏️ Редактировать профиль",
        callback_data=ProfileCallbackData(action="edit_start")
    )
    return builder.as_markup()

def get_profile_edit_choices_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    fields = {
        "full_name": "Имя и Фамилия",
        "email": "Email",
        "phone": "Телефон",
        "city": "Город",
        "birth_date": "Дата рождения (ГГГГ-ММ-ДД)",
        "education": "Образование",
        "work_experience": "Опыт работы",
        "skills": "Навыки",
        "desired_salary": "Желаемая ЗП (число)",
        "desired_employment": "Желаемая занятость",
        "relocation_readiness": "Готовность к переезду (Да/Нет)",
        "about_me": "О себе",
    }
    for field_key, field_name in fields.items():
         builder.button(
             text=f"📝 {field_name}",
             callback_data=ProfileCallbackData(action="edit_field", field=field_key)
         )

    builder.button(
        text="❌ Отмена",
        callback_data=ProfileCallbackData(action="edit_cancel")
    )
    builder.adjust(2)
    return builder.as_markup()

def format_job_details(job: Job) -> str:
    details = [ f"*{job.title}*", f"*{'Стажировка' if job.type == JobType.INTERNSHIP else 'Вакансия'}*", "", job.description or "-", "", f"🎓 *Образование:* {job.required_education or '-'}", f"🛠️ *Опыт:* {job.required_experience or '-'}", f"💡 *Навыки:* {job.required_skills or '-'}", ]
    if job.additional_skills: details.append(f"✨ *Доп. навыки:* {job.additional_skills}")
    if job.employment_type: details.append(f"⏰ *Тип занятости:* {job.employment_type}")
    if job.work_schedule: details.append(f"📅 *График:* {job.work_schedule}")
    if job.salary:
        try:
            details.append(f"💰 *Зарплата:* {float(job.salary):.2f} руб.")
        except (ValueError, TypeError):
            details.append(f"💰 *Зарплата:* {job.salary}")
    if job.additional_info: details.append(f"\nℹ️ *Дополнительно:* {job.additional_info}")
    return "\n".join(details)

def format_activity_details(activity: Activity) -> str:
    details = [ f"*{activity.title}*", "", activity.description or "-", "", f"🕒 *Начало:* {activity.start_time.strftime('%d.%m.%Y %H:%M %Z')}", f"🕒 *Окончание:* {activity.end_time.strftime('%d.%m.%Y %H:%M %Z')}", f"📍 *Место:* {activity.address or '-'}", f"👥 *Аудитория:* {activity.target_audience or '-'}", ]
    return "\n".join(details)

def format_application_details(application: Application, target_details: Job | Activity | None) -> str:
    status_text = application.status.value if isinstance(application.status, ApplicationStatus) else str(application.status)
    details = [ f"**Детали заявки ID: {application.id}**", f"*Статус:* {status_text}", f"*Подана:* {application.application_time.strftime('%d.%m.%Y %H:%M')}", "" ]
    if application.hr_comment: details.extend([f"*Комментарий HR:* {application.hr_comment}", ""])
    details.append("**Цель заявки:**")
    if application.job_id and isinstance(target_details, Job): details.extend([f"*{'Стажировка' if target_details.type == JobType.INTERNSHIP else 'Вакансия'}:* {target_details.title}", f"  _Навыки:_ {target_details.required_skills or '-'}"])
    elif application.activity_id and isinstance(target_details, Activity): details.extend([f"*Активность:* {target_details.title}", f"  _Время:_ {target_details.start_time.strftime('%d.%m %H:%M')} - {target_details.end_time.strftime('%H:%M')}"])
    else: details.append("Информация о цели заявки не найдена.")
    return "\n".join(details)

def format_profile_details(user: User) -> str:
    details = [
        "**👤 Ваш профиль:**",
        f"*ID:* `{user.id}`",
        f"*Имя:* {user.full_name or '-'}",
        f"*Email:* {user.email or '(не указан)'}",
        f"*Телефон:* {user.phone or '(не указан)'}",
        f"*Город:* {user.city or '(не указан)'}",
        f"*Дата рождения:* {user.birth_date.strftime('%d.%m.%Y') if user.birth_date else '(не указана)'}",
        f"*Образование:*", f"{user.education or '(не указано)'}", # Текстовые поля в новой строке
        f"*Опыт работы:*", f"{user.work_experience or '(не указан)'}",
        f"*Навыки:*", f"{user.skills or '(не указаны)'}",
        f"*Желаемая ЗП:* {f'{user.desired_salary:.2f}' if user.desired_salary else '(не указана)'}",
        f"*Желаемая занятость:* {user.desired_employment or '(не указана)'}",
        f"*Готовность к переезду:* {'Да' if user.relocation_readiness else 'Нет'}",
        f"*О себе:*", f"{user.about_me or '(не указано)'}",
    ]
    return "\n".join(d for d in details if d is not None)