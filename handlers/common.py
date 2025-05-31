import logging
import os
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardRemove

import config
import database
import keyboards
from localization import _

common_router = Router()

async def show_main_menu_options(message: Message):
    """Sends the main menu keyboard."""
    user_id = message.from_user.id
    # text = _("Welcome to the club, buddy!", user_id=user_id)
    keyboard = keyboards.get_main_menu_keyboard(user_id=user_id)
    await message.answer("\u200b",reply_markup=keyboard, parse_mode=None)

@common_router.message(CommandStart())
async def command_start_handler(message: Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name

    database.add_or_ignore_user(user_id, full_name)

    text = _("Hello, {name}! Choose your language:", user_id=user_id).format(name=full_name)
    await message.answer(text, reply_markup=keyboards.get_language_keyboard())

@common_router.message(F.text.in_({"English", "Русский"}))
async def set_language(message: Message):
    lang = "en" if message.text == "English" else "ru"
    user_id = message.from_user.id

    if database.set_user_language(user_id, lang):
        await message.answer(
            _("Language set to {lang}.", user_id=user_id).format(lang=message.text)
        )
        await show_main_menu_options(message)
        await message.answer(_("Welcome to the club, buddy!", user_id=user_id))
    else:
        await message.answer(_("Sorry, could not update language settings. Please try again.", user_id=user_id))


@common_router.message(F.text == (_("Upload")))
async def upload_receipt_prompt(message: Message):
    text = _("Please send your billing screenshot.", user_id=message.from_user.id)
    await message.answer(text, reply_markup=ReplyKeyboardRemove())

@common_router.message(F.photo)
async def handle_photo(message: Message, bot: "Bot"):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    file_id = message.photo[-1].file_id
    timestamp_str = datetime.now().strftime('%Y%m%d%H%M%S')
    file_path = os.path.join(config.RECEIPTS_DIR, f"{user_id}_{timestamp_str}.jpg")

    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, file_path)

        if database.add_payment_record(user_id, file_path):
            debt = database.get_user_debt(user_id)
            debt_str = f"{debt:.2f}" if debt is not None else _("N/A", user_id=user_id)

            # await message.answer(
            #     _("Received your receipt, {name}. Your current debt: ${debt}", user_id=user_id).format(name=full_name, debt=debt_str)
            # )
            await message.answer(_("Received your receipt, {name}.\n"
                                   "Await approval!", user_id=user_id).format(name=full_name))
            await show_main_menu_options(message)
        else:
             await message.answer(_("Sorry, there was an error saving your receipt information.", user_id=user_id))

    except Exception as e:
        logging.error(f"Error handling photo for user {user_id}: {e}", exc_info=True)
        await message.answer(_("Sorry, there was an error processing your receipt.", user_id=user_id))

@common_router.message(F.text == (_("Stats")))
async def view_stats(message: Message):
    user_id = message.from_user.id
    debt = database.get_user_debt(user_id)

    if debt is not None:
        await message.answer(_("Your current debt: ${debt}", user_id=user_id).format(debt=f"{debt:.2f}"))
    else:
        await message.answer(_("Could not retrieve your stats. Maybe try /start again?", user_id=user_id))



@common_router.message(F.text & ~F.text.startswith('/'))
async def handle_other_text(message: Message):
    logging.info(f"Received unhandled text from {message.from_user.id}: {message.text}")
    await message.answer(_("Unhandled command. Going back to main menu", user_id=message.from_user.id))
    await show_main_menu_options(message)
    pass
