import logging
import os

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Telegram bot token
WEBAPP_URL = os.getenv("WEBAPP_URL") or "https://your-frontend-url.com"

# ---------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# LANGUAGE HELPERS
# ---------------------------------------------------------------------

def get_lang(update: Update) -> str:
    """
    Kullanıcının dilini Telegram'dan al.
    TR ise 'tr', diğer her şey için 'en' döner.
    """
    user = update.effective_user
    code = (user.language_code or "").lower() if user else ""
    if code.startswith("tr"):
        return "tr"
    return "en"


TEXTS = {
    "tr": {
        "start": (
            "✨ DailyQuoteBot'a hoş geldin!\n\n"
            "Günün motivasyon sözlerini, favorilerini, görevlerini ve "
            "ödüllü reklamlarla ekstra sözleri artık **premium Mini App** "
            "üzerinden kullanabilirsin.\n\n"
            "Aşağıdaki butona dokunarak açabilirsin 👇"
        ),
        "help": (
            "DailyQuoteBot artık Mini App olarak çalışıyor.\n\n"
            "Günün sözlerini ve tüm özellikleri görmek için aşağıdaki butondan açabilirsin 👇"
        ),
        "fallback": (
            "DailyQuoteBot'u kullanmak için aşağıdaki butondan premium Mini App'i açabilirsin 👇"
        ),
        "button": "▶ DailyQuoteBot'u Aç",
    },
    "en": {
        "start": (
            "✨ Welcome to DailyQuoteBot!\n\n"
            "You can now enjoy daily motivational quotes, favorites, tasks and "
            "extra quotes from rewarded ads through our **premium Mini App**.\n\n"
            "Tap the button below to open it 👇"
        ),
        "help": (
            "DailyQuoteBot now runs as a Mini App.\n\n"
            "Tap the button below to open all features 👇"
        ),
        "fallback": (
            "Tap the button below to open the premium DailyQuoteBot Mini App 👇"
        ),
        "button": "▶ Open DailyQuoteBot",
    },
}


def build_open_app_keyboard(lang: str) -> InlineKeyboardMarkup:
    text = TEXTS[lang]["button"]
    keyboard = [
        [
            InlineKeyboardButton(
                text=text,
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# ---------------------------------------------------------------------
# HANDLERS
# ---------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    t = TEXTS[lang]["start"]
    reply_markup = build_open_app_keyboard(lang)

    if update.message:
        await update.message.reply_text(t, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(t, reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    t = TEXTS[lang]["help"]
    reply_markup = build_open_app_keyboard(lang)
    await update.message.reply_text(t, reply_markup=reply_markup)


async def fallback_launcher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Kullanıcı rastgele bir mesaj yazarsa tekrar Mini App'e yönlendir.
    İstersen bu handler'ı kaldırabilirsin.
    """
    lang = get_lang(update)
    t = TEXTS[lang]["fallback"]
    reply_markup = build_open_app_keyboard(lang)
    await update.message.reply_text(t, reply_markup=reply_markup)


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable set edilmemiş. "
            "Örn: export BOT_TOKEN='123456:ABC-DEF'"
        )

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_launcher)
    )

    logger.info("DailyQuoteBot launcher running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
