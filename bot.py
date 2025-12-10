import os
import random
import logging
import pytz
import datetime
import requests
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ========================
# LOGGING
# ========================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ========================
# USER DATA
# ========================
users = {}  # Stores user settings

# ========================
# DAILY QUOTE (single global)
# ========================
daily_quote = {"text": None, "author": None, "topic": None}

def refresh_daily_quote():
    """Every day choose 1 random quote globally."""
    from quotes import QUOTES
    flat = []
    for t, arr in QUOTES.items():
        flat.extend(arr)

    chosen = random.choice(flat)
    daily_quote["text"] = chosen["text"]
    daily_quote["author"] = chosen["author"]
    daily_quote["topic"] = chosen["topic"]
    logger.info("New daily quote selected.")

refresh_daily_quote()  # First time select

# ========================
# ADSGRAM REKLAM
# ========================
ADSGRAM_UNIT_ID = "bot-17933"

def get_adsgram_ad():
    url = f"https://adsgram.ai/api/v1/getAd?unitId={ADSGRAM_UNIT_ID}"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            data = r.json()
            if "ad" in data and data["ad"]:
                title = data["ad"].get("title", "")
                text = data["ad"].get("text", "")
                link = data["ad"].get("link", "")

                return f"📢 *{title}*\n{text}\n👉 [Reklamı Aç]({link})"
    except:
        pass

    # fallback ad
    return (
        "📢 *Sponsored*\n"
        "Your entertainment, anytime.\n"
        "👉 [Explore Now](https://t.me/QuoteMastersBot)"
    )


# ========================
# MENU BUILDER
# ========================
def main_menu(lang):
    if lang == "tr":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 Günün Sözü", callback_data="today_quote")],
            [
                InlineKeyboardButton("📤 WhatsApp", callback_data="wa_share"),
                InlineKeyboardButton("📣 Telegram", callback_data="tg_share")
            ],
            [
                InlineKeyboardButton("🔄 Sözü Değiştir", callback_data="new_quote"),
                InlineKeyboardButton("📚 Konuyu Değiştir", callback_data="change_topic")
            ],
            [InlineKeyboardButton("⚙ Ayarlar", callback_data="settings")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 Quote of the Day", callback_data="today_quote")],
            [
                InlineKeyboardButton("📤 WhatsApp", callback_data="wa_share"),
                InlineKeyboardButton("📣 Telegram", callback_data="tg_share")
            ],
            [
                InlineKeyboardButton("🔄 New Quote", callback_data="new_quote"),
                InlineKeyboardButton("📚 Change Topic", callback_data="change_topic")
            ],
            [InlineKeyboardButton("⚙ Settings", callback_data="settings")]
        ])


def topic_menu(lang):
    topics = [
        ("Motivasyon", "motivation"),
        ("Başarı", "success"),
        ("Kendine İyi Bak", "selfcare"),
        ("Disiplin", "discipline"),
        ("Dayanıklılık", "resilience"),
        ("İş & Kariyer", "career"),
        ("Aşk", "love"),
        ("Hayat", "life"),
        ("Spor", "sport"),
        ("Dostluk", "friendship"),
        ("Yaratıcılık", "creativity"),
        ("Şükran", "gratitude")
    ]

    rows = []
    for i in range(0, len(topics), 2):
        row = []
        for label, key in topics[i:i+2]:
            row.append(
                InlineKeyboardButton(
                    label if lang == "tr" else key.capitalize(),
                    callback_data=f"topic_{key}"
                )
            )
        rows.append(row)

    return InlineKeyboardMarkup(rows)

# ========================
# COMMANDS
# ========================
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    lang = detect_language(update)

    users[user_id] = {"lang": lang, "topic": None, "notify": True}

    if lang == "tr":
        msg = "✨ *Quote Masters'a Hoş Geldin!* \nAnlamlı sözleri kategorilere göre keşfetmek için dili seç:"
    else:
        msg = "✨ *Welcome to Quote Masters!* \nDiscover meaningful quotes by choosing your language:"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ])

    update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)


def detect_language(update):
    code = update.effective_user.language_code
    if code and code.startswith("tr"):
        return "tr"
    return "en"


# ========================
# CALLBACK HANDLER
# ========================
def handle_buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id

    if user_id not in users:
        users[user_id] = {"lang": "en", "topic": None, "notify": True}

    lang = users[user_id]["lang"]

    # ---- LANGUAGE CHANGE ----
    if query.data == "lang_tr":
        users[user_id]["lang"] = "tr"
        query.edit_message_text("Dil seçildi: Türkçe\nBir konu seç:", reply_markup=topic_menu("tr"))
        return

    if query.data == "lang_en":
        users[user_id]["lang"] = "en"
        query.edit_message_text("Language set to English\nChoose a topic:", reply_markup=topic_menu("en"))
        return

    # ---- TOPIC SELECT ----
    if query.data.startswith("topic_"):
        users[user_id]["topic"] = query.data.replace("topic_", "")
        send_random_quote(update, context, user_id)
        return

    # ---- NEW QUOTE ----
    if query.data == "new_quote":
        send_random_quote(update, context, user_id)
        return

    # ---- QUOTE OF THE DAY ----
    if query.data == "today_quote":
        send_daily(update, context, user_id)
        return

    # ---- CHANGE TOPIC ----
    if query.data == "change_topic":
        query.edit_message_text("Bir konu seç:" if lang == "tr" else "Choose a topic:", reply_markup=topic_menu(lang))
        return

    # ---- SETTINGS ----
    if query.data == "settings":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Dil / Language", callback_data="change_lang")],
            [InlineKeyboardButton("🔔 Bildirimleri Aç/Kapat", callback_data="toggle_notify")]
        ])
        query.edit_message_text("Ayarlar:" if lang == "tr" else "Settings:", reply_markup=kb)
        return

    if query.data == "change_lang":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"),
             InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
        ])
        query.edit_message_text("Dili seç:" if lang == "tr" else "Choose language:", reply_markup=kb)
        return

    if query.data == "toggle_notify":
        users[user_id]["notify"] = not users[user_id]["notify"]
        query.edit_message_text(
            "Bildirimler açıldı." if users[user_id]["notify"] else "Bildirimler kapatıldı."
        )
        return

    # ---- SHARE ----
    if query.data in ["wa_share", "tg_share"]:
        share(update, context, user_id, query.data)
        return


# ========================
# QUOTE SENDING
# ========================
def send_random_quote(update, context, user_id):
    from quotes import QUOTES
    lang = users[user_id]["lang"]
    topic = users[user_id]["topic"]

    arr = QUOTES.get(topic, [])
    chosen = random.choice(arr)

    txt = f"“{chosen['text']}”"
    if chosen["author"]:
        txt += f"\n— *{chosen['author']}*"

    ad = get_adsgram_ad()

    update.callback_query.edit_message_text(
        f"{txt}\n\n{ad}",
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=main_menu(lang)
    )


def send_daily(update, context, user_id):
    lang = users[user_id]["lang"]
    q = daily_quote

    txt = f"*Günün sözü:*\n“{q['text']}”" if lang == "tr" else f"*Quote of the Day:*\n“{q['text']}”"
    if q['author']:
        txt += f"\n— *{q['author']}*"

    ad = get_adsgram_ad()

    update.callback_query.edit_message_text(
        f"{txt}\n\n{ad}",
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=main_menu(lang)
    )


def share(update, context, user_id, mode):
    lang = users[user_id]["lang"]
    q = daily_quote

    if lang == "tr":
        message = f"Bugünün sözü: “{q['text']}”\nhttps://t.me/QuoteMastersBot"
    else:
        message = f"Quote of the Day: “{q['text']}”\nhttps://t.me/QuoteMastersBot"

    if mode == "wa_share":
        link = f"https://wa.me/?text={message}"
    else:
        link = f"https://t.me/share/url?url={message}"

    update.callback_query.edit_message_text(
        "Paylaşmak için aç:" if lang=="tr" else "Tap to share:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Aç", url=link)]])
    )


# ========================
# DAILY NOTIFICATION
# ========================
def daily_job(context: CallbackContext):
    refresh_daily_quote()
    for uid, data in users.items():
        if data.get("notify", True):
            try:
                msg = "🎯 Bugünün sözü hazır! /start" if data["lang"] == "tr" else "🎯 Today's quote is ready! /start"
                context.bot.send_message(chat_id=uid, text=msg)
            except:
                pass


# ========================
# MAIN BOOTSTRAP
# ========================
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(handle_buttons))

    tr = pytz.timezone("Europe/Istanbul")
    now = datetime.datetime.now(tr)
    run_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
    if now > run_time:
        run_time += datetime.timedelta(days=1)

    updater.job_queue.run_daily(daily_job, time=run_time.time())

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
