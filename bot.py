# bot.py
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils.i18n.middleware import SimpleI18nMiddleware



import database
from localization import i18n

from handlers import common, admin
import config

from scheduler import scheduler_loop




async def main():

    database.init_db()

    bot = Bot(
        token=config.TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    dp.update.middleware(SimpleI18nMiddleware(i18n=i18n))

    dp.include_router(common.common_router)
    dp.include_router(admin.admin_router)

    scheduler_task = asyncio.create_task(scheduler_loop(bot))

    logging.info("Starting bot polling...")
    try:
        await dp.start_polling(bot)
    finally:
        logging.info("Stopping bot...")
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            logging.info("Scheduler task cancelled successfully.")
        # Close bot session
        await bot.session.close()
        logging.info("Bot stopped.")


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
    )

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot execution stopped manually.")
