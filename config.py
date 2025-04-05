import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DB_FILE = "spotify_family.db"
BILLING_DATE = datetime(2025, 5, 10)
RECEIPTS_DIR = "receipts"
LOCALES_DIR = "locales"
DEFAULT_LOCALE = "en"
I18N_DOMAIN = "messages"


ADMIN_IDS = {int(admin_id) for admin_id in os.getenv("ADMIN_IDS", "123456789").split(',')} # Example: Load from .env


os.makedirs(RECEIPTS_DIR, exist_ok=True)