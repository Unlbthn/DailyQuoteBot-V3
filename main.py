import datetime
import random
import urllib.parse
from typing import Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
)

from adsgram import send_adsgram_ad
from db import (
    ensure_user,
    get_daily_enabled,
    get_last_favorites,
    get_stats_summary,
    get_user_lang,
    log_stat,
    set_daily_enabled,
    set_user_lang,
)
from quotes import SOZLER, normalize_author

# --------------------------------
# AYARLAR
# --------------------------------
BOT_TOKEN = "8515430219:AAHH3d2W7Ao4ao-ARwHMonRxZY5MnOyHz9k"
ADMIN_ID = 5664983086

# Bot linkini burada güncelle
BOT_LINK = "https://t.me/QuoteMastersBot"


# --------------------------------
# Dil bazlı metinler
# --------------------------------
TEXTS = {
    "tr": {
        "start": (
            "DailyQuoteBot\n\n"
            "Önce dilini seç, sonra her gün seçtiğin dilde sözler al.\n\n"
            "Komutlar:\n"
            "/random - Rastgele bir söz\n\n"
            "/today - Bugünün sözü\n\n"
            "/favorites - Favori sözlerin\n\n"
            "/settings - Ayarlarını düzenle\n"
        ),
        "choose_category": "Bir konu başlığı seç:",
        "random_prefix": "Rastgele Söz",
        "today_prefix": "Bugünün Sözü",
        "quote_of_day_prefix": "Bugünün Sözü",
        "favorites_empty": "Henüz favori sözün yok. ⭐ ile ekleyebilirsin.",
        "favorites_title": "Son 10 favori sözün:\n",
        "settings_title": "Ayarların:\n\n",
        "settings_lang_label": "Dil",
        "settings_daily_label": "Günlük bildirim",
        "settings_explain": "Dil ve günlük bildirim ayarını aşağıdan değiştirebilirsin.",
        "settings_daily_on_btn": "🔕 Günlük bildirimi kapat",
        "settings_daily_off_btn": "🔔 Günlük bildirimi aç",
        "lang_tr_button": "🇹🇷 Türkçe",
        "lang_en_button": "🇬🇧 English",
        "back_start": (
            "Dil seçerek yeniden başlayabilirsin.\n\n"
            "Komutlar:\n"
            "/random - Rastgele söz\n\n"
            "/today - Bugünün sözü"
        ),
        "favorite_added": "Favorilere eklendi ✅",
        "favorite_error": "Favori eklenirken hata oluştu.",
        "category_not_found": "Bu kategori bulunamadı.",
        "settings_lang_changed_tr": "Dil Türkçe olarak ayarlandı.",
        "settings_lang_changed_en": "Dil İngilizce olarak ayarlandı.",
        "settings_daily_on_msg": "Günlük bildirimler açıldı.",
        "settings_daily_off_msg": "Günlük bildirimler kapatıldı.",
        "daily_on_label": "Açık ✅",
        "daily_off_label": "Kapalı ❌",
        "favorites_label": "Favori sözlerin",
        "telegram_share_button": "📤 Telegram'da Paylaş",
        "whatsapp_share_button": "📲 WhatsApp'ta Paylaş",
        "change_button": "Değiştir 🔄",
        "favorite_button": "⭐ Favorilere Ekle",
        "back_button": "Dil / Konu Değiştir ⬅",
    },
    "en": {
        "start": (
            "DailyQuoteBot\n\n"
            "First choose your language, then receive quotes every day in that language.\n\n"
            "Commands:\n"
            "/random - Random quote\n\n"
            "/today - Quote of the day\n\n"
            "/favorites - Your favorite quotes\n\n"
            "/settings - Change your settings\n"
        ),
        "choose_category": "Choose a topic:",
        "random_prefix": "Random Quote",
        "today_prefix": "Quote of the Day",
        "quote_of_day_prefix": "Quote of the Day",
        "favorites_empty": "You don’t have any favorite quotes yet. Use ⭐ to add.",
        "favorites_title": "Your last 10 favorite quotes:\n",
        "settings_title": "Your settings:\n\n",
        "settings_lang_label": "Language",
        "settings_daily_label": "Daily notification",
        "settings_explain": "You can change your language and daily notification settings below.",
        "settings_daily_on_btn": "🔕 Turn off daily notification",
        "settings_daily_off_btn": "🔔 Turn on daily notification",
        "lang_tr_button": "🇹🇷 Turkish",
        "lang_en_button": "🇬🇧 English",
        "back_start": (
            "You can start again by choosing your language.\n\n"
            "Commands:\n"
            "/random - Random quote\n\n"
            "/today - Quote of the day"
        ),
        "favorite_added": "Added to favorites ✅",
        "favorite_error": "An error occurred while adding to favorites.",
        "category_not_found": "Category not found.",
        "settings_lang_changed_tr": "Language set to Turkish.",
        "settings_lang_changed_en": "Language set to English.",
        "settings_daily_on_msg": "Daily notifications turned on.",
        "settings_daily_off_msg": "Daily notifications turned off.",
        "daily_on_label": "On ✅",
        "daily_off_label": "Off ❌",
        "favorites_label": "Your favorites",
        "telegram_share_button": "📤 Share on Telegram",
        "whatsapp_share_button": "📲 Share on WhatsApp",
        "change_button": "Change 🔄",
        "favorite_button": "⭐ Add to Favorites",
        "back_button": "Change Language / Topic ⬅",
    },
}


def t(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS["tr"]).get(key, "")


# --------------------------------
# Yardımcı fonksiyonlar
# --------------------------------
def clean_author(yazar: Optional[str]) -> str:
    """
    Yazar adını normalize eder, 'Anonim' ise boş döner.
    'Nelson Mandela’ya atfedilir' -> 'Nelson Mandela'
    """
    if not yazar:
        return ""
    a = normalize_author(yazar)
    if not a:
        return ""
    if a.strip().lower().startswith("anonim"):
        return ""
    return a.strip()


def build_share_text(full_text: str, lang: str) -> str:
    """Paylaşırken kullanılacak metni (bot linki ile birlikte) oluşturur."""
    if lang == "tr":
        return f"{full_text}\n\nBu ve binlercesi {BOT_LINK}'ta. Denemek için tıkla!"
    else:
        return f"{full_text}\n\nMore quotes like this on {BOT_LINK} – tap to try!"


def build_main_keyboard(
    category: str,
    lang: str,
    idx: int,
    full_text: str,
    share_text: str,
    include_back: bool = False,
) -> InlineKeyboardMarkup:
    """Değiştir, Favori, Telegram/WhatsApp paylaş butonları."""
    # WhatsApp paylaş
    whatsapp_encoded = urllib.parse.quote_plus(share_text)
    whatsapp_url = f"https://api.whatsapp.com/send?text={whatsapp_encoded}"

    # Telegram paylaş (t.me/share/url)
    telegram_encoded = urllib.parse.quote_plus(share_text)
    telegram_share_url = f"https://t.me/share/url?text={telegram_encoded}"

    buttons: list[list[InlineKeyboardButton]] = []

    # 1) Değiştir
    buttons.append(
        [InlineKeyboardButton(t(lang, "change_button"), callback_data=f"change_{category}")]
    )

    # 2) Favorilere ekle
    buttons.append(
        [
            InlineKeyboardButton(
                t(lang, "favorite_button"),
                callback_data=f"fav|{category}|{lang}|{idx}",
            )
        ]
    )

    # 3) Telegram'da paylaş
    buttons.append(
        [InlineKeyboardButton(t(lang, "telegram_share_button"), url=telegram_share_url)]
    )

    # 4) WhatsApp'ta paylaş
    buttons.append(
        [InlineKeyboardButton(t(lang, "whatsapp_share_button"), url=whatsapp_url)]
    )

    # 5) Geri dön
    if include_back:
        buttons.append(
            [
                InlineKeyboardButton(
                    t(lang, "back_button"), callback_data="back_start"
                )
            ]
        )

    return InlineKeyboardMarkup(buttons)


# --------------------------------
# Bugünün sözü (motivation sabit)
# --------------------------------
def build_today_quote(category: str, user_id: int):
    lang = get_user_lang(user_id)
    today = datetime.date.today().toordinal()

    tr_list = SOZLER[category]["tr"]
    en_list = SOZLER[category]["en"]

    if lang == "tr":
        idx = today % len(tr_list)
        metin, yazar = tr_list[idx]
        author = clean_author(yazar)
        prefix = t(lang, "quote_of_day_prefix")
        if author:
            text = f"{prefix}:\n\n{metin}\n\n— {author}"
        else:
            text = f"{prefix}:\n\n{metin}"
    else:
        idx = today % len(en_list)
        metin_en, _, yazar = en_list[idx]  # TR çeviriyi kullanmıyoruz
        author = clean_author(yazar)
        prefix = t(lang, "quote_of_day_prefix")
        if author:
            text = f"{prefix}:\n\n{metin_en}\n\n— {author}"
        else:
            text = f"{prefix}:\n\n{metin_en}"

    return text, idx, lang


# --------------------------------
# /start
# --------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)
    lang = get_user_lang(user_id)
    set_daily_enabled(user_id, True)

    keyboard = [
        [
            InlineKeyboardButton(t("tr", "lang_tr_button"), callback_data="lang_tr"),
            InlineKeyboardButton(t("en", "lang_en_button"), callback_data="lang_en"),
        ]
    ]

    text = t(lang, "start")

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# --------------------------------
# Dil seçimi
# --------------------------------
async def dil_sec(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest:
        pass

    user_id = query.from_user.id
    set_user_lang(user_id, lang)

    buttons = []
    for key, data in SOZLER.items():
        buttons.append([InlineKeyboardButton(data["label"], callback_data=f"cat_{key}")])

    await query.edit_message_text(
        t(lang, "choose_category"),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# --------------------------------
# Seçilen kategoriden söz getir
# --------------------------------
async def get_soz(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest:
        pass

    user_id = query.from_user.id
    ensure_user(user_id)
    lang = get_user_lang(user_id)

    if category not in SOZLER:
        try:
            await query.edit_message_text(t(lang, "category_not_found"))
        except BadRequest:
            pass
        return

    if lang == "tr":
        tr_list = SOZLER[category]["tr"]
        idx = random.randrange(len(tr_list))
        metin, yazar = tr_list[idx]
        author = clean_author(yazar)
        prefix = t(lang, "today_prefix")
        if author:
            full_text = f"{prefix}:\n\n{metin}\n\n— {author}"
        else:
            full_text = f"{prefix}:\n\n{metin}"
    else:
        en_list = SOZLER[category]["en"]
        idx = random.randrange(len(en_list))
        metin_en, _, yazar = en_list[idx]
        author = clean_author(yazar)
        prefix = t(lang, "today_prefix")
        if author:
            full_text = f"{prefix}:\n\n{metin_en}\n\n— {author}"
        else:
            full_text = f"{prefix}:\n\n{metin_en}"

    share_text = build_share_text(full_text, lang)
    keyboard = build_main_keyboard(category, lang, idx, full_text, share_text, include_back=True)

    try:
        await query.edit_message_text(full_text, reply_markup=keyboard)
    except BadRequest as e:
        print("edit_message_text hatası:", e)

    log_stat("quote_category", user_id, category)

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
    ensure_user(user_id)
    lang = get_user_lang(user_id)

    category = random.choice(list(SOZLER.keys()))
    label = SOZLER[category]["label"]

    if lang == "tr":
        tr_list = SOZLER[category]["tr"]
        idx = random.randrange(len(tr_list))
        metin, yazar = tr_list[idx]
        author = clean_author(yazar)
        prefix = t(lang, "random_prefix")
        if author:
            full_text = f"{prefix} ({label}):\n\n{metin}\n\n— {author}"
        else:
            full_text = f"{prefix} ({label}):\n\n{metin}"
    else:
        en_list = SOZLER[category]["en"]
        idx = random.randrange(len(en_list))
        metin_en, _, yazar = en_list[idx]
        author = clean_author(yazar)
        prefix = t(lang, "random_prefix")
        if author:
            full_text = f"{prefix} ({label}):\n\n{metin_en}\n\n— {author}"
        else:
            full_text = f"{prefix} ({label}):\n\n{metin_en}"

    share_text = build_share_text(full_text, lang)
    keyboard = build_main_keyboard(category, lang, idx, full_text, share_text, include_back=False)

    if update.message:
        await update.message.reply_text(full_text, reply_markup=keyboard)

        log_stat("quote_random", user_id, category)

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
    ensure_user(user_id)
    set_daily_enabled(user_id, True)

    category = "motivation"
    full_text, idx, lang = build_today_quote(category, user_id)
    share_text = build_share_text(full_text, lang)

    keyboard = build_main_keyboard(category, lang, idx, full_text, share_text, include_back=False)

    if update.message:
        await update.message.reply_text(full_text, reply_markup=keyboard)

        log_stat("quote_today", user_id, category)

        await send_adsgram_ad(
            context=context,
            chat_id=update.effective_chat.id,
            user_id=user_id,
            lang=lang,
        )


# --------------------------------
# Günlük 10:00 job
# --------------------------------
async def send_daily_quote(context: ContextTypes.DEFAULT_TYPE):
    from db import db_execute  # döngüyü önlemek için lokal import

    cur = db_execute(
        "SELECT user_id FROM users WHERE daily_enabled = 1",
        (),
    )
    rows = cur.fetchall()
    user_ids = [row["user_id"] for row in rows]

    category = "motivation"

    for user_id in user_ids:
        try:
            full_text, idx, lang = build_today_quote(category, user_id)
            msg = await context.bot.send_message(chat_id=user_id, text=full_text)

            log_stat("quote_today", user_id, category)

            await send_adsgram_ad(
                context=context,
                chat_id=msg.chat_id,
                user_id=user_id,
                lang=lang,
            )
        except Exception as e:
            print("daily_quote hata:", e)
            continue


# --------------------------------
# Admin: TR/EN söz ekleme
# --------------------------------
async def addquote_tr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        if update.message:
            await update.message.reply_text("Bu komut sadece admin içindir.")
        return

    parts = update.message.text.split(" ", 1)
    if len(parts) < 2:
        await update.message.reply_text(
            "Kullanım: /addquote_tr kategori | söz | yazar (yazar boş olabilir)"
        )
        return

    payload = parts[1]
    fields = [f.strip() for f in payload.split("|")]
    if len(fields) < 2:
        await update.message.reply_text(
            "Kullanım: /addquote_tr kategori | söz | yazar"
        )
        return

    category_key = fields[0].lower()
    metin = fields[1]
    yazar = fields[2] if len(fields) >= 3 and fields[2] else "Anonim"

    if category_key not in SOZLER:
        SOZLER[category_key] = {
            "label": category_key.title(),
            "tr": [],
            "en": [],
        }

    SOZLER[category_key]["tr"].append((metin, yazar))
    await update.message.reply_text(
        f"Yeni TR söz eklendi.\nKategori: {category_key}\nYazar: {yazar}"
    )


async def addquote_en(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        if update.message:
            await update.message.reply_text("Bu komut sadece admin içindir.")
        return

    parts = update.message.text.split(" ", 1)
    if len(parts) < 2:
        await update.message.reply_text(
            "Kullanım: /addquote_en kategori | English söz | Türkçe çeviri | Yazar"
        )
        return

    payload = parts[1]
    fields = [f.strip() for f in payload.split("|")]
    if len(fields) < 3:
        await update.message.reply_text(
            "Kullanım: /addquote_en kategori | English söz | Türkçe çeviri | Yazar"
        )
        return

    category_key = fields[0].lower()
    metin_en = fields[1]
    metin_tr = fields[2]
    yazar = fields[3] if len(fields) >= 4 and fields[3] else "Anonim"

    if category_key not in SOZLER:
        SOZLER[category_key] = {
            "label": category_key.title(),
            "tr": [],
            "en": [],
        }

    SOZLER[category_key]["en"].append((metin_en, metin_tr, yazar))
    await update.message.reply_text(
        f"Yeni EN söz eklendi.\nKategori: {category_key}\nYazar: {yazar}"
    )


# --------------------------------
# /favorites
# --------------------------------
async def favorites_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)
    lang = get_user_lang(user_id)

    rows = get_last_favorites(user_id, limit=10)
    if not rows:
        await update.message.reply_text(t(lang, "favorites_empty"))
        return

    lines = [t(lang, "favorites_title")]
    for i, row in enumerate(rows, start=1):
        cat = row["category"]
        author = clean_author(row["author"])
        quote_text = row["quote_text"]

        label = SOZLER.get(cat, {}).get("label", cat)
        lines.append(f"{i}) [{label}]")
        lines.append(f"{quote_text}")
        if author:
            lines.append(f"— {author}")
        lines.append("")

    await update.message.reply_text("\n".join(lines))


# --------------------------------
# /settings
# --------------------------------
async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)
    lang = get_user_lang(user_id)
    daily_enabled = get_daily_enabled(user_id)

    lang_text = "Türkçe" if lang == "tr" else "English"
    daily_text = t(lang, "daily_on_label") if daily_enabled else t(lang, "daily_off_label")

    text = (
        t(lang, "settings_title")
        + f"{t(lang, 'settings_lang_label')}: {lang_text}\n"
        + f"{t(lang, 'settings_daily_label')}: {daily_text}\n\n"
        + t(lang, "settings_explain")
    )

    if daily_enabled:
        daily_button = InlineKeyboardButton(
            t(lang, "settings_daily_on_btn"), callback_data="set_daily_off"
        )
    else:
        daily_button = InlineKeyboardButton(
            t(lang, "settings_daily_off_btn"), callback_data="set_daily_on"
        )

    keyboard = [
        [
            InlineKeyboardButton(t("tr", "lang_tr_button"), callback_data="set_lang_tr"),
            InlineKeyboardButton(t("en", "lang_en_button"), callback_data="set_lang_en"),
        ],
        [daily_button],
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# --------------------------------
# /stats – admin
# --------------------------------
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Bu komut sadece admin içindir.")
        return

    summary = get_stats_summary()
    total_users = summary["total_users"]
    daily_users = summary["daily_users"]
    total_favs = summary["total_favs"]
    ad_shown_count = summary["ad_shown_count"]
    top_cat_views_row = summary["top_cat_views_row"]
    top_cat_favs_row = summary["top_cat_favs_row"]

    if top_cat_views_row and top_cat_views_row["category"] in SOZLER:
        top_cat_views = (
            f"{SOZLER[top_cat_views_row['category']]['label']} ({top_cat_views_row['c']})"
        )
    else:
        top_cat_views = "Yok"

    if top_cat_favs_row and top_cat_favs_row["category"] in SOZLER:
        top_cat_favs = (
            f"{SOZLER[top_cat_favs_row['category']]['label']} ({top_cat_favs_row['c']})"
        )
    else:
        top_cat_favs = "Yok"

    text = (
        "📊 Bot İstatistikleri\n\n"
        f"Toplam kullanıcı: {total_users}\n"
        f"Günlük bildirim açık kullanıcı: {daily_users}\n"
        f"Toplam favori sayısı: {total_favs}\n"
        f"En çok görüntülenen kategori: {top_cat_views}\n"
        f"En çok favori eklenen kategori: {top_cat_favs}\n"
        f"Toplam gösterilen reklam sayısı: {ad_shown_count}\n"
    )

    await update.message.reply_text(text)


# --------------------------------
# Favori callback
# --------------------------------
async def handle_favorite_from_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, payload: str
):
    from db import add_favorite  # döngü kırmak için lokal import

    query = update.callback_query
    user_id = query.from_user.id
    ensure_user(user_id)
    lang = get_user_lang(user_id)

    try:
        _, category, payload_lang, idx_str = payload.split("|")
        idx = int(idx_str)
    except Exception:
        await query.answer(t(lang, "favorite_error"), show_alert=True)
        return

    if category not in SOZLER:
        await query.answer(t(lang, "category_not_found"), show_alert=True)
        return

    try:
        if payload_lang == "tr":
            tr_list = SOZLER[category]["tr"]
            metin, yazar = tr_list[idx]
            author = clean_author(yazar)
            quote_text = metin
            quote_tr = None
        else:
            en_list = SOZLER[category]["en"]
            metin_en, metin_tr, yazar = en_list[idx]
            author = clean_author(yazar)
            quote_text = metin_en
            quote_tr = metin_tr  # DB'de dursun

        add_favorite(
            user_id=user_id,
            category=category,
            lang=payload_lang,
            quote_text=quote_text,
            quote_tr=quote_tr,
            author=author,
        )
        log_stat("favorite_add", user_id, category)
        await query.answer(t(lang, "favorite_added"), show_alert=False)
    except Exception as e:
        print("Favori ekleme hata:", e)
        await query.answer(t(lang, "favorite_error"), show_alert=True)


# --------------------------------
# Callback router
# --------------------------------
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    lang = get_user_lang(user_id)

    if data == "lang_tr":
        await dil_sec(update, context, "tr")
    elif data == "lang_en":
        await dil_sec(update, context, "en")
    elif data.startswith("cat_"):
        category = data.replace("cat_", "")
        await get_soz(update, context, category)
    elif data.startswith("change_"):
        category = data.replace("change_", "")
        await get_soz(update, context, category)
    elif data == "back_start":
        keyboard = [
            [
                InlineKeyboardButton(t("tr", "lang_tr_button"), callback_data="lang_tr"),
                InlineKeyboardButton(t("en", "lang_en_button"), callback_data="lang_en"),
            ]
        ]
        try:
            await query.edit_message_text(
                t(lang, "back_start"),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except BadRequest as e:
            print("back_start edit hatası:", e)

    # Ayarlar
    elif data == "set_lang_tr":
        set_user_lang(user_id, "tr")
        await query.answer(t("tr", "settings_lang_changed_tr"), show_alert=False)
    elif data == "set_lang_en":
        set_user_lang(user_id, "en")
        await query.answer(t("en", "settings_lang_changed_en"), show_alert=False)
    elif data == "set_daily_on":
        set_daily_enabled(user_id, True)
        await query.answer(t(lang, "settings_daily_on_msg"), show_alert=False)
    elif data == "set_daily_off":
        set_daily_enabled(user_id, False)
        await query.answer(t(lang, "settings_daily_off_msg"), show_alert=False)

    # Favori
    elif data.startswith("fav|"):
        await handle_favorite_from_callback(update, context, data)


# --------------------------------
# Inline Mode – söz önerileri
# --------------------------------
async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query
    if query is None:
        return

    user_id = query.from_user.id
    ensure_user(user_id)
    lang = get_user_lang(user_id)

    q = (query.query or "").strip().lower()

    if q:
        matched_categories = []
        for key, data in SOZLER.items():
            label = data["label"].lower()
            if q in key.lower() or q in label:
                matched_categories.append(key)
        if not matched_categories:
            matched_categories = list(SOZLER.keys())
    else:
        matched_categories = list(SOZLER.keys())

    results = []
    max_results = 10

    for i in range(max_results):
        category = random.choice(matched_categories)
        label = SOZLER[category]["label"]

        if lang == "tr":
            tr_list = SOZLER[category]["tr"]
            idx = random.randrange(len(tr_list))
            metin, yazar = tr_list[idx]
            author = clean_author(yazar)
            if author:
                base_text = f"{metin}\n\n— {author}"
            else:
                base_text = metin
        else:
            en_list = SOZLER[category]["en"]
            idx = random.randrange(len(en_list))
            metin_en, _, yazar = en_list[idx]
            author = clean_author(yazar)
            if author:
                base_text = f"{metin_en}\n\n— {author}"
            else:
                base_text = metin_en

        full_text = base_text
        share_text = build_share_text(full_text, lang)
        keyboard = build_main_keyboard(
            category, lang, idx, full_text, share_text, include_back=False
        )

        result = InlineQueryResultArticle(
            id=f"{category}_{lang}_{idx}_{i}",
            title=label,
            description=label,
            input_message_content=InputTextMessageContent(share_text),
            reply_markup=keyboard,
        )
        results.append(result)

    await query.answer(results, cache_time=5, is_personal=True)


# --------------------------------
# Hata handler
# --------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("Hata yakalandı:", context.error)


# --------------------------------
# MAIN
# --------------------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("random", random_cmd))
    app.add_handler(CommandHandler("today", today_cmd))
    app.add_handler(CommandHandler("addquote_tr", addquote_tr))
    app.add_handler(CommandHandler("addquote_en", addquote_en))
    app.add_handler(CommandHandler("favorites", favorites_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))

    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(InlineQueryHandler(inline_query_handler))

    app.add_error_handler(error_handler)

    if app.job_queue is not None:
        app.job_queue.run_daily(
            send_daily_quote,
            time=datetime.time(hour=10, minute=0),
        )
        print("JobQueue aktif: Günlük 10:00 gönderimi ayarlandı.")
    else:
        print("Uyarı: JobQueue yok, günlük 10:00 gönderimi kapalı.")

    print("DailyQuoteBot V3 çalışıyor...")
    app.run_polling()


if __name__ == "__main__":
    main()
