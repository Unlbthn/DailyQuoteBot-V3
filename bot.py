import logging
import os
import random
from datetime import date
from io import BytesIO

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
WEBAPP_URL = os.getenv("WEBAPP_URL")       # Varsa WebApp için

ADSGRAM_BLOCK_ID = 16417                   # Senin AdsGram block ID

AD_FREQUENCY = 4                           # Her 4 sözde bir otomatik reklam
MAX_ADS_PER_DAY = 10                       # Kullanıcı başı günlük reklam sınırı

DEFAULT_TOPIC = "motivation"

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
# Tamamen bizden çıkan, generic ve güvenli cümleler
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
        "start": (
            "✨ DailyQuoteBot'a hoş geldin!\n\n"
            "Konulara göre anlamlı sözler keşfedebilirsin:\n"
            "• Motivasyon\n"
            "• Aşk\n"
            "• Başarı\n"
            "• Hayat\n"
            "• Kendine iyi bak\n\n"
            "Aşağıdaki butonlardan konunu seç, ardından 'Yeni söz' ile devam et 👇"
        ),
        "help": (
            "📚 DailyQuoteBot yardım\n\n"
            "/start - Karşılama mesajı ve menü\n"
            "/quote - Mevcut konuya göre yeni söz\n\n"
            "Mesaj altındaki butonlardan da:\n"
            "• Konu seçebilir\n"
            "• Yeni söz alabilir\n"
            "• Ekstra söz için reklam izleyebilirsin."
        ),
        "btn_new": "🔁 Yeni söz",
        "btn_extra": "🎁 Ekstra söz (reklam)",
        "btn_webapp": "🌐 Web App",
        "quote_prefix": "Bugünün sözü:",
        "no_quote": "Şu an için gösterecek söz bulamadım.",
        "ad_error": "Şu anda reklam gösterilemiyor, lütfen daha sonra tekrar dene.",
        "fallback": "DailyQuoteBot'u kullanmak için aşağıdaki butonları kullanabilirsin 👇",
        "topic_changed": "Konu değiştirildi: {topic}. Şimdi yeni bir söz alabilirsin.",
    },
    "en": {
        "start": (
            "✨ Welcome to DailyQuoteBot!\n\n"
            "You can discover meaningful quotes by topics:\n"
            "• Motivation\n"
            "• Love\n"
            "• Success\n"
            "• Life\n"
            "• Self-care\n\n"
            "Choose your topic from the buttons below, then tap 'New quote' 👇"
        ),
        "help": (
            "📚 DailyQuoteBot help\n\n"
            "/start - Welcome message and menu\n"
            "/quote - New quote for your current topic\n\n"
            "From the buttons below you can:\n"
            "• Change topic\n"
            "• Get new quotes\n"
            "• Watch an ad to get an extra quote."
        ),
        "btn_new": "🔁 New quote",
        "btn_extra": "🎁 Extra quote (ad)",
        "btn_webapp": "🌐 Web App",
        "quote_prefix": "Today's quote:",
        "no_quote": "I don't have a quote to show right now.",
        "ad_error": "Ad is not available right now, please try again later.",
        "fallback": "You can use the buttons below to use DailyQuoteBot 👇",
        "topic_changed": "Topic changed to: {topic}. Now you can get a new quote.",
    },
}

# ---------------------------------------------------------------------
# STATE
# ---------------------------------------------------------------------

# Kullanıcı günlük sayaçları
# {user_id: {"day": date, "quotes": int, "ads": int}}
USER_STATS = {}

# Kullanıcı seçili konusu
# {user_id: "motivation" | "love" | ...}
USER_TOPIC = {}


def get_lang(update: Update) -> str:
    user = update.effective_user
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


# ---------------------------------------------------------------------
# GÖRSEL KART
# ---------------------------------------------------------------------

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


def build_main_keyboard(lang: str, user_id: int) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    topic_labels = TOPIC_LABELS[lang]
    current_topic = get_user_topic(user_id)

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
        [InlineKeyboardButton(t["btn_new"], callback_data="new_quote")],
        [InlineKeyboardButton(t["btn_extra"], callback_data="extra_quote")],
        topic_buttons[:2],
        topic_buttons[2:],
    ]

    if WEBAPP_URL:
        rows.append(
            [InlineKeyboardButton(t["btn_webapp"], web_app=WebAppInfo(url=WEBAPP_URL))]
        )

    return InlineKeyboardMarkup(rows)


async def send_quote_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    quote: str,
    lang: str,
    user_id: int,
):
    kb = build_main_keyboard(lang, user_id)
    img_bytes = render_quote_image(quote, lang)

    if update.message:
        await update.message.reply_photo(photo=img_bytes, reply_markup=kb)
    elif update.callback_query:
        await update.callback_query.message.reply_photo(photo=img_bytes, reply_markup=kb)
    else:
        chat_id = update.effective_chat.id
        await context.bot.send_photo(chat_id=chat_id, photo=img_bytes, reply_markup=kb)


# ---------------------------------------------------------------------
# ADSGRAM
# ---------------------------------------------------------------------

async def send_adsgram_ad(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lang: str,
    user_id: int,
):
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
# HANDLER'LAR
# ---------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update)
    t = TEXTS[lang]
    user = update.effective_user
    user_id = user.id if user else 0

    # Varsayılan konu
    get_user_topic(user_id)

    kb = build_main_keyboard(lang, user_id)
    await update.message.reply_text(t["start"], reply_markup=kb)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update)
    t = TEXTS[lang]
    user_id = update.effective_user.id
    kb = build_main_keyboard(lang, user_id)
    await update.message.reply_text(t["help"], reply_markup=kb)


async def send_new_quote(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    extra: bool = False,
):
    lang = get_lang(update)
    user = update.effective_user
    user_id = user.id if user else 0

    stats = ensure_stats(user_id)
    quote = get_random_quote_for_user(user_id, lang)

    if not quote:
        t = TEXTS[lang]
        kb = build_main_keyboard(lang, user_id)
        if update.message:
            await update.message.reply_text(t["no_quote"], reply_markup=kb)
        elif update.callback_query:
            await update.callback_query.message.reply_text(t["no_quote"], reply_markup=kb)
        else:
            chat_id = update.effective_chat.id
            await context.bot.send_message(chat_id=chat_id, text=t["no_quote"], reply_markup=kb)
        return

    await send_quote_image(update, context, quote, lang, user_id)

    stats["quotes"] += 1

    if not extra:
        if stats["quotes"] % AD_FREQUENCY == 0 and stats["ads"] < MAX_ADS_PER_DAY:
            await send_adsgram_ad(update, context, lang, user_id)


async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_new_quote(update, context, extra=False)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    lang = get_lang(update)
    user = update.effective_user
    user_id = user.id if user else 0

    if data == "new_quote":
        await send_new_quote(update, context, extra=False)

    elif data == "extra_quote":
        await send_adsgram_ad(update, context, lang, user_id)
        await send_new_quote(update, context, extra=True)

    elif data.startswith("topic:"):
        topic_key = data.split(":", 1)[1]
        set_user_topic(user_id, topic_key)
        t = TEXTS[lang]
        label = TOPIC_LABELS[lang].get(topic_key, topic_key)
        msg = t["topic_changed"].format(topic=label)
        kb = build_main_keyboard(lang, user_id)
        await query.answer()
        await query.message.r
