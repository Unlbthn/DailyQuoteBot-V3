import random
import datetime
import logging
import sqlite3
import urllib.parse
from typing import Optional, Tuple, Dict

import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    Application,
)
from telegram.error import BadRequest

from quotes import SOZLER, normalize_author

# --------------------------------
# AYARLAR
# --------------------------------

# KENDI TOKEN'INI BURAYA YAZ
BOT_TOKEN = "8515430219:AAHH3d2W7Ao4ao-ARwHMonRxZY5MnOyHz9k"

# AdsGram
ADSGRAM_BLOCK_ID = 17933  # sen kendi block ID'ni buraya yazdınsa dokunma

# Admin
ADMIN_ID = 5664983086

# Bot kullanıcı adı (paylaşım linkleri için)
BOT_USERNAME = "QuoteMastersBot"  # örn: t.me/QuoteMastersBot

# DB dosyası
DB_PATH = "daily_quote_bot.db"

# --------------------------------
# LOGGING
# --------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --------------------------------
# GLOBAL DURUMLAR (RAM)
# --------------------------------
USER_LANG: Dict[int, str] = {}  # user_id -> "tr" / "en"
USER_LAST_CATEGORY: Dict[int, str] = {}  # kullanıcı en son hangi kategoriden söz aldı

# Kullanıcıya gösterilen SON sözü saklıyoruz:
# user_id -> (category, quote_text, author)
LAST_SHOWN: Dict[int, Tuple[str, str, str]] = {}


# --------------------------------
# DB YARDIMCILAR
# --------------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            lang        TEXT,
            created_at  TEXT,
            last_seen   TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS favorites (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            category    TEXT,
            lang        TEXT,
            text        TEXT,
            author      TEXT,
            created_at  TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS suggestions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            category    TEXT,
            lang        TEXT,
            text        TEXT,
            author      TEXT,
            created_at  TEXT
        )
        """
    )

    conn.commit()
    conn.close()


def upsert_user(user_id: int, lang: Optional[str] = None):
    """
    Her /start, /random, /today vs çağrısında user kaydı güncellenir.
    Tüm user_id'ler kalıcı olarak DB'de tutuluyor.
    """
    now = datetime.datetime.utcnow().isoformat()
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()

    if row:
        if lang:
            cur.execute(
                "UPDATE users SET lang = ?, last_seen = ? WHERE user_id = ?",
                (lang, now, user_id),
            )
        else:
            cur.execute(
                "UPDATE users SET last_seen = ? WHERE user_id = ?",
                (now, user_id),
            )
    else:
        cur.execute(
            "INSERT INTO users (user_id, lang, created_at, last_seen) VALUES (?, ?, ?, ?)",
            (user_id, lang or "tr", now, now),
        )

    conn.commit()
    conn.close()


def get_user_lang_from_db(user_id: int) -> str:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row and row["lang"]:
        return row["lang"]
    return "tr"


def add_favorite(
    user_id: int, category: str, lang: str, text: str, author: str
) -> None:
    now = datetime.datetime.utcnow().isoformat()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO favorites (user_id, category, lang, text, author, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, category, lang, text, author, now),
    )
    conn.commit()
    conn.close()


def get_favorites(user_id: int, limit: int = 50):
    """
    Tüm dillerdeki favorileri birlikte getiriyoruz (TR+EN karışık).
    DB'de hiçbir favori silinmez, sadece burada max limit kadar gösteriyoruz.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, category, lang, text, author, created_at
        FROM favorites
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_favorite(fav_id: int, user_id: int) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM favorites WHERE id = ? AND user_id = ?",
        (fav_id, user_id),
    )
    conn.commit()
    conn.close()


def add_suggestion(
    user_id: int, category: str, lang: str, text: str, author: str
) -> None:
    now = datetime.datetime.utcnow().isoformat()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO suggestions (user_id, category, lang, text, author, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, category, lang, text, author, now),
    )
    conn.commit()
    conn.close()


# --------------------------------
# AdsGram yardımcı: veri çek (JSON döner ya da None)
# --------------------------------
def fetch_adsgram_data(user_id: int, lang_param: Optional[str]) -> Optional[dict]:
    """
    Belirli bir language parametresiyle AdsGram'dan reklam çekmeyi dener.
    Uygun reklam yoksa veya yanıt JSON değilse None döner.
    """
    try:
        params = {
            "tgid": str(user_id),
            "blockid": str(ADSGRAM_BLOCK_ID),
        }
        if lang_param:
            params["language"] = lang_param

        resp = requests.get(
            "https://api.adsgram.ai/advbot",
            params=params,
            timeout=3,
        )

        logger.info(
            "AdsGram request user=%s lang=%s status=%s",
            user_id,
            lang_param,
            resp.status_code,
        )
        logger.info("AdsGram response (ilk 200 char): %s", resp.text[:200])

        if resp.status_code != 200:
            return None

        raw = resp.text.strip()
        if not raw.startswith("{"):
            # Reklam yoksa bazen düz metin dönebiliyor
            return None

        data = resp.json()
        return data

    except Exception as e:
        logger.warning("AdsGram hata (lang=%s): %s", lang_param, e)
        return None


# --------------------------------
# AdsGram: reklam mesajı gönder (KOMPAKT + TR→EN FALLBACK)
# --------------------------------
async def send_adsgram_ad(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
    lang: Optional[str] = None,
):
    """
    Önce kullanıcının diline göre reklam çekmeye çalışır.
    - lang == 'tr' ise: önce TR dener, reklam yoksa EN'e düşer.
    - lang == 'en' ise: direkt EN dener.
    - Diğer durumlarda: language parametresi olmadan dener.
    Reklam varsa küçük bir "Sponsored" metni olarak gönderir (görsel YOK).
    """
    data: Optional[dict] = None

    if lang == "tr":
        # 1) Önce TR dene
        data = fetch_adsgram_data(user_id, "tr")
        # 2) Reklam yoksa EN'e fallback
        if data is None:
            data = fetch_adsgram_data(user_id, "en")
    elif lang == "en":
        data = fetch_adsgram_data(user_id, "en")
    else:
        data = fetch_adsgram_data(user_id, None)

    if data is None:
        return

    text_html = data.get("text_html") or ""
    click_url = data.get("click_url")
    button_name = data.get("button_name")
    reward_name = data.get("button_reward_name")
    reward_url = data.get("reward_url")

    # image_url'u BİLEREK kullanmıyoruz -> büyük görsel yok
    # image_url = data.get("image_url")

    # Hem text yok hem de tıklanacak buton yoksa hiç göndermeyelim
    if not text_html and not (button_name and click_url):
        return

    buttons = []
    if button_name and click_url:
        buttons.append([InlineKeyboardButton(button_name, url=click_url)])
    if reward_name and reward_url:
        buttons.append([InlineKeyboardButton(reward_name, url=reward_url)])

    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

    full_text = "Sponsored\n\n" + text_html

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=full_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            protect_content=True,
        )
    except Exception as e:
        logger.warning("AdsGram send_message hata: %s", e)


# --------------------------------
# Yardımcılar – dil, kategori, metin, buton
# --------------------------------
def get_user_lang(user_id: int) -> str:
    if user_id in USER_LANG:
        return USER_LANG[user_id]
    lang = get_user_lang_from_db(user_id)
    USER_LANG[user_id] = lang
    return lang


def set_user_lang(user_id: int, lang: str):
    USER_LANG[user_id] = lang
    upsert_user(user_id, lang)


def build_category_keyboard(lang: str) -> InlineKeyboardMarkup:
    buttons = []
    for key, data in SOZLER.items():
        if lang == "en":
            label = data.get("label_en", data.get("label_tr", key.title()))
        else:
            label = data.get("label_tr", data.get("label_en", key.title()))
        buttons.append([InlineKeyboardButton(label, callback_data=f"cat_{key}")])
    return InlineKeyboardMarkup(buttons)


def build_main_menu_text(lang: str) -> str:
    if lang == "en":
        return (
            "Daily Quote Bot\n\n"
            "Commands:\n"
            "/random   - Random quote\n\n"
            "/today    - Quote of the day\n\n"
            "/favorites - Your favorite quotes\n\n"
            "/settings  - Adjust your preferences\n"
        )
    else:
        return (
            "Daily Quote Bot\n\n"
            "Komutlar:\n"
            "/random   - Rastgele bir söz\n\n"
            "/today    - Bugünün sözü\n\n"
            "/favorites - Favori sözlerin\n\n"
            "/settings  - Ayarlarını düzenle\n"
        )


def build_main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    topic_btn = "Choose Topic" if lang == "en" else "Konu Seç"
    buttons = [[InlineKeyboardButton(topic_btn, callback_data="choose_topic")]]
    return InlineKeyboardMarkup(buttons)


def choose_random_quote(category: str, lang: str) -> Tuple[str, str]:
    """
    Seçilen kategoriden ve dilden bir söz (metin, yazar) döndürür.
    yazar boş string olabilir -> ekranda hiç gösterilmeyecek.
    """
    if category not in SOZLER:
        category = "motivation"

    data = SOZLER[category]
    if lang == "en":
        lst = data.get("en", [])
        if not lst:
            lst = data.get("tr", [])
            if not lst:
                return "", ""
            metin_tr, author = random.choice(lst)
            return metin_tr, normalize_author(author)
        metin_en, _metin_tr, author = random.choice(lst)
        return metin_en, normalize_author(author)
    else:
        lst = data.get("tr", [])
        if not lst:
            lst = data.get("en", [])
            if not lst:
                return "", ""
            metin_en, _metin_tr, author = random.choice(lst)
            return metin_en, normalize_author(author)
        metin_tr, author = random.choice(lst)
        return metin_tr, normalize_author(author)


def build_share_text(quote_text: str, author: str, lang: str) -> str:
    bot_link = f"https://t.me/{BOT_USERNAME}"

    if lang == "en":
        base = "Quote of the Day:\n\n" + quote_text
        if author:
            base += f"\n\n— {author}"
        base += f"\n\nDiscover more quotes at {bot_link}"
    else:
        base = "Günün Sözü:\n\n" + quote_text
        if author:
            base += f"\n\n— {author}"
        base += f"\n\nDaha fazla söz için: {bot_link}"
    return base


def build_share_keyboard(
    category: str, quote_text: str, author: str, lang: str
) -> InlineKeyboardMarkup:
    if lang == "en":
        fav_txt = "⭐ Add to Favorites"
        change_txt = "Change 🔄"
        back_txt = "⬅ Choose Topic"
        share_tg_txt = "📤 Share on Telegram"
        share_wa_txt = "📲 Share on WhatsApp"
    else:
        fav_txt = "⭐ Favorilere Ekle"
        change_txt = "Değiştir 🔄"
        back_txt = "⬅ Konu Seç"
        share_tg_txt = "📤 Telegram'da Paylaş"
        share_wa_txt = "📲 WhatsApp'ta Paylaş"

    full_share = build_share_text(quote_text, author, lang)
    encoded = urllib.parse.quote_plus(full_share)

    bot_link = f"https://t.me/{BOT_USERNAME}"
    telegram_share_url = f"https://t.me/share/url?url={urllib.parse.quote_plus(bot_link)}&text={encoded}"
    whatsapp_share_url = f"https://wa.me/?text={encoded}"

    buttons = [
        [
            InlineKeyboardButton(
                fav_txt,
                callback_data=f"fav|{category}",
            )
        ],
        [
            InlineKeyboardButton(share_tg_txt, url=telegram_share_url),
        ],
        [
            InlineKeyboardButton(share_wa_txt, url=whatsapp_share_url),
        ],
        [
            InlineKeyboardButton(change_txt, callback_data=f"change_{category}"),
        ],
        [
            InlineKeyboardButton(back_txt, callback_data="choose_topic"),
        ],
    ]

    return InlineKeyboardMarkup(buttons)


# --------------------------------
# Bugünün sözü
# --------------------------------
def build_today_quote_text(user_id: int) -> Tuple[str, str, str]:
    """
    (text, author, category_key) döndürür.
    """
    lang = get_user_lang(user_id)
    category = "motivation"

    today_ordinal = datetime.date.today().toordinal()
    data = SOZLER.get(category, {})

    if lang == "en":
        lst = data.get("en", [])
        if not lst:
            lst = data.get("tr", [])
            if not lst:
                return "", "", category
            idx = today_ordinal % len(lst)
            metin_tr, author = lst[idx]
            return metin_tr, normalize_author(author), category
        idx = today_ordinal % len(lst)
        metin_en, _metin_tr, author = lst[idx]
        return metin_en, normalize_author(author), category
    else:
        lst = data.get("tr", [])
        if not lst:
            lst = data.get("en", [])
            if not lst:
                return "", "", category
            idx = today_ordinal % len(lst)
            metin_en, _metin_tr, author = lst[idx]
            return metin_en, normalize_author(author), category
        idx = today_ordinal % len(lst)
        metin_tr, author = lst[idx]
        return metin_tr, normalize_author(author), category


# --------------------------------
# /start
# --------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    upsert_user(user_id)

    keyboard = [
        [
            InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        ]
    ]
    text = (
        "Daily Quote Bot\n\n"
        "Lütfen dili seç:\n\n"
        "Please choose your language:"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# --------------------------------
# Dil seçimi callback
# --------------------------------
async def dil_sec(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest:
        pass

    user_id = query.from_user.id
    set_user_lang(user_id, lang)

    text = build_main_menu_text(lang)
    keyboard = build_main_menu_keyboard(lang)

    try:
        await query.edit_message_text(text, reply_markup=keyboard)
    except BadRequest as e:
        logger.warning("dil_sec edit_message_text hatası: %s", e)


# --------------------------------
# Konu seç ekranı
# --------------------------------
async def choose_topic_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    lang = get_user_lang(user_id)

    try:
        await query.answer()
    except BadRequest:
        pass

    text = "Choose a topic:" if lang == "en" else "Bir konu başlığı seç:"
    keyboard = build_category_keyboard(lang)

    try:
        await query.edit_message_text(text, reply_markup=keyboard)
    except BadRequest as e:
        logger.warning("choose_topic edit hata: %s", e)


# --------------------------------
# Seçilen kategoriden söz getir
# --------------------------------
async def send_quote_for_category(
    update: Update, context: ContextTypes.DEFAULT_TYPE, category: str
):
    query = update.callback_query
    user_id = query.from_user.id
    lang = get_user_lang(user_id)

    try:
        await query.answer()
    except BadRequest:
        pass

    quote_text, author = choose_random_quote(category, lang)
    if not quote_text:
        msg = (
            "Bu kategori için söz bulunamadı."
            if lang == "tr"
            else "No quote found for this category."
        )
        try:
            await query.edit_message_text(msg)
        except BadRequest:
            pass
        return

    USER_LAST_CATEGORY[user_id] = category
    LAST_SHOWN[user_id] = (category, quote_text, author)

    if lang == "en":
        prefix = "Quote of the Day:\n\n"
    else:
        prefix = "Günün Sözü:\n\n"

    if author:
        full_text = f"{prefix}{quote_text}\n\n— {author}"
    else:
        full_text = f"{prefix}{quote_text}"

    keyboard = build_share_keyboard(category, quote_text, author, lang)

    try:
        await query.edit_message_text(full_text, reply_markup=keyboard)
    except BadRequest as e:
        logger.warning("send_quote_for_category edit hata: %s", e)

    await send_adsgram_ad(
        context=context,
        chat_id=query.message.chat_id,
        user_id=user_id,
        lang=lang,
    )


# --------------------------------
# /random – rastgele söz
# --------------------------------
async def random_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    upsert_user(user_id)

    category = random.choice(list(SOZLER.keys()))
    USER_LAST_CATEGORY[user_id] = category

    quote_text, author = choose_random_quote(category, lang)
    if not quote_text:
        if update.message:
            await update.message.reply_text(
                "Şu anda söz bulunamadı."
                if lang == "tr"
                else "No quote available right now."
            )
        return

    LAST_SHOWN[user_id] = (category, quote_text, author)

    if lang == "en":
        prefix = f"Random Quote ({SOZLER[category]['label_en']}):\n\n"
    else:
        prefix = f"Rastgele Söz ({SOZLER[category]['label_tr']}):\n\n"

    if author:
        full_text = f"{prefix}{quote_text}\n\n— {author}"
    else:
        full_text = f"{prefix}{quote_text}"

    if update.message:
        keyboard = build_share_keyboard(category, quote_text, author, lang)
        await update.message.reply_text(full_text, reply_markup=keyboard)

        await send_adsgram_ad(
            context=context,
            chat_id=update.effective_chat.id,
            user_id=user_id,
            lang=lang,
        )


# --------------------------------
# /today – bugünün sözü
# --------------------------------
async def today_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    upsert_user(user_id)

    quote_text, author, category = build_today_quote_text(user_id)
    if not quote_text:
        if update.message:
            await update.message.reply_text(
                "Bugünün sözü bulunamadı."
                if lang == "tr"
                else "Could not find today's quote."
            )
        return

    USER_LAST_CATEGORY[user_id] = category
    LAST_SHOWN[user_id] = (category, quote_text, author)

    if lang == "en":
        prefix = "Quote of the Day:\n\n"
    else:
        prefix = "Bugünün Sözü:\n\n"

    if author:
        full_text = f"{prefix}{quote_text}\n\n— {author}"
    else:
        full_text = f"{prefix}{quote_text}"

    if update.message:
        keyboard = build_share_keyboard(category, quote_text, author, lang)
        await update.message.reply_text(full_text, reply_markup=keyboard)

        await send_adsgram_ad(
            context=context,
            chat_id=update.effective_chat.id,
            user_id=user_id,
            lang=lang,
        )


# --------------------------------
# Günlük 10:00 job – tüm kullanıcılara bugünün sözü
# --------------------------------
async def send_daily_quote(context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, lang FROM users")
    rows = cur.fetchall()
    conn.close()

    for row in rows:
        user_id = row["user_id"]
        lang = row["lang"] or "tr"
        try:
            quote_text, author, category = build_today_quote_text(user_id)
            if not quote_text:
                continue

            USER_LAST_CATEGORY[user_id] = category
            LAST_SHOWN[user_id] = (category, quote_text, author)

            if lang == "en":
                prefix = "Quote of the Day:\n\n"
            else:
                prefix = "Bugünün Sözü:\n\n"

            if author:
                full_text = f"{prefix}{quote_text}\n\n— {author}"
            else:
                full_text = f"{prefix}{quote_text}"

            msg = await context.bot.send_message(chat_id=user_id, text=full_text)
            await send_adsgram_ad(
                context=context,
                chat_id=msg.chat_id,
                user_id=user_id,
                lang=lang,
            )
        except Exception as e:
            logger.warning("daily_quote hata (user %s): %s", user_id, e)
            continue


# --------------------------------
# /favorites – favoriler + silme butonu
# --------------------------------
async def favorites_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    rows = get_favorites(user_id, limit=50)  # TR+EN birlikte, son 50

    if not rows:
        msg = (
            "Henüz favori sözün yok.\n\n"
            "Beğendiğin sözlerin altındaki ⭐ butonuna basarak favorilere ekleyebilirsin."
            if lang == "tr"
            else "You don’t have any favorite quotes yet.\n\nUse the ⭐ button under a quote to save it."
        )
        if update.message:
            await update.message.reply_text(msg)
        return

    if lang == "tr":
        header = "Favori sözlerin (en fazla 50 adet gösteriliyor):\n"
    else:
        header = "Your favorite quotes (showing up to 50):\n"

    if update.message:
        await update.message.reply_text(header)

        for r in rows:
            fav_id = r["id"]
            text = r["text"]
            author = normalize_author(r["author"])

            if author:
                body = f"{text}\n\n— {author}"
            else:
                body = text

            if lang == "tr":
                btn_text = "❌ Favorilerden Çıkar"
            else:
                btn_text = "❌ Remove from Favorites"

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            btn_text,
                            callback_data=f"favdel|{fav_id}",
                        )
                    ]
                ]
            )

            await update.message.reply_text(body, reply_markup=keyboard)


# --------------------------------
# /settings – dil ayarları
# --------------------------------
async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)

    if lang == "en":
        text = (
            "Settings:\n\n"
            "• Language: English\n\n"
            "You can switch language from the button below."
        )
        keyboard = [
            [
                InlineKeyboardButton("🇹🇷 Switch to Turkish", callback_data="lang_tr"),
            ]
        ]
    else:
        text = (
            "Ayarlar:\n\n"
            "• Dil: Türkçe\n\n"
            "Dili aşağıdaki butondan değiştirebilirsin."
        )
        keyboard = [
            [
                InlineKeyboardButton("🇬🇧 İngilizceye Geç", callback_data="lang_en"),
            ]
        ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# --------------------------------
# /suggest – söz önerisi
# /suggest kategori | söz | yazar
# --------------------------------
async def suggest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)

    if not update.message or not update.message.text:
        return

    parts = update.message.text.split(" ", 1)
    if len(parts) < 2:
        if lang == "en":
            msg = "Usage: /suggest category | quote | author(optional)"
        else:
            msg = "Kullanım: /suggest kategori | söz | yazar (opsiyonel)"
        await update.message.reply_text(msg)
        return

    payload = parts[1]
    fields = [f.strip() for f in payload.split("|")]
    if len(fields) < 2:
        if lang == "en":
            msg = "Usage: /suggest category | quote | author(optional)"
        else:
            msg = "Kullanım: /suggest kategori | söz | yazar (opsiyonel)"
        await update.message.reply_text(msg)
        return

    category_key = fields[0].lower()
    text = fields[1]
    author = fields[2] if len(fields) >= 3 else ""

    add_suggestion(user_id, category_key, lang, text, author)

    if lang == "en":
        await update.message.reply_text("Thanks! Your suggestion has been saved.")
    else:
        await update.message.reply_text("Teşekkürler! Önerin kaydedildi.")


# --------------------------------
# /stats – admin mini istatistik
# --------------------------------
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM users")
    total_users = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM favorites")
    total_favs = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) AS c FROM suggestions")
    total_sugg = cur.fetchone()["c"]
    conn.close()

    msg = (
        f"Users: {total_users}\n"
        f"Favorites: {total_favs}\n"
        f"Suggestions: {total_sugg}"
    )
    if update.message:
        await update.message.reply_text(msg)


# --------------------------------
# Callback router (butonlar)
# --------------------------------
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    lang = get_user_lang(user_id)

    # Dil değiştirme
    if data == "lang_tr":
        await dil_sec(update, context, "tr")
        return
    elif data == "lang_en":
        await dil_sec(update, context, "en")
        return

    # Konu seç ekranı
    if data == "choose_topic":
        await choose_topic_screen(update, context)
        return

    # Kategori seçimi
    if data.startswith("cat_"):
        category = data.replace("cat_", "")
        await send_quote_for_category(update, context, category)
        return

    # Değiştir butonu
    if data.startswith("change_"):
        category = data.replace("change_", "")
        await send_quote_for_category(update, context, category)
        return

    # Favoriye ekle (gösterilen SON sözü kaydediyoruz)
    if data.startswith("fav|"):
        _, category = data.split("|", 1)

        if user_id in LAST_SHOWN:
            last_cat, quote_text, author = LAST_SHOWN[user_id]
            real_category = last_cat or category
            add_favorite(user_id, real_category, lang, quote_text, author)

        try:
            await query.answer(
                "Favorilerine eklendi." if lang == "tr" else "Added to favorites.",
                show_alert=False,
            )
        except BadRequest:
            pass
        return

    # Favoriden çıkar
    if data.startswith("favdel|"):
        try:
            _, fav_id_str = data.split("|", 1)
            fav_id = int(fav_id_str)
        except Exception:
            try:
                await query.answer("Hata oluştu.", show_alert=True)
            except BadRequest:
                pass
            return

        delete_favorite(fav_id, user_id)

        msg_text = query.message.text or ""
        if lang == "tr":
            suffix = "\n\n(Favorilerden çıkarıldı)"
        else:
            suffix = "\n\n(Removed from favorites)"

        try:
            await query.edit_message_text(msg_text + suffix)
            await query.answer(
                "Favorilerden çıkarıldı."
                if lang == "tr"
                else "Removed from favorites.",
                show_alert=False,
            )
        except BadRequest:
            pass

        return


# --------------------------------
# Genel hata yakalayıcı
# --------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Hata yakalandı: %s", context.error)


# --------------------------------
# MAIN
# --------------------------------
def main():
    init_db()

    app: Application = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("random", random_cmd))
    app.add_handler(CommandHandler("today", today_cmd))
    app.add_handler(CommandHandler("favorites", favorites_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("suggest", suggest_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))

    app.add_handler(CallbackQueryHandler(callback_router))

    app.add_error_handler(error_handler)

    # Günlük 10:00 job (sunucu zamanına göre)
    if app.job_queue is not None:
        app.job_queue.run_daily(
            send_daily_quote,
            time=datetime.time(hour=10, minute=0),
        )
        print("JobQueue aktif: Günlük 10:00 gönderimi ayarlandı.")
    else:
        print("Uyarı: JobQueue yok, günlük 10:00 gönderimi kapalı.")

    print("DailyQuoteBot çalışıyor...")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
