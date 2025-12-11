# =========================================================
#  Quote Masters Bot - Final Version (A + C Share System)
# =========================================================

import os
import random
import requests
import pytz
from datetime import time
from urllib.parse import quote_plus

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# =========================================================
#  CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
IST = pytz.timezone("Europe/Istanbul")
BOT_LINK = "https://t.me/QuoteMastersBot"

# =========================================================
#  DATA (KATEGORİLER)
# =========================================================

CATEGORIES_TR = [
    "Motivasyon", "Başarı", "Kendine İyi Bak", "Disiplin",
    "Dayanıklılık", "Hayat", "Aşk", "Spor",
    "Dostluk", "Yaratıcılık", "Kariyer", "Şükran",
]

CATEGORIES_EN = [
    "Motivation", "Success", "Self-Care", "Discipline",
    "Resilience", "Life", "Love", "Sport",
    "Friendship", "Creativity", "Career", "Gratitude",
]

# =========================================================
#  QUOTES (sadece örnek — sen daha fazla ekleyebilirsin)
# =========================================================

QUOTES_TR = {
    "Spor": [
        "Kelebek gibi uçar, arı gibi sokarım. — Muhammed Ali",
        "Zorluklar, şampiyonları belirler.",
        "Ter, başarıya açılan kapının anahtarıdır.",
    ],
    "Motivasyon": [
        "Başarı tesadüf değildir; emek ister.",
        "Yavaş ilerlemekten korkma, yerinde saymaktan kork.",
    ],
}

QUOTES_EN = {
    "Sport": [
        "Float like a butterfly, sting like a bee. — Muhammad Ali",
        "Champions keep playing until they get it right.",
    ],
    "Motivation": [
        "Success is no accident.",
        "Great things never come from comfort zones.",
    ],
}

# =========================================================
#  USER MEMORY
# =========================================================

USER_LANG = {}      # user_id -> "tr" / "en"
USER_TOPIC = {}     # user_id -> category name
USER_NOTIFY = {}    # user_id -> True/False
USER_LAST_QUOTE = {}  # user_id -> text

# =========================================================
#  ADSGRAM REKLAM
# =========================================================

def fetch_adsgram_ad():
    platform = 16417
    url = f"https://adsgram.ai/api/v1/show?platform={platform}"

    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            data = r.json()
            if data.get("ok") and data.get("result"):
                ad = data["result"]
                title = ad.get("title", "")
                desc = ad.get("description", "")
                link = ad.get("link", "")
                return f"🟣 *Sponsored*\n\n*{title}*\n{desc}\n{link}"
    except:
        pass

    return (
        "🟣 *Sponsored*\n"
        "Günün anlamlı sözleri için Quote Masters'ı paylaş.\n"
        "https://t.me/QuoteMastersBot"
    )

# =========================================================
#  HELPER FUNCTIONS
# =========================================================

def get_lang(user_id):
    return USER_LANG.get(user_id, "tr")

def get_categories(lang):
    return CATEGORIES_TR if lang == "tr" else CATEGORIES_EN

def pick_quote(lang, topic):
    if lang == "tr":
        pool = QUOTES_TR.get(topic, [])
    else:
        pool = QUOTES_EN.get(topic, [])

    if not pool:
        return "“...”"

    return random.choice(pool)

# =========================================================
#  MENU BUTTONS (A + C SHARE SYSTEM)
# =========================================================

def menu_buttons(lang, quote_text=""):

    if lang == "tr":
        share_text = f"{quote_text}\n\n⭐ Daha fazla söz için: @QuoteMastersBot"
    else:
        share_text = f"{quote_text}\n\n⭐ More quotes: @QuoteMastersBot"

    encoded = quote_plus(share_text)
    encoded_bot = quote_plus(BOT_LINK)

    whatsapp_url = f"https://wa.me/?text={encoded}"
    telegram_url = f"https://t.me/share/url?url={encoded_bot}&text={encoded}"

    if lang == "tr":
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📅 Günün Sözü", callback_data="daily"),
                InlineKeyboardButton("📲 WhatsApp’ta Paylaş", url=whatsapp_url),
            ],
            [
                InlineKeyboardButton("📨 Telegram’da Paylaş", url=telegram_url),
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
                InlineKeyboardButton("📲 Share on WhatsApp", url=whatsapp_url),
            ],
            [
                InlineKeyboardButton("📨 Share on Telegram", url=telegram_url),
                InlineKeyboardButton("✨ New Quote", callback_data="new_quote")
            ],
            [
                InlineKeyboardButton("🔄 Change Topic", callback_data="change_topic"),
                InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
            ],
        ])

# =========================================================
#  CATEGORY BUTTONS
# =========================================================

def categories_buttons(lang):
    cats = get_categories(lang)
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

# =========================================================
#  SETTINGS BUTTONS
# =========================================================

def settings_buttons(lang):
    if lang == "tr":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Dili değiştir", callback_data="lang")],
            [InlineKeyboardButton("🔔 Bildirimleri Aç/Kapat", callback_data="notify")],
            [InlineKeyboardButton("⬅️ Geri", callback_data="back_menu")],
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Change Language", callback_data="lang")],
            [InlineKeyboardButton("🔔 Toggle Notifications", callback_data="notify")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_menu")],
        ])

# =========================================================
#  SEND QUOTE WITH UI
# =========================================================

async def send_quote(update, context, quote, lang):
    ad = fetch_adsgram_ad()
    msg = f"{quote}\n\n{ad}"
    keyboard = menu_buttons(lang, quote)
    await update.message.reply_text(msg, reply_markup=keyboard)

async def send_quote_edit(update, context, quote, lang):
    ad = fetch_adsgram_ad()
    msg = f"{quote}\n\n{ad}"
    keyboard = menu_buttons(lang, quote)
    await update.callback_query.edit_message_text(msg, reply_markup=keyboard)

# =========================================================
#  START HANDLER
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    USER_LANG[user.id] = "tr" if (user.language_code or "").startswith("tr") else "en"

    lang = USER_LANG[user.id]

    if lang == "tr":
        txt = "✨ Quote Masters'a hoş geldin!\nBir dil seç:"
    else:
        txt = "✨ Welcome to Quote Masters!\nChoose a language:"

    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇹🇷 Türkçe", callback_data="set_lang_tr"),
            InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en"),
        ]
    ]))

# =========================================================
#  CALLBACK HANDLER
# =========================================================

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    # --------------- DİL SEÇİMİ ---------------------
    if data == "set_lang_tr":
        USER_LANG[user_id] = "tr"
        await query.message.edit_text("Bir kategori seç:", reply_markup=categories_buttons("tr"))
        return

    if data == "set_lang_en":
        USER_LANG[user_id] = "en"
        await query.message.edit_text("Choose a category:", reply_markup=categories_buttons("en"))
        return

    lang = USER_LANG.get(user_id, "tr")

    # --------------- KATEGORİ SEÇİMİ ----------------
    if data.startswith("cat_"):
        topic = data.replace("cat_", "")
        USER_TOPIC[user_id] = topic

        quote = pick_quote(lang, topic)
        USER_LAST_QUOTE[user_id] = quote

        await query.message.edit_text(
            f"{quote}\n\n{fetch_adsgram_ad()}",
            reply_markup=menu_buttons(lang, quote)
        )
        return

    # --------------- YENİ SÖZ -----------------------
    if data == "new_quote":
        topic = USER_TOPIC.get(user_id, "Motivasyon")
        quote = pick_quote(lang, topic)
        USER_LAST_QUOTE[user_id] = quote
        await send_quote_edit(update, context, quote, lang)
        return

    # --------------- GÜNÜN SÖZÜ ---------------------
    if data == "daily":
        topic = USER_TOPIC.get(user_id, "Motivasyon")
        quote = pick_quote(lang, topic)
        USER_LAST_QUOTE[user_id] = quote
        await send_quote_edit(update, context, quote, lang)
        return

    # --------------- KONUYU DEĞİŞTİR ----------------
    if data == "change_topic":
        if lang == "tr":
            await query.message.edit_text("Bir kategori seç:", reply_markup=categories_buttons("tr"))
        else:
            await query.message.edit_text("Choose a category:", reply_markup=categories_buttons("en"))
        return

    # --------------- AYARLAR ------------------------
    if data == "settings":
        await query.message.edit_text(
            "Ayarlar:" if lang == "tr" else "Settings:",
            reply_markup=settings_buttons(lang)
        )
        return

    if data == "back_menu":
        quote = USER_LAST_QUOTE.get(user_id, "...")
        await send_quote_edit(update, context, quote, lang)
        return

    if data == "lang":
        await query.message.edit_text(
            "Bir dil seç:" if lang == "tr" else "Choose a language:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🇹🇷 Türkçe", callback_data="set_lang_tr"),
                    InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en"),
                ]
            ])
        )
        return

    if data == "notify":
        USER_NOTIFY[user_id] = not USER_NOTIFY.get(user_id, True)
        msg = "🔔 Bildirimler açık." if USER_NOTIFY[user_id] else "🔕 Bildirimler kapalı."
        await query.message.reply_text(msg)
        return


# =========================================================
#  DAILY JOB
# =========================================================

async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    for user_id, notify in USER_NOTIFY.items():
        if notify:
            lang = USER_LANG.get(user_id, "tr")
            txt = (
                "🎯 Günün sözü hazır! /start yaz."
                if lang == "tr"
                else "🎯 Quote of the day is ready! Type /start."
            )
            try:
                await context.bot.send_message(chat_id=user_id, text=txt)
            except:
                pass

# =========================================================
#  MAIN
# =========================================================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))

    app.job_queue.run_daily(
        daily_job,
        time=time(hour=10, minute=0, tzinfo=IST)
    )

    app.run_polling()

if __name__ == "__main__":
    main()
