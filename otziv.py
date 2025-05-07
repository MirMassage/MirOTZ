
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
import os

# 🔐 Загрузим переменные из .env
load_dotenv()  # Это загрузит все переменные из .env файла

API_TOKEN = os.getenv('API_TOKEN')  # Получаем API_TOKEN из .env файла
ADMINS = [140898735, 6705001934, 7310818609, 7947666885]  # замени на свой Telegram user_id

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

user_data = {}

def get_main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[ 
            [KeyboardButton(text="✅ Отправить отзыв")],
            [KeyboardButton(text="🔄 Очистить")]
        ],
        resize_keyboard=True
    )

def get_bonus_inline_kb():
    return InlineKeyboardMarkup(inline_keyboard=[ 
        [InlineKeyboardButton(text="🎁 Мануальная Терапия", callback_data="bonus_Мануальная Терапия")],
        [InlineKeyboardButton(text="🎁 Баночный массаж", callback_data="bonus_Баночный массаж")],
        [InlineKeyboardButton(text="🎁 Массаж Лица", callback_data="bonus_Массаж Лица")],
        [InlineKeyboardButton(text="🎁 Массаж ШВЗ", callback_data="bonus_Массаж ШВЗ")]
    ])

@dp.message(CommandStart())
async def start(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Привет! Поделитесь номером телефона:", reply_markup=kb)

@dp.message(F.contact)
async def handle_contact(message: Message):
    uid = message.from_user.id
    user_data[uid] = {
        'phone': message.contact.phone_number,
        'messages': [],
        'bonus': None
    }
    await message.answer(
        "Спасибо! Теперь отправьте сообщения для отзыва (текст, фото, видео и т.д.)."
        "Когда будете готовы — нажмите «✅ Отправить отзыв».",
        reply_markup=get_main_kb()
    )

@dp.message(F.text | F.photo | F.video | F.video_note)
async def collect_messages(message: Message):
    uid = message.from_user.id

    if uid not in user_data:
        await message.answer("Сначала поделитесь номером телефона.")
        return

    text = message.text.strip().lower() if message.text else ""

    if text.startswith("✅ отправить"):
        await confirm_send(message)
        return
    elif text.startswith("🔄 очистить"):
        await clear_review(message)
        return

    user_data[uid]['messages'].append(message)
    await message.answer("✅ Добавлено в отзыв.")
    print(f"[DEBUG] Добавлено сообщение: {message.content_type}")

async def confirm_send(message: Message):
    uid = message.from_user.id
    data = user_data.get(uid)

    if not data or not data.get("messages"):
        await message.answer("Вы ещё не добавили сообщений для отзыва.")
        return

    phone = data['phone']
    messages = data['messages']

    # Сохраняем отправленные сообщения
    user_data[uid]['sent'] = messages.copy()
    user_data[uid]['messages'] = []

    # Отправляем отзыв и номер телефона админам
    for admin_id in ADMINS:
        await bot.send_message(admin_id, f"📞 Новый отзыв от: {phone}")
        for msg in messages:
            if msg.text:
                await bot.send_message(admin_id, msg.text)
            elif msg.photo:
                await bot.send_photo(admin_id, photo=msg.photo[-1].file_id, caption=msg.caption or "")
            elif msg.video:
                await bot.send_video(admin_id, video=msg.video.file_id, caption=msg.caption or "")
            elif msg.video_note:
                await bot.send_video_note(admin_id, video_note=msg.video_note.file_id)

    # Удаляем reply-кнопки и предлагаем бонус
    await message.answer(
        "🙏 Спасибо за ваш отзыв! Теперь выберите бонусную процедуру:",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(
        "🎁 Доступные бонусы:",
        reply_markup=get_bonus_inline_kb()
    )

@dp.callback_query(F.data.startswith("bonus_"))
async def handle_bonus_choice(callback: CallbackQuery):
    uid = callback.from_user.id
    if uid not in user_data or not user_data[uid].get('sent'):
        await callback.message.answer("Сначала отправьте отзыв.")
        return

    bonus_text = callback.data.replace("bonus_", "")
    user_data[uid]['bonus'] = bonus_text
    phone = user_data[uid]['phone']

    for admin_id in ADMINS:
        await bot.send_message(admin_id, f"📞 Контакт: {phone} 🎁 Выбранный бонус: {bonus_text}")

    await callback.message.edit_text(f"🎉 Спасибо! Ваш бонус «{bonus_text}» отправлен администрации.")

    # Очистка
    user_data[uid]['sent'] = []
    user_data[uid]['bonus'] = None

async def clear_review(message: Message):
    uid = message.from_user.id
    if uid not in user_data:
        await message.answer("Сначала поделитесь номером телефона.")
        return

    if not user_data[uid].get('messages'):
        await message.answer("Вы ещё ничего не отправили.")
        return

    user_data[uid]['messages'] = []
    await message.answer("🗑️ Отзыв очищен. Можете начать заново.")

@dp.message(F.text)
async def debug_text(message: Message):
    print(f"[DEBUG] Получен текст: {message.text}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
