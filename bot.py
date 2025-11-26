import logging
import os
import random
from datetime import date

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")  # örn: Render'da env var, lokalde .env vs.

# Her X sözde bir reklam deneyelim
AD_FREQUENCY = 3

# Bir kullanıcıya günde en fazla kaç reklam gösterelim?
MAX_ADS_PER_DAY = 10

# ---------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# BASİT SÖZ HAVUZU (TR/EN)
# ---------------------------------------------------------------------

QUOTES = {
    "tr": [
        "Bugün kendine iyi davranmayı unutma.",
        "Her gün, yeni bir başlangıçtır.",
        "Vazgeçmeyenler, kazananlardır.",
        "Küçük adımlar, büyük değişimlere yol açar.",
        "Kendine inandığın an, her şey mümkündür.",
    ],
    "en": [
        "Be kind to yourself today.",
        "Every day is a new beginning.",
        "Those who never give up are the ones who win.",
        "Small steps lead to big changes.",
        "Once you believe in yourself, anything is possible.",
    ],
}

# ---------------------------------------------------------------------
# DİL METİNLERİ
# ---------------------------------------------------------------------

TEXTS = {
    "tr": {
        "start": (
            "✨ DailyQuoteBot'a hoş geldin!\n\n"
            "Günün motivasyon sözlerini görmek için aşağıdaki butonları kullanabilirsin.\n\n"
            "• 'Yeni söz' ile sıradaki sözü aç\n"
            "• 'Ekstra söz (reklam)' ile gönüllü olarak reklam görevinden sonra ekstra söz al\n\n"
            "Hazırsan başlıyoruz 👇"
        ),
        "help": (
            "📚 DailyQuoteBot yardım\n\n"
            "/start - Botu başlat / menüyü göster\n"
            "/quote - Yeni bir söz gönder\n"
            "/stats - Bugünkü söz ve reklam istatistiklerini göster\n\n"
            "Alt taraftaki butonlarla da aynı işlemleri yapabilirsin."
        ),
        "btn_new": "🔁 Yeni söz",
        "btn_extra": "🎁 Ekstra söz (reklam)",
        "quote_prefix": "Bugünün sözü:",
        "extra_thanks": "Reklam görevini tamamladığın için teşekkürler 🙌 İşte ekstra sözün:",
        "no_quote": "Şu an için gösterecek söz bulamadım.",
        "ad_label": "Reklam",
        "ad_placeholder": (
            "📢 [Reklam] Burada AdsGram üzerinden aldığın reklam mesajı gösterilecek.\n"
            "Gerçek entegrasyonda bu metni kendi AdsGram çağrınla değiştir."
        ),
        "stats": "📊 Bugünkü istatistiklerin:\n\nSöz sayısı: {quotes}\nGösterilen reklam sayısı: {ads}",
        "fallback": (
            "DailyQuoteBot'u kullanmak için aşağıdaki butonlardan birini seçebilirsin 👇"
        ),
    },
    "en": {
        "start": (
            "✨ Welcome to DailyQuoteBot!\n\n"
            "Use the buttons below to get your daily motivational quotes.\n\n"
            "• 'New quote' to get the next quote\n"
            "• 'Extra quote (ad)' to optionally watch an ad and get a bonus quote\n\n"
            "Let's begin 👇"
        ),
        "help": (
            "📚 DailyQuoteBot help\n\n"
            "/start - Show menu / welcome message\n"
            "/quote - Send a new quote\n"
            "/stats - Show today's quote & ad stats\n\n"
            "You can also use the buttons below the messages."
        ),
        "btn_new": "🔁 New quote",
        "btn_extra": "🎁 Extra quote (ad)",
        "quote_prefix": "Today's quote:",
        "extra_thanks": "Thanks for completing the ad task 🙌 Here is your extra quote:",
        "no_quote": "I don't have a quote to show right now.",
        "ad_label": "Ad",
        "ad_placeholder": (
            "📢 [Ad] This is where the AdsGram ad message should be shown.\n"
            "Replace this text with your real AdsGram integration."
        ),
        "stats": "📊 Your stats for today:\n\nQuotes: {quotes}\nAds shown: {ads}",
        "fallback": (
            "You can use the buttons below to get quotes 👇"
        ),
    },
}

# ---------------------------------------------------------------------
# KULLANICI BAZLI BASİT STATE (İN-MEMORY)
# ---------------------------------------------------------------------

# {user_id: {"day": date, "quotes": int, "ads": int}}
USER_STATS = {}


def get_lang(update: Update) -> str:
    """Telegram language_code'a göre 'tr' veya 'en' döner."""
    user = update.effective_user
    code = (user.language_code or "").lower() if user else ""
    if code.startswith("tr"):
        return "tr"
    return "en"


def ensure_user_stats(user_id: int) -> dict:
    """Kullanıcı için bugüne ait sayaçları hazırla."""
    today = date.today()
    stats = USER_STATS.get(user_id)
    if not stats or stats.get("day") != today:
        stats = {"day": today, "quotes": 0, "ads": 0}
        USER_STATS[user_id] = stats
    return stats


def get_random_quote(lang: str) -> str:
    """Dil için rastgele bir söz döner."""
    pool = QUOTES.get(lang) or QUOTES["en"]
    if not pool:
        return ""
    return random.choice(pool)


def build_main_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Ana inline keyboard (yeni söz + ekstra söz)."""
    t = TEXTS[lang]
    keyboard = [
        [InlineKeyboardButton(t["btn_new"], callback_data="new_quote")],
        [InlineKeyboardButton(t["btn_extra"], callback_data="extra_quote")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def send_adsgram_ad(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str, user_id: int):
    """
    Burada gerçek AdsGram entegrasyonunu çağıracaksın.
    Şu an sadece placeholder metin gönderiyor.
    """
    stats = ensure_user_stats(user_id)
    stats["ads"] += 1

    t = TEXTS[lang]
    text = f"🔔 {t['ad_label']}\n\n{t['ad_placeholder']}"

    if update.callback_query:
        await update.callback_query.message.reply_text(text)
    elif update.message:
        await update.message.reply_text(text)
    else:
        # fallback
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text=text)


# ---------------------------------------------------------------------
# HANDLER'LAR
# ---------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    t = TEXTS[lang]
    kb = build_main_keyboard(lang)
    await update.message.reply_text(t["start"], reply_markup=kb)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    t = TEXTS[lang]
    kb = build_main_keyboard(lang)
    await update.message.reply_text(t["help"], reply_markup=kb)


async def send_quote_logic(update: Update, context: ContextTypes.DEFAULT_TYPE, extra: bool = False) -> None:
    """
    Hem normal quote hem ekstra quote mantığı burada.
    extra=True ise 'reklam sonrası ekstra söz' mesajı ekler.
    """
    lang = get_lang(update)
    t = TEXTS[lang]

    user = update.effective_user
    user_id = user.id if user else 0
    stats = ensure_user_stats(user_id)

    quote = get_random_quote(lang)
    if not quote:
        msg = t["no_quote"]
    else:
        if extra:
            msg = f"{t['extra_thanks']}\n\n“{quote}”"
        else:
            msg = f"{t['quote_prefix']}\n\n“{quote}”"

    kb = build_main_keyboard(lang)

    if update.message:
        await update.message.reply_text(msg, reply_markup=kb)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(msg, reply_markup=kb)
    else:
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=kb)

    # Sayaç güncelle
    stats["quotes"] += 1

    # Otomatik reklam tetikleme (her AD_FREQUENCY sözde)
    if not extra:
        if stats["quotes"] % AD_FREQUENCY == 0 and stats["ads"] < MAX_ADS_PER_DAY:
            await send_adsgram_ad(update, context, lang, user_id)


async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ /quote komutu -> yeni söz """
    await send_quote_logic(update, context, extra=False)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Bugünkü istatistikleri göster. """
    lang = get_lang(update)
    t = TEXTS[lang]
    user = update.effective_user
    user_id = user.id if user else 0
    stats = ensure_user_stats(user_id)

    text = t["stats"].format(quotes=stats["quotes"], ads=stats["ads"])
    kb = build_main_keyboard(lang)
    await update.message.reply_text(text, reply_markup=kb)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline keyboard callback handler."""
    query = update.callback_query
    data = query.data
    lang = get_lang(update)

    if data == "new_quote":
        await send_quote_logic(update, context, extra=False)
    elif data == "extra_quote":
        # 1) Reklam (AdsGram entegrasyonu)
        user = update.effective_user
        user_id = user.id if user else 0
        await send_adsgram_ad(update, context, lang, user_id)

        # 2) Reklam sonrası ekstra söz
        await send_quote_logic(update, context, extra=True)
    else:
        # bilinmeyen callback
        await query.answer()


async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Kullanıcı rastgele bir şey yazarsa:
    - Ana butonları tekrar göster
    - Kullanıcıya nasıl kullanacağını hatırlat
    """
    lang = get_lang(update)
    t = TEXTS[lang]
    kb = build_main_keyboard(lang)
    await update.message.reply_text(t["fallback"], reply_markup=kb)


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

    # Komutlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("quote", quote_command))
    application.add_handler(CommandHandler("stats", stats_command))

    # Inline buton callback
    application.add_handler(CallbackQueryHandler(button_callback))

    # Diğer tüm metinlere fallback
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text))

    logger.info("DailyQuoteBot (message bot) is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
