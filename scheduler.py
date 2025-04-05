# scheduler.py
import asyncio
import logging
from datetime import datetime, timedelta, time

from aiogram import Bot

import config
import database
from localization import _ # Import translation helper

async def notify_users(bot: Bot):
    """Sends debt reminders to users with outstanding debt."""
    logging.info("Running daily notification check...")
    users_to_notify = database.get_users_for_notification() # Use DB function

    if not users_to_notify:
        logging.info("No users found for notifications.")
        return

    for telegram_id, full_name, debt in users_to_notify:
        try:
            if debt > 0:
                # Get user-specific translation
                text = _("Reminder: Your current debt is ${debt}. Please pay before the billing date.", user_id=telegram_id).format(debt=f"{debt:.2f}")
                await bot.send_message(telegram_id, text)
            # else: # Avoid spamming users with 0 debt
            #     pass
        except Exception as e:
            # Handle specific exceptions like BotBlocked, CantInitiateConversation etc. if needed
            logging.warning(f"Failed to send notification to user {telegram_id} ({full_name}): {e}")
        await asyncio.sleep(0.2) # Small delay between messages
    logging.info("Finished notification check.")


async def turn_off_explicit_songs_for_debtors():
    """Checks for debtors and triggers the external script (if implemented)."""
    logging.info("Running explicit content check...")
    debtor_ids = database.get_debtor_ids() # Use DB function

    if not debtor_ids:
        logging.info("No debtors found with debt > 0.")
        return

    logging.info(f"Debtors found (IDs): {debtor_ids}")

    # --- IMPORTANT ---
    # You need to implement the logic to map these telegram_ids to
    # whatever identifier your `script.py` needs (e.g., Spotify usernames).
    # This might involve adding a 'spotify_username' column to your 'users' table
    # and fetching those usernames for the debtor_ids.
    # --- Placeholder ---
    spotify_usernames_to_block = [] # Populate this list based on debtor_ids and mapping logic

    if spotify_usernames_to_block:
        logging.info(f"Attempting to run explicit songs script for users: {', '.join(spotify_usernames_to_block)}")
        try:
            # Example using subprocess (safer than os.system)
            # Adjust path and arguments as needed for your script.py
            # script_path = "/home/ilie/PycharmProjects/SpotifyFamily/script.py"
            # command = [sys.executable, script_path] + spotify_usernames_to_block
            # process = await asyncio.create_subprocess_exec(
            #     *command,
            #     stdout=asyncio.subprocess.PIPE,
            #     stderr=asyncio.subprocess.PIPE
            # )
            # stdout, stderr = await process.communicate()
            # if process.returncode == 0:
            #      logging.info(f"Explicit songs script finished successfully. Output:\n{stdout.decode()}")
            # else:
            #      logging.error(f"Explicit songs script failed (Code: {process.returncode}). Error:\n{stderr.decode()}")
            logging.warning("Actual call to script.py is commented out. Implement user mapping and uncomment/adapt the subprocess call.")
        except FileNotFoundError:
             logging.error("Error running script.py: Script not found at the specified path.")
        except Exception as e:
             logging.error(f"Error running explicit songs script: {e}", exc_info=True)
    else:
        logging.warning("Found debtors by ID, but could not map to Spotify usernames to run script (or mapping logic not implemented).")
    logging.info("Finished explicit content check.")


async def scheduler_loop(bot: Bot):
    """The main loop that runs scheduled tasks at appropriate times."""
    logging.info("Scheduler started.")
    while True:
        now = datetime.now()
        # --- Define Check Times ---
        # Run notifications daily at a specific time (e.g., 10:00 AM)
        notification_time = time(10, 0) # 10:00 AM
        # Run explicit check daily at a specific time (e.g., 11:00 AM)
        explicit_check_time = time(11, 0) # 11:00 AM

        # --- Calculate Next Run Times ---
        today_notification_dt = datetime.combine(now.date(), notification_time)
        today_explicit_check_dt = datetime.combine(now.date(), explicit_check_time)

        next_notification_dt = today_notification_dt
        if now >= today_notification_dt: # If time has passed for today, schedule for tomorrow
            next_notification_dt += timedelta(days=1)

        next_explicit_check_dt = today_explicit_check_dt
        if now >= today_explicit_check_dt: # If time has passed for today, schedule for tomorrow
            next_explicit_check_dt += timedelta(days=1)

        # --- Determine Sleep Duration ---
        sleep_target = min(next_notification_dt, next_explicit_check_dt)
        sleep_seconds = (sleep_target - now).total_seconds()
        sleep_seconds = max(sleep_seconds, 1) # Sleep at least 1 second

        logging.debug(f"Scheduler sleeping for {sleep_seconds:.0f} seconds (until {sleep_target.strftime('%Y-%m-%d %H:%M:%S')}).")
        await asyncio.sleep(sleep_seconds)

        # --- Run Tasks Due ---
        # Re-check 'now' after waking up
        now = datetime.now()

        # Check notification condition: e.g., run daily regardless of billing date?
        # Or only run near billing date? Modify condition as needed.
        # Current implementation runs daily at notification_time.
        if now >= today_notification_dt and now < today_notification_dt + timedelta(minutes=1): # Check within a minute window
             # Check if it's the day before billing
             is_day_before_billing = (now + timedelta(days=1)).day == config.BILLING_DATE.day
             if is_day_before_billing:
                 logging.info(f"It's the day before billing date ({config.BILLING_DATE.day}). Running notifications.")
                 await notify_users(bot)
             else:
                 logging.info(f"Daily notification time reached, but not the day before billing. Skipping notifications.")


        # Check explicit content condition: e.g., run daily regardless?
        # Or only run after billing date? Modify condition as needed.
        # Current implementation runs daily at explicit_check_time.
        if now >= today_explicit_check_dt and now < today_explicit_check_dt + timedelta(minutes=1): # Check within a minute window
            # Check if it's 3 days past the billing day
            is_3_days_past_billing = (now - timedelta(days=3)).day == config.BILLING_DATE.day
            if is_3_days_past_billing:
                 logging.info(f"It's 3 days past billing date ({config.BILLING_DATE.day}). Running explicit content check.")
                 await turn_off_explicit_songs_for_debtors()
            else:
                 logging.info(f"Daily explicit check time reached, but not 3 days past billing. Skipping check.")