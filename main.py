import datetime
import random
import urllib.parse

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.constants import ParseMode
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

BOT_TOKEN = "8515430219:AAHH3d2W7Ao4ao-ARwHMonRxZY5MnOyHz9k"
ADMIN_ID = 5664983086


# ------------------------------
# Yardımcı: Paylaş + Favori + Değiştir butonları
# ------------------------------
def build_main_keyboard(
    category: str,
    lang: str,
    idx: int,
    full_text: str,
    include_back: bool = False,
) -> InlineKeyboardMarkup:
    whatsapp_text = urllib.parse.quote_plus(full_text)
    whatsapp_url = f"https://api.whatsapp.com/send?text={whatsapp_text}"

    buttons: list[list[InlineKeyboardButton]] = []

    # 1) Değiştir butonu (aynı kategori için)
    buttons.append(
        [InlineKeyboardButton("Değiştir 🔄", callback_data=f"change_{category}")]
    )

    # 2) Favorilere ekle
    buttons.append(
        [
            InlineKeyboardButton(
                "⭐ Favorilere Ekle",
                callback_data=f"fav|{category}|{lang}|{idx}",
            )
        ]
    )

    # 3) Telegram'da paylaş (inline switch)
    buttons.append(
        [
            InlineKeyboardButton(
                "📤 Telegram'da Paylaş",
                switch_inline_query_current_chat=full_text,
            )
        ]
    )

    # 4) WhatsApp'ta paylaş
    buttons.append(
        [InlineKeyboardButton("📲 WhatsApp'ta Paylaş", url=whatsapp_url)]
    )

    # 5) Dil / konu değiştir (özellikle kategori seçim akışında güzel)
    if include_back:
        buttons.append(
            [
                InlineKeyboardButton(
                    "Dil / Konu Değiştir ⬅", callback_data="back_start"
                )
            ]
        )

    return InlineKeyboardMarkup(buttons)


# ------------------------------
# Bugünün sözü (motivation sabit)
# ------------------------------
def build_today_quote(category: str, user_id: int):
    lang = get_user_lang(user_id)
    today = datetime.date.today().toordinal()

    tr_list = SOZLER[category]["tr"]
    en_list = SOZLER[category]["en"]

    if lang == "tr":
        idx = today % len(tr_list)
        metin, yazar = tr_list[idx]
        yazar = normalize_author(yazar)
        text = f"Bugünün Sözü:\n\n{metin}\n\n— {yazar}"
    else:
        idx = today % len(en_list)
        metin_en, metin_tr, yazar = en_list[idx]
        yazar = normalize_author(yazar)
        text = (
            "Quote of the Day:\n\n"
            f"{metin_en}\n\n"
            f"Türkçesi: {metin_tr}\n\n"
            f"— {yazar}"
        )
    return text, idx, lang


# ------------------------------
# /start
# ------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)
    get_user_lang(user_id)
    set_daily_enabled(user_id, True)

    keyboard = [
        [
            InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        ]
    ]

    text = (
        "DailyQuoteBot\n\n"
        "Günün sözünü almak için önce dil seç.\n\n"
        "Komutlar:\n"
        "/random   - Rastgele bir söz\n"
        "/today    - Bugünün sözü\n"
        "/favorites - Favori sözlerin\n"
        "/settings  - Ayarlarını düzenle\n"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# ------------------------------
# Dil seçimi
# ------------------------------
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
        "Bir konu başlığı seç:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ------------------------------
# Seçilen kategoriden söz getir (Değiştir butonu dahil)
# ------------------------------
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
            await query.edit_message_text("Bu kategori bulunamadı.")
        except BadRequest:
            pass
        return

    if lang == "tr":
        tr_list = SOZLER[category]["tr"]
        idx = random.randrange(len(tr_list))
        metin, yazar = tr_list[idx]
        yazar = normalize_author(yazar)
        text = f"Günün Sözü:\n\n{metin}\n\n— {yazar}"
        full_text = text
    else:
        en_list = SOZLER[category]["en"]
        idx = random.randrange(len(en_list))
        metin_en, metin_tr, yazar = en_list[idx]
        yazar = normalize_author(yazar)
        text = (
            "Quote of the Day:\n\n"
            f"{metin_en}\n\n"
            f"Türkçesi: {metin_tr}\n\n"
            f"— {yazar}"
        )
        full_text = text

    keyboard = build_main_keyboard(category, lang, idx, full_text, include_back=True)

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


# ------------------------------
# /random – rastgele söz
# ------------------------------
async def random_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)
    lang = get_user_lang(user_id)

    category = random.choice(list(SOZLER.keys()))

    if lang == "tr":
        tr_list = SOZLER[category]["tr"]
        idx = random.randrange(len(tr_list))
        metin, yazar = tr_list[idx]
        yazar = normalize_author(yazar)
        full_text = f"Rastgele Söz ({SOZLER[category]['label']}):\n\n{metin}\n\n— {yazar}"
    else:
        en_list = SOZLER[category]["en"]
        idx = random.randrange(len(en_list))
        metin_en, metin_tr, yazar = en_list[idx]
        yazar = normalize_author(yazar)
        full_text = (
            f"Random Quote ({SOZLER[category]['label']}):\n\n"
            f"{metin_en}\n\n"
            f"Türkçesi: {metin_tr}\n\n"
            f"— {yazar}"
        )

    keyboard = build_main_keyboard(category, lang, idx, full_text, include_back=False)

    if update.message:
        await update.message.reply_text(full_text, reply_markup=keyboard)

        log_stat("quote_random", user_id, category)

        await send_adsgram_ad(
            context=context,
            chat_id=update.effective_chat.id,
            user_id=user_id,
            lang=lang,
        )


# ------------------------------
# /today – bugünün sözü
# ------------------------------
async def today_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)
    set_daily_enabled(user_id, True)

    category = "motivation"
    text, idx, lang = build_today_quote(category, user_id)
    full_text = text

    keyboard = build_main_keyboard(category, lang, idx, full_text, include_back=False)

    if update.message:
        await update.message.reply_text(full_text, reply_markup=keyboard)

        log_stat("quote_today", user_id, category)

        await send_adsgram_ad(
            context=context,
            chat_id=update.effective_chat.id,
            user_id=user_id,
            lang=lang,
        )


# ------------------------------
# Günlük 10:00 job
# ------------------------------
async def send_daily_quote(context: ContextTypes.DEFAULT_TYPE):
    from db import db_execute  # lokal import döngüyü önler

    cur = db_execute(
        "SELECT user_id FROM users WHERE daily_enabled = 1",
        (),
    )
    rows = cur.fetchall()
    user_ids = [row["user_id"] for row in rows]

    category = "motivation"

    for user_id in user_ids:
        try:
            text, idx, lang = build_today_quote(category, user_id)
            msg = await context.bot.send_message(chat_id=user_id, text=text)

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


# ------------------------------
# Admin: TR/EN söz ekleme
# ------------------------------
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


# ------------------------------
# /favorites
# ------------------------------
async def favorites_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)

    rows = get_last_favorites(user_id, limit=10)
    if not rows:
        await update.message.reply_text("Henüz favori sözün yok. ⭐ ile ekleyebilirsin.")
        return

    lines = ["Son 10 favori sözün:\n"]
    for i, row in enumerate(rows, start=1):
        cat = row["category"]
        author = row["author"]
        quote_text = row["quote_text"]
        quote_tr = row["quote_tr"]

        label = SOZLER.get(cat, {}).get("label", cat)
        lines.append(f"{i}) [{label}]")
        lines.append(f"{quote_text}")
        if quote_tr:
            lines.append(f"Türkçesi: {quote_tr}")
        lines.append(f"— {author}")
        lines.append("")

    await update.message.reply_text("\n".join(lines))


# ------------------------------
# /settings
# ------------------------------
async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(user_id)
    lang = get_user_lang(user_id)
    daily_enabled = get_daily_enabled(user_id)

    lang_text = "Türkçe" if lang == "tr" else "English"
    daily_text = "Açık ✅" if daily_enabled else "Kapalı ❌"

    text = (
        "Ayarların:\n\n"
        f"Dil: {lang_text}\n"
        f"Günlük bildirim: {daily_text}\n\n"
        "Dil ve günlük bildirim ayarını aşağıdan değiştirebilirsin."
    )

    if daily_enabled:
        daily_button = InlineKeyboardButton(
            "🔕 Günlük bildirimi kapat", callback_data="set_daily_off"
        )
    else:
        daily_button = InlineKeyboardButton(
            "🔔 Günlük bildirimi aç", callback_data="set_daily_on"
        )

    keyboard = [
        [
            InlineKeyboardButton("🇹🇷 Türkçe", callback_data="set_lang_tr"),
            InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en"),
        ],
        [daily_button],
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# ------------------------------
# /stats – admin
# ------------------------------
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


# ------------------------------
# Favori callback
# ------------------------------
async def handle_favorite_from_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, payload: str
):
    from db import add_favorite  # döngü kırmak için lokal import

    query = update.callback_query
    user_id = query.from_user.id
    ensure_user(user_id)

    try:
        _, category, lang, idx_str = payload.split("|")
        idx = int(idx_str)
    except Exception:
        await query.answer("Favori eklenirken hata oluştu.", show_alert=True)
        return

    if category not in SOZLER:
        await query.answer("Kategori bulunamadı.", show_alert=True)
        return

    try:
        if lang == "tr":
            tr_list = SOZLER[category]["tr"]
            metin, yazar = tr_list[idx]
            yazar = normalize_author(yazar)
            quote_text = metin
            quote_tr = None
        else:
            en_list = SOZLER[category]["en"]
            metin_en, metin_tr, yazar = en_list[idx]
            yazar = normalize_author(yazar)
            quote_text = metin_en
            quote_tr = metin_tr

        add_favorite(
            user_id=user_id,
            category=category,
            lang=lang,
            quote_text=quote_text,
            quote_tr=quote_tr,
            author=yazar,
        )
        log_stat("favorite_add", user_id, category)
        await query.answer("Favorilere eklendi ✅", show_alert=False)
    except Exception as e:
        print("Favori ekleme hata:", e)
        await query.answer("Favori eklenirken hata oluştu.", show_alert=True)


# ------------------------------
# Callback router
# ------------------------------
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

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
                InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"),
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            ]
        ]
        try:
            await query.edit_message_text(
                "Dil seçerek yeniden başlayabilirsin.\n\n"
                "Komutlar:\n"
                "/random  - Rastgele söz\n"
                "/today   - Bugünün sözü",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except BadRequest as e:
            print("back_start edit hatası:", e)

    # Ayarlar
    elif data == "set_lang_tr":
        set_user_lang(query.from_user.id, "tr")
        await query.answer("Dil Türkçe olarak ayarlandı.", show_alert=False)
    elif data == "set_lang_en":
        set_user_lang(query.from_user.id, "en")
        await query.answer("Language set to English.", show_alert=False)
    elif data == "set_daily_on":
        set_daily_enabled(query.from_user.id, True)
        await query.answer("Günlük bildirimler açıldı.", show_alert=False)
    elif data == "set_daily_off":
        set_daily_enabled(query.from_user.id, False)
        await query.answer("Günlük bildirimler kapatıldı.", show_alert=False)

    # Favori
    elif data.startswith("fav|"):
        await handle_favorite_from_callback(update, context, data)


# ------------------------------
# Inline Mode – söz önerileri
# ------------------------------
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
            yazar = normalize_author(yazar)
            full_text = f"{metin}\n\n— {yazar}"
        else:
            en_list = SOZLER[category]["en"]
            idx = random.randrange(len(en_list))
            metin_en, metin_tr, yazar = en_list[idx]
            yazar = normalize_author(yazar)
            full_text = (
                f"{metin_en}\n\n"
                f"Türkçesi: {metin_tr}\n\n"
                f"— {yazar}"
            )

        keyboard = build_main_keyboard(category, lang, idx, full_text, include_back=False)

        result = InlineQueryResultArticle(
            id=f"{category}_{lang}_{idx}_{i}",
            title=label,
            description=label,
            input_message_content=InputTextMessageContent(full_text),
            reply_markup=keyboard,
        )
        results.append(result)

    await query.answer(results, cache_time=5, is_personal=True)


# ------------------------------
# Hata handler
# ------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("Hata yakalandı:", context.error)


# ------------------------------
# MAIN
# ------------------------------
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
