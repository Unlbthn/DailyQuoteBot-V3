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

BOT_TOKEN = "8515430219:AAHH3d2W7Ao4ao-ARwHMonRxZY5MnOyHz9k"
WEBAPP_URL = os.getenv("WEBAPP_URL")  # Opsiyonel WebApp URL

ADSGRAM_BLOCK_ID = 16417             # Senin AdsGram ID
MAX_ADS_PER_DAY = 10                 # Kullanıcı başı günlük reklam sınırı

DEFAULT_TOPIC = "motivation"
DAILY_QUOTE_HOUR = 10                # Türkiye saatiyle 10:00

# ---------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# QUOTES YAPISI
# Her konu altında:
# QUOTES[topic]["tr"] = [{"text": "...", "author": "İsim" veya None}, ...]
# QUOTES[topic]["en"] = [{"text": "...", "author": "Name" veya None}, ...]
# Buradaki listeleri zamanla 100+ elemana kadar genişletebilirsin.
# ---------------------------------------------------------------------

QUOTES = {
    "motivation": {
        "tr": [
            {"text": "Bugün attığın küçük bir adım, yarınki büyük değişimin başlangıcı olabilir.", "author": None},
            {"text": "Yorulduğunda durma, sadece nefeslen; sonra yola devam et.", "author": None},
            {"text": "Zor günler biter, kazandığın güç seninle kalır.", "author": None},
            {"text": "Kendine inanmak, başarının yarısından fazlasıdır.", "author": None},
            {"text": "Kusursuz olmak zorunda değilsin, sadece vazgeçmemek yeter.", "author": None},
        ],
        "en": [
            {"text": "A small step today can be the beginning of a big change tomorrow.", "author": None},
            {"text": "When you feel tired, don’t quit, just pause and breathe.", "author": None},
            {"text": "Hard days end, but the strength you gain stays with you.", "author": None},
            {"text": "Believing in yourself is more than half of success.", "author": None},
            {"text": "You don’t need to be perfect, you just need to keep going.", "author": None},
        ],
    },
    "love": {
        "tr": [
            {"text": "Sevgi, söylemekten çok göstermeyi bilenlerin dilidir.", "author": None},
            {"text": "Doğru insan, seni değiştirmeye çalışmaz; olduğun halinle yanındadır.", "author": None},
            {"text": "Kalpten çıkan her şey, bir gün mutlaka sahibini bulur.", "author": None},
            {"text": "Yanında huzur bulduğun insan, en büyük şansındır.", "author": None},
            {"text": "Gerçek sevgi, en zor zamanda bile elini bırakmayandır.", "author": None},
        ],
        "en": [
            {"text": "Love is the language of those who know how to show more than they say.", "author": None},
            {"text": "The right person doesn’t try to change you; they stand by you as you are.", "author": None},
            {"text": "Everything that comes from the heart eventually finds its place.", "author": None},
            {"text": "The one who brings you peace is your greatest luck.", "author": None},
            {"text": "Real love doesn’t let go of your hand in the hardest moments.", "author": None},
        ],
    },
    "success": {
        "tr": [
            {"text": "Başarı, kimsenin görmediği saatlerde verilen emeklerin özetidir.", "author": None},
            {"text": "Disiplin, motivasyonun olmadığı günlerde seni yola devam ettiren güçtür.", "author": None},
            {"text": "Hatalar, yeterince cesur olanların öğretmenidir.", "author": None},
            {"text": "Planı olan, paniği yönetir; planı olmayan panikler.", "author": None},
            {"text": "Bugün konfor alanından çıkmazsan, yarın hayal ettiğin hayata giremezsin.", "author": None},
        ],
        "en": [
            {"text": "Success is the summary of all the effort no one sees.", "author": None},
            {"text": "Discipline is what keeps you moving when motivation is gone.", "author": None},
            {"text": "Mistakes are teachers for those who are brave enough to try.", "author": None},
            {"text": "Those with a plan manage panic; those without a plan panic.", "author": None},
            {"text": "If you never leave your comfort zone today, you can’t enter your dream life tomorrow.", "author": None},
        ],
    },
    "life": {
        "tr": [
            {"text": "Hayat, ertelediklerin değil; yaşadığın anların toplamıdır.", "author": None},
            {"text": "Zaman, geri alamadığın tek sermayendir; nereye harcadığına dikkat et.", "author": None},
            {"text": "Kıyaslamak, mutluluğun en hızlı katilidir.", "author": None},
            {"text": "Bazı kapılar kapanır, çünkü artık o odada işin bitmiştir.", "author": None},
            {"text": "Bugün, geri kalan hayatının ilk günü.", "author": None},
        ],
        "en": [
            {"text": "Life is not what you postpone, it’s what you actually live.", "author": None},
            {"text": "Time is the only capital you can’t get back; spend it wisely.", "author": None},
            {"text": "Comparison is the fastest killer of happiness.", "author": None},
            {"text": "Some doors close because your time in that room is over.", "author": None},
            {"text": "Today is the first day of the rest of your life.", "author": None},
        ],
    },
    "selfcare": {
        "tr": [
            {"text": "Dinlenmek, pes etmek değildir; yeniden başlamak için güç toplamaktır.", "author": None},
            {"text": "Hayır demek, bazen kendine evet demenin tek yoludur.", "author": None},
            {"text": "Sınır koymak, sevgisiz olmak değil; kendine saygı duymaktır.", "author": None},
            {"text": "Kendinle geçirdiğin zaman, en değerli randevundur.", "author": None},
            {"text": "Kendine şefkat göstermek, en güçlü iyileşme aracındır.", "author": None},
        ],
        "en": [
            {"text": "Resting is not giving up; it’s gathering strength to start again.", "author": None},
            {"text": "Sometimes saying no is the only way to say yes to yourself.", "author": None},
            {"text": "Setting boundaries is not a lack of love; it’s a sign of self-respect.", "author": None},
            {"text": "Time spent with yourself is your most valuable appointment.", "author": None},
            {"text": "Self-compassion is your strongest healing tool.", "author": None},
        ],
    },
    # 6) Spor
    "sport": {
        "tr": [
            {"text": "Kelebek gibi uçar, arı gibi sokarım.", "author": "Muhammed Ali"},
            {"text": "Kaybettiğimde değil, vazgeçtiğimde yenilirim.", "author": "Muhammed Ali"},
            {"text": "Zafere giden yol, ter ve sabırdan geçer.", "author": None},
            {"text": "Antrenmanda ne kadar çok terlersen, yarışta o kadar az yorulursun.", "author": None},
            {"text": "Yeteneğin varsa başlarsın, karakterin varsa tamamlarsın.", "author": None},
        ],
        "en": [
            {"text": "Float like a butterfly, sting like a bee.", "author": "Muhammad Ali"},
            {"text": "I never lose. I either win or learn.", "author": None},  # genel motivasyon
            {"text": "The more you sweat in training, the less you bleed in battle.", "author": None},
            {"text": "Talent gets you started, character keeps you going.", "author": None},
            {"text": "Champions are made when no one is watching.", "author": None},
        ],
    },
    # 7) Disiplin
    "discipline": {
        "tr": [
            {"text": "Disiplin, canın istemediğinde de doğru olanı yapabilmektir.", "author": None},
            {"text": "Rutinin, hayallerin kadar güçlü olursa başarı kaçınılmaz olur.", "author": None},
            {"text": "İrade, her gün küçük kararlarla güçlenir.", "author": None},
            {"text": "Disiplin, özgürlüğün bedelidir.", "author": None},
            {"text": "Hedefine göre yaşamazsan, anlık hislerine göre yaşarsın.", "author": None},
        ],
        "en": [
            {"text": "Discipline is doing what is right even when you don’t feel like it.", "author": None},
            {"text": "If your routine is as strong as your dreams, success becomes inevitable.", "author": None},
            {"text": "Willpower grows with small decisions you repeat every day.", "author": None},
            {"text": "Discipline is the price of freedom.", "author": None},
            {"text": "If you don’t live by your goals, you live by your impulses.", "author": None},
        ],
    },
    # 8) Dostluk
    "friendship": {
        "tr": [
            {"text": "Gerçek dost, kalabalık dağıldığında yanında kalandır.", "author": None},
            {"text": "Dostluk, aynı şeye gülüp aynı yerde susabilmektir.", "author": None},
            {"text": "İyi arkadaş, en zor günü bile hafifletir.", "author": None},
            {"text": "Yanındaymış gibi hissettiren insanlar, uzakta olsalar da yakındır.", "author": None},
            {"text": "Dost, hatanı yüzüne söyleyip, arkandan savunandır.", "author": None},
        ],
        "en": [
            {"text": "A true friend is the one who stays when the crowd is gone.", "author": None},
            {"text": "Friendship is laughing at the same things and being silent in the same moments.", "author": None},
            {"text": "A good friend makes even the hardest day lighter.", "author": None},
            {"text": "Those who feel close are never really far away.", "author": None},
            {"text": "A friend is the one who tells you your mistakes and defends you behind your back.", "author": None},
        ],
    },
    # 9) Dayanıklılık / Resilience
    "resilience": {
        "tr": [
            {"text": "Kırılabilirsin ama vazgeçmek zorunda değilsin.", "author": None},
            {"text": "Her düştüğünde yerden bir şey al; tecrübe mesela.", "author": None},
            {"text": "Güç, fırtınasız günde değil; fırtınanın içinden geçerken ortaya çıkar.", "author": None},
            {"text": "Zor zamanlar seni durdurmak için değil, dönüştürmek için gelir.", "author": None},
            {"text": "Bazen devam etmenin tek sebebi, başladığın günü hatırlamaktır.", "author": None},
        ],
        "en": [
            {"text": "You may break, but you don’t have to give up.", "author": None},
            {"text": "Every time you fall, pick something up from the ground — like experience.", "author": None},
            {"text": "Strength shows not on calm days, but in the middle of the storm.", "author": None},
            {"text": "Hard times come not to stop you, but to transform you.", "author": None},
            {"text": "Sometimes the only reason to keep going is remembering the day you started.", "author": None},
        ],
    },
    # 10) Yaratıcılık / Creativity
    "creativity": {
        "tr": [
            {"text": "Yaratıcılık, 'ya şöyle olursa?' sorusunu sormaktan korkmamaktır.", "author": None},
            {"text": "Boş bir sayfa, aslında sonsuz ihtimal demektir.", "author": None},
            {"text": "Hata, bazen yeni bir fikrin kapısıdır.", "author": None},
            {"text": "Farklı düşünmek, bazen sadece başka bir açıdan bakmaktır.", "author": None},
            {"text": "Zihnini beslersen, fikirlerin kendiliğinden çoğalır.", "author": None},
        ],
        "en": [
            {"text": "Creativity is not being afraid to ask ‘what if?’.", "author": None},
            {"text": "A blank page actually means infinite possibilities.", "author": None},
            {"text": "A mistake is often the door to a new idea.", "author": None},
            {"text": "Thinking differently is sometimes just looking from a different angle.", "author": None},
            {"text": "If you feed your mind, ideas multiply on their own.", "author": None},
        ],
    },
    # 11) İş & Kariyer / Work
    "work": {
        "tr": [
            {"text": "Sevdiğin işi yapmak güzeldir, ama yaptığın işi sevmeyi öğrenmek daha değerlidir.", "author": None},
            {"text": "İş hayatında en büyük CV, tutarlı sonuçlardır.", "author": None},
            {"text": "Toplantılardan çok, odaklandığın sessiz saatler geleceğini belirler.", "author": None},
            {"text": "İlerlemenin sırrı, bahane değil aksiyon üretmektir.", "author": None},
            {"text": "Bugün yaptığın iş, yarın hatırlanmak istediğin kişiyle uyumlu mu?", "author": None},
        ],
        "en": [
            {"text": "Doing what you love is great, but learning to love what you do can be even more powerful.", "author": None},
            {"text": "In your career, the strongest resume is consistent results.", "author": None},
            {"text": "Not meetings, but your focused quiet hours shape your future.", "author": None},
            {"text": "The secret of progress is producing actions, not excuses.", "author": None},
            {"text": "Is the work you do today aligned with the person you want to be remembered as tomorrow?", "author": None},
        ],
    },
    # 12) Şükran / Gratitude
    "gratitude": {
        "tr": [
            {"text": "Şükrettiğin her şey, gözünde büyür; şikâyet ettiğin her şey, kalbini küçültür.", "author": None},
            {"text": "Bugün sahip olduklarına, dün hayal ettiklerin gözüyle bak.", "author": None},
            {"text": "Küçük şeylere teşekkür etmeyi bilen, büyük mutluluklara daha yakındır.", "author": None},
            {"text": "Her gün en az bir şeye içinden 'iyi ki' de.", "author": None},
            {"text": "Neye odaklanırsan, ondan daha fazlasını görmeye başlarsın.", "author": None},
        ],
        "en": [
            {"text": "What you are grateful for grows; what you constantly complain about shrinks your heart.", "author": None},
            {"text": "Look at what you have today as things you once wished for.", "author": None},
            {"text": "Those who can thank for small things stand closer to big happiness.", "author": None},
            {"text": "Every day, say ‘I’m glad’ for at least one thing.", "author": None},
            {"text": "Whatever you focus on, you start seeing more of it.", "author": None},
        ],
    },
}

# Buradaki listeleri zamanla 100+ elemana çıkarmak için:
# - aynen bu formatta {"text": "...", "author": "..."} satırları eklemen yeterli.

TOPIC_LABELS = {
    "tr": {
        "motivation": "Motivasyon",
        "love": "Aşk",
        "success": "Başarı",
        "life": "Hayat",
        "selfcare": "Kendine iyi bak",
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
        "work": "Work & Career",
        "gratitude": "Gratitude",
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
            "Konulara göre anlamlı sözler keşfedebilirsin.\n"
            "Önce bir konu seç, sonra 'Yeni söz' ile devam et 👇"
        ),
        "help": (
            "📚 DailyQuoteBot yardım\n\n"
            "/start - Karşılama ve menü\n"
            "/quote - Mevcut konuya göre yeni söz\n\n"
            "Butonlarla:\n"
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
            "You can discover meaningful quotes by topics.\n"
            "First choose a topic, then tap 'New quote' 👇"
        ),
        "help": (
            "📚 DailyQuoteBot help\n\n"
            "/start - Welcome & menu\n"
            "/quote - New quote for current topic\n\n"
            "With the buttons you can:\n"
            "• Choose / change topic\n"
            "• Get new quotes\n"
            "• Add to favorites / view favorites\n"
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
USER_FAVORITES = {}     # {user_id: [full_quote_str, ...]}
LAST_QUOTE = {}         # {user_id: full_quote_str}
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


def get_random_quote_for_user(user_id: int, lang: str) -> tuple[str, Optional[str]]:
    topic = get_user_topic(user_id)
    topic_data = QUOTES.get(topic) or QUOTES[DEFAULT_TOPIC]
    lang_list = topic_data.get(lang) or topic_data.get("en") or []
    if not lang_list:
        return "", None
    item = random.choice(lang_list)
    return item["text"], item.get("author")


def render_quote_image(quote_text: str, author: Optional[str]) -> BytesIO:
    width, height = 800, 800
    bg_color = (0, 0, 0)
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    center = (width // 2, height // 2 - 60)
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
    try:
        font_author = ImageFont.truetype("arial.ttf", 26)
    except Exception:
        font_author = ImageFont.load_default()

    max_width = width - 160
    words = quote_text.split()
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
    used_height = total_text_height
    if author:
        used_height += 40

    start_y = center[1] - used_height // 2

    for i, line in enumerate(lines):
        w_width, _ = draw.textsize(line, font=font_quote)
        x = (width - w_width) // 2
        y = start_y + i * 40
        draw.text((x, y), line, fill=(229, 229, 229), font=font_quote)

    if author:
        author_text = f"— {author}"
        aw, ah = draw.textsize(author_text, font=font_author)
        ax = (width - aw) // 2
        ay = start_y + total_text_height + 10
        draw.text((ax, ay), author_text, fill=gold, font=font_author)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def build_main_keyboard(lang: str, user_id: int, quote: Optional[str] = None) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    topic_labels = TOPIC_LABELS[lang]
    current_topic = get_user_topic(user_id)

    topic_keys = [
        "motivation", "love", "success", "life", "selfcare", "sport",
        "discipline", "friendship", "resilience", "creativity", "work", "gratitude",
    ]

    topic_buttons = []
    for key in topic_keys:
        label = topic_labels.get(key, key)
        if key == current_topic:
            label = f"● {label}"
        else:
            label = f"○ {label}"
        topic_buttons.append(
            InlineKeyboardButton(label, callback_data=f"topic:{key}")
        )

    row1 = topic_buttons[:6]
    row2 = topic_buttons[6:12]

    rows = [
        [
            InlineKeyboardButton("🔁 " + ("Yeni söz" if lang == "tr" else "New quote"),
                                 callback_data="new_quote"),
            InlineKeyboardButton("🎁 " + ("Ekstra söz (reklam)" if lang == "tr" else "Extra quote (ad)"),
                                 callback_data="extra_quote"),
        ],
        row1,
        row2,
        [
            InlineKeyboardButton("⭐ " + ("Favorilere ekle" if lang == "tr" else "Add to favorites"),
                                 callback_data="fav_add"),
            InlineKeyboardButton("📂 " + ("Favorilerim" if lang == "tr" else "My favorites"),
                                 callback_data="fav_list"),
        ],
    ]

    if quote:
        encoded = urllib.parse.quote_plus(quote)
        wa_url = f"https://wa.me/?text={encoded}"
        tg_url = f"https://t.me/share/url?url=&text={encoded}"
        rows.append(
            [
                InlineKeyboardButton("📤 WhatsApp", url=wa_url),
                InlineKeyboardButton("📤 Telegram", url=tg_url),
            ]
        )

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
    DAILY_ENABLED.setdefault(user_id, True)

    stats = ensure_stats(user_id)
    quote_text, author = get_random_quote_for_user(user_id, lang)

    if not quote_text:
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

    full_text = quote_text if not author else f"{quote_text}\n— {author}"
    LAST_QUOTE[user_id] = full_text

    img_bytes = render_quote_image(quote_text, author)
    kb = build_main_keyboard(lang, user_id, quote=full_text)

    if update.message:
        await update.message.reply_photo(photo=img_bytes, reply_markup=kb)
    elif update.callback_query:
        await update.callback_query.message.reply_photo(photo=img_bytes, reply_markup=kb)
    else:
        chat_id = update.effective_chat.id
        await context.bot.send_photo(chat_id=chat_id, photo=img_bytes, reply_markup=kb)

    stats["quotes"] += 1

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
    user = update.effective_user
    user_id = user.id if user else 0
    KNOWN_USERS.add(user_id)
    DAILY_ENABLED.setdefault(user_id, True)

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
    DAILY_ENABLED.setdefault(user_id, True)

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
    DAILY_ENABLED.setdefault(user_id, True)

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
    DAILY_ENABLED.setdefault(user_id, True)

    # Dil seçimi
    if data.startswith("set_lang:"):
        lang_code = data.split(":", 1)[1]
        USER_LANG[user_id] = "tr" if lang_code == "tr" else "en"
        get_user_topic(user_id)
        lang = USER_LANG[user_id]
        t = TEXTS[lang]
        kb = build_main_keyboard(lang, user_id, quote=None)
        await query.answer()
        await query.message.reply_text(t["start"], reply_markup=kb)
        return

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
            text = t["fav_header"] + "\n\n" + "\n\n".join(f"• {q}" for q in favs[:50])
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
    DAILY_ENABLED.setdefault(user_id, True)

    if user_id not in USER_LANG:
        await send_language_selection(update, context)
        return

    lang = USER_LANG[user_id]
    t = TEXTS[lang]
    kb = build_main_keyboard(lang, user_id, quote=LAST_QUOTE.get(user_id))
    await update.message.reply_text(t["fallback"], reply_markup=kb)


# ---------------------------------------------------------------------
# GÜNLÜK GÜNÜN SÖZÜ JOB (TR 10:00)
# ---------------------------------------------------------------------

async def daily_quote_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    for user_id in list(KNOWN_USERS):
        if not DAILY_ENABLED.get(user_id, True):
            continue

        lang = USER_LANG.get(user_id, "tr")
        t = TEXTS[lang]

        quote_text, author = get_random_quote_for_user(user_id, lang)
        if not quote_text:
            continue

        full_text = quote_text if not author else f"{quote_text}\n— {author}"
        kb = build_main_keyboard(lang, user_id, quote=full_text)
        text = f"{t['daily_quote_title']}\n\n{t['quote_prefix']}\n\n{full_text}"

        try:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=kb)
            stats = ensure_stats(user_id)
            stats["quotes"] += 1
        except Exception as e:
            logger.warning(f"Error sending daily quote to {user_id}: {e}")


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------


    
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("quote", quote_command))

    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text))

    # Günlük job - Türkiye saati 10:00
    ist_tz = ZoneInfo("Europe/Istanbul")
    app.job_queue.run_daily(
        daily_quote_job,
        time=time(hour=DAILY_QUOTE_HOUR, minute=0, tzinfo=ist_tz),
    )

    logger.info("DailyQuoteBot (lang + 12 topics + ads + favorites + daily 10:00) is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()


