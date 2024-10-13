import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, html, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv

# TODO: Implement aiogram_i18n

load_dotenv() # TODO: Implement loading only of Telegram Bot Token
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
dp = Dispatcher()

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
        input_field_placeholder="Выберите язык",
    )
    await message.answer(f"Hello, {message.from_user.first_name}!\n\nChoose your language:", reply_markup=keyboard)

@dp.message(Command("language"))
async def commmand_change_language(message: Message) -> None:
    kb = [
        [
            types.KeyboardButton(text="Русский 🇷🇺"),
            types.KeyboardButton(text="English 🇬🇧")
        ],
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Выберите язык",
    )
    await message.answer(f"Choose your language:", reply_markup=keyboard)
    
@dp.message(Command("send"))
async def command_send_handler(message: Message) -> None:
    await message.answer(f"Hello, {message.from_user.first_name}!")

async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())