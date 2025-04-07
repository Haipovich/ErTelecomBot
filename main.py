import telebot
from telebot import types
import os

BOT_TOKEN = '7768965319:AAEvPIesB4LEji_9W9wrB-0j2-VjeyXdWGI'
bot = telebot.TeleBot(BOT_TOKEN)

# Главное меню
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("📚 Стажировки")
    btn2 = types.KeyboardButton("💼 Вакансии")
    btn3 = types.KeyboardButton("🎯 Активности")
    btn4 = types.KeyboardButton("📄 Мои заявки")
    btn5 = types.KeyboardButton("🆘 Поддержка")
    markup.add(btn1, btn2)
    markup.add(btn3)
    markup.add(btn4, btn5)
    return markup

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Добро пожаловать! Выберите раздел:", reply_markup=main_menu())

# Обработка нажатий
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    if message.text == "📚 Стажировки":
        bot.send_message(message.chat.id, "Раздел *Стажировки* в разработке 🛠️", parse_mode="Markdown")
    elif message.text == "💼 Вакансии":
        bot.send_message(message.chat.id, "Раздел *Вакансии* в разработке 🛠️", parse_mode="Markdown")
    elif message.text == "🎯 Активности":
        bot.send_message(message.chat.id, "Раздел *Активности* в разработке 🛠️", parse_mode="Markdown")
    elif message.text == "📄 Мои заявки":
        bot.send_message(message.chat.id, "Раздел *Мои заявки* в разработке 🛠️", parse_mode="Markdown")
    elif message.text == "🆘 Поддержка":
        bot.send_message(message.chat.id, "По вопросам поддержки напишите @support_username")
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выбери раздел с кнопки ниже.", reply_markup=main_menu())

# Запуск
bot.polling(none_stop=True)