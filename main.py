import random
import datetime
import logging
import sqlite3
import urllib.parse
import re
from typing import Optional, Tuple, Dict

import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
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

BOT_TOKEN = "8515430219:AAHH3d2W7Ao4ao-ARwHMonRxZY5MnOyHz9k"
ADSGRAM_BLOCK_ID = 17933
ADMIN_ID = 5664983086
BOT_USERNAME = "QuoteMastersBot"
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
USER_LANG: Dict[int, str] = {}          # user_id -> "tr" / "en"
USER_LAST_CATEGORY: Dict[int, str] = {}
LAST_SHOWN: Dict[int, Tuple[str, str, str]] = {}   # user_id -> (category, quote, author)


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
# AdsGram – metni temizleme + tek OPEN butonu
# --------------------------------
def fetch_adsgram_data(user_id: int, lang_param: Optional[str]) -> Optional[dict]:
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
            return None

        return resp.json()

    except Exception as e:
        logger.warning("AdsGram hata (lang=%s): %s", lang_param, e)
        return None


def html_to_plain(text_html: str) -> str:
    if not text_html:
        return ""
    text = text_html.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    max_len = 400
    if len(text) > max_len:
        text = text[: max_len - 3].rstrip() + "..."
    return text


def get_adsgram(user_id: int, lang: str) -> Tuple[Optional[str], Optional[str]]:
    data: Optional[dict] = None

    if lang == "tr":
        data = fetch_adsgram_data(user_id, "tr")
        if data is None:
            data = fetch_adsgram_data(user_id, "en")
    elif lang == "en":
        data = fetch_adsgram_data(user_id, "en")
    else:
        data = fetch_adsgram_data(user_id, None)

    if data is None:
        return None, None

    text_html = data.get("text_html") or ""
    click_url = data.get("click_url")

    ad_plain = html_to_plain(text_html)
    if not ad_plain and not click_url:
        return None, None

    return (ad_plain or None), (click_url or None)


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
    row = []
    for key, data in SOZLER.items():
        if lang == "en":
            label = data.get("label_en", data.get("label_tr", key.title()))
        else:
            label = data.get("label_tr", data.get("label_en", key.title()))

        row.append(InlineKeyboardButton(label, callback_data=f"cat_{key}"))

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(buttons)


def build_main_menu_text(lang: str) -> str:
    if lang == "en":
        return (
            "🌍 Daily Quote Bot\n\n"
            "Commands:\n"
            "/random   - Random quote\n\n"
            "/today    - Quote of the day\n\n"
            "/favorites - Your favorite quotes\n\n"
            "/settings  - Adjust your preferences\n"
        )
    else:
        return (
            "🌍 Daily Quote Bot\n\n"
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
        metin_en, _mt_tr, author = random.choice(lst)
        return metin_en, normalize_author(author)
    else:
        lst = data.get("tr", [])
        if not lst:
            lst = data.get("en", [])
            if not lst:
                return "", ""
            metin_en, _mt_tr, author = random.choice(lst)
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
    category: str,
    quote_text: str,
    author: str,
    lang: str,
    open_url: Optional[str],
    mode: str = "main",
) -> InlineKeyboardMarkup:
    buttons = []

    # Ana görünüm: sadece WhatsApp / Telegram / Menü
    if mode == "main":
        if lang == "en":
            wa_txt = "WhatsApp"
            tg_txt = "Telegram"
            menu_txt = "Menu"
        else:
            wa_txt = "WhatsApp"
            tg_txt = "Telegram"
            menu_txt = "Menü"

        full_share = build_share_text(quote_text, author, lang)
        encoded = urllib.parse.quote_plus(full_share)
        bot_link = f"https://t.me/{BOT_USERNAME}"

        telegram_share_url = (
            f"https://t.me/share/url?url={urllib.parse.quote_plus(bot_link)}&text={encoded}"
        )
        whatsapp_share_url = f"https://wa.me/?text={encoded}"

        buttons.append(
            [
                InlineKeyboardButton(wa_txt, url=whatsapp_share_url),
                InlineKeyboardButton(tg_txt, url=telegram_share_url),
                InlineKeyboardButton(menu_txt, callback_data=f"menu|{category}"),
            ]
        )

    # Menü görünümü: Favori / Değiştir / Konu / Favoriler / Ayarlar / Dil / Geri
    else:
        if lang == "en":
            fav_add = "Add to Favorites"
            change_q = "Change Quote"
            change_topic = "Change Topic"
            favs_txt = "Favorites"
            settings_txt = "Settings"
            lang_txt = "Change Language"
            back_txt = "Back"
        else:
            fav_add = "Favorilere Ekle"
            change_q = "Sözü Değiştir"
            change_topic = "Konuyu Değiştir"
            favs_txt = "Favoriler"
            settings_txt = "Ayarlar"
            lang_txt = "Dili Değiştir"
            back_txt = "Geri"

        buttons.append(
            [
                InlineKeyboardButton(fav_add, callback_data=f"fav|{category}"),
                InlineKeyboardButton(change_q, callback_data=f"change_{category}"),
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(change_topic, callback_data="choose_topic"),
                InlineKeyboardButton(favs_txt, callback_data="open_favs"),
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(settings_txt, callback_data="open_settings"),
                InlineKeyboardButton(lang_txt, callback_data="open_lang"),
            ]
        )
        buttons.append(
            [InlineKeyboardButton(back_txt, callback_data=f"backmenu|{category}")]
        )

    # Reklam OPEN
    if open_url:
        buttons.append([InlineKeyboardButton("OPEN", url=open_url)])

    return InlineKeyboardMarkup(buttons)


# --------------------------------
# Bugünün sözü (metin)
# --------------------------------
def build_today_quote_text(user_id: int) -> Tuple[str, str, str]:
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
        metin_en, _tr, author = lst[idx]
        return metin_en, normalize_author(author), category
    else:
        lst = data.get("tr", [])
        if not lst:
            lst = data.get("en", [])
            if not lst:
                return "", "", category
            idx = today_ordinal % len(lst)
            metin_en, _tr, author = lst[idx]
            return metin_en, normalize_author(author), category
        idx = today_ordinal % len(lst)
        metin_tr, author = lst[idx]
        return metin_tr, normalize_author(author), category


# --------------------------------
# Mesaj şablonu: üstte başlık + söz, altta reklam bloğu
# --------------------------------
def build_full_message_text(
    lang: str,
    quote_text: str,
    author: str,
    ad_text: Optional[str],
) -> str:
    if lang == "en":
        header = "Quote of the Day"
        share_line = "If you liked today’s quote, support us by sharing with a friend. 💜"
        ad_header = "Sponsored"
        ad_support = "You can support us by tapping the ad. 💫"
    else:
        header = "Günün Sözü"
        share_line = "Günün sözünü beğendiysen bize destek için bir arkadaşınla paylaş. 💜"
        ad_header = "Sponsored"
        ad_support = "Bize destek olmak için reklama tıklayabilirsin. 💫"

    lines = [
        header,
        "──────────",
        "",
        quote_text,
    ]

    if author:
        lines.append("")
        lines.append(f"— {author}")

    lines.append("")
    lines.append(share_line)
    lines.append("")

    if ad_text:
        lines.append(ad_header)
        lines.append("──────────")
        lines.append("")
        lines.append(ad_support)
        lines.append("")
        lines.append(ad_text)

    return "\n".join(lines)


# --------------------------------
# Favoriler ve Ayarlar için ortak yardımcılar
# --------------------------------
async def send_favorites_list(chat_id: int, user_id: int, lang: str, bot):
    rows = get_favorites(user_id, limit=50)

    if not rows:
        msg = (
            "Henüz favori sözün yok.\n\n"
            "Beğendiğin sözlerin altındaki menüden Favorilere Ekle seçeneğini kullanabilirsin."
            if lang == "tr"
            else "You don’t have any favorite quotes yet.\n\nUse the menu under a quote to add favorites."
        )
        await bot.send_message(chat_id=chat_id, text=msg)
        return

    header = (
        "Favori sözlerin (en fazla 50 adet gösteriliyor):\n"
        if lang == "tr"
        else "Your favorite quotes (showing up to 50):\n"
    )
    await bot.send_message(chat_id=chat_id, text=header)

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

        await bot.send_message(chat_id=chat_id, text=body, reply_markup=keyboard)


async def send_settings_panel(chat_id: int, user_id: int, lang: str, bot):
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

    await bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))


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
        "🌍 Daily Quote Bot\n\n"
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

    ad_text, open_url = get_adsgram(user_id, lang)
    full_text = build_full_message_text(lang, quote_text, author, ad_text)
    keyboard = build_share_keyboard(category, quote_text, author, lang, open_url, mode="main")

    try:
        await query.edit_message_text(
            full_text,
            reply_markup=keyboard,
        )
    except BadRequest as e:
        logger.warning("send_quote_for_category edit hata: %s", e)


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
    ad_text, open_url = get_adsgram(user_id, lang)
    full_text = build_full_message_text(lang, quote_text, author, ad_text)

    if update.message:
        keyboard = build_share_keyboard(category, quote_text, author, lang, open_url, mode="main")
        await update.message.reply_text(
            full_text,
            reply_markup=keyboard,
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
    ad_text, open_url = get_adsgram(user_id, lang)
    full_text = build_full_message_text(lang, quote_text, author, ad_text)

    if update.message:
        keyboard = build_share_keyboard(category, quote_text, author, lang, open_url, mode="main")
        await update.message.reply_text(
            full_text,
            reply_markup=keyboard,
        )


# --------------------------------
# Günlük 10:00 job – tüm kullanıcılara bugünün sözü (TR saatiyle 10)
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

            ad_text, open_url = get_adsgram(user_id, lang)
            full_text = build_full_message_text(lang, quote_text, author, ad_text)
            keyboard = build_share_keyboard(category, quote_text, author, lang, open_url, mode="main")

            await context.bot.send_message(
                chat_id=user_id,
                text=full_text,
                reply_markup=keyboard,
            )
        except Exception as e:
            logger.warning("daily_quote hata (user %s): %s", user_id, e)
            continue


# --------------------------------
# /favorites – favoriler + silme
# --------------------------------
async def favorites_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if update.message:
        await send_favorites_list(
            chat_id=update.message.chat_id,
            user_id=user_id,
            lang=lang,
            bot=context.bot,
        )


# --------------------------------
# /settings – dil ayarları
# --------------------------------
async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    if update.message:
        await send_settings_panel(
            chat_id=update.message.chat_id,
            user_id=user_id,
            lang=lang,
            bot=context.bot,
        )


# --------------------------------
# /suggest – söz önerisi
# --------------------------------
async def suggest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)

    if not update.message or not update.message.text:
        return

    parts = update.message.text.split(" ", 1)
    if len(parts) < 2:
        msg = (
            "Kullanım: /suggest kategori | söz | yazar (opsiyonel)"
            if lang == "tr"
            else "Usage: /suggest category | quote | author(optional)"
        )
        await update.message.reply_text(msg)
        return

    payload = parts[1]
    fields = [f.strip() for f in payload.split("|")]
    if len(fields) < 2:
        msg = (
            "Kullanım: /suggest kategori | söz | yazar (opsiyonel)"
            if lang == "tr"
            else "Usage: /suggest category | quote | author(optional)"
        )
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
# Callback router
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

    # Dil değiştir butonu (ayrı mesajla menü aç)
    if data == "open_lang":
        try:
            await query.answer()
        except BadRequest:
            pass
        keyboard = [
            [
                InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"),
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            ]
        ]
        text = "Dili değiştir:" if lang == "tr" else "Change language:"
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
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

    # Sözü değiştir
    if data.startswith("change_"):
        category = data.replace("change_", "")
        await send_quote_for_category(update, context, category)
        return

    # Menü aç/kapat
    if data.startswith("menu|"):
        _, category = data.split("|", 1)
        # Mevcut metni bozma, sadece keyboard değişsin
        _, quote_text, author = LAST_SHOWN.get(user_id, (category, "", ""))
        _, open_url = get_adsgram(user_id, lang)
        kb = build_share_keyboard(category, quote_text, author, lang, open_url, mode="menu")
        try:
            await query.edit_message_reply_markup(reply_markup=kb)
            await query.answer()
        except BadRequest:
            pass
        return

    if data.startswith("backmenu|"):
        _, category = data.split("|", 1)
        _, quote_text, author = LAST_SHOWN.get(user_id, (category, "", ""))
        _, open_url = get_adsgram(user_id, lang)
        kb = build_share_keyboard(category, quote_text, author, lang, open_url, mode="main")
        try:
            await query.edit_message_reply_markup(reply_markup=kb)
            await query.answer()
        except BadRequest:
            pass
        return

    # Favoriye ekle
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

    # Menüden Favoriler aç
    if data == "open_favs":
        try:
            await query.answer()
        except BadRequest:
            pass
        await send_favorites_list(
            chat_id=query.message.chat_id,
            user_id=user_id,
            lang=lang,
            bot=context.bot,
        )
        return

    # Menüden Ayarlar aç
    if data == "open_settings":
        try:
            await query.answer()
        except BadRequest:
            pass
        await send_settings_panel(
            chat_id=query.message.chat_id,
            user_id=user_id,
            lang=lang,
            bot=context.bot,
        )
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
        suffix = (
            "\n\n(Favorilerden çıkarıldı)"
            if lang == "tr"
            else "\n\n(Removed from favorites)"
        )

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

    ist_tz = datetime.timezone(datetime.timedelta(hours=3))
    app.job_queue.run_daily(
        send_daily_quote,
        time=datetime.time(hour=10, minute=0, tzinfo=ist_tz),
    )
    print("JobQueue aktif: TR saatiyle her gün 10:00'da gönderim ayarlandı.")

    print("DailyQuoteBot çalışıyor...")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
