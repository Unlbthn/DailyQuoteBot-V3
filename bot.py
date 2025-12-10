import logging
import os
import random
from datetime import date, time
from typing import Optional
from zoneinfo import ZoneInfo
import urllib.parse

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
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")

# AdsGram ayarları
ADSGRAM_BLOCK_ID = 16417
MAX_ADS_PER_DAY = 10  # kullanıcı başı günlük max reklam

# Varsayılan konu ve günlük bildirim saati
DEFAULT_TOPIC = "motivation"
DAILY_QUOTE_HOUR = 10  # Türkiye saati ile 10:00

# -------------------------------------------------
# LOGGING
# -------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# -------------------------------------------------
# QUOTES
# -------------------------------------------------

# QUOTES[topic][lang] -> list of {"text": "...", "author": "...." or None}
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
    # Spor TR+EN
    "sport": {
        "tr": [
            {"text": "Kelebek gibi uçar, arı gibi sokarım.", "author": "Muhammed Ali"},
            {"text": "Zorluklar, şampiyonları belirler.", "author": None},
            {"text": "Ter, başarıya açılan kapının anahtarıdır.", "author": None},
            {"text": "Kaybetmekten korkma; denememekten kork.", "author": None},
            {"text": "Disiplin, yeteneği yener.", "author": None},
            {"text": "İmkânsız sadece daha uzun süren bir şeydir.", "author": "Muhammed Ali"},
            {"text": "Ağrıyı kucakla, o seni büyütür.", "author": None},
            {"text": "Koşarken beden yorulur, karakter güçlenir.", "author": None},
            {"text": "Bugün acı çek, yarın şampiyon ol.", "author": None},
            {"text": "Çalışmadan kazanılan hiçbir zafer kalıcı değildir.", "author": None},
            {"text": "Hedefi olmayan rüzgârla savrulur.", "author": None},
            {"text": "Başarı tesadüf değildir; emek ister.", "author": "Michael Jordan"},
            {"text": "Yavaş ilerlemekten korkma, yerinde saymaktan kork.", "author": None},
            {"text": "Zihnin pes derse, beden zaten bırakır.", "author": None},
            {"text": "Kazanmak isteği değil, kazanmak için hazırlanmak fark yaratır.", "author": "Bear Bryant"},
            {"text": "Devam eden kazanır.", "author": None},
            {"text": "Bugün yapacakların yarınki gücünü belirler.", "author": None},
            {"text": "Zaferin bedeli terdir.", "author": None},
            {"text": "Rakibini değil, kendini geçmeye çalış.", "author": None},
            {"text": "Pes etmek kolaydır, mücadele etmek karakter ister.", "author": None},
            {"text": "Mazeretler şampiyon yaratmaz.", "author": None},
            {"text": "En büyük rakibin dünkü halindir.", "author": None},
            {"text": "Güç, vazgeçmeyenlerindir.", "author": None},
            {"text": "Cesaret, adım atmaktan ibarettir.", "author": None},
            {"text": "Zafer, hazırlanmış olanlarındır.", "author": "Herodot"},
            {"text": "Şampiyonlar antrenmanda doğar.", "author": None},
            {"text": "Yorulduğunda durma, işin bittiğinde dur.", "author": None},
            {"text": "Disiplin, özgürlüğün kapısıdır.", "author": None},
            {"text": "Bir gün değil, her gün çalış.", "author": None},
            {"text": "Yüreği olan kazanır.", "author": None},
            {"text": "Korku, sınırlarını aşmak için var.", "author": None},
            {"text": "Zafer, inananlarındır.", "author": "Mustafa Kemal Atatürk"},
            {"text": "Düşmek kaderindir ama kalkmak tercihindir.", "author": None},
            {"text": "Cesaret risk almaktır.", "author": None},
            {"text": "İlerlemek istiyorsan önce terle.", "author": None},
            {"text": "Büyük işler küçük adımlarla başlar.", "author": None},
            {"text": "Kendine inan, geri kalan kendiliğinden gelir.", "author": None},
            {"text": "Sınırlarını zorlamadan gelişemezsin.", "author": None},
            {"text": "Zafer, vazgeçmeyenlere gelir.", "author": None},
            {"text": "Her adım seni daha güçlü kılar.", "author": None},
            {"text": "Kazanmak, önce kafada başlar.", "author": None},
            {"text": "Bedeni zayıf olanın iradesi güçlü olmalıdır.", "author": None},
            {"text": "Çalışmak hiç kimseyi küçültmez.", "author": None},
            {"text": "Tekrar et, güçlen.", "author": None},
            {"text": "Rakibin yoksa kendini rakip yap.", "author": None},
            {"text": "Güç gelişir, karakter kalır.", "author": None},
            {"text": "Ne kadar çok çalışırsan, o kadar şanslı olursun.", "author": "Gary Player"},
            {"text": "Bitirmeden pes etme.", "author": None},
            {"text": "En büyük zafer, kendini yenmektir.", "author": "Plato"},
            {"text": "Hızlı olmak değil, kararlı olmak kazandırır.", "author": None},
            {"text": "Bugünün mücadelesi yarının gücüdür.", "author": None},
        ],
        "en": [
            {"text": "I float like a butterfly, I sting like a bee.", "author": "Muhammad Ali"},
            {"text": "Winners are not people who never fail, but people who never quit.", "author": None},
            {"text": "Hard work beats talent when talent doesn’t work hard.", "author": "Tim Notke"},
            {"text": "Champions keep playing until they get it right.", "author": "Billie Jean King"},
            {"text": "Pain is temporary, pride is forever.", "author": "Lance Armstrong"},
            {"text": "Success is no accident.", "author": "Pelé"},
            {"text": "You miss 100% of the shots you don’t take.", "author": "Wayne Gretzky"},
            {"text": "Discipline is choosing what you want most over what you want now.", "author": None},
            {"text": "Winners train, losers complain.", "author": None},
            {"text": "The body achieves what the mind believes.", "author": None},
            {"text": "Victory belongs to the most persevering.", "author": "Napoleon Bonaparte"},
            {"text": "Champions are made from something deep inside.", "author": "Muhammad Ali"},
            {"text": "Don’t stop when you’re tired. Stop when you’re done.", "author": None},
            {"text": "Great things never come from comfort zones.", "author": None},
            {"text": "The harder the battle, the sweeter the victory.", "author": "Les Brown"},
            {"text": "Run when you can, walk if you have to, crawl if you must.", "author": "Dean Karnazes"},
            {"text": "A champion is someone who gets up when he can’t.", "author": "Jack Dempsey"},
            {"text": "Don’t dream of winning. Train for it.", "author": None},
            {"text": "It never gets easier; you just get stronger.", "author": "Greg LeMond"},
            {"text": "Practice like you’ve never won. Perform like you’ve never lost.", "author": None},
            {"text": "Push yourself. No one else is going to do it for you.", "author": None},
            {"text": "Sweat is fat crying.", "author": None},
            {"text": "Believe you can and you’re halfway there.", "author": "Theodore Roosevelt"},
            {"text": "Strength doesn’t come from what you can do; it comes from overcoming what you thought you couldn’t.", "author": "Rikki Rogers"},
            {"text": "The will to win means nothing without the will to prepare.", "author": "Juma Ikangaa"},
            {"text": "Train insane or remain the same.", "author": None},
            {"text": "Go the extra mile. It’s never crowded.", "author": None},
            {"text": "Sports do not build character. They reveal it.", "author": "Heywood Broun"},
            {"text": "If it doesn’t challenge you, it won’t change you.", "author": "Fred DeVito"},
            {"text": "Champions are born in training, not on the field.", "author": None},
            {"text": "Don’t count the days; make the days count.", "author": "Muhammad Ali"},
            {"text": "You have to expect things of yourself before you can do them.", "author": "Michael Jordan"},
            {"text": "Pain is weakness leaving the body.", "author": None},
            {"text": "Success trains. Failure complains.", "author": None},
            {"text": "You don’t get what you wish for. You get what you work for.", "author": None},
            {"text": "Every champion was once a beginner.", "author": "Muhammad Ali"},
            {"text": "Fall seven times, stand up eight.", "author": "Japanese Proverb"},
            {"text": "Tough times don’t last; tough people do.", "author": "Robert H. Schuller"},
            {"text": "The only bad workout is the one you didn’t do.", "author": None},
            {"text": "Champions believe in themselves even when no one else does.", "author": None},
            {"text": "You are stronger than you think.", "author": None},
            {"text": "Success is earned, not given.", "author": None},
            {"text": "Effort is the difference between good and great.", "author": None},
            {"text": "Victory requires payment in advance.", "author": None},
            {"text": "Be stronger than your excuses.", "author": None},
            {"text": "Work hard in silence, let success make the noise.", "author": "Frank Ocean"},
            {"text": "A little progress each day adds up to big results.", "author": None},
            {"text": "Do something today that your future self will thank you for.", "author": None},
            {"text": "Great athletes are made, not born.", "author": None},
            {"text": "Keep going. Your future self is cheering for you.", "author": None},
        ],
    },
    "discipline": {
        "tr": [
            {"text": "Disiplin, canın istemediğinde de doğru olanı yapabilmektir.", "author": None},
            {"text": "Rutinin, hayallerin kadar güçlü olursa başarı kaçınılmaz olur.", "author": None},
        ],
        "en": [
            {"text": "Discipline is doing what is right even when you don’t feel like it.", "author": None},
            {"text": "If your routine is as strong as your dreams, success becomes inevitable.", "author": None},
        ],
    },
    "friendship": {
        "tr": [
            {"text": "Gerçek dost, kalabalık dağıldığında yanında kalandır.", "author": None},
            {"text": "Dostluk, aynı şeye gülüp aynı yerde susabilmektir.", "author": None},
        ],
        "en": [
            {"text": "A true friend is the one who stays when the crowd is gone.", "author": None},
            {"text": "Friendship is laughing at the same things and being silent in the same moments.", "author": None},
        ],
    },
    "resilience": {
        "tr": [
            {"text": "Kırılabilirsin ama vazgeçmek zorunda değilsin.", "author": None},
            {"text": "Her düştüğünde yerden bir şey al; tecrübe mesela.", "author": None},
        ],
        "en": [
            {"text": "You may break, but you don’t have to give up.", "author": None},
            {"text": "Every time you fall, pick something up from the ground — like experience.", "author": None},
        ],
    },
    "creativity": {
        "tr": [
            {"text": "Yaratıcılık, 'ya şöyle olursa?' sorusunu sormaktan korkmamaktır.", "author": None},
            {"text": "Boş bir sayfa, aslında sonsuz ihtimal demektir.", "author": None},
        ],
        "en": [
            {"text": "Creativity is not being afraid to ask ‘what if?’.", "author": None},
            {"text": "A blank page actually means infinite possibilities.", "author": None},
        ],
    },
    "work": {
        "tr": [
            {"text": "Sevdiğin işi yapmak güzeldir, ama yaptığın işi sevmeyi öğrenmek daha değerlidir.", "author": None},
            {"text": "İş hayatında en büyük CV, tutarlı sonuçlardır.", "author": None},
        ],
        "en": [
            {"text": "Doing what you love is great, but learning to love what you do can be even more powerful.", "author": None},
            {"text": "In your career, the strongest resume is consistent results.", "author": None},
        ],
    },
    "gratitude": {
        "tr": [
            {"text": "Şükrettiğin her şey, gözünde büyür; şikâyet ettiğin her şey, kalbini küçültür.", "author": None},
            {"text": "Bugün sahip olduklarına, dün hayal ettiklerin gözüyle bak.", "author": None},
        ],
        "en": [
            {"text": "What you are grateful for grows; what you constantly complain about shrinks your heart.", "author": None},
            {"text": "Look at what you have today as things you once wished for.", "author": None},
        ],
    },
}

# -------------------------------------------------
# TOPIC LABELS
# -------------------------------------------------

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

# -------------------------------------------------
# TEXTS
# -------------------------------------------------

TEXTS = {
    "tr": {
        "welcome_lang": "Lütfen dil seç:\n\nPlease select your language:",
        "start": (
            "✨ Quote Masters'a hoş geldin!\n\n"
            "Konulara göre anlamlı sözler keşfedebilirsin."
        ),
        "help": """📚 Quote Masters yardım

/start - Karşılama ve menü
/quote - Mevcut konuya göre yeni söz

Butonlarla:
• Sözü değiştir
• Günün sözünü gör
• Konuyu değiştir (kategoriler)
• WhatsApp / Telegram'da paylaş
• Ayarlar (dil, bildirimler)
""",
        "quote_prefix": "Bugünün sözü:",
        "no_quote": "Şu an için gösterecek söz bulamadım.",
        "fallback": "Quote Masters'ı kullanmak için aşağıdaki butonları kullanabilirsin 👇",
        "topic_menu_title": "Lütfen bir konu seç:",
        "settings_title": ⚙️ Ayarlar",
        "settings_daily_on": "Günün sözü bildirimi: Açık",
        "settings_daily_off": "Günün sözü bildirimi: Kapalı",
        "settings_lang": "Dil:",
        "daily_quote_title": "📅 Günün sözü",
    },
    "en": {
        "welcome_lang": "Please select your language:\n\nLütfen dil seç:",
        "start": (
            "✨ Welcome to Quote Masters!\n\n"
            "You can discover meaningful quotes by topics."
        ),
        "help": """📚 Quote Masters help

/start - Welcome & menu
/quote - New quote for current topic

Buttons:
• Change quote
• Show today's quote
• Change topic (categories)
• Share via WhatsApp / Telegram
• Settings (language, notifications)
""",
        "quote_prefix": "Today's quote:",
        "no_quote": "I don't have a quote to show right now.",
        "fallback": "You can use the buttons below to use Quote Masters 👇",
        "topic_menu_title": "Please choose a topic:",
        "settings_title": "⚙️ Settings",
        "settings_daily_on": "Daily quote notification: ON",
        "settings_daily_off": "Daily quote notification: OFF",
        "settings_lang": "Language:",
        "daily_quote_title": "📅 Daily quote",
    },
}

# -------------------------------------------------
# STATE
# -------------------------------------------------

USER_LANG = {}       # {user_id: 'tr'/'en'}
USER_TOPIC = {}      # {user_id: topic}
USER_STATS = {}      # {user_id: {day, quotes, ads}}
LAST_QUOTE = {}      # {user_id: full_quote}
DAILY_ENABLED = {}   # {user_id: bool}
KNOWN_USERS = set()  # {user_id}

# -------------------------------------------------
# HELPERS
# -------------------------------------------------

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


def get_global_daily_quote(lang: str) -> tuple[str, Optional[str]]:
    """
    Bugünün tarihi üzerinden seed alarak:
    - Tüm konulardan
    - Seçilen dilde
    tek bir söz seçer.
    Aynı gün için her yerde aynı sonuç gelir.
    """
    combos = []
    for topic, langs in QUOTES.items():
        if lang in langs:
            for idx, _ in enumerate(langs[lang]):
                combos.append((topic, idx))
    if not combos:
        return "", None

    seed = int(date.today().strftime("%Y%m%d"))
    if lang == "en":
        seed += 999
    rnd = random.Random(seed)
    topic, idx = rnd.choice(combos)
    item = QUOTES[topic][lang][idx]
    return item["text"], item.get("author")


def build_main_keyboard(lang: str, user_id: int, quote: Optional[str] = None) -> InlineKeyboardMarkup:
    quote_text = quote or LAST_QUOTE.get(user_id) or ""
    if lang == "tr":
        share_body = (
            "Bugünün sözü:\n\n"
            f"{quote_text}\n\n"
            "— Quote Masters\n"
            "Türkçe & İngilizce anlamlı sözler için: https://t.me/QuoteMastersBot"
        )
    else:
        share_body = (
            "Today's quote:\n\n"
            f"{quote_text}\n\n"
            "— Quote Masters\n"
            "Discover meaningful quotes in Turkish & English: https://t.me/QuoteMastersBot"
        )

    encoded = urllib.parse.quote_plus(share_body)

    wa_url = f"https://wa.me/?text={encoded}"
    tg_url = f"https://t.me/share/url?url=&text={encoded}"

    rows = [
        [
            InlineKeyboardButton(
                "📅 Günün Sözü" if lang == "tr" else "📅 Daily quote",
                callback_data="daily_now",
            ),
            InlineKeyboardButton("📤 WhatsApp", url=wa_url),
        ],
        [
            InlineKeyboardButton("📤 Telegram", url=tg_url),
            InlineKeyboardButton(
                "🔁 " + ("Sözü değiştir" if lang == "tr" else "Change quote"),
                callback_data="new_quote",
            ),
        ],
        [
            InlineKeyboardButton(
                "🧭 " + ("Konuyu değiştir" if lang == "tr" else "Change topic"),
                callback_data="topic_menu",
            ),
            InlineKeyboardButton(
                "⚙️ " + ("Ayarlar" if lang == "tr" else "Settings"),
                callback_data="settings",
            ),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def build_topic_keyboard(lang: str) -> InlineKeyboardMarkup:
    topic_labels = TOPIC_LABELS[lang]
    topic_keys = [
        "motivation", "love", "success", "life", "selfcare", "sport",
        "discipline", "friendship", "resilience", "creativity", "work", "gratitude",
    ]

    buttons = []
    for key in topic_keys:
        label = topic_labels.get(key, key)
        buttons.append(InlineKeyboardButton(label, callback_data=f"topic:{key}"))

    rows = []
    for i in range(0, len(buttons), 2):
        row = [buttons[i]]
        if i + 1 < len(buttons):
            row.append(buttons[i + 1])
        rows.append(row)

    return InlineKeyboardMarkup(rows)

# -------------------------------------------------
# ADSGRAM
# -------------------------------------------------

async def send_adsgram_ad(
    update: Optional[Update],
    context: ContextTypes.DEFAULT_TYPE,
    lang: str,
    user_id: int,
) -> None:
    """Sözden sonra altına reklam mesajı atar."""
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
        raw = resp.text.strip()
        if not raw:
            logger.warning("AdsGram empty response")
            return
        try:
            data = resp.json()
        except ValueError:
            logger.warning("AdsGram JSON parse error: %s", raw[:200])
            return
    except Exception as e:
        logger.warning(f"AdsGram error: {e}")
        return

    if not isinstance(data, dict):
        logger.warning("AdsGram invalid JSON structure: %r", data)
        return

    # Daha toleranslı alan okuma
    text_html = data.get("text_html") or data.get("text") or ""
    click_url = data.get("click_url") or data.get("url")
    button_name = data.get("button_name") or data.get("button_text")
    image_url = data.get("image_url")
    button_reward_name = data.get("button_reward_name")
    reward_url = data.get("reward_url")

    if not text_html:
        logger.warning("AdsGram missing text/text_html")
        return

    buttons = []
    if button_name and click_url:
        buttons.append([InlineKeyboardButton(button_name, url=click_url)])
    if button_reward_name and reward_url:
        buttons.append([InlineKeyboardButton(button_reward_name, url=reward_url)])

    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

    if update and update.effective_chat:
        chat_id = update.effective_chat.id
    else:
        chat_id = user_id

    try:
        if image_url:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=image_url,
                caption=text_html,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text_html,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )
        stats["ads"] += 1
    except Exception as e:
        logger.warning("Error sending AdsGram message: %s", e)

# -------------------------------------------------
# MAIN QUOTE SENDER (TOPIC-BASED)
# -------------------------------------------------

async def send_quote_with_ui(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Seçili konuya göre söz + alt menü + altına reklam."""
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

    t = TEXTS[lang]
    if lang == "tr":
        text = f"{t['quote_prefix']}\n\n“{quote_text}”"
        if author:
            text += f"\n— {author}"
        text += "\n\nGünün sözünü beğendiysen bize destek olmak için bir arkadaşınla paylaş. 💜"
    else:
        text = f"{t['quote_prefix']}\n\n“{quote_text}”"
        if author:
            text += f"\n— {author}"
        text += "\n\nIf you liked today’s quote, support us by sharing it with a friend. 💜"

    kb = build_main_keyboard(lang, user_id, quote=full_text)

    if update.message:
        await update.message.reply_text(text, reply_markup=kb)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=kb)
    else:
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)

    stats["quotes"] += 1

    if stats["ads"] < MAX_ADS_PER_DAY:
        await send_adsgram_ad(update, context, lang, user_id)

# -------------------------------------------------
# DAILY QUOTE (GLOBAL)
# -------------------------------------------------

async def send_daily_quote_to_user(
    user_id: int,
    lang: str,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    t = TEXTS[lang]
    quote_text, author = get_global_daily_quote(lang)
    if not quote_text:
        return

    full_text = quote_text if not author else f"{quote_text}\n— {author}"
    LAST_QUOTE[user_id] = full_text
    kb = build_main_keyboard(lang, user_id, quote=full_text)
    text = f"{t['daily_quote_title']}\n\n{t['quote_prefix']}\n\n{full_text}"

    await context.bot.send_message(chat_id=user_id, text=text, reply_markup=kb)
    stats = ensure_stats(user_id)
    stats["quotes"] += 1
    if stats["ads"] < MAX_ADS_PER_DAY:
        await send_adsgram_ad(None, context, lang, user_id)

# -------------------------------------------------
# LANGUAGE SELECTION / SETTINGS
# -------------------------------------------------

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

    text = f"{t['settings_title']}\n\n{daily_text}\n{t['settings_lang']} {lang_label}\n\n"
    if lang == "tr":
        text += "• Dil değiştir\n• Bildirimleri aç/kapat"
    else:
        text += "• Change language\n• Toggle daily quote"

    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇹🇷 Türkçe", callback_data="set_lang:tr"),
                InlineKeyboardButton("🇬🇧 English", callback_data="set_lang:en"),
            ],
            [
                InlineKeyboardButton(
                    "🔔 " + ("Bildirimleri aç/kapat" if lang == "tr" else "Toggle daily quote"),
                    callback_data="toggle_daily",
                )
            ],
        ]
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=kb)
    elif update.message:
        await update.message.reply_text(text, reply_markup=kb)

# -------------------------------------------------
# HANDLERS
# -------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Her /start çağrısında dil seçimi açılır.
    """
    user = update.effective_user
    user_id = user.id if user else 0
    KNOWN_USERS.add(user_id)
    DAILY_ENABLED.setdefault(user_id, True)

    await send_language_selection(update, context)


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

    await send_quote_with_ui(update, context)


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
        lang = USER_LANG[user_id]
        t = TEXTS[lang]
        kb = build_topic_keyboard(lang)
        text = (
            "✨ Quote Masters'a hoş geldin!\n\n" + t["topic_menu_title"]
            if lang == "tr"
            else "✨ Welcome to Quote Masters!\n\n" + t["topic_menu_title"]
        )
        await query.answer()
        await query.message.reply_text(text, reply_markup=kb)
        return

    if user_id not in USER_LANG:
        await send_language_selection(update, context)
        await query.answer()
        return

    lang = USER_LANG[user_id]
    t = TEXTS[lang]

    if data == "new_quote":
        await query.answer()
        await send_quote_with_ui(update, context)

    elif data == "topic_menu":
        await query.answer()
        kb = build_topic_keyboard(lang)
        await query.message.reply_text(t["topic_menu_title"], reply_markup=kb)

    elif data.startswith("topic:"):
        topic_key = data.split(":", 1)[1]
        set_user_topic(user_id, topic_key)
        await query.answer()
        await send_quote_with_ui(update, context)

    elif data == "settings":
        await query.answer()
        await show_settings(update, context)

    elif data == "toggle_daily":
        DAILY_ENABLED[user_id] = not DAILY_ENABLED.get(user_id, True)
        await query.answer()
        await show_settings(update, context)

    elif data == "daily_now":
        await query.answer()
        await send_daily_quote_to_user(user_id, lang, context)

    else:
        await query.answer()


async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kullanıcı /start demeden yazarsa burada yakalanır."""
    user = update.effective_user
    user_id = user.id if user else 0
    KNOWN_USERS.add(user_id)
    DAILY_ENABLED.setdefault(user_id, True)

    if user_id not in USER_LANG:
        guess_lang = get_lang(update)
        if guess_lang == "tr":
            msg = "✨ Quote Masters'a hoş geldin!\n\nBaşlamak için /start yaz."
        else:
            msg = "✨ Welcome to Quote Masters!\n\nType /start to begin."
        await update.message.reply_text(msg)
        return

    lang = USER_LANG[user_id]
    t = TEXTS[lang]
    kb = build_main_keyboard(lang, user_id, quote=LAST_QUOTE.get(user_id))
    await update.message.reply_text(t["fallback"], reply_markup=kb)

# -------------------------------------------------
# MAIN
# -------------------------------------------------

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable set edilmemiş. "
            "Örn: export BOT_TOKEN='123456:ABC-DEF'"
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("quote", quote_command))

    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text))

    # Günlük job
    ist_tz = ZoneInfo("Europe/Istanbul")
    jq = app.job_queue
    if jq is not None:
        jq.run_daily(
            daily_quote_job,
            time=time(hour=DAILY_QUOTE_HOUR, minute=0, tzinfo=ist_tz),
        )
        logger.info("JobQueue aktif, günlük bildirim planlandı (TR %02d:00).", DAILY_QUOTE_HOUR)
    else:
        logger.warning(
            "JobQueue mevcut değil. Günlük bildirim çalışmayacak. "
            "requirements.txt içine python-telegram-bot[job-queue] ekleyebilirsin."
        )

    logger.info("Quote Masters botu çalışıyor...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


async def daily_quote_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Her gün TR 10:00'da çağrılır: herkes için tek gün sözü."""
    for user_id in list(KNOWN_USERS):
        if not DAILY_ENABLED.get(user_id, True):
            continue
        lang = USER_LANG.get(user_id, "tr")
        try:
            await send_daily_quote_to_user(user_id, lang, context)
        except Exception as e:
            logger.warning(f"Error sending daily quote to {user_id}: {e}")


if __name__ == "__main__":
    main()
