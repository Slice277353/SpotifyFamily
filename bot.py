import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.i18n import gettext as _, I18n, ConstI18nMiddleware
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
dp = Dispatcher()

i18n = I18n(path="locales", default_locale='en', domain="messages")
i18n_middleware = ConstI18nMiddleware(i18n=i18n, locale='en')

dp.message.middleware(i18n_middleware)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    kb = [
        [
            types.KeyboardButton(text="Русский 🇷🇺"),
            types.KeyboardButton(text="English 🇬🇧")
        ],
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
    )
    await message.answer(_("Hello, {name}!\n\nChoose your language:").format(name=message.from_user.full_name), reply_markup=keyboard)

@dp.message(Command("setlang"))
async def command_set_language(message: Message) -> None:
    kb = [
        [
            types.KeyboardButton(text="Русский 🇷🇺"),
            types.KeyboardButton(text="English 🇬🇧")
        ],
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
    )
    await message.answer(_("Choose your language:"))
    await set_language(message, reply_markup=keyboard)

@dp.message(lambda message: message.text in ['English 🇬🇧', 'Русский 🇷🇺'])
async def set_language(message: Message) -> None:
    if message.text == "English 🇬🇧":
        i18n.current_locale = 'en'
        await message.answer(_("Language set to English."))
    elif message.text == "Русский 🇷🇺":
        i18n.current_locale = 'ru'
        await message.answer(_("Language set to Russian."))

@dp.message(Command("send"))
async def command_send_handler(message: Message) -> None:
    await message.answer(_("Hello, {name}!").format(name=message.from_user.first_name))

async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())