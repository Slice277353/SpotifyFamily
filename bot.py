import asyncio
import logging
import os
import sys
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.i18n import I18n
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from aiogram.utils.keyboard import ReplyKeyboardBuilder

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
dp = Dispatcher()

DB_FILE = "spotify_family.db"
BILLING_DATE = datetime(2025, 3, 10)  # Example billing date, adjust as needed


# Initialize SQLite database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        telegram_id INTEGER UNIQUE,
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
    conn.commit()
    conn.close()


init_db()

i18n = I18n(path="locales", default_locale="en", domain="messages")


def _(text_key, user_id=None, **kwargs):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT language FROM users WHERE telegram_id = ?", (user_id,))
    result = cursor.fetchone()
    locale = result[0] if result else "en"
    conn.close()
    translation = i18n.gettext(text_key, locale=locale)
    return translation.format(**kwargs) if kwargs else translation


@dp.message(CommandStart())
async def command_start_handler(message: Message):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (telegram_id, full_name) VALUES (?, ?)",
                   (message.from_user.id, message.from_user.full_name))
    conn.commit()
    conn.close()

    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Русский"))
    builder.add(types.KeyboardButton(text="English"))

    text = _("Hello, {name}! Choose your language:", user_id=message.from_user.id).format(name=message.from_user.full_name)
    await message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(lambda message: message.text)
async def main_menu(message: Message):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text=_("Upload")))
    builder.add(types.KeyboardButton(text=_("Stats")))
    text = _("Welcome to the club, buddy!")
    await message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True))

# Call main_menu with the message object
@dp.message(lambda message: message.text in ["English", "Русский"])
async def set_language(message: Message):
    lang = "en" if message.text == "English" else "ru"
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET language = ? WHERE telegram_id = ?", (lang, message.from_user.id))
    conn.commit()
    conn.close()
    await message.answer(_("Language set to {lang}.", user_id=message.from_user.id).format(lang=message.text))
    await main_menu(message)


@dp.message(Command("upload"))
async def upload_receipt(message: Message):
    kb = [[KeyboardButton(text=_("Upload"))]]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    text = _("Please send your billing screenshot.", user_id=message.from_user.id)
    await message.answer(text, reply_markup=keyboard)


@dp.message(lambda message: message.photo)
async def handle_photo(message: Message):
    file_id = message.photo[-1].file_id
    file_path = f"receipts/{message.from_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    os.makedirs("receipts", exist_ok=True)
    
    file = await message.bot.get_file(file_id)
    await message.bot.download_file(file.file_path, file_path)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO payments (user_id, image_path, timestamp) VALUES (?, ?, ?)",
                   (message.from_user.id, file_path, datetime.now().isoformat()))
    conn.commit()
    cursor.execute("SELECT debt FROM users WHERE telegram_id = ?", (message.from_user.id,))
    debt = cursor.fetchone()[0]
    conn.close()

    await message.answer(_("Received your receipt, {name}. Your current debt: ${debt}", user_id=message.from_user.id).format(name=message.from_user.full_name, debt=debt))


@dp.message(Command("stats"))
async def view_stats(message: Message):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT debt FROM users WHERE telegram_id = ?", (message.from_user.id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        await message.answer(_("Your current debt: ${debt}", user_id=message.from_user.id).format(debt=result[0]))
    else:
        await message.answer(_("No data found.", user_id=message.from_user.id))


@dp.message(Command("admin_stats"))
async def admin_view_stats(message: Message):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id, full_name, debt FROM users")
    users = cursor.fetchall()
    conn.close()

    text = _("User stats:\n", user_id=message.from_user.id) + "\n".join([f"{user[1]} (ID: {user[0]}) - Debt: ${user[2]}" for user in users])
    await message.answer(text)


@dp.message(Command("update_debt"))
async def update_debt(message: Message):
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer(_("Usage: /update_debt <user_id> <amount>", user_id=message.from_user.id))
        return
    user_id, amount = parts[1], float(parts[2])
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET debt = debt - ? WHERE telegram_id = ?", (amount, user_id))
    conn.commit()
    conn.close()
    await message.answer(_("Updated debt for user {uid} by ${amt}", user_id=message.from_user.id).format(uid=user_id, amt=amount))


async def notify_users():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id, full_name, debt FROM users")
    users = cursor.fetchall()
    conn.close()

    for user in users:
        telegram_id, full_name, debt = user
        if debt > 0:
            text = _("Reminder: Your current debt is ${debt}. Please pay before the billing date.", user_id=telegram_id).format(debt=debt)
            await dp.bot.send_message(telegram_id, text)
        else:
            text = _("Thank you for your payment, {name}. Your debt is cleared.", user_id=telegram_id).format(name=full_name)
            await dp.bot.send_message(telegram_id, text)

async def turn_off_explicit_songs():
    os.system("python /home/ilie/PycharmProjects/SpotifyFamily/script.py")

async def scheduled_tasks():
    while True:
        now = datetime.now()
        if now.date() == BILLING_DATE.date() + timedelta(days=3):
            await turn_off_explicit_songs()
        if now.date() == BILLING_DATE.date() - timedelta(days=1):
            await notify_users()
        await asyncio.sleep(86400)  # Sleep for a day

async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    asyncio.create_task(scheduled_tasks())
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
