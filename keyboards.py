# keyboards.py
from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from localization import _

def get_language_keyboard() -> types.ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Русский"))
    builder.add(types.KeyboardButton(text="English"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def get_main_menu_keyboard(user_id: int) -> types.ReplyKeyboardMarkup:
    """Returns the main menu keyboard, translated for the user."""
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text=_("Upload", user_id=user_id)))
    builder.add(types.KeyboardButton(text=_("Stats", user_id=user_id)))
    return builder.as_markup(resize_keyboard=True)
