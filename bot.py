import logging
import os
import random
from datetime import date, time
from io import BytesIO
from typing import Optional
from zoneinfo import ZoneInfo
import urllib.parse

import requests
from PIL import Image, ImageDraw, ImageFont

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.constants import ParseMode
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

BOT_TOKEN = os.getenv("BOT_TOKEN")          # Render / local env
WEBAPP_URL = os.getenv("WEBAPP_URL")       # Varsa WebApp için (opsiyonel)

ADSGRAM_BLOCK_ID = 16417                   # Senin AdsGram block ID

MAX_ADS_PER_DAY = 10                       # Kullanıcı başı günlük reklam sınırı
DEFAULT_TOPIC = "motivation"

DAILY_QUOTE_HOUR = 9                       # TR saatiyle 09:00'da günün sözü

# ---------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# SÖZ HAVUZU (TOPIC -> {tr: [], en: []})
# ---------------------------------------------------------------------

QUOTES = {
    "motivation": {
        "tr": [
            "Bugün attığın küçük bir adım, yarınki büyük değişimin başlangıcı olabilir.",
            "Yorulduğunda durma, sadece nefeslen; sonra yola devam et.",
            "Zor günler biter, kazandığın güç seninle kalır.",
            "Kendine inanmak, başarının yarısından fazlasıdır.",
            "Kusursuz olmak zorunda değilsin, sadece vazgeçmemek yeter.",
            "Bir şey seni korkutuyorsa, büyük ihtimalle büyüme alanındır.",
            "Dünün pişmanlıklarıyla değil, bugünün imkanlarıyla ilgilen.",
            "Kendin için çalıştığın her gün, gelecekteki sana bir teşekkür borcudur.",
            "Hedeflerin seni biraz korkutuyorsa, doğru yoldasın demektir.",
            "Bugün başlamak için en iyi gün."
        ],
        "en": [
            "A small step today can be the beginning of a big change tomorrow.",
            "When you feel tired, don’t quit, just pause and breathe.",
            "Hard days end, but the strength you gain stays with you.",
            "Believing in yourself is more than half of success.",
            "You don’t need to be perfect, you just need to keep going.",
            "If something scares you, it’s probably where you grow.",
            "Care less about yesterday’s regrets, more about today’s possibilities.",
            "Every day you work for yourself, your future self owes you a thank you.",
            "If your goals scare you a little, you’re on the right track.",
            "Today is the best day to start."
        ],
    },
    "love": {
        "tr": [
            "Sevgi, söylemekten çok göstermeyi bilenlerin dilidir.",
            "Doğru insan, seni değiştirmeye çalışmaz; olduğun halinle yanındadır.",
            "Kalpten çıkan her şey, bir gün mutlaka sahibini bulur.",
            "Bazı insanlar, hayatımıza iyi ki ve iyi ki daha erken girseydi dedirtir.",
            "Sevmek; aynı gökyüzüne bakarken aynı duayı fısıldamaktır.",
            "İyi bir kalbin varsa, dünyanın en güzel zenginliğine sahipsin demektir.",
            "Değer verdiğini göstermediğin sevgi, zamanla küser.",
            "Yanında huzur bulduğun insan, en büyük şansındır.",
            "Gerçek sevgi, en zor zamanda bile elini bırakmayandır.",
            "Kalbini yormayan her şey, sana iyi gelir."
        ],
        "en": [
            "Love is the language of those who know how to show more than they say.",
            "The right person doesn’t try to change you; they stand by you as you are.",
            "Everything that comes from the heart eventually finds its place.",
            "Some people make you say ‘I’m glad you came’ and ‘I wish you came earlier’.",
            "To love is to whisper the same wish under the same sky.",
            "If you have a kind heart, you already own the most beautiful wealth.",
            "Love that is not shown slowly fades away.",
            "The one who brings you peace is your greatest luck.",
            "Real love doesn’t let go of your hand in the hardest moments.",
            "Anything that doesn’t exhaust your heart is good for you."
        ],
    },
    "success": {
        "tr": [
            "Başarı, kimsenin görmediği saatlerde verilen emeklerin özetidir.",
            "Disiplin, motivasyonun olmadığı günlerde seni yola devam ettiren güçtür.",
            "Hatalar, yeterince cesur olanların öğretmenidir.",
            "Hayallerine yatırım yaptığın her gün, en iyi faizle sana geri döner.",
            "Başarılı insanlar bahane değil, çözüm arar.",
            "Her ‘olmadı’ dediğin anda, aslında bir şeyler öğrenmiş olursun.",
            "Bir hedefin yoksa, vardığın yerin anlamı olmaz.",
            "Planı olan, paniği yönetir; planı olmayan panikler.",
            "Başarı, aynı hatayı tekrar etmemeyi öğrenmektir.",
            "Bugün konfor alanından çıkmazsan, yarın hayal ettiğin hayata giremezsin."
        ],
        "en": [
            "Success is the summary of all the effort no one sees.",
            "Discipline is what keeps you moving when motivation is gone.",
            "Mistakes are teachers for those who are brave enough to try.",
            "Every day you invest in your dreams pays back with the best interest.",
            "Successful people search for solutions, not excuses.",
            "Every time you say ‘it didn’t work’, you still learn something.",
            "If you have no goal, the place you arrive loses its meaning.",
            "Those with a plan manage panic; those without a plan panic.",
            "Success is learning not to repeat the same mistake.",
            "If you never leave your comfort zone today, you can’t enter your dream life tomorrow."
        ],
    },
    "life": {
        "tr": [
            "Hayat, ertelediklerin değil; yaşadığın anların toplamıdır.",
            "Bazen hiçbir şey yolunda gitmez, ama sen yine de yolunda gitmek zorundasın.",
            "Zaman, geri alamadığın tek sermayendir; nereye harcadığına dikkat et.",
            "Kıyaslamak, mutluluğun en hızlı katilidir.",
            "Kabul etmek, değiştiremediğin şeylerle barışmanın ilk adımıdır.",
            "Bazı kapılar kapanır, çünkü artık o odada işin bitmiştir.",
            "Düşüncelerini değiştirdiğinde, hikâyen de değişmeye başlar.",
            "Her şey üstüne geliyorsa, belki de doğruldun demektir.",
            "Bazen en büyük cesaret, devam etmek değil; bırakabilmektir.",
            "Bugün, geri kalan hayatının ilk günü."
        ],
        "en": [
            "Life is not what you postpone, it’s what you actually live.",
            "Sometimes nothing goes right, but you still need to keep moving.",
            "Time is the only capital you can’t get back; spend it wisely.",
            "Comparison is the fastest killer of happiness.",
            "Acceptance is the first step to making peace with what you can’t change.",
            "Some doors close because your time in that room is over.",
            "When you change your thoughts, your story starts to change too.",
            "If everything feels like it’s coming at you, maybe you’ve finally stood up.",
            "Sometimes the biggest courage is not to continue, but to let go.",
            "Today is the first day of the rest of your life."
        ],
    },
    "selfcare": {
        "tr": [
            "Dinlenmek, pes etmek değildir; yeniden başlamak için güç toplamaktır.",
            "Hayır demek, bazen kendine evet demenin tek yoludur.",
            "Herkesi memnun etmeye çalışırken, en çok kendini kırarsın.",
            "Sınır koymak, sevgisiz olmak değil; kendine saygı duymaktır.",
            "Yavaşlamak, hayattan geri kalmak değil; hayatı daha iyi görmek demektir.",
            "Kendinle geçirdiğin zaman, en değerli randevundur.",
            "İyi hissetmek için bazen hiçbir şey yapmamak gerekir.",
            "Kendine şefkat göstermek, en güçlü iyileşme aracındır.",
            "İzin ver; bazı günler sadece ‘idare eder’ ol, bu da normal.",
            "Kendini dinlemezsen, bedenin ve ruhun bir gün seni susturur."
        ],
        "en": [
            "Resting is not giving up; it’s gathering strength to start again.",
            "Sometimes saying no is the only way to say yes to yourself.",
            "Trying to please everyone often breaks you the most.",
            "Setting boundaries is not a lack of love; it’s a sign of self-respect.",
            "Slowing down is not falling behind; it’s seeing life more clearly.",
            "Time spent with yourself is your most valuable appointment.",
            "Sometimes to feel better, you need to do nothing at all.",
            "Self-compassion is your strongest healing tool.",
            "Allow yourself to be ‘just okay’ on some days; that’s normal too.",
            "If you don’t listen to yourself, your body and soul will one day silence you."
        ],
    },
}

TOPIC_LABELS = {
    "tr": {
        "motivation": "Motivasyon",
        "love": "Aşk",
        "success": "Başarı",
        "life": "Hayat",
        "selfcare": "Kendine iyi bak",
    },
    "en": {
        "motivation": "Motivation",
        "love": "Love",
        "success": "Success",
        "life": "Life",
        "selfcare": "Self-care",
    },
}

# ---------------------------------------------------------------------
# METİN DİZİLERİ
# ---------------------------------------------------------------------

TEXTS = {
    "tr": {
        "welcome_lang": "Lütfen dil seç:\n\nPlease select your language:",
        "start": (
            "✨ DailyQuoteBot'a hoş geldin!\n\n"
            "Konulara göre anlamlı sözler keşfedebilirsin:\n"
            "• Motivasyon\n"
            "• Aşk\n"
            "• Başarı\n"
            "• Hayat\n"
            "• Kendine iyi bak\n\n"
            "Önce bir konu seç, sonra 'Yeni söz' ile devam et 👇"
        ),
        "help": (
            "📚 DailyQuoteBot yardım\n\n"
            "/start - Karşılama mesajı ve menü\n"
            "/quote - Mevcut konuya göre yeni söz\n\n"
            "Mesaj altındaki butonlardan:\n"
            "• Konu seç / değiştir\n"
            "• Yeni söz al\n"
            "• Favorilere ekle / Favorilerim\n"
            "• WhatsApp / Telegram paylaş\n"
            "• Ayarlar (dil + günün sözü bildirimi)\n"
        ),
        "quote_prefix": "Bugünün sözü:",
        "no_quote": "Şu an için gösterecek söz bulamadım.",
        "ad_error": "Şu anda reklam gösterilemiyor, lütfen daha sonra tekrar dene.",
        "fallback": "DailyQuoteBot'u kullanmak için aşağıdaki butonları kullanabilirsin 👇",
        "topic_changed": "Konu değiştirildi: {topic}. Şimdi yeni bir söz alabilirsin.",
        "fav_added": "Bu sözü favorilerine ekledim ⭐",
        "fav_empty": "Henüz favori söz eklemedin.",
        "fav_header": "📂 Favori sözlerin:",
        "settings_title": "⚙️ Ayarlar",
        "settings_daily_on": "Günün sözü bildirimi: Açık",
        "settings_daily_off": "Günün sözü bildirimi: Kapalı",
        "settings_lang": "Dil / Language:",
        "daily_quote_title": "📅 Günün sözü",
    },
    "en": {
        "welcome_lang": "Please select your language:\n\nLütfen dil seç:",
        "start": (
            "✨ Welcome to DailyQuoteBot!\n\n"
            "You can discover meaningful quotes by topics:\n"
            "• Motivation\n"
            "• Love\n"
            "• Success\n"
            "• Life\n"
            "• Self-care\n\n"
            "First choose a topic, then tap 'New quote' 👇"
        ),
        "help": (
            "📚 DailyQuoteBot help\n\n"
            "/start - Welcome message and menu\n"
            "/quote - New quote for your current topic\n\n"
            "From the buttons below you can:\n"
            "• Choose / change topic\n"
            "• Get new quote\n"
            "• Add to favorites / see favorites\n"
            "• Share via WhatsApp / Telegram\n"
            "• Open settings (language + daily quote notification)\n"
        ),
        "quote_prefix": "Today's quote:",
        "no_quote": "I don't have a quote to show right now.",
        "ad_error": "Ad is not available right now, please try again later.",
        "fallback": "You can use the buttons below to use DailyQuoteBot 👇",
        "topic_changed": "Topic changed to: {topic}. Now you can get a new quote.",
        "fav_added": "I added this quote to your favorites ⭐",
        "fav_empty": "You don't have any favorite quotes yet.",
        "fav_header": "📂 Your favorite quotes:",
        "settings_title": "⚙️ Settings",
        "settings_daily_on": "Daily quote notification: ON",
        "settings_daily_off": "Daily quote notification: OFF",
        "settings_lang": "Language / Dil:",
        "daily_quote_title": "📅 Daily quote",
    },
}

# ---------------------------------------------------------------------
# STATE
# ---------------------------------------------------------------------

USER_LANG = {}          # {user_id: 'tr' / 'en'}
USER_TOPIC = {}         # {user_id: topic_key}
USER_STATS = {}         # {user_id: {"day": date, "quotes": int, "ads": int}}
USER_FAVORITES = {}     # {user_id: [quote_str, ...]}
LAST_QUOTE = {}         # {user_id: last_quote_str}
DAILY_ENABLED = {}      # {user_id: bool}
KNOWN_USERS = set()     # {user_id}


# ---------------------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------------------

def get_lang(update: Update) -> str:
    user = update.effective_user
    user_id = user.id if user else 0
    if user_id in USER_LANG:
        return USER_LANG[user_id]
    # Telegram language_code'ya göre default
    code = (user.language_code or "").lower() if user else ""
    if code.startswith("tr"):
        return "tr"
    return "en"


def ensure_stats(user_id: int) -> dict:
    today = date.today()
    stats = USER_STATS.get(user_id)
    if not stats or stats.get("day") != today:
        stats = {"day": today, "quotes": 0, "ads": 0}
        USER_STATS[user_id] = stats
    return stats


def get_user_topic(user_id: int) -> str:
    topic = USER_TOPIC.get(user_id)
    if topic not in QUOTES:
        topic = DEFAULT_TOPIC
        USER_TOPIC[user_id] = topic
    return topic


def set_user_topic(user_id: int, topic: str):
    if topic in QUOTES:
        USER_TOPIC[user_id] = topic


def get_random_quote_for_user(user_id: int, lang: str) -> str:
    topic = get_user_topic(user_id)
    topic_data = QUOTES.get(topic) or QUOTES[DEFAULT_TOPIC]
    lang_list = topic_data.get(lang) or topic_data.get("en") or []
    if not lang_list:
        return ""
    return random.choice(lang_list)


def render_quote_image(quote: str, lang: str) -> BytesIO:
    width, height = 800, 800
    bg_color = (0, 0, 0)
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    center = (width // 2, height // 2 - 80)
    radius = 260
    gold = (212, 175, 55)
    draw.ellipse(
        [
            (center[0] - radius, center[1] - radius),
            (center[0] + radius, center[1] + radius),
        ],
        outline=gold,
        width=4,
    )

    mark_text = "❝"
    try:
        font_mark = ImageFont.truetype("arial.ttf", 80)
    except Exception:
        font_mark = ImageFont.load_default()
    draw.text((width // 2 - 25, 80), mark_text, fill=gold, font=font_mark)

    try:
        font_quote = ImageFont.truetype("arial.ttf", 32)
    except Exception:
        font_quote = ImageFont.load_default()

    max_width = width - 160
    words = quote.split()
    lines = []
    current = ""
    for w in words:
        test = (current + " " + w).strip()
        w_width, _ = draw.textsize(test, font=font_quote)
        if w_width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)

    total_text_height = len(lines) * 40
    start_y = center[1] - total_text_height // 2

    for i, line in enumerate(lines):
        w_width, _ = draw.textsize(line, font=font_quote)
        x = (width - w_width) // 2
        y = start_y + i * 40
        draw.text((x, y), line, fill=(229, 229, 229), font=font_quote)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def build_main_keyboard(lang: str, user_id: int, quote: Optional[str] = None) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    topic_labels = TOPIC_LABELS[lang]
    current_topic = get_user_topic(user_id)

    # Konu butonları
    topic_buttons = []
    for key in ["motivation", "love", "success", "life", "selfcare"]:
        label = topic_labels.get(key, key)
        if key == current_topic:
            label = f"● {label}"
        else:
            label = f"○ {label}"
        topic_buttons.append(
            InlineKeyboardButton(label, callback_data=f"topic:{key}")
        )

    rows = [
        [
            InlineKeyboardButton("🔁 " + ( "Yeni söz" if lang == "tr" else "New quote" ),
                                 callback_data="new_quote"),
            InlineKeyboardButton("🎁 " + ( "Ekstra söz (reklam)" if lang == "tr" else "Extra quote (ad)" ),
                                 callback_data="extra_quote"),
        ],
        topic_buttons[:3],
        topic_buttons[3:],
        [
            InlineKeyboardButton("⭐ " + ("Favorilere ekle" if lang == "tr" else "Add to favorites"),
                                 callback_data="fav_add"),
            InlineKeyboardButton("📂 " + ("Favorilerim" if lang == "tr" else "My favorites"),
                                 callback_data="fav_list"),
        ],
    ]

    # Paylaş butonları (quote varsa)
    if quote:
        text = quote
        encoded = urllib.parse.quote_plus(text)
        wa_url = f"https://wa.me/?text={encoded}"
        tg_url = f"https://t.me/share/url?url=&text={encoded}"
        rows.append(
            [
                InlineKeyboardButton("📤 WhatsApp", url=wa_url),
                InlineKeyboardButton("📤 Telegram", url=tg_url),
            ]
        )

    # Ayarlar + WebApp
    settings_btn = InlineKeyboardButton("⚙️ " + ("Ayarlar" if lang == "tr" else "Settings"),
                                        callback_data="settings")
    if WEBAPP_URL:
        rows.append(
            [
                settings_btn,
                InlineKeyboardButton("🌐 Web App", web_app=WebAppInfo(url=WEBAPP_URL)),
            ]
        )
    else:
        rows.append([settings_btn])

    return InlineKeyboardMarkup(rows)


async def send_quote_with_ui(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    extra: bool = False,
) -> None:
    user = update.effective_user
    user_id = user.id if user else 0
    lang = get_lang(update)
    KNOWN_USERS.add(user_id)

    stats = ensure_stats(user_id)
    quote = get_random_quote_for_user(user_id, lang)

    if not quote:
        t = TEXTS[lang]
        kb = build_main_keyboard(lang, user_id, quote=None)
        if update.message:
            await update.message.reply_text(t["no_quote"], reply_markup=kb)
        elif update.callback_query:
            await update.callback_query.message.reply_text(t["no_quote"], reply_markup=kb)
        else:
            chat_id = update.effective_chat.id
            await context.bot.send_message(chat_id=chat_id, text=t["no_quote"], reply_markup=kb)
        return

    LAST_QUOTE[user_id] = quote
    img_bytes = render_quote_image(quote, lang)
    kb = build_main_keyboard(lang, user_id, quote=quote)

    if update.message:
        await update.message.reply_photo(photo=img_bytes, reply_markup=kb)
    elif update.callback_query:
        await update.callback_query.message.reply_photo(photo=img_bytes, reply_markup=kb)
    else:
        chat_id = update.effective_chat.id
        await context.bot.send_photo(chat_id=chat_id, photo=img_bytes, reply_markup=kb)

    stats["quotes"] += 1

    # Her sözden sonra, günlük limit içinde reklam
    if stats["ads"] < MAX_ADS_PER_DAY:
        await send_adsgram_ad(update, context, lang, user_id)


# ---------------------------------------------------------------------
# ADSGRAM
# ---------------------------------------------------------------------

async def send_adsgram_ad(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lang: str,
    user_id: int,
) -> None:
    stats = ensure_stats(user_id)
    if stats["ads"] >= MAX_ADS_PER_DAY:
        return

    params = {
        "tgid": user_id,
        "blockid": ADSGRAM_BLOCK_ID,
        "language": "tr" if lang == "tr" else "en",
    }

    try:
        resp = requests.get("https://api.adsgram.ai/advbot", params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"AdsGram error: {e}")
        t = TEXTS[lang]
        if update.callback_query:
            await update.callback_query.message.reply_text(t["ad_error"])
        elif update.message:
            await update.message.reply_text(t["ad_error"])
        return

    text_html = data.get("text_html")
    click_url = data.get("click_url")
    button_name = data.get("button_name")
    image_url = data.get("image_url")
    button_reward_name = data.get("button_reward_name")
    reward_url = data.get("reward_url")

    buttons = []
    if button_name and click_url:
        buttons.append([InlineKeyboardButton(button_name, url=click_url)])
    if button_reward_name and reward_url:
        buttons.append([InlineKeyboardButton(button_reward_name, url=reward_url)])

    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

    if image_url:
        if update.callback_query:
            await update.callback_query.message.reply_photo(
                photo=image_url,
                caption=text_html,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=True,
            )
        elif update.message:
            await update.message.reply_photo(
                photo=image_url,
                caption=text_html,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=True,
            )
        else:
            chat_id = update.effective_chat.id
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=image_url,
                caption=text_html,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=True,
            )
    else:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text_html,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=True,
            )
        elif update.message:
            await update.message.reply_text(
                text_html,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=True,
            )
        else:
            chat_id = update.effective_chat.id
            await context.bot.send_message(
                chat_id=chat_id,
                text=text_html,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=True,
            )

    stats["ads"] += 1


# ---------------------------------------------------------------------
# DİL SEÇİMİ / AYARLAR
# ---------------------------------------------------------------------

async def send_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Dil seçimi ekranı
    user = update.effective_user
    user_id = user.id if user else 0
    KNOWN_USERS.add(user_id)

    # Telegram diline göre metin
    temp_lang = get_lang(update)
    t = TEXTS[temp_lang]

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇹🇷 Türkçe", callback_data="set_lang:tr"),
                InlineKeyboardButton("🇬🇧 English", callback_data="set_lang:en"),
            ]
        ]
    )

    if update.message:
        await update.message.reply_text(t["welcome_lang"], reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.message.reply_text(t["welcome_lang"], reply_markup=keyboard)


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id if user else 0
    lang = USER_LANG.get(user_id, get_lang(update))
    t = TEXTS[lang]

    DAILY_ENABLED.setdefault(user_id, True)

    daily_text = t["settings_daily_on"] if DAILY_ENABLED[user_id] else t["settings_daily_off"]
    lang_label = "Türkçe" if lang == "tr" else "English"

    text = f"{t['settings_title']}\n\n{daily_text}\n{t['settings_lang']} {lang_label}"

    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔔 " + ("Bildirim Aç/Kapat" if lang == "tr" else "Toggle daily quote"),
                    callback_data="toggle_daily",
                )
            ],
            [
                InlineKeyboardButton("🇹🇷 Türkçe", callback_data="set_lang:tr"),
                InlineKeyboardButton("🇬🇧 English", callback_data="set_lang:en"),
            ],
        ]
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=kb)
    elif update.message:
        await update.message.reply_text(text, reply_markup=kb)


# ---------------------------------------------------------------------
# HANDLER'LAR
# ---------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id if user else 0
    KNOWN_USERS.add(user_id)
    DAILY_ENABLED.setdefault(user_id, True)

    if user_id not in USER_LANG:
        await send_language_selection(update, context)
        return

    lang = USER_LANG[user_id]
    t = TEXTS[lang]
    # Varsayılan konu
    get_user_topic(user_id)
    kb = build_main_keyboard(lang, user_id, quote=None)

    if update.message:
        await update.message.reply_text(t["start"], reply_markup=kb)
    else:
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text=t["start"], reply_markup=kb)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id if user else 0
    KNOWN_USERS.add(user_id)

    if user_id not in USER_LANG:
        await send_language_selection(update, context)
        return

    lang = USER_LANG[user_id]
    t = TEXTS[lang]
    kb = build_main_keyboard(lang, user_id, quote=LAST_QUOTE.get(user_id))

    await update.message.reply_text(t["help"], reply_markup=kb)


async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id if user else 0
    KNOWN_USERS.add(user_id)

    if user_id not in USER_LANG:
        await send_language_selection(update, context)
        return

    await send_quote_with_ui(update, context, extra=False)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data
    user = update.effective_user
    user_id = user.id if user else 0
    KNOWN_USERS.add(user_id)

    # Dil seçimi
    if data.startswith("set_lang:"):
        lang_code = data.split(":", 1)[1]
        USER_LANG[user_id] = "tr" if lang_code == "tr" else "en"
        # varsayılan ayarlar
        DAILY_ENABLED.setdefault(user_id, True)
        get_user_topic(user_id)
        lang = USER_LANG[user_id]
        t = TEXTS[lang]
        kb = build_main_keyboard(lang, user_id, quote=None)
        await query.answer()
        await query.message.reply_text(t["start"], reply_markup=kb)
        return

    # Kullanıcının dili yoksa önce dil iste
    if user_id not in USER_LANG:
        await send_language_selection(update, context)
        await query.answer()
        return

    lang = USER_LANG[user_id]
    t = TEXTS[lang]

    if data == "new_quote":
        await query.answer()
        await send_quote_with_ui(update, context, extra=False)

    elif data == "extra_quote":
        await query.answer()
        await send_quote_with_ui(update, context, extra=True)

    elif data.startswith("topic:"):
        topic_key = data.split(":", 1)[1]
        set_user_topic(user_id, topic_key)
        label = TOPIC_LABELS[lang].get(topic_key, topic_key)
        msg = t["topic_changed"].format(topic=label)
        kb = build_main_keyboard(lang, user_id, quote=LAST_QUOTE.get(user_id))
        await query.answer()
        await query.message.reply_text(msg, reply_markup=kb)

    elif data == "fav_add":
        await query.answer()
        quote = LAST_QUOTE.get(user_id)
        if quote:
            favs = USER_FAVORITES.setdefault(user_id, [])
            if quote not in favs:
                favs.append(quote)
            kb = build_main_keyboard(lang, user_id, quote=quote)
            await query.message.reply_text(t["fav_added"], reply_markup=kb)

    elif data == "fav_list":
        await query.answer()
        favs = USER_FAVORITES.get(user_id, [])
        if not favs:
            kb = build_main_keyboard(lang, user_id, quote=LAST_QUOTE.get(user_id))
            await query.message.reply_text(t["fav_empty"], reply_markup=kb)
        else:
            text = t["fav_header"] + "\n\n" + "\n\n".join(f"• {q}" for q in favs[:20])
            kb = build_main_keyboard(lang, user_id, quote=LAST_QUOTE.get(user_id))
            await query.message.reply_text(text, reply_markup=kb)

    elif data == "settings":
        await query.answer()
        await show_settings(update, context)

    elif data == "toggle_daily":
        DAILY_ENABLED[user_id] = not DAILY_ENABLED.get(user_id, True)
        await query.answer()
        await show_settings(update, context)

    else:
        await query.answer()


async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id if user else 0
    KNOWN_USERS.add(user_id)

    if user_id not in USER_LANG:
        await send_language_selection(update, context)
        return

    lang = USER_LANG[user_id]
    t = TEXTS[lang]
    kb = build_main_keyboard(lang, user_id, quote=LAST_QUOTE.get(user_id))
    await update.message.reply_text(t["fallback"], reply_markup=kb)


# ---------------------------------------------------------------------
# GÜNLÜK GÜNÜN SÖZÜ JOB
# ---------------------------------------------------------------------

async def daily_quote_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    for user_id in list(KNOWN_USERS):
        if not DAILY_ENABLED.get(user_id, True):
            continue

        lang = USER_LANG.get(user_id, "tr")
        t = TEXTS[lang]
        # Kullanıcının konusu yoksa default
        topic = get_user_topic(user_id)
        quote = get_random_quote_for_user(user_id, lang)
        if not quote:
            continue

        text = f"{t['daily_quote_title']}\n\n{t['quote_prefix']}\n\n{quote}"
        kb = build_main_keyboard(lang, user_id, quote=quote)
        try:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=kb)
            # Günlük sayaçlara da işleyelim
            stats = ensure_stats(user_id)
            stats["quotes"] += 1
        except Exception as e:
            logger.warning(f"Error sending daily quote to {user_id}: {e}")


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable set edilmemiş. "
            "Örn: export BOT_TOKEN='123456:ABC-DEF'"
        )

    app = Application.builder().token(BOT_TOKEN).build()

    # Komutlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("quote", quote_command))

    # Inline callback
    app.add_handler(CallbackQueryHandler(button_callback))

    # Diğer metinler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text))

    # Günlük job (TR saatiyle)
    ist_tz = ZoneInfo("Europe/Istanbul")
    app.job_queue.run_daily(
        daily_quote_job,
        time=time(hour=DAILY_QUOTE_HOUR, minute=0, tzinfo=ist_tz),
    )

    logger.info("DailyQuoteBot (lang + topics + ads + favorites + daily job) is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
