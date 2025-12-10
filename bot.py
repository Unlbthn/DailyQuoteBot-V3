import os
import logging
import random
import json
from datetime import datetime, time

import pytz
import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
)
from telegram.ext import (
    Updater,
    CallbackContext,
    CommandHandler,
    CallbackQueryHandler,
    PicklePersistence,
)

# -------------------------------------------------
#  CONFIG
# -------------------------------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable set edilmemiş. "
        "Örn: export BOT_TOKEN='123456:ABC-DEF'"
    )

# AdsGram
ADSGRAM_URL = "https://api.adsgram.ai/advbot"
ADSGRAM_PLATFORM_ID = 16417           # PlatformID (ekranda gördüğün 16417)
ADSGRAM_TIMEOUT = 3

# Zaman dilimi – günlük bildirimler için
TZ_ISTANBUL = pytz.timezone("Europe/Istanbul")

# Günlük söz durumu dosyası (her gün 1 söz, herkes için aynı)
DAILY_STATE_FILE = "daily_state.json"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# -------------------------------------------------
#  METİNLER
# -------------------------------------------------

TEXTS = {
    "tr": {
        "welcome": (
            "✨ Quote Masters'a hoş geldin!\n\n"
            "Konuya göre anlamlı sözler keşfedebilir, günlük bildirim alabilirsin."
        ),
        "ask_language": "Lütfen bir dil seç:",
        "ask_topic": "Bir konu seç:",
        "daily_quote_title": "📅 Günün sözü",
        "quote_footer": "Günün sözünü beğendiysen bize destek olmak için bir arkadaşınla paylaş. 💜",
        "menu_title": "Menü:",
        "settings_title": "⚙️ Ayarlar",
        "settings_language": "Dil",
        "settings_notifications": "Bildirimler",
        "notifications_on": "Açık",
        "notifications_off": "Kapalı",
        "notifications_enabled": "🔔 Günlük bildirimler açıldı (her gün 10:00 TR).",
        "notifications_disabled": "🔕 Günlük bildirimler kapatıldı.",
        "share_text": (
            "“{quote}”\n\n"
            "Türkçe & İngilizce anlamlı sözler için Quote Masters botunu dene:\n"
            "https://t.me/QuoteMastersBot"
        ),
        "topic_button_daily": "📅 Günün Sözü",
        "topic_button_change_topic": "🔄 Konuyu değiştir",
        "topic_button_new_quote": "🔁 Sözü değiştir",
        "topic_button_settings": "⚙️ Ayarlar",
        "share_whatsapp": "📤 WhatsApp",
        "share_telegram": "📨 Telegram",
        "language_tr": "🇹🇷 Türkçe",
        "language_en": "🇬🇧 English",
        "notifications_menu_on": "🔔 Bildirimler: Açık",
        "notifications_menu_off": "🔕 Bildirimler: Kapalı",
    },
    "en": {
        "welcome": (
            "✨ Welcome to Quote Masters!\n\n"
            "Discover meaningful quotes by topic and get a quote of the day."
        ),
        "ask_language": "Please choose a language:",
        "ask_topic": "Choose a topic:",
        "daily_quote_title": "📅 Quote of the day",
        "quote_footer": "If you like the quote, share it with a friend to support us. 💜",
        "menu_title": "Menu:",
        "settings_title": "⚙️ Settings",
        "settings_language": "Language",
        "settings_notifications": "Notifications",
        "notifications_on": "On",
        "notifications_off": "Off",
        "notifications_enabled": "🔔 Daily notifications enabled (10:00 Istanbul time).",
        "notifications_disabled": "🔕 Daily notifications disabled.",
        "share_text": (
            "“{quote}”\n\n"
            "Get daily motivational quotes with Quote Masters bot:\n"
            "https://t.me/QuoteMastersBot"
        ),
        "topic_button_daily": "📅 Quote of the Day",
        "topic_button_change_topic": "🔄 Change Topic",
        "topic_button_new_quote": "🔁 New Quote",
        "topic_button_settings": "⚙️ Settings",
        "share_whatsapp": "📤 WhatsApp",
        "share_telegram": "📨 Telegram",
        "language_tr": "🇹🇷 Turkish",
        "language_en": "🇬🇧 English",
        "notifications_menu_on": "🔔 Notifications: On",
        "notifications_menu_off": "🔕 Notifications: Off",
    },
}

# Burada sadece örnek birkaç söz var. Sen elindeki uzun listeleri
# aynen bu formata ekleyebilirsin.
# key: (dil, konu_kodu)
QUOTES = {
    ("tr", "motivation"): [
        {"text": "Başladığın işi bitirene kadar pes etme.", "author": None},
        {"text": "Zorluklar, seni güçlendirmek için var.", "author": None},
    ],
    ("en", "motivation"): [
        {"text": "Don’t stop when you’re tired. Stop when you’re done.", "author": None},
        {"text": "Great things never come from comfort zones.", "author": None},
    ],
    ("tr", "sport"): [
        {"text": "Kelebek gibi uçar, arı gibi sokarım.", "author": "Muhammed Ali"},
        {"text": "Zafer, hazırlanmış olanlarındır.", "author": "Herodot"},
    ],
    ("en", "sport"): [
        {"text": "I float like a butterfly, I sting like a bee.", "author": "Muhammad Ali"},
        {"text": "Success is no accident.", "author": "Pelé"},
    ],
}

TOPICS = [
    ("motivation", {"tr": "Motivasyon", "en": "Motivation"}),
    ("success", {"tr": "Başarı", "en": "Success"}),
    ("selfcare", {"tr": "Kendine iyi bak", "en": "Self-care"}),
    ("discipline", {"tr": "Disiplin", "en": "Discipline"}),
    ("resilience", {"tr": "Dayanıklılık", "en": "Resilience"}),
    ("career", {"tr": "İş & Kariyer", "en": "Career"}),
    ("love", {"tr": "Aşk", "en": "Love"}),
    ("life", {"tr": "Hayat", "en": "Life"}),
    ("sport", {"tr": "Spor", "en": "Sport"}),
    ("friendship", {"tr": "Dostluk", "en": "Friendship"}),
    ("creativity", {"tr": "Yaratıcılık", "en": "Creativity"}),
    ("gratitude", {"tr": "Şükran", "en": "Gratitude"}),
]

DEFAULT_LANG = "tr"
SUPPORTED_LANGS = ("tr", "en")

# -------------------------------------------------
#  PERSISTENCE YARDIMCI FONKSİYONLARI
# -------------------------------------------------


def get_user_settings(context: CallbackContext, user_id: int) -> dict:
    """Kullanıcı ayarlarını bot_data içinde sakla."""
    all_settings = context.bot_data.setdefault("user_settings", {})
    if user_id not in all_settings:
        all_settings[user_id] = {
            "lang": DEFAULT_LANG,
            "topic": "motivation",
            "notifications": True,
        }
    return all_settings[user_id]


def save_daily_state(state: dict) -> None:
    try:
        with open(DAILY_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception as e:
        logger.warning("Daily state write error: %s", e)


def load_daily_state() -> dict:
    try:
        with open(DAILY_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_or_create_daily_quote(bot_data: dict) -> dict:
    """Her gün için tek bir 'günün sözü' belirle (global)."""
    today = datetime.now(TZ_ISTANBUL).strftime("%Y-%m-%d")
    state = bot_data.setdefault("daily_state", {})

    if state.get("date") == today and "quote" in state:
        return state["quote"]

    # Tüm QUOTES içinden rastgele bir (lang, topic, quote) seç
    all_keys = list(QUOTES.keys())
    if not all_keys:
        return {"lang": DEFAULT_LANG, "topic": "motivation", "text": "…", "author": None}

    lang_topic = random.choice(all_keys)
    quotes = QUOTES[lang_topic]
    q = random.choice(quotes)

    daily = {
        "lang": lang_topic[0],
        "topic": lang_topic[1],
        "text": q["text"],
        "author": q.get("author"),
    }
    state["date"] = today
    state["quote"] = daily
    bot_data["daily_state"] = state
    save_daily_state({"date": today, "quote": daily})
    return daily


# -------------------------------------------------
#  INLINE KEYBOARD YARDIMCI FONKSİYONLARI
# -------------------------------------------------


def build_language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(TEXTS["tr"]["language_tr"], callback_data="lang:tr"),
            InlineKeyboardButton(TEXTS["en"]["language_en"], callback_data="lang:en"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_topics_keyboard(lang: str) -> InlineKeyboardMarkup:
    """12 konu – 6 satır 2 sütun."""
    buttons = []
    row = []
    for code, names in TOPICS:
        label = names.get(lang, names["en"])
        row.append(InlineKeyboardButton(label, callback_data=f"topic:{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def build_main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    keyboard = [
        [
            InlineKeyboardButton(t["topic_button_daily"], callback_data="action:daily"),
            InlineKeyboardButton(t["share_whatsapp"], callback_data="share:whatsapp"),
        ],
        [
            InlineKeyboardButton(t["share_telegram"], callback_data="share:telegram"),
            InlineKeyboardButton(t["topic_button_new_quote"], callback_data="action:new"),
        ],
        [
            InlineKeyboardButton(t["topic_button_change_topic"], callback_data="action:change_topic"),
            InlineKeyboardButton(t["topic_button_settings"], callback_data="action:settings"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_settings_keyboard(lang: str, notifications: bool) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    notif_label = (
        t["notifications_menu_on"] if notifications else t["notifications_menu_off"]
    )
    keyboard = [
        [
            InlineKeyboardButton(t["language_tr"], callback_data="settings:lang:tr"),
            InlineKeyboardButton(t["language_en"], callback_data="settings:lang:en"),
        ],
        [
            InlineKeyboardButton(
                notif_label, callback_data="settings:toggle_notifications"
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# -------------------------------------------------
#  AdsGram ENTEGRASYONU
# -------------------------------------------------


def fetch_adsgram_ad(user_id: int) -> dict | None:
    """
    AdsGram'dan reklam çek. Dil her zaman 'en' gönderiliyor,
    böylece Türkçe kullanıcılar için de İngilizce reklam alınabiliyor.
    """
    try:
        resp = requests.post(
            ADSGRAM_URL,
            data={
                "platform": ADSGRAM_PLATFORM_ID,
                "telegram_user_id": user_id,
                "language": "en",  # İSTENEN: TR kullanıcıya bile EN reklam
            },
            timeout=ADSGRAM_TIMEOUT,
        )
        body = resp.text.strip()
        logger.info("AdsGram status=%s body=%s", resp.status_code, body[:200])

        # AdsGram boş / metinsel cevap veriyorsa (No available advertisement…)
        if not body or body.lower().startswith("no available advertisement"):
            return None

        data = resp.json()
        return data
    except Exception as e:
        logger.warning("AdsGram error: %s", e)
        return None


def render_adsgram_message(data: dict) -> tuple[str, InlineKeyboardMarkup | None]:
    """
    AdsGram JSON'unu olabildiğince esnek şekilde çöz.
    Hangi alanların geleceğini %100 bilemediğimiz için birkaç opsiyon deniyoruz.
    """
    text_html = (
        data.get("text_html")
        or data.get("text")
        or data.get("title")
        or "Sponsored"
    )

    button_name = data.get("button_name") or data.get("button_text")
    click_url = data.get("click_url") or data.get("url")
    reward_button_name = data.get("button_reward_name")
    reward_url = data.get("reward_url")

    keyboard_rows = []
    if button_name and click_url:
        keyboard_rows.append(
            [InlineKeyboardButton(button_name, url=click_url)]
        )
    if reward_button_name and reward_url:
        keyboard_rows.append(
            [InlineKeyboardButton(reward_button_name, url=reward_url)]
        )

    reply_markup = InlineKeyboardMarkup(keyboard_rows) if keyboard_rows else None
    return text_html, reply_markup


def send_adsgram_after_quote(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    ad_data = fetch_adsgram_ad(user.id)
    if not ad_data:
        return

    text_html, reply_markup = render_adsgram_message(ad_data)
    try:
        chat.send_message(
            text=text_html,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False,
        )
    except Exception as e:
        logger.warning("AdsGram send error: %s", e)


# -------------------------------------------------
#  SÖZ SEÇİMİ
# -------------------------------------------------


def pick_random_quote(lang: str, topic: str) -> dict:
    key = (lang, topic)
    if key not in QUOTES or not QUOTES[key]:
        # Dil + konu yoksa İngilizce motivasyon düş
        fallback_key = ("en", "motivation")
        quote = random.choice(QUOTES.get(fallback_key, [{"text": "...", "author": None}]))
        return quote

    return random.choice(QUOTES[key])


def format_quote(lang: str, quote: dict) -> str:
    text = quote["text"]
    author = quote.get("author")
    if author:
        return f"“{text}”\n\n— {author}"
    return f"“{text}”"


# -------------------------------------------------
#  HANDLER’LAR
# -------------------------------------------------


def send_quote_with_menu(
    update: Update,
    context: CallbackContext,
    lang: str,
    quote: dict,
    show_header: bool = False,
    is_daily: bool = False,
) -> None:
    chat = update.effective_chat
    if not chat:
        return

    t = TEXTS[lang]
    header = t["daily_quote_title"] if show_header else None
    body = format_quote(lang, quote)

    parts = []
    if header:
        parts.append(header)
        parts.append("")  # boş satır
    parts.append(body)
    parts.append("")
    parts.append(t["quote_footer"])

    text = "\n".join(parts)

    chat.send_message(
        text=text,
        reply_markup=build_main_menu_keyboard(lang),
    )

    # Her sözden sonra AdsGram reklam dene
    send_adsgram_after_quote(update, context)


def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    # Kullanıcıyı kaydet
    settings = get_user_settings(context, user.id)

    # Telegram dil kodundan varsayılan belirle (sadece ilk girişte)
    if "initialized" not in settings:
        if user.language_code and user.language_code.startswith("en"):
            settings["lang"] = "en"
        else:
            settings["lang"] = "tr"
        settings["initialized"] = True

    lang = settings["lang"]
    t = TEXTS[lang]

    chat.send_message(
        text=t["welcome"],
    )
    chat.send_message(
        text=t["ask_language"],
        reply_markup=build_language_keyboard(),
    )

    # Kullanıcı ID'sini listeye ekle (günlük broadcast için)
    user_ids = context.bot_data.setdefault("user_ids", set())
    user_ids.add(user.id)


def handle_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    if not query:
        return

    user = query.from_user
    data = query.data
    settings = get_user_settings(context, user.id)
    lang = settings["lang"]
    t = TEXTS[lang]

    # her callback'te notification cevap penceresini kapat
    query.answer()

    if data.startswith("lang:"):
        new_lang = data.split(":")[1]
        if new_lang in SUPPORTED_LANGS:
            settings["lang"] = new_lang
            lang = new_lang
            t = TEXTS[lang]

        query.message.reply_text(
            text=t["ask_topic"],
            reply_markup=build_topics_keyboard(lang),
        )
        return

    if data.startswith("topic:"):
        topic = data.split(":")[1]
        settings["topic"] = topic
        quote = pick_random_quote(lang, topic)
        send_quote_with_menu(update, context, lang, quote, show_header=False)
        return

    if data.startswith("action:"):
        action = data.split(":")[1]
        if action == "daily":
            # global günlük söz
            daily = get_or_create_daily_quote(context.bot_data)
            # Kullanıcının diliyle formatlıyoruz ama söz dilini değiştirmiyoruz
            quote_for_user = {
                "text": daily["text"],
                "author": daily.get("author"),
            }
            send_quote_with_menu(
                update, context, lang, quote_for_user, show_header=True, is_daily=True
            )
            return

        if action == "new":
            topic = settings.get("topic", "motivation")
            quote = pick_random_quote(lang, topic)
            send_quote_with_menu(update, context, lang, quote, show_header=False)
            return

        if action == "change_topic":
            query.message.reply_text(
                text=t["ask_topic"],
                reply_markup=build_topics_keyboard(lang),
            )
            return

        if action == "settings":
            notif = settings.get("notifications", True)
            query.message.reply_text(
                text=t["settings_title"],
                reply_markup=build_settings_keyboard(lang, notif),
            )
            return

    if data.startswith("settings:"):
        parts = data.split(":")
        if len(parts) == 3 and parts[1] == "lang":
            new_lang = parts[2]
            if new_lang in SUPPORTED_LANGS:
                settings["lang"] = new_lang
                lang = new_lang
                t = TEXTS[lang]
            notif = settings.get("notifications", True)
            query.message.reply_text(
                text=t["settings_title"],
                reply_markup=build_settings_keyboard(lang, notif),
            )
            return

        if data == "settings:toggle_notifications":
            current = settings.get("notifications", True)
            settings["notifications"] = not current
            notif = settings["notifications"]
            msg = (
                t["notifications_enabled"]
                if notif
                else t["notifications_disabled"]
            )
            query.message.reply_text(
                text=msg,
                reply_markup=build_settings_keyboard(lang, notif),
            )
            return

    if data.startswith("share:"):
        share_type = data.split(":")[1]
        # Mesajdaki son sözü bulmak için: callback mesajını kullanıyoruz
        # (en son gönderdiğimiz söz mesajı bu butonlarla birlikte geliyor)
        quote_text = query.message.text
        # Alıntıyı temizce çekmek zor olabilir; en temiz yöntem:
        # Kullanıcı yeni söz istediğinde paylaşım yaparsa, alıntı gövdedeki ilk tırnaklı kısım.
        # Basit yaklaşım: tüm mesajı quote kabul et.
        share_msg = t["share_text"].format(quote=quote_text.strip())

        if share_type == "whatsapp":
            # WhatsApp paylaşımı için URL
            from urllib.parse import quote_plus

            url = "https://wa.me/?text=" + quote_plus(share_msg)
            query.message.reply_text(url)
        elif share_type == "telegram":
            query.message.reply_text(share_msg)

        return


# -------------------------------------------------
#  GÜNLÜK BİLDİRİM JOB'U
# -------------------------------------------------


def daily_broadcast_job(context: CallbackContext) -> None:
    bot = context.bot
    bot_data = context.bot_data

    daily = get_or_create_daily_quote(bot_data)
    user_ids = bot_data.get("user_ids", set())
    all_settings = bot_data.get("user_settings", {})

    for user_id in list(user_ids):
        settings = all_settings.get(user_id) or {
            "lang": DEFAULT_LANG,
            "notifications": True,
        }
        if not settings.get("notifications", True):
            continue

        lang = settings.get("lang", DEFAULT_LANG)
        t = TEXTS[lang]
        quote_for_user = {
            "text": daily["text"],
            "author": daily.get("author"),
        }

        try:
            text = f"{t['daily_quote_title']}\n\n{format_quote(lang, quote_for_user)}"
            bot.send_message(chat_id=user_id, text=text)
        except Exception as e:
            logger.warning("Daily send error for %s: %s", user_id, e)


# -------------------------------------------------
#  MAIN
# -------------------------------------------------


def main() -> None:
    persistence = PicklePersistence("quote_master_persistence.pkl")
    updater = Updater(BOT_TOKEN, use_context=True, persistence=persistence)

    dp = updater.dispatcher
    jq = updater.job_queue

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(handle_callback))

    # Günlük job – her gün 10:00 TR
    run_time = time(hour=10, minute=0, tzinfo=TZ_ISTANBUL)
    jq.run_daily(daily_broadcast_job, time=run_time)

    logger.info("Quote Masters bot is starting...")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
