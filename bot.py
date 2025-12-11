import json
import random
import logging
import requests
import datetime
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
BOT_TOKEN = "8515430219:AAHH3d2W7Ao4ao-ARwHMonRxZY5MnOyHz9k"
ADSGRAM_PLATFORM_ID = 16417
ADSGRAM_BLOCK_ID = 17933

# ---------------------------------------------------------
# LOGGING
# ---------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# LOAD QUOTES
# ---------------------------------------------------------
with open("quotes.json", "r", encoding="utf-8") as f:
    QUOTES = json.load(f)

CATEGORIES_TR = list(QUOTES["tr"].keys())
CATEGORIES_EN = list(QUOTES["en"].keys())

# ---------------------------------------------------------
# USER DATA STORAGE
# ---------------------------------------------------------
users = {}  # user_id → {lang, category, notify}

# ---------------------------------------------------------
# ADSGRAM FETCH
# ---------------------------------------------------------
def get_ads():
    try:
        url = f"https://partner.adsgram.ai/api/getAd?platform=telegram&platformId={ADSGRAM_PLATFORM_ID}&adUnitId={ADSGRAM_BLOCK_ID}"
        r = requests.get(url, timeout=3)
        data = r.json()

        if "title" not in data:
            return None

        ad_text = f"👁 Sponsored\n{data['title']}\n{data['description']}\n👉 {data['cta']}"
        return ad_text

    except Exception as e:
        logger.warning(f"AdsGram error: {e}")
        return None

# ---------------------------------------------------------
# BUTTON BUILDERS
# ---------------------------------------------------------
def menu_buttons(lang, quote_text=""):
    encoded = requests.utils.quote(quote_text)

    whatsapp_url = f"https://wa.me/?text={encoded}"
    telegram_url = f"https://t.me/share/url?url={encoded}&text={encoded}"

    if lang == "tr":
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📅 Günün Sözü", callback_data="daily"),
                InlineKeyboardButton("📤 WhatsApp", url=whatsapp_url),
            ],
            [
                InlineKeyboardButton("📣 Telegram", url=telegram_url),
                InlineKeyboardButton("✨ Yeni Söz", callback_data="new_quote")
            ],
            [
                InlineKeyboardButton("🔄 Konuyu değiştir", callback_data="change_topic"),
                InlineKeyboardButton("⚙️ Ayarlar", callback_data="settings"),
            ],
        ])
    else:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📅 Quote of the Day", callback_data="daily"),
                InlineKeyboardButton("📤 WhatsApp", url=whatsapp_url),
            ],
            [
                InlineKeyboardButton("📣 Telegram", url=telegram_url),
                InlineKeyboardButton("✨ New Quote", callback_data="new_quote")
            ],
            [
                InlineKeyboardButton("🔄 Change Topic", callback_data="change_topic"),
                InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
            ],
        ])

def categories_buttons(lang):
    cats = CATEGORIES_TR if lang == "tr" else CATEGORIES_EN
    rows = []
    row = []
    for c in cats:
        row.append(InlineKeyboardButton(c, callback_data=f"cat_{c}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def settings_buttons(lang):
    if lang == "tr":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Dili değiştir", callback_data="lang")],
            [InlineKeyboardButton("🔔 Bildirimleri Aç/Kapat", callback_data="notify")],
            [InlineKeyboardButton("⬅️ Geri", callback_data="back_menu")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Change Language", callback_data="lang")],
            [InlineKeyboardButton("🔔 Toggle Notifications", callback_data="notify")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_menu")]
        ])

# ---------------------------------------------------------
# GET RANDOM QUOTE
# ---------------------------------------------------------
def get_random_quote(lang, category):
    q_list = QUOTES[lang][category]
    return random.choice(q_list)

# ---------------------------------------------------------
# COMMAND HANDLERS
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users[user.id] = users.get(user.id, {"lang": None, "category": None, "notify": True})

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
        ]
    ])
    await update.message.reply_text("✨ Welcome to Quote Masters!\nSelect language:", reply_markup=kb)

# ---------------------------------------------------------
# CALLBACK HANDLER
# ---------------------------------------------------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = users.get(query.from_user.id, {"lang": None, "category": None, "notify": True})

    data = query.data

    # LANGUAGE SELECT
    if data.startswith("lang_"):
        lang = data.split("_")[1]
        user["lang"] = lang
        users[query.from_user.id] = user
        await query.message.reply_text(
            "Konu seç:" if lang == "tr" else "Choose a topic:",
            reply_markup=categories_buttons(lang)
        )
        return

    # CATEGORY SELECT
    if data.startswith("cat_"):
        category = data.split("_")[1]
        user["category"] = category
        users[query.from_user.id] = user

        lang = user["lang"]
        quote = get_random_quote(lang, category)
        ad = get_ads()

        msg = quote
        if ad:
            msg += "\n\n" + ad

        await query.message.reply_text(msg, reply_markup=menu_buttons(lang, quote))
        return

    # NEW QUOTE
    if data == "new_quote":
        lang = user["lang"]
        cat = user["category"]
        quote = get_random_quote(lang, cat)
        ad = get_ads()
        msg = quote
        if ad:
            msg += "\n\n" + ad
        await query.message.reply_text(msg, reply_markup=menu_buttons(lang, quote))
        return

    # CHANGE TOPIC
    if data == "change_topic":
        lang = user["lang"]
        await query.message.reply_text(
            "Konu seç:" if lang == "tr" else "Choose a topic:",
            reply_markup=categories_buttons(lang)
        )
        return

    # SETTINGS
    if data == "settings":
        lang = user["lang"]
        await query.message.reply_text(
            "Ayarlar:" if lang == "tr" else "Settings:",
            reply_markup=settings_buttons(lang)
        )
        return

    # LANGUAGE CHANGE FROM SETTINGS
    if data == "lang":
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"),
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
            ]
        ])
        await query.message.reply_text("Dil seçin:", reply_markup=kb)
        return

    # TOGGLE NOTIFY
    if data == "notify":
        user["notify"] = not user["notify"]
        await query.message.reply_text("✔ Güncellendi.")
        return

    # BACK MENU
    if data == "back_menu":
        lang = user["lang"]
        cat = user["category"]
        quote = get_random_quote(lang, c

