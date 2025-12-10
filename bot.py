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
users = {}  # user_id: {"lang": "tr/en", "topic": "...", "notify": True}

# ========================
# DAILY QUOTE (single global)
# ========================
daily_quote = {"text": None, "author": None, "topic": None}

def refresh_daily_quote():
    """Every day choose 1 random quote globally."""
    from quotes import QUOTES  # quotes.py dosyasında tutuluyor
    flat = []
    for t, arr in QUOTES.items():
        flat.extend(arr)

    chosen = random.choice(flat)
    daily_quote["text"] = chosen["text"]
    daily_quote["author"] = chosen["author"]
    daily_quote["topic"] = chosen["topic"]
    logger.info("New daily quote selected.")

# ilk açılışta seç
refresh_daily_quote()

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
                cta = data["ad"].get("cta_text", "")
                link = data["ad"].get("link", "")
                return f"📢 *{title}*\n{text}\n👉 [Reklamı Aç]({link})"
    except:
        pass

    # fallback reklam
    return (
        "📢 *Sponsored*\n"
        "Your entertainment, anytime.\n"
        "👉 [Explore Now](https://t.me/QuoteMastersBot)"
    )

# ========================
# UI BUILDER
# ========================
def main_menu(lang):
    if lang == "tr":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 Günün Sözü", callback_data="g_today")],
            [
                InlineKeyboardButton("📤 WhatsApp", callback_data="share_whatsapp"),
                InlineKeyboardButton("📣 Telegram", callback_data="share_telegram")
            ],
            [
                InlineKeyboardButton("🔄 Sözü değiştir", callback_data="change_quote"),
                InlineKeyboardButton("📚 Konuyu değiştir", callback_data="change_topic")
            ],
            [InlineKeyboardButton("⚙ Ayarlar", callback_data="settings")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎯 Quote of the Day", callback_data="g_today")],
            [
                InlineKeyboardButton("📤 WhatsApp", callback_data="share_whatsapp"),
                InlineKeyboardButton("📣 Telegram", callback_data="share_telegram")
            ],
            [
                InlineKeyboardButton("🔄 New Quote", callback_data="change_quote"),
                InlineKeyboardButton("📚 Change Topic", callback_data="change_topic")
            ],
            [InlineKeyboardButton("⚙ Settings", callback_data="settings")]
        ])

def topic_menu(lang):
    topics = [
        ("Motivasyon","motivation"),
        ("Başarı","success"),
        ("Kendine İyi Bak","selfcare"),
        ("Disiplin","discipline"),
        ("Dayanıklılık","resilience"),
        ("İş & Kariyer","career"),
        ("Aşk","love"),
        ("Hayat","life"),
        ("Spor","sport"),
        ("Dostluk","friendship"),
        ("Yaratıcılık","creativity"),
        ("Şükran","gratitude"),
    ]
    rows=[]
    for i in range(0,len(topics),2):
        row=[]
        for t in topics[i:i+2]:
            txt=t[0] if lang=="tr" else t[1].capitalize()
            row.append(InlineKeyboardButton(txt, callback_data=f"topic_{t[1]}"))
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
        msg = "✨ *Quote Masters'a Hoş Geldin!* \nAnlamlı sözleri konulara göre keşfet.\n\nLütfen dil seç:"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"),
             InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
        ])
    else:
        msg = "✨ *Welcome to Quote Masters!* \nDiscover meaningful quotes by topics.\n\nPlease choose a language:"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇹🇷 Turkish", callback_data="lang_tr"),
             InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
        ])

    update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)

def detect_language(update):
    lang_code = update.effective_user.language_code
    if lang_code and lang_code.startswith("tr"):
        return "tr"
    return "en"

# ========================
# CALLBACK HANDLING
# ========================
def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    u
