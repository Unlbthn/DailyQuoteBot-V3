# ============================================================
#  QuoteMastersBot - FINAL VERSION (Daily Quote + AdsGram + Share)
# ============================================================

import os
import random
import urllib.parse
import logging
from datetime import date, time
from zoneinfo import ZoneInfo

import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ============================================================
#  LOAD TOKENS
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADSGRAM_BLOCK_ID = os.getenv("ADSGRAM_BLOCK_ID")  # ÖRN: "12345"

TZ_IST = ZoneInfo("Europe/Istanbul")
DAILY_QUOTE_HOUR = 10

# ============================================================
#  QUOTES IMPORT
# ============================================================

from quotes import quotes.py       # Tüm kategoriler TR/EN


# ============================================================
#  GLOBAL STATE
# ============================================================

USER_LANG = {}             # user_id -> "tr" / "en"
USER_TOPIC = {}            # user_id -> "motivation" vb.
USER_DAILY = {}            # user_id -> True/False
USER_LAST = {}             # user_id -> last quote text
KNOWN_USERS = set()        # günlük job için

DAILY_QUOTES = {"tr": "", "en": ""}   # o günün sabit sözü
DAILY_DATE = None                     # hangi güne ait olduğunu takip eder

DEFAULT_TOPIC = "motivation"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QuoteMastersBot")

# ============================================================
#  HELPER FUNCTIONS
# ============================================================

def get_user_lang(user) -> str:
    """Kullanıcı dili yoksa otomatik tespit eder."""
    uid = user.id
    if uid in USER_LANG:
        return USER_LANG[uid]

    lang_code = (user.language_code or "").lower()
    lang = "tr" if lang_code.startswith("tr") else "en"

    USER_LANG[uid] = lang
    USER_TOPIC.setdefault(uid, DEFAULT_TOPIC)
    USER_DAILY.setdefault(uid, True)
    KNOWN_USERS.add(uid)
    return lang


def pick_from_topic(topic: str, lang: str) -> str:
    """Sadece seçilen kategoriden rastgele söz getirir."""
    arr = QUOTES.get(topic, {}).get(lang, [])
    if not arr:
        return TEXTS[lang]["no_quote"]
    entry = random.choice(arr)
    text = entry["text"]
    author = entry.get("author")
    return f"{text} — {author}" if author else text


def pick_from_all(lang: str) -> str:
    """Günün sözü için tüm kategorilerden rastgele söz alır."""
    all_items = []
    for topic_data in QUOTES.values():
        all_items.extend(topic_data.get(lang, []))

    if not all_items:
        return TEXTS[lang]["no_quote"]

    entry = random.choice(all_items)
    text = entry["text"]
    author = entry.get("author")
    return f"{text} — {author}" if author else text


def ensure_daily_quotes():
    """Her gün TR ve EN için sabit günlük söz seçer."""
    global DAILY_DATE, DAILY_QUOTES

    today = date.today()
    if DAILY_DATE == today and DAILY_QUOTES["tr"] and DAILY_QUOTES["en"]:
        return  # zaten bugünün sözü seçilmiş

    DAILY_DATE = today
    DAILY_QUOTES["tr"] = pick_from_all("tr")
    DAILY_QUOTES["en"] = pick_from_all("en")
    logger.info("Yeni günlük sözler seçildi.")
# ============================================================
#  ADSGRAM REKLAM BLOĞU
# ============================================================

def fetch_adsgram_ad() -> str:
    """
    AdsGram reklam metnini çekerek aşağıdaki formatta döndürür:
    
    🟣 *Sponsored*
    <title>
    <description>
    <link>

    Eğer reklam yoksa → sadece 🟣 *Sponsored* döner.
    """
    if not ADSGRAM_BLOCK_ID:
        return "🟣 *Sponsored*"

    try:
        url = f"https://adsgram.ai/api/v1/show?block_id={ADSGRAM_BLOCK_ID}"
        response = requests.get(url, timeout=3)

        if response.status_code != 200:
            return "🟣 *Sponsored*"

        data = response.json()
        if not data.get("ok"):
            return "🟣 *Sponsored*"

        result = data.get("result", {})
        title = result.get("title", "")
        desc = result.get("description", "")
        link = result.get("link", "")
        text = result.get("text", "")

        lines = ["🟣 *Sponsored*"]
        if title:
            lines.append(f"*{title}*")
        if desc:
            lines.append(desc)
        if text and text not in desc:
            lines.append(text)
        if link:
            lines.append(link)

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"AdsGram error: {e}")
        return "🟣 *Sponsored*"


# ============================================================
#  PAYLAŞIM + MENÜ BUTONLARI
# ============================================================

def build_menu(lang: str, quote_text: str) -> InlineKeyboardMarkup:
    """WhatsApp + Telegram paylaşım butonları ile premium alt menü oluşturur."""

    if lang == "tr":
        daily_label = "📅 Günün Sözü"
        new_label = "✨ Sözü değiştir"
        change_label = "🔄 Konuyu değiştir"
        settings_label = "⚙️ Ayarlar"
        wa_label = "📲 WhatsApp’ta Paylaş"
        tg_label = "📨 Telegram’da Paylaş"
        share_tail = "\n\n⭐ Daha fazla söz için: @QuoteMastersBot"
    else:
        daily_label = "📅 Quote of the Day"
        new_label = "✨ New Quote"
        change_label = "🔄 Change Topic"
        settings_label = "⚙️ Settings"
        wa_label = "📲 Share on WhatsApp"
        tg_label = "📨 Share on Telegram"
        share_tail = "\n\n⭐ More quotes: @QuoteMastersBot"

    share_text = quote_text + share_tail
    encoded = urllib.parse.quote_plus(share_text)
    encoded_bot = urllib.parse.quote_plus("https://t.me/QuoteMastersBot")

    whatsapp_url = f"https://wa.me/?text={encoded}"
    telegram_url = f"https://t.me/share/url?url={encoded_bot}&text={encoded}"

    keyboard = [
        [
            InlineKeyboardButton(daily_label, callback_data="action:daily"),
            InlineKeyboardButton(wa_label, url=whatsapp_url),
        ],
        [
            InlineKeyboardButton(tg_label, url=telegram_url),
            InlineKeyboardButton(new_label, callback_data="action:new"),
        ],
        [
            InlineKeyboardButton(change_label, callback_data="action:change"),
            InlineKeyboardButton(settings_label, callback_data="action:settings"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
#  KATEGORİ SEÇİM BUTONLARI
# ============================================================

TOPIC_LABELS = {
    "tr": {
        "motivation": "Motivasyon",
        "love": "Aşk",
        "success": "Başarı",
        "life": "Hayat",
        "selfcare": "Kendine İyi Bak",
        "sport": "Spor",
        "discipline": "Disiplin",
        "friendship": "Dostluk",
        "resilience": "Dayanıklılık",
        "creativity": "Yaratıcılık",
        "work": "İş & Kariyer",
        "gratitude": "Şükran",
    },
    "en": {
        "motivation": "Motivation",
        "love": "Love",
        "success": "Success",
        "life": "Life",
        "selfcare": "Self-care",
        "sport": "Sport",
        "discipline": "Discipline",
        "friendship": "Friendship",
        "resilience": "Resilience",
        "creativity": "Creativity",
        "work": "Career",
        "gratitude": "Gratitude",
    },
}

TOPIC_ORDER = [
    "motivation",
    "love",
    "success",
    "life",
    "selfcare",
    "sport",
    "discipline",
    "friendship",
    "resilience",
    "creativity",
    "work",
    "gratitude",
]


def build_topics(lang: str) -> InlineKeyboardMarkup:
    """6 satır × 2 sütun konu seçme menüsü."""
    labels = TOPIC_LABELS[lang]
    rows = []
    row = []

    for topic in TOPIC_ORDER:
        btn = InlineKeyboardButton(labels[topic], callback_data=f"topic:{topic}")
        row.append(btn)
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    return InlineKeyboardMarkup(rows)


# ============================================================
#  AYARLAR MENÜSÜ
# ============================================================

def build_settings(lang: str) -> InlineKeyboardMarkup:
    if lang == "tr":
        btn_lang = "🌐 Dili değiştir"
        btn_notif = "🔔 Bildirimleri Aç/Kapat"
        btn_back = "⬅️ Geri"
    else:
        btn_lang = "🌐 Change Language"
        btn_notif = "🔔 Toggle Daily Quote"
        btn_back = "⬅️ Back"

    keyboard = [
        [InlineKeyboardButton(btn_lang, callback_data="settings:lang")],
        [InlineKeyboardButton(btn_notif, callback_data="settings:toggle")],
        [InlineKeyboardButton(btn_back, callback_data="settings:back")],
    ]

    return InlineKeyboardMarkup(keyboard)
# ============================================================
#  SÖZ GÖNDERİMİ
# ============================================================

async def send_quote(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    quote_text: str,
    lang: str,
    edit: bool = False,
    daily: bool = False
):
    """Her söz gönderiminde reklam + alt menü ekleyerek gönderir."""

    USER_LAST[update.effective_user.id] = quote_text  # type: ignore

    # Günün sözü başlığı
    if daily:
        title = TEXTS[lang]["daily_quote"]
        text = f"{title}\n\n{quote_text}"
    else:
        text = quote_text

    # Reklam bloğu
    ad = fetch_adsgram_ad()
    if ad:
        text += f"\n\n{ad}"

    # Alt menü
    keyboard = build_menu(lang, quote_text)

    # Mesaj güncelleme / yeni mesaj
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.effective_chat.send_message(  # type: ignore
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )


# ============================================================
#  /START KOMUTU
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)

    welcome = WELCOME_TEXT[lang]

    await update.message.reply_text(
        welcome,
        parse_mode="Markdown",
        reply_markup=language_keyboard()
    )


# ============================================================
#  CALLBACK HANDLER
# ============================================================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id
    lang = get_user_lang(user)
    data = query.data or ""

    # --------------------------------------------------------
    # DİL DEĞİŞTİRME
    # --------------------------------------------------------

    if data.startswith("lang:"):
        new_lang = data.split(":")[1]
        USER_LANG[user_id] = new_lang
        lang = new_lang

        if lang == "tr":
            text = TEXTS["tr"]["topic_select"]
        else:
            text = TEXTS["en"]["topic_select"]

        await query.edit_message_text(text, reply_markup=build_topics(lang))
        return

    # --------------------------------------------------------
    # KONU SEÇİMİ
    # --------------------------------------------------------

    if data.startswith("topic:"):
        topic = data.split(":")[1]
        USER_TOPIC[user_id] = topic

        quote_text = pick_from_topic(topic, lang)
        await send_quote(update, context, quote_text, lang, edit=True)
        return

    # --------------------------------------------------------
    # ALT MENÜ AKSİYONLARI
    # --------------------------------------------------------

    if data.startswith("action:"):
        action = data.split(":")[1]

        # ✨ SÖZÜ DEĞİŞTİR
        if action == "new":
            topic = USER_TOPIC.get(user_id, DEFAULT_TOPIC)
            quote_text = pick_from_topic(topic, lang)
            await send_quote(update, context, quote_text, lang, edit=True)
            return

        # 📅 GÜNÜN SÖZÜ
        if action == "daily":
            ensure_daily_quotes()
            quote_text = DAILY_QUOTES[lang]
            await send_quote(update, context, quote_text, lang, edit=True, daily=True)
            return

        # 🔄 KONUYU DEĞİŞTİR
        if action == "change":
            if lang == "tr":
                text = TEXTS["tr"]["topic_select"]
            else:
                text = TEXTS["en"]["topic_select"]

            await query.edit_message_text(text, reply_markup=build_topics(lang))
            return

        # ⚙️ AYARLAR
        if action == "settings":
            await query.edit_message_text(
                TEXTS[lang]["settings"],
                reply_markup=build_settings(lang)
            )
            return

    # --------------------------------------------------------
    # AYARLAR ALT MENÜSÜ
    # --------------------------------------------------------

    if data.startswith("settings:"):
        sub = data.split(":")[1]

        # 🌐 DİL DEĞİŞTİR
        if sub == "lang":
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang:tr"),
                    InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
                ]
            ])
            await query.edit_message_text(TEXTS[lang]["language"], reply_markup=keyboard)
            return

        # 🔔 BİLDİRİM AÇ/KAPAT
        if sub == "toggle":
            current = USER_DAILY.get(user_id, True)
            USER_DAILY[user_id] = not current

            msg = (
                TEXTS["tr"]["notif_off"] if current else TEXTS["tr"]["notif_on"]
            ) if lang == "tr" else (
                TEXTS["en"]["notif_off"] if current else TEXTS["en"]["notif_on"]
            )

            await query.answer(msg, show_alert=True)
            return

        # ⬅️ GERİ
        if sub == "back":
            last = USER_LAST.get(user_id)
            if not last:
                last = pick_from_all(lang)
            await send_quote(update, context, last, lang, edit=True)
            return


# ============================================================
#  GÜNDELİK BİLDİRİM JOB'U (SAAT 10:00)
# ============================================================

async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    ensure_daily_quotes()

    for user_id in list(KNOWN_USERS):
        # Bildirim kapalıysa geç
        if not USER_DAILY.get(user_id, True):
            continue

        lang = USER_LANG.get(user_id, "tr")
        quote_text = DAILY_QUOTES[lang]

        ad = fetch_adsgram_ad()

        msg = f"{TEXTS[lang]['daily_quote']}\n\n{quote_text}"
        if ad:
            msg += f"\n\n{ad}"

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=build_menu(lang, quote_text)
            )
        except Exception as e:
            logger.warning(f"Daily quote failed for {user_id}: {e}")


# ============================================================
#  BOTU BAŞLAT
# ============================================================

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing!")

    app = Application.builder().token(BOT_TOKEN).build()

    # Komutlar
    app.add_handler(CommandHandler("start", start))

    # Callback
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Günlük saat 10:00 job
    send_time = time(hour=DAILY_QUOTE_HOUR, minute=0, tzinfo=TZ_IST)
    app.job_queue.run_daily(daily_job, time=send_time)

    app.run_polling()


if __name__ == "__main__":
    main()

