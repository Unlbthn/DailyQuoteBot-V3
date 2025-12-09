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

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")          # Render env
WEBAPP_URL = os.getenv("WEBAPP_URL")       # Opsiyonel WebApp URL

ADSGRAM_BLOCK_ID = 16417                   # Senin AdsGram block ID
MAX_ADS_PER_DAY = 10                       # Kullanıcı başı günlük reklam sınırı

DEFAULT_TOPIC = "motivation"
DAILY_QUOTE_HOUR = 10                      # Türkiye saatiyle 10:00

# -------------------------------------------------
# LOGGING
# -------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# -------------------------------------------------
# QUOTES YAPISI
# topic -> lang -> [{"text": "...", "author": "İsim" veya None}, ...]
# -------------------------------------------------

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

    # -------------------------------------------------
    # SPOR – senin gönderdiğin 100 söz (TR + EN)
    # -------------------------------------------------
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
            {"text": "Pain is weakness leaving the body.", "author": None},  # U.S. Marines anonim
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

    # Kalan diğer kategoriler (kısa listeler)
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
# METİN DİZİLERİ
# -------------------------------------------------

# -------------------------------------------------
# METİN DİZİLERİ
# -------------------------------------------------

TEXTS = {
    "tr": {
        "welcome_lang": "Lütfen dil seç:\n\nPlease select your language:",
        "start": (
            "✨ DailyQuoteBot'a hoş geldin!\n\n"
            "Konulara göre anlamlı sözler keşfedebilirsin.\n"
            "Önce bir konu seç, sonra 'Yeni söz' ile devam et 👇"
        ),
        "help": """📚 DailyQuoteBot yardım

/start - Karşılama ve menü
/quote - Mevcut konuya göre yeni söz

Butonlarla:
• Konu seç / değiştir
• Yeni söz al
• Favorilere ekle / Favorilerim
• WhatsApp / Telegram paylaş
• Ayarlar (dil + günün sözü bildirimi)
""",
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
        "help": """📚 DailyQuoteBot help

/start - Welcome & menu
/quote - New quote for current topic

With the buttons you can:
• Choose / change topic
• Get new quotes
• Add to favorites / view favorites
• Share via WhatsApp / Telegram
• Open settings (language + daily quote notification)
""",
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
