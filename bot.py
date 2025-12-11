# bot.py
import os
import logging
import random
import datetime
from typing import Dict, Any

import pytz
import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from quotes import QUOTES

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env değişkeni set edilmemiş.")

# AdsGram (platform tabanlı örnek)
ADSGRAM_URL = "https://api.adsgram.ai/advbot"
ADSGRAM_PLATFORM_ID = 16417  # senin AdsGram platform ID

IST_TIMEZONE = pytz.timezone("Europe/Istanbul")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# -------------------------------------------------
# GLOBAL STATE
# -------------------------------------------------

# Kullanıcı ayarları: {user_id: {"lang": "tr/en", "topic": "motivation", "notify": True, "last_quote": {...}}}
users: Dict[int, Dict[str, Any]] = {}

# Günün sözü (global)
daily_quote: Dict[str, Any] = {"text": None, "author": None}

# -------------------------------------------------
# METİN TABLOSU
# -------------------------------------------------

TEXTS = {
    "tr": {
        "welcome": (
            "✨ Quote Masters'a hoş geldin!\n\n"
            "Konuya göre anlamlı sözler keşfedebilir ve her gün saat 10:00'da "
            "günün sözünü alabilirsin."
        ),
        "choose_language": "Lütfen bir dil seç:",
        "choose_topic": "Bir konu seç:",
        "daily_header": "📅 Günün Sözü",
        "settings": "⚙ Ayarlar",
        "settings_lang": "🌐 Dil / Language",
        "settings_notify": "🔔 Bildirimleri Aç/Kapat",
        "notify_on": "🔔 Günlük bildirimler açıldı (10:00 TR).",
        "notify_off": "🔕 Günlük bildirimler kapatıldı.",
        "share_link_ready": "🔗 Paylaşım linki hazır:",
        "topic_labels": {
            "motivation": "Motivasyon",
            "success": "Başarı",
            "selfcare": "Kendine İyi Bak",
            "discipline": "Disiplin",
            "resilience": "Dayanıklılık",
            "career": "İş & Kariyer",
            "love": "Aşk",
            "life": "Hayat",
            "sport": "Spor",
            "friendship": "Dostluk",
            "creativity": "Yaratıcılık",
            "gratitude": "Şükran",
        },
        "menu_daily": "📅 Günün Sözü",
        "menu_share_wa": "📤 WhatsApp",
        "menu_share_tg": "📣 Telegram",
        "menu_new": "🔄 Sözü değiştir",
        "menu_change_topic": "📚 Konuyu değiştir",
        "menu_settings": "⚙ Ayarlar",
        "daily_ping": "🎯 Bugünün sözü hazır! Görmek için /start yaz.",
    },
    "en": {
        "welcome": (
            "✨ Welcome to Quote Masters!\n\n"
            "Discover meaningful quotes by topic and receive a quote of the day at 10:00 Istanbul time."
        ),
        "choose_language": "Please choose a language:",
        "choose_topic": "Choose a topic:",
        "daily_header": "📅 Quote of the Day",
        "settings": "⚙ Settings",
        "settings_lang": "🌐 Language",
        "settings_notify": "🔔 Toggle daily notifications",
        "notify_on": "🔔 Daily notifications enabled (10:00 Istanbul time).",
        "notify_off": "🔕 Daily notifications disabled.",
        "share_link_ready": "🔗 Share link is ready:",
        "topic_labels": {
            "motivation": "Motivation",
            "success": "Success",
            "selfcare": "Self-care",
            "discipline": "Discipline",
            "resilience": "Resilience",
            "career": "Career",
            "love": "Love",
            "life": "Life",
            "sport": "Sport",
            "friendship": "Friendship",
            "creativity": "Creativity",
            "gratitude": "Gratitude",
        },
        "menu_daily": "📅 Quote of the Day",
        "menu_share_wa": "📤 WhatsApp",
        "menu_share_tg": "📣 Telegram",
        "menu_new": "🔄 New Quote",
        "menu_change_topic": "📚 Change Topic",
        "menu_settings": "⚙ Settings",
        "daily_ping": "🎯 Today's quote is ready! Type /start to see it.",
    },
}


TOPICS_ORDER = [
    "motivation",
    "success",
    "selfcare",
    "discipline",
    "resilience",
    "career",
    "love",
    "life",
    "sport",
    "friendship",
    "creativity",
    "gratitude",
]

SUPPORTED_LANGS = ("tr", "en")


# -------------------------------------------------
# UTILS
# -------------------------------------------------

def get_user(user_id: int) -> Dict[str, Any]:
    if user_id not in users:
        users[user_id] = {
            "lang": "tr",
            "topic": "motivation",
            "notify": True,
            "last_quote": None,
        }
    return users[user_id]


def detect_initial_lang(update: Update) -> str:
    code = (update.effective_user.language_code or "").lower()
    if code.startswith("tr"):
        return "tr"
    return "en"


def pick_random_quote(lang: str, topic: str) -> Dict[str, Any]:
    # Önce tam eşleşme (lang, topic)
    key = (lang, topic)
    if key in QUOTES and QUOTES[key]:
        return random.choice(QUOTES[key])

    # Sonra diğer dilde aynı konu
    for other_lang in SUPPORTED_LANGS:
        key2 = (other_lang, topic)
        if key2 in QUOTES and QUOTES[key2]:
            return random.choice(QUOTES[key2])

    # En son fallback: en/motivation
    if ("en", "motivation") in QUOTES and QUOTES[("en", "motivation")]:
        return random.choice(QUOTES[("en", "motivation")])

    return {"text": "...", "author": None}


def format_quote_text(q: Dict[str, Any]) -> str:
    text = q.get("text", "")
    author = q.get("author") or ""
    if author:
        return f"“{text}”\n— {author}"
    return f"“{text}”"


def refresh_daily_quote() -> None:
    """Her gün için global tek bir söz seç."""
    all_quotes = []
    for lst in QUOTES.values():
        all_quotes.extend(lst)
    if not all_quotes:
        daily_quote["text"] = "..."
        daily_quote["author"] = None
        return

    chosen = random.choice(all_quotes)
    daily_quote["text"] = chosen.get("text")
    daily_quote["author"] = chosen.get("author")


def build_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang:tr"),
                InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
            ]
        ]
    )


def build_topics_keyboard(lang: str) -> InlineKeyboardMarkup:
    labels = TEXTS[lang]["topic_labels"]
    rows = []
    row = []
    for topic in TOPICS_ORDER:
        label = labels.get(topic, topic.capitalize())
        row.append(InlineKeyboardButton(label, callback_data=f"topic:{topic}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def build_main_menu(lang: str) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t["menu_daily"], callback_data="action:daily"),
                InlineKeyboardButton(t["menu_share_wa"], callback_data="share:wa"),
            ],
            [
                InlineKeyboardButton(t["menu_share_tg"], callback_data="share:tg"),
                InlineKeyboardButton(t["menu_new"], callback_data="action:new"),
            ],
            [
                InlineKeyboardButton(
                    t["menu_change_topic"], callback_data="action:change_topic"
                ),
                InlineKeyboardButton(
                    t["menu_settings"], callback_data="action:settings"
                ),
            ],
        ]
    )


def build_settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t["settings_lang"], callback_data="settings:lang"
                )
            ],
            [
                InlineKeyboardButton(
                    t["settings_notify"], callback_data="settings:notify"
                )
            ],
        ]
    )


# -------------------------------------------------
# AdsGram
# -------------------------------------------------

def fetch_adsgram_text(user_id: int) -> str:
    """
    AdsGram'dan reklam çekmeye çalışır.
    Eğer reklam yoksa statik fallback döner.
    """
    try:
        resp = requests.post(
            ADSGRAM_URL,
            data={
                "platform": ADSGRAM_PLATFORM_ID,
                "telegram_user_id": user_id,
                "language": "en",  # TR olsa da EN reklam çekmeye çalışıyoruz
            },
            timeout=3,
        )
        body = resp.text.strip()
        logger.info("AdsGram status=%s body=%s", resp.status_code, body[:200])

        # AdsGram bazen düz text dönebiliyor ("No available advertisement...")
        if not body or body.lower().startswith("no available advertisement"):
            raise ValueError("No ad available")

        data = resp.json()
        text = (
            data.get("text") or data.get("text_html") or data.get("title") or None
        )
        url = data.get("click_url") or data.get("url")
        if text and url:
            return f"📢 {text}\n{url}"

        if text:
            return f"📢 {text}"

        # bir şey anlamlı gelmediyse fallback
        raise ValueError("Invalid ad JSON")
    except Exception as e:
        logger.warning("AdsGram error or no ad: %s", e)
        # Statik fallback reklam
        return (
            "📢 Sponsored\n"
            "Günün anlamlı sözleri için Quote Masters'ı arkadaşlarınla paylaş.\n"
            "https://t.me/QuoteMastersBot"
        )


# -------------------------------------------------
# HANDLER’LAR
# -------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    user_data = get_user(user.id)

    # ilk gelişte dili tespit et
    initial_lang = detect_initial_lang(update)
    user_data["lang"] = initial_lang

    t = TEXTS[initial_lang]

    await chat.send_message(t["welcome"])
    await chat.send_message(
        t["choose_language"], reply_markup=build_language_keyboard()
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()

    user = query.from_user
    chat = query.message.chat
    data = query.data

    user_data = get_user(user.id)
    lang = user_data["lang"]
    t = TEXTS[lang]

    # DİL SEÇİMİ
    if data.startswith("lang:"):
        new_lang = data.split(":", 1)[1]
        if new_lang in SUPPORTED_LANGS:
            user_data["lang"] = new_lang
            lang = new_lang
            t = TEXTS[lang]
        await query.message.reply_text(
            t["choose_topic"], reply_markup=build_topics_keyboard(lang)
        )
        return

    # TOPİK SEÇİMİ
    if data.startswith("topic:"):
        topic = data.split(":", 1)[1]
        user_data["topic"] = topic
        quote = pick_random_quote(lang, topic)
        user_data["last_quote"] = quote

        text = format_quote_text(quote)
        ad = fetch_adsgram_text(user.id)
        full = f"{text}\n\n{ad}"

        await query.message.reply_text(
            full,
            reply_markup=build_main_menu(lang),
        )
        return

    # AKSİYONLAR
    if data.startswith("action:"):
        action = data.split(":", 1)[1]

        # Günün sözü
        if action == "daily":
            if not daily_quote["text"]:
                refresh_daily_quote()
            # Günün sözü başlık + söz
            header = t["daily_header"]
            base = f"“{daily_quote['text']}”"
            if daily_quote.get("author"):
                base += f"\n— {daily_quote['author']}"
            ad = fetch_adsgram_text(user.id)
            full = f"{header}\n\n{base}\n\n{ad}"

            # last_quote güncellenir ki paylaşınca bu gitsin
            user_data["last_quote"] = {
                "text": daily_quote["text"],
                "author": daily_quote["author"],
            }

            await query.message.reply_text(
                full,
                reply_markup=build_main_menu(lang),
            )
            return

        # Yeni söz (aynı konu)
        if action == "new":
            topic = user_data.get("topic") or "motivation"
            quote = pick_random_quote(lang, topic)
            user_data["last_quote"] = quote

            text = format_quote_text(quote)
            ad = fetch_adsgram_text(user.id)
            full = f"{text}\n\n{ad}"

            await query.message.reply_text(
                full,
                reply_markup=build_main_menu(lang),
            )
            return

        # Konu değiştir
        if action == "change_topic":
            await query.message.reply_text(
                t["choose_topic"], reply_markup=build_topics_keyboard(lang)
            )
            return

        # Ayarlar
        if action == "settings":
            await query.message.reply_text(
                t["settings"], reply_markup=build_settings_keyboard(lang)
            )
            return

    # AYARLAR
    if data.startswith("settings:"):
        _, what = data.split(":", 1)

        # Dil alt menü
        if what == "lang":
            await query.message.reply_text(
                t["choose_language"], reply_markup=build_language_keyboard()
            )
            return

        # Bildirim aç/kapat
        if what == "notify":
            user_data["notify"] = not user_data.get("notify", True)
            msg = t["notify_on"] if user_data["notify"] else t["notify_off"]
            await query.message.reply_text(msg)
            return

    # PAYLAŞIM
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from urllib.parse import quote_plus

def build_share_keyboard(quote_text: str, lang: str) -> InlineKeyboardMarkup:
    # Paylaşılacak metin
    share_text = (
        f"{quote_text}\n\n"
        "Türkçe ve İngilizce anlamlı sözler için: @QuoteMastersBot"
        if lang == "tr"
        else f"{quote_text}\n\n"
             "Meaningful quotes in Turkish & English: @QuoteMastersBot"
    )

    wa_url = f"https://wa.me/?text={quote_plus(share_text)}"
    tg_url = f"https://t.me/share/url?url={quote_plus('@QuoteMastersBot')}&text={quote_plus(share_text)}"

    keyboard = [
        [
            InlineKeyboardButton("📲 WhatsApp", url=wa_url),
            InlineKeyboardButton("📨 Telegram", url=tg_url),
        ],
        # alttaki satırda Günün Sözü / Sözü Değiştir / Konuyu Değiştir / Ayarlar vs durabilir
    ]
    return InlineKeyboardMarkup(keyboard)



# -------------------------------------------------
# GÜNLÜK JOB
# -------------------------------------------------

async def daily_broadcast_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Her gün 10:00 TR'de herkese günün sözünü yollar."""
    refresh_daily_quote()
    for user_id, data in list(users.items()):
        if not data.get("notify", True):
            continue
        lang = data.get("lang", "tr")
        t = TEXTS[lang]
        try:
            await context.bot.send_message(chat_id=user_id, text=t["daily_ping"])
        except Exception as e:
            logger.warning("Daily ping send error for %s: %s", user_id, e)


# -------------------------------------------------
# MAIN
# -------------------------------------------------

def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Günlük job: 10:00 TR
    job_queue = application.job_queue
    job_queue.run_daily(
        daily_broadcast_job,
        time=datetime.time(hour=10, minute=0, tzinfo=IST_TIMEZONE),
        name="daily-broadcast",
    )

    logger.info("Quote Masters bot starting (PTB 20.7)...")
    application.run_polling()


if __name__ == "__main__":
    main()

