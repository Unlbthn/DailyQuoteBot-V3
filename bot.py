# ============================================================
#  QuoteMastersBot - FINAL (Daily Quote + AdsGram + Share)
#  - QUOTES_TR / QUOTES_EN -> quotes.py'den geliyor
#  - Günün sözü: tüm sözlerden random, günde 1 kez (10:00 TR)
#  - "Günün Sözü" butonu her zaman o gün seçilmiş aynı sözü gösterir
#  - "Sözü değiştir" sadece seçili konudan random getirir
#  - WhatsApp / Telegram paylaş butonları sadece paylaşım ekranını açar
#  - Her sözün altında AdsGram reklam metni (varsa) gösterilir
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
    ContextTypes,
)

# quotes.py içeriğini kullan
from quotes import QUOTES_TR, QUOTES_EN


# ============================================================
#  CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADSGRAM_BLOCK_ID = os.getenv("ADSGRAM_BLOCK_ID")  # Render env'de: bot-17933 yazıyor
TZ_IST = ZoneInfo("Europe/Istanbul")
DAILY_QUOTE_HOUR = 10  # 10:00 TR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QuoteMastersBot")

# ============================================================
#  GLOBAL STATE
# ============================================================

USER_LANG: dict[int, str] = {}       # user_id -> "tr" / "en"
USER_TOPIC: dict[int, str] = {}      # user_id -> kategori label (örn: "Motivasyon" / "Motivation")
USER_DAILY: dict[int, bool] = {}     # user_id -> günlük bildirim açık mı
KNOWN_USERS: set[int] = set()        # günlük job için user listesi

DAILY_QUOTES: dict[str, str] = {"tr": "", "en": ""}  # o günün sabit sözleri
DAILY_DATE: date | None = None                        # hangi güne ait olduğunu takip eder


# ============================================================
#  STATIK METINLER
# ============================================================

TEXTS = {
    "tr": {
        "welcome": (
            "✨ Quote Masters'a hoş geldin!\n\n"
            "Konuya göre anlamlı sözler keşfet, her gün saat 10:00’da günün sözünü al."
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
        "menu_daily": "📅 Günün Sözü",
        "menu_share_wa": "📤 WhatsApp",
        "menu_share_tg": "📣 Telegram",
        "menu_new": "🔄 Sözü değiştir",
        "menu_change_topic": "📚 Konuyu değiştir",
        "menu_settings": "⚙ Ayarlar",
        "daily_ping": "🎯 Bugünün sözü hazır! Görmek için /start yaz.",
        "no_quote": "Şu an bu konu için söz bulunamadı.",
    },
    "en": {
        "welcome": (
            "✨ Welcome to Quote Masters!\n\n"
            "Discover meaningful quotes by topic and get a quote of the day at 10:00 Istanbul time."
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
        "menu_daily": "📅 Quote of the Day",
        "menu_share_wa": "📤 WhatsApp",
        "menu_share_tg": "📣 Telegram",
        "menu_new": "🔄 New Quote",
        "menu_change_topic": "📚 Change Topic",
        "menu_settings": "⚙ Settings",
        "daily_ping": "🎯 Today's quote is ready! Type /start to see it.",
        "no_quote": "No quote available for this topic yet.",
    },
}


# ============================================================
#  HELPERS: DIL & DATA
# ============================================================

def get_user_lang(user) -> str:
    """Kullanıcının dilini belirle; yoksa Telegram dil koduna göre tahmin et."""
    uid = user.id
    if uid in USER_LANG:
        return USER_LANG[uid]

    lang_code = (user.language_code or "").lower()
    lang = "tr" if lang_code.startswith("tr") else "en"

    USER_LANG[uid] = lang
    USER_DAILY.setdefault(uid, True)
    KNOWN_USERS.add(uid)
    return lang


def get_quotes_dict(lang: str) -> dict[str, list[str]]:
    return QUOTES_TR if lang == "tr" else QUOTES_EN


def pick_from_topic(topic_label: str, lang: str) -> str:
    """Sadece seçilen kategoriden rastgele söz getirir (quotes.py'den)."""
    data = get_quotes_dict(lang)
    arr = data.get(topic_label, [])
    if not arr:
        return TEXTS[lang]["no_quote"]
    return random.choice(arr)


def pick_from_all(lang: str) -> str:
    """Günün sözü için tüm kategorilerden rastgele söz alır."""
    data = get_quotes_dict(lang)
    all_items: list[str] = []
    for lst in data.values():
        all_items.extend(lst)

    if not all_items:
        return TEXTS[lang]["no_quote"]

    return random.choice(all_items)


def ensure_daily_quotes() -> None:
    """Gün değişmişse TR ve EN için yeni günlük söz üret."""
    global DAILY_DATE, DAILY_QUOTES

    today = date.today()
    if DAILY_DATE == today:
        return

    DAILY_DATE = today
    DAILY_QUOTES["tr"] = pick_from_all("tr")
    DAILY_QUOTES["en"] = pick_from_all("en")
    logger.info("New daily quotes selected: TR='%s' | EN='%s'",
                DAILY_QUOTES['tr'][:40], DAILY_QUOTES['en'][:40])


# ============================================================
#  ADSGRAM
# ============================================================

def fetch_adsgram_ad() -> str:
    """
    AdsGram'den reklam çeker.
    Türkçe reklam yoksa / reklam bulunamazsa yine de *Sponsored* fallback metnini döner.
    """
    # Platform ID botu AdsGram panelinde oluşturduğun sayfa
    platform_id = 16417

    if not ADSGRAM_BLOCK_ID:
        # Yine de fallback göster
        return (
            "🟣 *Sponsored*\n"
            "Günün anlamlı sözleri için Quote Masters'ı arkadaşlarınla paylaş."
        )

    url = (
        "https://adsgram.ai/api/v1/show"
        f"?platform={platform_id}&block_id={ADSGRAM_BLOCK_ID}"
    )

    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            data = r.json()
            if data.get("ok") and data.get("result"):
                ad = data["result"]
                title = ad.get("title", "")
                desc = ad.get("description", "")
                link = ad.get("link", "")
                parts = ["🟣 *Sponsored*"]
                if title:
                    parts.append(f"\n*{title}*")
                if desc:
                    parts.append(f"\n{desc}")
                if link:
                    parts.append(f"\n{link}")
                return "".join(parts)
    except Exception as e:
        logger.warning("AdsGram error: %s", e)

    # Fallback
    return (
        "🟣 *Sponsored*\n"
        "Günün anlamlı sözleri için Quote Masters'ı arkadaşlarınla paylaş."
    )


def format_quote_with_ad(quote_text: str, lang: str) -> str:
    ad_text = fetch_adsgram_ad()
    header = TEXTS[lang]["daily_header"]
    return f"{header}\n\n{quote_text}\n\n{ad_text}"


# ============================================================
#  BUTTON BUILDERS
# ============================================================

def menu_buttons(lang: str, quote_text: str = "") -> InlineKeyboardMarkup:
    """
    Ana menü butonları.
    WhatsApp / Telegram share butonları sadece paylaşım ekranını açar.
    """
    encoded = urllib.parse.quote(quote_text or "")
    whatsapp_url = f"https://wa.me/?text={encoded}"
    telegram_url = f"https://t.me/share/url?url={encoded}&text={encoded}"

    t = TEXTS[lang]
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t["menu_daily"], callback_data="daily"),
            InlineKeyboardButton(t["menu_share_wa"], url=whatsapp_url),
        ],
        [
            InlineKeyboardButton(t["menu_share_tg"], url=telegram_url),
            InlineKeyboardButton(t["menu_new"], callback_data="new_quote"),
        ],
        [
            InlineKeyboardButton(t["menu_change_topic"], callback_data="change_topic"),
            InlineKeyboardButton(t["menu_settings"], callback_data="settings"),
        ],
    ])


def categories_buttons(lang: str) -> InlineKeyboardMarkup:
    data = get_quotes_dict(lang)
    labels = list(data.keys())
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    for label in labels:
        row.append(InlineKeyboardButton(label, callback_data=f"cat::{label}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    return InlineKeyboardMarkup(rows)


def settings_buttons(lang: str) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t["settings_lang"], callback_data="toggle_lang")],
        [InlineKeyboardButton(t["settings_notify"], callback_data="toggle_notify")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_menu")],
    ])


# ============================================================
#  HANDLERS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    lang = get_user_lang(user)
    ensure_daily_quotes()

    # İlk kez gelenlerde konu seçtirelim
    uid = user.id
    if uid not in USER_TOPIC:
        text = TEXTS[lang]["welcome"] + "\n\n" + TEXTS[lang]["choose_topic"]
        await update.message.reply_text(
            text,
            reply_markup=categories_buttons(lang),
        )
        return

    # Daha önce konu seçmişse, direkt ana menü + günlük söz
    daily = DAILY_QUOTES[lang]
    msg = format_quote_with_ad(daily, lang)
    await update.message.reply_text(
        msg,
        reply_markup=menu_buttons(lang, daily),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    lang = get_user_lang(user)
    uid = user.id

    data = query.data or ""

    # Konu seçimi
    if data.startswith("cat::"):
        label = data.split("::", 1)[1]
        USER_TOPIC[uid] = label
        quote = pick_from_topic(label, lang)
        msg = f"{quote}\n\n{fetch_adsgram_ad()}"
        await query.edit_message_text(
            msg,
            reply_markup=menu_buttons(lang, quote),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        return

    # Günün sözü (sabit)
    if data == "daily":
        ensure_daily_quotes()
        quote = DAILY_QUOTES[lang]
        msg = format_quote_with_ad(quote, lang)
        await query.edit_message_text(
            msg,
            reply_markup=menu_buttons(lang, quote),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        return

    # Sözü değiştir (sadece seçili konudan)
    if data == "new_quote":
        topic_label = USER_TOPIC.get(uid)
        if not topic_label:
            # Konu seçilmemişse önce konu seçtir
            await query.edit_message_text(
                TEXTS[lang]["choose_topic"],
                reply_markup=categories_buttons(lang),
            )
            return

        quote = pick_from_topic(topic_label, lang)
        msg = f"{quote}\n\n{fetch_adsgram_ad()}"
        await query.edit_message_text(
            msg,
            reply_markup=menu_buttons(lang, quote),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        return

    # Konuyu değiştir
    if data == "change_topic":
        await query.edit_message_text(
            TEXTS[lang]["choose_topic"],
            reply_markup=categories_buttons(lang),
        )
        return

    # Ayarlar menüsü
    if data == "settings":
        await query.edit_message_text(
            TEXTS[lang]["settings"],
            reply_markup=settings_buttons(lang),
        )
        return

    # Dil değiştir
    if data == "toggle_lang":
        USER_LANG[uid] = "en" if lang == "tr" else "tr"
        new_lang = USER_LANG[uid]
        await query.edit_message_text(
            TEXTS[new_lang]["settings"],
            reply_markup=settings_buttons(new_lang),
        )
        return

    # Bildirim aç / kapa
    if data == "toggle_notify":
        current = USER_DAILY.get(uid, True)
        USER_DAILY[uid] = not current
        txt_key = "notify_on" if USER_DAILY[uid] else "notify_off"
        await query.edit_message_text(
            TEXTS[lang][txt_key],
            reply_markup=settings_buttons(lang),
        )
        return

    # Menüyü geri getir
    if data == "back_to_menu":
        ensure_daily_quotes()
        quote = DAILY_QUOTES[lang]
        msg = format_quote_with_ad(quote, lang)
        await query.edit_message_text(
            msg,
            reply_markup=menu_buttons(lang, quote),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        return


# ============================================================
#  DAILY JOB
# ============================================================

async def daily_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Her gün 10:00'da bildirim açmış kullanıcılara günün sözünü gönderir."""
    ensure_daily_quotes()
    for uid in list(KNOWN_USERS):
        lang = USER_LANG.get(uid, "tr")
        if not USER_DAILY.get(uid, True):
            continue
        quote = DAILY_QUOTES[lang]
        msg = format_quote_with_ad(quote, lang)
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.warning("Failed to send daily quote to %s: %s", uid, e)


# ============================================================
#  MAIN
# ============================================================

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Günlük job (10:00 TR)
    job_queue = application.job_queue
    job_queue.run_daily(
        daily_job,
        time=time(hour=DAILY_QUOTE_HOUR, minute=0, tzinfo=TZ_IST),
        name="daily_quote_job",
    )

    logger.info("QuoteMastersBot is starting…")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
