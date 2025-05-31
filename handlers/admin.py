import logging

from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message

import config
import database
from handlers.common import show_main_menu_options
from localization import _

admin_router = Router()


async def is_admin(user_id: int) -> bool:
    """Checks if a user ID is in the configured admin list."""
    return user_id in config.ADMIN_IDS

@admin_router.message(Command("admin_stats"))
async def admin_view_stats(message: Message):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        await message.answer(_("You are not authorized to use this command.", user_id=user_id))
        return

    users_data = database.get_all_users_stats()

    if not users_data:
        await message.answer(_("No users found in the database.", user_id=user_id))
        return

    text_lines = [_("User stats:", user_id=user_id)]
    for user_tg_id, name, debt, lang in users_data:
        text_lines.append(f"{name or 'N/A'} (ID: {user_tg_id}, Lang: {lang}) - Debt: ${debt:.2f}")

    await message.answer("\n".join(text_lines))

@admin_router.message(Command("update_debt"))
async def update_debt(message: Message, bot: Bot):
    admin_user_id = message.from_user.id
    if not await is_admin(admin_user_id):
        await message.answer(_("You are not authorized to use this command.", user_id=admin_user_id))
        return

    parts = message.text.split()
    if len(parts) != 3:
        await message.answer(_("Usage: /update_debt <user_telegram_id> <new_debt_amount>", user_id=admin_user_id))
        return

    try:
        target_user_id = int(parts[1])
        new_debt = float(parts[2])

        if database.update_user_debt(target_user_id, new_debt): # Use DB function
            await message.answer(
                _("Updated debt for user {uid} to ${amt}", user_id=admin_user_id).format(uid=target_user_id, amt=f"{new_debt:.2f}")
            )

            try:
                await bot.send_message(
                    target_user_id,
                    _("An admin has updated your debt to ${debt}.", user_id=target_user_id).format(debt=f"{new_debt:.2f}")
                )
                await show_main_menu_options(message)
            except Exception as notify_err:
                logging.warning(f"Could not notify user {target_user_id} about debt update: {notify_err}")
                await show_main_menu_options(message)
        else:
            await message.answer(
                _("User with ID {uid} not found or could not update debt.", user_id=admin_user_id).format(uid=target_user_id)
            )
            await show_main_menu_options(message)

    except ValueError:
        await message.answer(_("Invalid user ID or amount. Please use numbers.", user_id=admin_user_id))
    except Exception as e:
        logging.error(f"Unexpected error during update_debt: {e}", exc_info=True)
        await message.answer(_("An unexpected error occurred.", user_id=admin_user_id))
