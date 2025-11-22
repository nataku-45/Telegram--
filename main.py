import asyncio
import logging
import os
import uuid
import requests # Добавляем импорт

import aiogram
import google.generativeai as genai
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

# Получаем токены из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Проверяем, что токены установлены
if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Необходимо установить TELEGRAM_BOT_TOKEN и GEMINI_API_KEY в .env файле")

# Инициализируем бота и диспетчер
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Конфигурируем Gemini API
genai.configure(api_key=GEMINI_API_KEY)


@dp.message(CommandStart())
async def send_welcome(message: Message):
    """
    Обработчик команды /start. Отправляет приветственное сообщение.
    """
    await message.answer("Привет! Отправь мне голосовое сообщение, и я его транскрибирую и сделаю summary.")


@dp.message(F.voice)
async def handle_voice_message(message: Message):
    """
    Обработчик голосовых сообщений.
    """
    # Уведомляем пользователя, что сообщение получено
    await message.reply("Голосовое сообщение получено. Начинаю обработку...")

    voice_file_info = await bot.get_file(message.voice.file_id)
    file_path = voice_file_info.file_path
    
    # Создаем уникальное имя файла
    ogg_filename = f"{uuid.uuid4()}.ogg"

    try:
        # Скачиваем файл
        await bot.download_file(file_path, destination=ogg_filename)
        logging.info(f"Файл сохранен как {ogg_filename}")

        # Загружаем файл в Gemini
        audio_file = genai.upload_file(path=ogg_filename)
        logging.info(f"Файл {ogg_filename} успешно загружен в Gemini.")

        # Создаем модель
        model = genai.GenerativeModel('gemini-2.5-flash')

        # Промпт для модели
        prompt = (
            "Твоя задача — послушать аудио, сделать полную транскрипцию текста, "
            "а затем выделить 3-4 ключевых пункта (summary). Ответь на русском языке."
        )

        # Отправляем запрос в Gemini
        response = await model.generate_content_async([prompt, audio_file])

        # Отправляем результат пользователю
        await message.answer(response.text)
        logging.info("Результат отправлен пользователю.")

    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")
        await message.reply("К сожалению, произошла ошибка при обработке вашего сообщения. Попробуйте еще раз позже.")
    
    finally:
        # Удаляем временный файл
        if os.path.exists(ogg_filename):
            os.remove(ogg_filename)
            logging.info(f"Временный файл {ogg_filename} удален.")


async def main():
    """
    Основная функция для запуска бота.
    """
    # --- Проверка IP-адреса ---
    try:
        response = requests.get("https://ipinfo.io/json")
        data = response.json()
        country = data.get("country")
        ip = data.get("ip")
        logging.info(f"Скрипт запущен с IP: {ip}, Страна: {country}")
        if country not in ['US', 'DE', 'GB', 'FR']: # Пример разрешенных стран
             logging.warning("ВНИМАНИЕ: Страна вашего IP-адреса может не поддерживаться Gemini API.")
    except Exception as e:
        logging.error(f"Не удалось определить IP-адрес: {e}")
    # -------------------------

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())