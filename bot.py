import asyncio
import logging
import os
import sys
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.i18n import I18n
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv
from aiogram.utils.keyboard import ReplyKeyboardBuilder

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
dp = Dispatcher()

DB_FILE = "spotify_family.db"
BILLING_DATE = datetime(2025, 5, 10)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        telegram_id INTEGER UNIQUE NOT NULL,
                        full_name TEXT,
                        language TEXT DEFAULT 'en',
                        debt REAL DEFAULT 1.0,
                        role TEXT DEFAULT 'member')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        image_path TEXT,
                        timestamp TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(telegram_id))''')
    # Ensure telegram_id cannot be NULL if somehow inserted otherwise
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_telegram_id ON users (telegram_id)")
    conn.commit()
    conn.close()

init_db()

i18n = I18n(path="locales", default_locale="en", domain="messages")

def _(text_key, user_id=None, **kwargs):
    locale = "en" # Default locale
    if user_id:
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT language FROM users WHERE telegram_id = ?", (user_id,))
            result = cursor.fetchone()
            if result and result[0]:
                locale = result[0]
            conn.close()
        except sqlite3.Error as e:
            logging.error(f"Database error fetching language for user {user_id}: {e}")
            # Keep default locale 'en'
    try:
        translation = i18n.gettext(text_key, locale=locale)
        return translation.format(**kwargs) if kwargs else translation
    except KeyError:
        logging.warning(f"Missing translation key '{text_key}' for locale '{locale}'")
        # Fallback to English or the key itself
        try:
            translation = i18n.gettext(text_key, locale='en')
            return translation.format(**kwargs) if kwargs else translation
        except KeyError:
             return f"[{text_key}]" # Return key if totally missing


@dp.message(CommandStart())
async def command_start_handler(message: Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (telegram_id, full_name) VALUES (?, ?)",
                       (user_id, full_name))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Database error during /start for user {user_id}: {e}")
        await message.answer("Sorry, there was a problem setting up your account. Please try again later.")
        return

    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Русский"))
    builder.add(types.KeyboardButton(text="English"))

    text = _("Hello, {name}! Choose your language:", user_id=user_id).format(name=full_name)
    await message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True))


async def show_main_menu_options(message: Message):
    builder = ReplyKeyboardBuilder()
    user_id=message.from_user.id
    builder.add(types.KeyboardButton(text=_("Upload", user_id=user_id)))
    builder.add(types.KeyboardButton(text=_("Stats", user_id=user_id)))
    text = _("Welcome to the club, buddy!", user_id=user_id)
    await message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))


@dp.message(F.text.in_({"English", "Русский"}))
async def set_language(message: Message):
    lang = "en" if message.text == "English" else "ru"
    user_id = message.from_user.id
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET language = ? WHERE telegram_id = ?", (lang, user_id))
        conn.commit()
        conn.close()
        await message.answer(_("Language set to {lang}.", user_id=user_id).format(lang=message.text))
        await show_main_menu_options(message)
    except sqlite3.Error as e:
        logging.error(f"Database error updating language for user {user_id}: {e}")
        await message.answer("Sorry, could not update language settings. Please try again.")


@dp.message(F.text.translated(_("Upload")))
async def upload_receipt_prompt(message: Message):
    text = _("Please send your billing screenshot.", user_id=message.from_user.id)
    await message.answer(text, reply_markup=types.ReplyKeyboardRemove())


@dp.message(F.photo)
async def handle_photo(message: Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    file_id = message.photo[-1].file_id
    timestamp_str = datetime.now().strftime('%Y%m%d%H%M%S')
    file_path = f"receipts/{user_id}_{timestamp_str}.jpg"
    os.makedirs("receipts", exist_ok=True)

    try:
        file = await message.bot.get_file(file_id)
        await message.bot.download_file(file.file_path, file_path)

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO payments (user_id, image_path, timestamp) VALUES (?, ?, ?)",
                       (user_id, file_path, datetime.now().isoformat()))
        # Here you might want to reset debt or require admin approval first
        # For now, let's assume upload confirms payment and resets debt (adjust if needed)
        cursor.execute("UPDATE users SET debt = 0.0 WHERE telegram_id = ?", (user_id,))
        conn.commit()
        cursor.execute("SELECT debt FROM users WHERE telegram_id = ?", (user_id,))
        debt_result = cursor.fetchone()
        conn.close()
        debt = debt_result[0] if debt_result else "N/A" # Handle if user fetch failed

        await message.answer(_("Received your receipt, {name}. Your current debt: ${debt}", user_id=user_id).format(name=full_name, debt=debt))
        await show_main_menu_options(message) # Show menu again after upload

    except Exception as e:
        logging.error(f"Error handling photo for user {user_id}: {e}")
        await message.answer(_("Sorry, there was an error processing your receipt.", user_id=user_id))


@dp.message(F.text.translated(_("Stats")))
async def view_stats(message: Message):
    user_id = message.from_user.id
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT debt FROM users WHERE telegram_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            await message.answer(_("Your current debt: ${debt}", user_id=user_id).format(debt=result[0]))
        else:
            await message.answer(_("No data found. Have you used /start?", user_id=user_id))
    except sqlite3.Error as e:
        logging.error(f"Database error fetching stats for user {user_id}: {e}")
        await message.answer(_("Could not retrieve stats.", user_id=user_id))

# --- Admin Commands ---

async def is_admin(user_id: int) -> bool:
    # Simple check: Replace with your actual admin verification logic
    # Maybe check against a list of IDs or a role in the DB
    ADMIN_IDS = {123456789} # Replace with actual admin Telegram IDs
    return user_id in ADMIN_IDS

@dp.message(Command("admin_stats"))
async def admin_view_stats(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer(_("You are not authorized to use this command.", user_id=message.from_user.id))
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id, full_name, debt, language FROM users")
        users = cursor.fetchall()
        conn.close()

        if not users:
             await message.answer(_("No users found in the database.", user_id=message.from_user.id))
             return

        text_lines = [_("User stats:", user_id=message.from_user.id)]
        for user in users:
            tg_id, name, debt, lang = user
            text_lines.append(f"{name or 'N/A'} (ID: {tg_id}, Lang: {lang}) - Debt: ${debt:.2f}")

        await message.answer("\n".join(text_lines))

    except sqlite3.Error as e:
        logging.error(f"Database error during admin_stats: {e}")
        await message.answer(_("Failed to retrieve admin stats due to a database error.", user_id=message.from_user.id))


@dp.message(Command("update_debt"))
async def update_debt(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer(_("You are not authorized to use this command.", user_id=message.from_user.id))
        return

    parts = message.text.split()
    if len(parts) != 3:
        await message.answer(_("Usage: /update_debt <user_telegram_id> <new_debt_amount>", user_id=message.from_user.id))
        return

    try:
        target_user_id = int(parts[1])
        new_debt = float(parts[2])

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET debt = ? WHERE telegram_id = ?", (new_debt, target_user_id))
        updated_rows = cursor.rowcount
        conn.commit()
        conn.close()

        if updated_rows > 0:
            await message.answer(_("Updated debt for user {uid} to ${amt}", user_id=message.from_user.id).format(uid=target_user_id, amt=new_debt))
            # Optionally notify the user whose debt was updated
            try:
                 await dp.bot.send_message(target_user_id, _("An admin has updated your debt to ${debt}.", user_id=target_user_id).format(debt=new_debt))
            except Exception as notify_err:
                 logging.warning(f"Could not notify user {target_user_id} about debt update: {notify_err}")
        else:
            await message.answer(_("User with ID {uid} not found.", user_id=message.from_user.id).format(uid=target_user_id))

    except ValueError:
        await message.answer(_("Invalid user ID or amount. Please use numbers.", user_id=message.from_user.id))
    except sqlite3.Error as e:
        logging.error(f"Database error during update_debt: {e}")
        await message.answer(_("Failed to update debt due to a database error.", user_id=message.from_user.id))
    except Exception as e:
        logging.error(f"Unexpected error during update_debt: {e}")
        await message.answer(_("An unexpected error occurred.", user_id=message.from_user.id))


# --- Scheduled Tasks ---

async def notify_users():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id, full_name, debt FROM users")
        users = cursor.fetchall()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Database error fetching users for notification: {e}")
        return

    bot = dp.bot # Get bot instance from dispatcher if available this way

    if not bot:
        logging.error("Bot instance not found in dispatcher for notifications.")
        return


    for user in users:
        telegram_id, full_name, debt = user
        try:
            if debt > 0:
                text = _("Reminder: Your current debt is ${debt}. Please pay before the billing date.", user_id=telegram_id).format(debt=debt)
                await bot.send_message(telegram_id, text)
            else:
                # Optional: Send thank you message only if recently paid?
                # text = _("Thank you for your payment, {name}. Your debt is cleared.", user_id=telegram_id).format(name=full_name)
                # await bot.send_message(telegram_id, text)
                pass # Avoid spamming users with 0 debt every day
        except Exception as e:
            logging.warning(f"Failed to send notification to user {telegram_id}: {e}")
        await asyncio.sleep(0.2) # Small delay to avoid hitting rate limits


async def turn_off_explicit_songs_for_debtors():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # Fetch telegram_ids of users with debt > 0
        cursor.execute("SELECT telegram_id FROM users WHERE debt > 0")
        debtor_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not debtor_ids:
            logging.info("No debtors found, explicit songs script not run.")
            return

        # You need a way to map telegram_id to Spotify username/credentials
        # This part is highly dependent on how your script.py works.
        # Example: Assume script.py takes usernames as arguments
        # You'll need another table or logic to link telegram_id to spotify_username

        # Placeholder: You need to implement the logic to get Spotify usernames
        spotify_usernames_to_block = [] # Populate this list based on debtor_ids

        if spotify_usernames_to_block:
             logging.info(f"Running explicit songs script for users: {', '.join(spotify_usernames_to_block)}")
             # Modify this command based on how your script.py accepts input
             # Example: os.system(f"python /path/to/your/script.py {' '.join(spotify_usernames_to_block)}")
             # Make sure script.py handles errors and logging
             # Consider using subprocess module for better control than os.system
             # return_code = os.system("python /home/ilie/PycharmProjects/SpotifyFamily/script.py") # Adapt this call
             # logging.info(f"Explicit songs script finished with return code: {return_code}")
             logging.warning("Actual call to script.py is commented out. Implement user mapping and uncomment/adapt the system call.")
        else:
             logging.info("Found debtors by ID, but could not map to Spotify usernames to run script.")


    except sqlite3.Error as e:
        logging.error(f"Database error fetching debtors for explicit songs script: {e}")
    except Exception as e:
        logging.error(f"Error running or preparing for explicit songs script: {e}")


async def scheduled_tasks(bot_instance):
    dp.bot = bot_instance # Make bot instance available globally via dispatcher
    while True:
        now = datetime.now()
        # Check if today is 1 day before the billing day of the month
        if now.day == (BILLING_DATE.day - 1):
             logging.info(f"Running daily notification check (Day before billing: {BILLING_DATE.day}).")
             await notify_users()

        # Check if today is 3 days after the billing day of the month
        if now.day == (BILLING_DATE.day + 3):
             logging.info(f"Running explicit content check (3 days past billing: {BILLING_DATE.day}).")
             await turn_off_explicit_songs_for_debtors()

        # Sleep until roughly the same time tomorrow
        tomorrow = datetime.combine(now.date() + timedelta(days=1), now.time())
        sleep_seconds = (tomorrow - now).total_seconds()
        logging.debug(f"Scheduler sleeping for {sleep_seconds:.0f} seconds.")
        await asyncio.sleep(max(sleep_seconds, 60)) # Sleep at least 60s


# Catch other text messages that aren't commands or specific button presses
@dp.message(F.text & ~F.text.startswith('/'))
async def handle_other_text(message: Message):
    logging.info(f"Received unhandled text from {message.from_user.id}: {message.text}")
    # Optionally provide help or ignore
    # await message.answer(_("Use the buttons or commands like /stats.", user_id=message.from_user.id))
    pass # Or just ignore potentially random text input


async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    # Pass bot instance to scheduled_tasks starter
    scheduler_task = asyncio.create_task(scheduled_tasks(bot))
    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel() # Ensure scheduler stops when polling stops
        try:
            await scheduler_task
        except asyncio.CancelledError:
            logging.info("Scheduler task cancelled.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(main())