import logging
from aiogram.utils.i18n import I18n
import config
import database # Import database functions

i18n = I18n(path=config.LOCALES_DIR, default_locale=config.DEFAULT_LOCALE, domain=config.I18N_DOMAIN)


# async def get_user_locale(event_from_user: types.User | None) -> str:
#     """
#     Gets the user locale from the database.
#     Required signature for SimpleI18nMiddleware locale_provider.
#     """
#     if event_from_user is None:
#         return config.DEFAULT_LOCALE # Or handle anonymous users as needed

#     user_id = event_from_user.id
#     locale = database.get_user_language(user_id) # Use your DB function
#     # Ensure the locale exists in your i18n setup, otherwise fallback
#     if locale in i18n.available_locales:
#          return locale
#     return config.DEFAULT_LOCALE


def _(text_key: str, user_id: int | None = None, **kwargs) -> str:
    """Gets the translation for a key, fetching user locale from DB if user_id is provided."""
    locale = config.DEFAULT_LOCALE # Start with default
    if user_id:
        locale = database.get_user_language(user_id) # Fetch from DB

    try:
        # Use gettext directly; formatting is handled separately if needed
        translation = i18n.gettext(text_key, locale=locale)
        return translation # kwargs formatting will be done where needed, e.g., in handlers
    except KeyError:
        logging.warning(f"Missing translation key '{text_key}' for locale '{locale}'")
        # Fallback to English or the key itself
        try:
            translation = i18n.gettext(text_key, locale='en')
            return translation
        except KeyError:
            return f"[{text_key}]" # Return key if totally missing

# Example of how to use formatting outside the function:
# text = _("Hello, {name}!", user_id=user_id).format(name=full_name)
