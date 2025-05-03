import logging
from aiogram import Router, F, types

from DataBase.models.content_repo import ContentRepository

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "🆘 Поддержка / FAQ")
async def handle_support_faq(message: types.Message):
    content_repo = ContentRepository()
    content = await content_repo.get_all_content()
    response_lines = ["**Часто задаваемые вопросы (FAQ):**\n"]
    if content.faqs:
        for faq in content.faqs:
            response_lines.append(f"❓ *{faq.question}*\n{faq.answer}\n")
    else:
        response_lines.append("Раздел FAQ пока пуст.\n")

    response_lines.append("\n**Контакты поддержки:**\n")
    if content.hr_contacts:
        response_lines.append("*Отдел подбора персонала:*")
        for contact in content.hr_contacts:
            response_lines.append(f"- {contact.full_name}: {contact.email}, {contact.phone}")
    if content.company_contacts:
         response_lines.append("\n*Другие контакты:*")
         for contact in content.company_contacts:
             response_lines.append(f"- {contact.department}: {contact.email}, {contact.phone}")

    if not content.hr_contacts and not content.company_contacts:
        response_lines.append("Контактная информация не найдена.")
    await message.answer(
        "\n".join(response_lines),
        parse_mode="Markdown"
    )