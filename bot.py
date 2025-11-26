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

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Render / local env üzerinden gelecek
WEBAPP_URL = os.getenv("WEBAPP_URL")  # İstersen mini app / landing page için

# AdsGram Bot monetization
# Kullanıcı: PlatformID / blockId = 16417
ADSGRAM_BLOCK_ID = 16417

# Her X sözde bir otomatik reklam
AD_FREQUENCY = 3

# Kullanıcı başı günlük max reklam sayısı
MAX_ADS_PER_DAY = 10

# ---------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# BASİT SÖZ HAVUZU (TR/EN)
# ---------------------------------------------------------------------

QUOTES = {
    "tr": [
        "Bugün kendine iyi davranmayı unutma.",
        "Her gün, yeni bir başlangıçtır.",
        "Vazgeçmeyenler, kazananlardır.",
        "Küçük adımlar, büyük değişimlere yol açar.",
        "Kendine inandığın an, her şey mümkündür.",
    ],
    "en": [
        "Be kind to yourself today.",
        "Every day is a new beginning.",
        "Those who never give up are the ones who win.",
        "Small steps lead to big changes.",
        "Once you believe in yourself, anything is possible.",
    ],
}

# ---------------------------------------------------------------------
# DİL METİNLERİ
# ---------------------------------------------------------------------

TEXTS = {
    "tr": {
        "start": (
            "✨ DailyQuoteBot'a hoş geldin!\n\n"
            "Günün motivasyon sözlerini görmek için aşağıdaki butonları kullanabilirsin.\n\n"
            "• 'Yeni söz' ile sıradaki sözü aç\n"
            "• 'Ekstra söz (reklam)' ile gönüllü reklam sonrası bonus söz al\n"
            "• 'Web App' ile premium arayüze (varsa) geçiş yap\n\n"
            "Hazırsan başlıyoruz 👇"
        ),
        "help": (
            "📚 DailyQuoteBot yardım\n\n"
            "/start - Botu başlat / menüyü göster\n"
            "/quote - Yeni bir söz gönder\n"
            "/stats - Bugünkü söz ve reklam istatistiklerini göster\n"
            "/invite - Davet linkini al (referral)\n\n"
            "Alt taraftaki butonlarla da aynı işlemleri yapabilirsin."
        ),
        "btn_new": "🔁 Yeni söz",
        "btn_extra": "🎁 Ekstra söz (reklam)",
        "btn_webapp": "🌐 Web App",
        "quote_prefix": "Bugünün sözü:",
        "extra_thanks": "Reklam görevini tamamladığın için teşekkürler 🙌 İşte ekstra sözün:",
        "no_quote": "Şu an için gösterecek söz bulamadım.",
        "ad_label": "Reklam",
        "ad_error": "Şu anda reklam gösterilemiyor, lütfen daha sonra tekrar dene.",
        "stats": (
            "📊 Bugünkü istatistiklerin:\n\n"
            "Söz sayısı: {quotes}\n"
            "Gösterilen reklam sayısı: {ads}\n"
            "Bugün davet ettiğin yeni kullanıcı: {refs}\n"
        ),
        "fallback": (
            "DailyQuoteBot'u kullanmak için aşağıdaki butonlardan birini seçebilirsin 👇"
        ),
        "invite_text": "Arkadaşlarını davet etmek için linkin:\n{link}\n\nŞu ana kadar toplam {count} kullanıcı seni referans alarak geldi.",
        "ref_thanks": "Bu botu bir arkadaşının davetiyle kullanmaya başladın ❤️",
    },
    "en": {
        "start": (
            "✨ Welcome to DailyQuoteBot!\n\n"
            "Use the buttons below to get your daily motivational quotes.\n\n"
            "• 'New quote' to get the next quote\n"
            "• 'Extra quote (ad)' to optionally watch an ad and get a bonus quote\n"
            "• 'Web App' to switch to the premium interface (if available)\n\n"
            "Let's begin 👇"
        ),
        "help": (
            "📚 DailyQuoteBot help\n\n"
            "/start - Show menu / welcome message\n"
            "/quote - Send a new quote\n"
            "/stats - Show today's quote & ad stats\n"
            "/invite - Get your invite link (referral)\n\n"
            "You can also use the buttons below the messages."
        ),
        "btn_new": "🔁 New quote",
        "btn_extra": "🎁 Extra quote (ad)",
        "btn_webapp": "🌐 Web App",
        "quote_prefix": "Today's quote:",
        "extra_thanks": "Thanks for completing the ad task 🙌 Here is your extra quote:",
        "no_quote": "I don't have a quote to show right now.",
        "ad_label": "Ad",
        "ad_error": "Ad is not available right now, please try again later.",
        "stats": (
            "📊 Your stats for today:\n\n"
            "Quotes: {quotes}\n"
            "Ads shown: {ads}\n"
            "New users referred today: {refs}\n"
        ),
        "fallback": (
            "You can use the buttons below to get quotes 👇"
        ),
        "invite_text": "Here is your invite link:\n{link}\n\nSo far {count} users joined via your referral.",
        "ref_thanks": "You joined this bot via your friend's invite ❤️",
    },
}

# ---------------------------------------------------------------------
# KULLANICI STATE: SAYAÇ + REFERRAL
# ---------------------------------------------------------------------

# {user_id: {"day": date, "quotes": int, "ads": int, "refs_today": int}}
USER_STATS = {}

# Referral ilişkileri
# {user_id: referrer_id}
REFERRED_BY = {}
# {referrer_id: set(user_ids)}
REFERRALS = {}


def get_lang(update: Update) -> str:
    """Telegram language_code'a göre 'tr' veya 'en' döner."""
    user = update.effective_user
    code = (user.language_code or "").lower() if user else ""
    if code.startswith("tr"):
        return "tr"
    return "en"


def ensure_user_stats(user_id: int) -> dict:
    """Kullanıcı için bugüne ait sayaçları hazırla."""
    today = date.today()
    stats = USER_STATS.get(user_id)
    if not stats or stats.get("day") != today:
        stats = {"day": today, "quotes": 0, "ads": 0, "refs_today": 0}
        USER_STATS[user_id] = stats
    return stats


def get_random_quote(lang: str) -> str:
    """Dil için rastgele bir söz döner."""
    pool = QUOTES.get(lang) or QUOTES["en"]
    if not pool:
        return ""
    return random.choice(pool)


# ---------------------------------------------------------------------
# GÖRSEL QUOTE KARTI (PIL)
# ---------------------------------------------------------------------

def render_quote_image(quote: str, lang: str) -> BytesIO:
    """
    Söz için basit bir siyah+altın temalı görsel üretir.
    """
    width, height = 800, 800
    bg_color = (0, 0, 0)
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Altın daire / vurgu
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

    # Üstte tırnak işareti
    mark_text = "❝"
    try:
        font_mark = ImageFont.truetype("arial.ttf", 80)
    except Exception:
        font_mark = ImageFont.load_default()
    draw.text((width // 2 - 25, 80), mark_text, fill=gold, font=font_mark)

    # Quote metni
    try:
        font_quote = ImageFont.truetype("arial.ttf", 32)
    except Exception:
        font_quote = ImageFont.load_default()

    # Basit satır kaydırma
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
        w_width, w_height = draw.textsize(line, font=font_quote)
        x = (width - w_width) // 2
        y = start_y + i * 40
        draw.text((x, y), line, fill=(229, 229, 229), font=font_quote)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


async def send_quote_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    quote: str,
    lang: str,
    extra_prefix: str | None = None,
) -> None:
    """Sözü görsel kart olarak gönderir, altına butonları koyar."""
    kb = build_main_keyboard(lang)
    img_bytes = render_quote_image(quote, lang)

    caption = None
    if extra_prefix:
        caption = extra_prefix

    if update.message:
        await update.message.reply_photo(
            photo=img_bytes,
            caption=caption,
            reply_markup=kb,
        )
    elif update.callback_query:
        await update.callback_query.message.reply_photo(
            photo=img_bytes,
            caption=caption,
            reply_markup=kb,
        )
    else:
        chat_id = update.effective_chat.id
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=img_bytes,
            caption=caption,
            reply_markup=kb,
        )


# ---------------------------------------------------------------------
# ADSGRAM ENTEGRASYONU
# ---------------------------------------------------------------------

async def send_adsgram_ad(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lang: str,
    user_id: int,
) -> None:
    """
    AdsGram Bot Monetization API:
    GET https://api.adsgram.ai/advbot?tgid={TELEGRAM_USER_ID}&blockid={BLOCK_ID}&language={lang}
    Dönen veriyi HTML + buton ile gönderir. :contentReference[oaicite:0]{index=0}
    """
    stats = ensure_user_stats(user_id)
    if stats["ads"] >= MAX_ADS_PER_DAY:
        return  # günlük limit doluysa sessizce çık

    params = {
        "tgid": user_id,
        "blockid": ADSGRAM_BLOCK_ID,  # numeric, 'bot-' prefixsiz
        "language": "tr" if lang == "tr" else "en",
    }

    try:
        resp = requests.get("https://api.adsgram.ai/advbot", params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"AdsGram error: {e}")
        t = TEXTS[lang]
        # Hata varsa kullanıcıyı boğmadan basit mesaj
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
        buttons.append(
            [InlineKeyboardButton(button_name, url=click_url)]
        )
    if button_reward_name and reward_url:
        buttons.append(
            [InlineKeyboardButton(button_reward_name, url=reward_url)]
        )

    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

    # Reklam forward edilemesin diye protect_content=True kullanıyoruz. :contentReference[oaicite:1]{index=1}
    if image_url:
        # Fotoğraf + HTML caption
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
        # Sadece HTML text
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
# REFERRAL SİSTEMİ
# ---------------------------------------------------------------------

def handle_referral(user_id: int, args: list[str], lang: str) -> str | None:
    """
    /start ref_123 şeklinde gelen daveti işler.
    """
    if not args:
        return None

    first = args[0]
    if not first.startswith("ref_"):
        return None

    try:
        referrer_id = int(first.replace("ref_", ""))
    except ValueError:
        return None

    if referrer_id == user_id:
        return None

    # Kullanıcı daha önce refer edildi ise tekrar yazma
    if user_id in REFERRED_BY:
        return None

    REFERRED_BY[user_id] = referrer_id
    if referrer_id not in REFERRALS:
        REFERRALS[referrer_id] = set()
    REFERRALS[referrer_id].add(user_id)

    # Günlük referral sayaçları
    stats = ensure_user_stats(referrer_id)
    stats["refs_today"] += 1

    t = TEXTS[lang]
    return t["ref_thanks"]


def build_invite_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref_{user_id}"


# ---------------------------------------------------------------------
# KLAVYE
# ---------------------------------------------------------------------

def build_main_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Ana inline keyboard (yeni söz + ekstra söz + webapp)."""
    t = TEXTS[lang]
    buttons = [
        [InlineKeyboardButton(t["btn_new"], callback_data="new_quote")],
        [InlineKeyboardButton(t["btn_extra"], callback_data="extra_quote")],
    ]
    if WEBAPP_URL:
        buttons.append(
            [
                InlineKeyboardButton(
                    t["btn_webapp"],
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ]
        )
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------
# HANDLER'LAR
# ---------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    t = TEXTS[lang]
    user = update.effective_user
    user_id = user.id if user else 0

    # Referral kontrolü
    ref_msg = handle_referral(user_id, context.args, lang)

    kb = build_main_keyboard(lang)
    text = t["start"]
    if ref_msg:
        text = ref_msg + "\n\n" + text

    await update.message.reply_text(text, reply_markup=kb)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = get_lang(update)
    t = TEXTS[lang]
    kb = build_main_keyboard(lang)
    await update.message.reply_text(t["help"], reply_markup=kb)


async def send_quote_logic(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    extra: bool = False,
) -> None:
    """
    Hem normal quote hem ekstra quote mantığı burada.
    extra=True ise 'reklam sonrası ekstra söz' mesajı ekler.
    """
    lang = get_lang(update)
    t = TEXTS[lang]

    user = update.effective_user
    user_id = user.id if user else 0
    stats = ensure_user_stats(user_id)

    quote = get_random_quote(lang)
    if not quote:
        msg = t["no_quote"]
        kb = build_main_keyboard(lang)
        if update.message:
            await update.message.reply_text(msg, reply_markup=kb)
        elif update.callback_query:
            await update.callback_query.message.reply_text(msg, reply_markup=kb)
        else:
            chat_id = update.effective_chat.id
            await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=kb)
        return

    extra_prefix = t["extra_thanks"] if extra else None
    await send_quote_image(update, context, quote, lang, extra_prefix=extra_prefix)

    # Sayaç güncelle
    stats["quotes"] += 1

    # Otomatik reklam tetikleme (her AD_FREQUENCY sözde)
    if not extra:
        if stats["quotes"] % AD_FREQUENCY == 0 and stats["ads"] < MAX_ADS_PER_DAY:
            await send_adsgram_ad(update, context, lang, user_id)


async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ /quote komutu -> yeni söz """
    await send_quote_logic(update, context, extra=False)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Bugünkü istatistikleri göster. """
    lang = get_lang(update)
    t = TEXTS[lang]
    user = update.effective_user
    user_id = user.id if user else 0
    stats = ensure_user_stats(user_id)

    # Referral toplamı
    total_refs = len(REFERRALS.get(user_id, set()))
    text = t["stats"].format(
        quotes=stats["quotes"],
        ads=stats["ads"],
        refs=stats["refs_today"],
    )
    text += f"\nToplam referanslı kullanıcı sayın: {total_refs}" if lang == "tr" else f"\nTotal users referred so far: {total_refs}"

    kb = build_main_keyboard(lang)
    await update.message.reply_text(text, reply_markup=kb)


async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kullanıcıya davet linki gönderir."""
    lang = get_lang(update)
    t = TEXTS[lang]
    user = update.effective_user
    user_id = user.id if user else 0

    bot_username = context.bot.username
    link = build_invite_link(bot_username, user_id)
    total_refs = len(REFERRALS.get(user_id, set()))

    msg = t["invite_text"].format(link=link, count=total_refs)
    kb = build_main_keyboard(lang)
    await update.message.reply_text(msg, reply_markup=kb)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inline keyboard callback handler."""
    query = update.callback_query
    data = query.data
    lang = get_lang(update)

    if data == "new_quote":
        await send_quote_logic(update, context, extra=False)
    elif data == "extra_quote":
        user = update.effective_user
        user_id = user.id if user else 0
        # 1) Reklam (AdsGram entegrasyonu)
        await send_adsgram_ad(update, context, lang, user_id)
        # 2) Reklam sonrası ekstra söz
        await send_quote_logic(update, context, extra=True)
    else:
        await query.answer()


async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Kullanıcı rastgele bir şey yazarsa:
    - Ana butonları tekrar göster
    - Kullanıcıya nasıl kullanacağını hatırlat
    """
    lang = get_lang(update)
    t = TEXTS[lang]
    kb = build_main_keyboard(lang)
    await update.message.reply_text(t["fallback"], reply_markup=kb)


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable set edilmemiş. "
            "Örn: export BOT_TOKEN='123456:ABC-DEF'"
        )

    application = Application.builder().token(BOT_TOKEN).build()

    # Komutlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("quote", quote_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("invite", invite_command))

    # Inline buton callback
    application.add_handler(CallbackQueryHandler(button_callback))

    # Diğer tüm metinlere fallback
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text))

    logger.info("DailyQuoteBot (message bot + AdsGram + referral) is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
