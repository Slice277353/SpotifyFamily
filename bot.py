import asyncio
import logging
import os
import sys
import json

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.i18n import I18n
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
dp = Dispatcher()

# Load user language preferences from file
LANGUAGE_FILE = "user_languages.json"


def load_languages():
    if os.path.exists(LANGUAGE_FILE):
        with open(LANGUAGE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}


def save_languages():
    with open(LANGUAGE_FILE, "w", encoding="utf-8") as file:
        json.dump(user_languages, file, indent=4)


user_languages = load_languages()

# Initialize i18n (pybabel translations)
i18n = I18n(path="locales", default_locale="en", domain="messages")


# Custom translation function
def translate(text_key, user_id=None, **kwargs):
    locale = user_languages.get(str(user_id), "en") if user_id else "en"
    translation = i18n.gettext(text_key, locale=locale)

    if kwargs:
        translation = translation.format(**kwargs)

    return translation


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    kb = [[types.KeyboardButton(text="Русский"), types.KeyboardButton(text="English")]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    text = translate("Hello, {name}!\n\nChoose your language:", user_id=message.from_user.id,
                     name=message.from_user.full_name)
    await message.answer(text, reply_markup=keyboard)


@dp.message(Command("setlang"))
async def command_set_language(message: Message) -> None:
    kb = [[types.KeyboardButton(text="Русский"), types.KeyboardButton(text="English")]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    text = translate("Choose your language:", user_id=message.from_user.id)
    await message.answer(text, reply_markup=keyboard)


@dp.message(lambda message: message.text in ["English", "Русский"])
async def set_language(message: Message) -> None:
    user_id = str(message.from_user.id)

    if message.text == "English":
        user_languages[user_id] = "en"
        text = translate("Language set to English.", user_id=user_id)
    elif message.text == "Русский":
        user_languages[user_id] = "ru"
        text = translate("Language set to Russian.", user_id=user_id)

    save_languages()  # Persist language settings
    await message.answer(text)


@dp.message(Command("send"))
async def command_send_handler(message: Message) -> None:
    user_id = str(message.from_user.id)
    text = translate("Hello, {name}!", user_id=user_id, name=message.from_user.first_name)
    await message.answer(text)


@dp.message(Command("checklang"))
async def check_language(message: Message) -> None:
    user_id = str(message.from_user.id)
    user_lang = user_languages.get(user_id, "en")
    await message.answer(f"Your current language setting is: {user_lang}")


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
