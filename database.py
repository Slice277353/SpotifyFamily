import sqlite3
import logging
from datetime import datetime
import config


# --- Initialization ---
def init_db():
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
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
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_telegram_id ON users (telegram_id)")
            conn.commit()
            logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database initialization error: {e}", exc_info=True)
        raise # Re-raise the exception to be handled by the caller if needed

# --- User Operations ---
def add_or_ignore_user(user_id: int, full_name: str):
    """Adds a user if they don't exist."""
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO users (telegram_id, full_name) VALUES (?, ?)",
                           (user_id, full_name))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"DB Error adding/ignoring user {user_id}: {e}")

def set_user_language(user_id: int, lang: str):
    """Updates the user's language preference."""
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET language = ? WHERE telegram_id = ?", (lang, user_id))
            conn.commit()
            return True
    except sqlite3.Error as e:
        logging.error(f"DB Error updating language for user {user_id}: {e}")
        return False

def get_user_language(user_id: int) -> str:
    """Fetches the user's language preference."""
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT language FROM users WHERE telegram_id = ?", (user_id,))
            result = cursor.fetchone()
            if result and result[0]:
                return result[0]
    except sqlite3.Error as e:
        logging.error(f"DB Error fetching language for user {user_id}: {e}")
    return config.DEFAULT_LOCALE # Fallback to default

def get_user_debt(user_id: int) -> float | None:
    """Fetches the user's current debt."""
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT debt FROM users WHERE telegram_id = ?", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None
    except sqlite3.Error as e:
        logging.error(f"DB Error fetching debt for user {user_id}: {e}")
        return None

def update_user_debt(user_id: int, new_debt: float) -> bool:
    """Updates a specific user's debt."""
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET debt = ? WHERE telegram_id = ?", (new_debt, user_id))
            conn.commit()
            return cursor.rowcount > 0 # Return True if update happened
    except sqlite3.Error as e:
        logging.error(f"DB Error updating debt for user {user_id}: {e}")
        return False

def get_all_users_stats() -> list:
    """Fetches stats for all users."""
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_id, full_name, debt, language FROM users")
            return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"DB Error fetching all user stats: {e}")
        return []

def get_users_for_notification() -> list:
    """Fetches all users (id, name, debt) for notifications."""
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_id, full_name, debt FROM users")
            return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"DB Error fetching users for notification: {e}")
        return []

def get_debtor_ids() -> list[int]:
    """Fetches telegram_ids of users with debt > 0."""
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_id FROM users WHERE debt > 0")
            return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"DB Error fetching debtor IDs: {e}")
        return []

# --- Payment Operations ---
def add_payment_record(user_id: int, image_path: str):
    """Adds a payment record and resets user debt."""
    try:
        with sqlite3.connect(config.DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO payments (user_id, image_path, timestamp) VALUES (?, ?, ?)",
                           (user_id, image_path, datetime.now().isoformat()))
            # Reset debt upon successful payment record insertion
            cursor.execute("UPDATE users SET debt = 0.0 WHERE telegram_id = ?", (user_id,))
            conn.commit()
            return True
    except sqlite3.Error as e:
        logging.error(f"DB Error adding payment for user {user_id}: {e}")
        return False
