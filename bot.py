# -*- coding: utf-8 -*-
"""
Quote Masters Bot (QuoteMastersBot)
- TR/EN language selection on EVERY /start
- Topic selection after language selection
- "Daily" quote cached per-day (random from all quotes) and served consistently all day
- "New Quote" rotates randomly within the selected topic
- AdsGram sponsored block (shows only when an ad is available)
"""

from __future__ import annotations

import os
import json
import random
import logging
from datetime import datetime, date, time as dtime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import requests
from apscheduler.schedulers.background import BackgroundScheduler

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# ----------------------------
# CONFIG
# ----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADSGRAM_BLOCK_ID = os.getenv("ADSGRAM_BLOCK_ID", "").strip()  # example: bot-17933

# Europe/Istanbul is UTC+3 (no DST)
TZ = timezone(timedelta(hours=3))

STATE_FILE = "state.json"  # persisted daily quote (in working dir)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("quote-masters-bot")

# ----------------------------
# QUOTES SOURCE
# ----------------------------
# quotes.py must expose QUOTES_TR and QUOTES_EN dicts: { "Category": ["quote1", "quote2", ...], ... }
from quotes import QUOTES_TR, QUOTES_EN  # noqa: E402


# ----------------------------
# UI TEXTS (keep in bot.py)
# ----------------------------
TEXTS = {
    "tr": {
        "pick_lang": "Lütfen dil seçiniz:",
        "pick_topic": "Bir konu seç:",
        "daily_title": "Günün Sözü",
        "new_quote": "Yeni Söz",
        "change_topic": "Konuyu değiştir",
        "settings": "Ayarlar",
        "share_whatsapp": "WhatsApp'ta Paylaş",
        "share_telegram": "Telegram'da Paylaş",
        "back": "Geri",
        "lang": "Dili değiştir",
        "saved_lang": "Dil ayarlandı.",
        "saved_topic": "Konu ayarlandı.",
        "no_quotes": "Bu kategoride henüz söz yok.",
    },
    "en": {
        "pick_lang": "Please choose a language:",
        "pick_topic": "Choose a topic:",
        "daily_title": "Quote of the Day",
        "new_quote": "New Quote",
        "change_topic": "Change Topic",
        "settings": "Settings",
        "share_whatsapp": "Share on WhatsApp",
        "share_telegram": "Share on Telegram",
        "back": "Back",
        "lang": "Change Language",
        "saved_lang": "Language updated.",
        "saved_topic": "Topic updated.",
        "no_quotes": "No quotes in this category yet.",
    },
}

# ----------------------------
# PERSISTED STATE
# ----------------------------
def _load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("State load failed: %s", e)
        return {}


def _save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("State save failed: %s", e)


STATE = _load_state()
# STATE schema:
# {
#   "daily": {
#       "date": "YYYY-MM-DD",
#       "tr": {"text": "...", "category": "..."},
#       "en": {"text": "...", "category": "..."}
#   }
# }


# ----------------------------
# ADSGRAM
# ----------------------------
def fetch_adsgram_ad() -> str:
    """
    Returns an AdsGram ad message. If no ad available, returns "" (empty).
    Desired format:
      🟣 *Sponsored*
      <title>
      <description>
      <link>
    """
    if not ADSGRAM_BLOCK_ID:
        return ""

    url = f"https://adsgram.ai/api/v1/show?block_id={ADSGRAM_BLOCK_ID}"
    try:
        r = requests.get(url, timeout=10)
        body = (r.text or "").strip()

        # AdsGram sometimes returns plain text like:
        # "No available advertisement at the moment, try again later!"
        if not body:
            return ""
        if "No available advertisement" in body:
            return ""

        # Try JSON
        data = None
        try:
            data = r.json()
        except Exception:
            # Not JSON => treat as no ad
            return ""

        # Normalize possible shapes
        # Common guess: {"data": {"title":..., "description":..., "text":..., "link":...}}
        payload = data.get("data") if isinstance(data, dict) else None
        if not isinstance(payload, dict):
            # Some APIs return {"message": "..."} on error
            msg = ""
            if isinstance(data, dict):
                msg = str(data.get("message") or data.get("error") or "")
            if "No available advertisement" in msg:
                return ""
            return ""

        title = str(payload.get("title") or "").strip()
        desc = str(payload.get("description") or "").strip()
        text = str(payload.get("text") or "").strip()
        link = str(payload.get("link") or payload.get("url") or "").strip()

        lines = ["🟣 *Sponsored*"]
        for s in [title, desc, text]:
            s = s.strip()
            if s and s not in lines:
                lines.append(s)
        if link:
            lines.append(link)

        # If we only have the header, hide it
        if len(lines) == 1:
            return ""
        return "\n".join(lines)

    except Exception as e:
        logger.warning("AdsGram error: %s", e)
        return ""


# ----------------------------
# QUOTE HELPERS
# ----------------------------
def all_quotes(lang: str) -> List[Tuple[str, str]]:
    """Return list of (category, quote) for a language."""
    src = QUOTES_TR if lang == "tr" else QUOTES_EN
    out: List[Tuple[str, str]] = []
    for cat, arr in src.items():
        if not arr:
            continue
        for q in arr:
            q = str(q).strip()
            if q:
                out.append((cat, q))
    return out


def random_quote_from_category(lang: str, category: str) -> Optional[str]:
    src = QUOTES_TR if lang == "tr" else QUOTES_EN
    arr = src.get(category) or []
    arr = [str(x).strip() for x in arr if str(x).strip()]
    if not arr:
        return None
    return random.choice(arr)


def compute_daily_if_needed() -> None:
    """Ensure STATE['daily'] exists for today (TR and EN)."""
    global STATE
    today = datetime.now(TZ).date().isoformat()
    daily = STATE.get("daily", {})
    if daily.get("date") == today and daily.get("tr") and daily.get("en"):
        return

    # Pick independently per language (so each language can have its own daily quote)
    for lang in ("tr", "en"):
        pool = all_quotes(lang)
        if not pool:
            chosen = {"category": "", "text": ""}
        else:
            cat, q = random.choice(pool)
            chosen = {"category": cat, "text": q}

        daily.setdefault(lang, {})
        daily[lang] = chosen

    daily["date"] = today
    STATE["daily"] = daily
    _save_state(STATE)
    logger.info("Daily quote computed for %s", today)


def get_daily_quote(lang: str) -> str:
    compute_daily_if_needed()
    daily = STATE.get("daily", {})
    payload = daily.get(lang) or {}
    return str(payload.get("text") or "").strip()


# ----------------------------
# BUTTON BUILDERS
# ----------------------------
def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang:tr")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")],
        ]
    )


def categories_buttons(lang: str) -> InlineKeyboardMarkup:
    cats = list((QUOTES_TR if lang == "tr" else QUOTES_EN).keys())
    # keep stable order
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for c in cats:
        row.append(InlineKeyboardButton(c, callback_data=f"cat:{c}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def menu_buttons(lang: str, quote_text: str = "") -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    encoded = requests.utils.quote(quote_text or "")

    # NOTE: Telegram bots cannot force-open native apps directly.
    # URL buttons are the best possible UX in Telegram (opens the relevant share page).
    whatsapp_url = f"https://wa.me/?text={encoded}"
    telegram_url = f"https://t.me/share/url?text={encoded}"

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(f"📅 {t['daily_title']}", callback_data="daily"),
                InlineKeyboardButton(f"📤 {t['share_whatsapp']}", url=whatsapp_url),
            ],
            [
                InlineKeyboardButton(f"📣 {t['share_telegram']}", url=telegram_url),
                InlineKeyboardButton(f"✨ {t['new_quote']}", callback_data="new_quote"),
            ],
            [
                InlineKeyboardButton(f"🔄 {t['change_topic']}", callback_data="change_topic"),
                InlineKeyboardButton(f"⚙️ {t['settings']}", callback_data="settings"),
            ],
        ]
    )


def settings_buttons(lang: str) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"🌐 {t['lang']}", callback_data="settings:lang")],
            [InlineKeyboardButton(f"⬅️ {t['back']}", callback_data="back_menu")],
        ]
    )


# ----------------------------
# RENDER HELPERS
# ----------------------------
def build_quote_message(quote: str, sponsored: str = "") -> str:
    quote = (quote or "").strip()
    if sponsored:
        return f"{quote}\n\n{ sponsored }"
    return quote


def user_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang") or "tr"


def user_topic(context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
    return context.user_data.get("topic")


# ----------------------------
# HANDLERS
# ----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Every /start => ask language first (as requested).
    After language => ask topic.
    """
    context.user_data.clear()
    # mark flow state
    context.user_data["awaiting_lang"] = True
    await update.effective_message.reply_text(
        "🇹🇷 Dil seçiniz / 🇬🇧 Choose language:",
        reply_markup=language_keyboard(),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()

    data = query.data or ""

    # ----- Language selection -----
    if data.startswith("lang:"):
        lang = data.split(":", 1)[1].strip()
        if lang not in ("tr", "en"):
            lang = "tr"
        context.user_data["lang"] = lang
        context.user_data.pop("awaiting_lang", None)

        # After language selection => ask topic (no extra marketing text)
        await query.edit_message_text(
            TEXTS[lang]["pick_topic"],
            reply_markup=categories_buttons(lang),
        )
        return

    lang = user_lang(context)

    # ----- Category selection -----
    if data.startswith("cat:"):
        category = data.split(":", 1)[1]
        context.user_data["topic"] = category

        q = random_quote_from_category(lang, category)
        if not q:
            await query.edit_message_text(TEXTS[lang]["no_quotes"])
            return

        # save last quote for sharing buttons
        context.user_data["last_quote"] = q

        sponsored = fetch_adsgram_ad()
        msg = build_quote_message(q, sponsored=sponsored)

        await query.edit_message_text(
            msg,
            parse_mode="Markdown",
            disable_web_page_preview=False,
            reply_markup=menu_buttons(lang, quote_text=q),
        )
        return

    # ----- Daily quote button -----
    if data == "daily":
        dq = get_daily_quote(lang)
        if not dq:
            await query.answer("No daily quote.", show_alert=False)
            return

        context.user_data["last_quote"] = dq
        sponsored = fetch_adsgram_ad()
        msg = build_quote_message(dq, sponsored=sponsored)

        await query.edit_message_text(
            msg,
            parse_mode="Markdown",
            disable_web_page_preview=False,
            reply_markup=menu_buttons(lang, quote_text=dq),
        )
        return

    # ----- New quote (within topic) -----
    if data == "new_quote":
        category = user_topic(context)
        if not category:
            # if topic not set, ask topic
            await query.edit_message_text(
                TEXTS[lang]["pick_topic"],
                reply_markup=categories_buttons(lang),
            )
            return

        q = random_quote_from_category(lang, category)
        if not q:
            await query.edit_message_text(TEXTS[lang]["no_quotes"])
            return

        context.user_data["last_quote"] = q
        sponsored = fetch_adsgram_ad()
        msg = build_quote_message(q, sponsored=sponsored)

        await query.edit_message_text(
            msg,
            parse_mode="Markdown",
            disable_web_page_preview=False,
            reply_markup=menu_buttons(lang, quote_text=q),
        )
        return

    # ----- Change topic -----
    if data == "change_topic":
        await query.edit_message_text(
            TEXTS[lang]["pick_topic"],
            reply_markup=categories_buttons(lang),
        )
        return

    # ----- Settings -----
    if data == "settings":
        await query.edit_message_text(
            TEXTS[lang]["settings"],
            reply_markup=settings_buttons(lang),
        )
        return

    if data == "settings:lang":
        # language change from settings
        context.user_data["awaiting_lang"] = True
        await query.edit_message_text(
            TEXTS[lang]["pick_lang"],
            reply_markup=language_keyboard(),
        )
        return

    if data == "back_menu":
        # return to last quote if present, else topic selection
        last = (context.user_data.get("last_quote") or "").strip()
        if last:
            sponsored = fetch_adsgram_ad()
            msg = build_quote_message(last, sponsored=sponsored)
            await query.edit_message_text(
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=False,
                reply_markup=menu_buttons(lang, quote_text=last),
            )
        else:
            await query.edit_message_text(
                TEXTS[lang]["pick_topic"],
                reply_markup=categories_buttons(lang),
            )
        return

    # fallback
    await query.answer("OK", show_alert=False)


# ----------------------------
# SCHEDULER (Daily quote at 10:00)
# ----------------------------
def _next_run_10am() -> datetime:
    now = datetime.now(TZ)
    run = now.replace(hour=10, minute=0, second=0, microsecond=0)
    if now >= run:
        run = run + timedelta(days=1)
    return run


def start_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone=TZ)
    # compute daily quote at 10:00 every day
    sched.add_job(
        compute_daily_if_needed,
        trigger="cron",
        hour=10,
        minute=0,
        id="compute_daily",
        replace_existing=True,
    )
    sched.start()
    logger.info("Scheduler started. Next 10:00 run (approx): %s", _next_run_10am().isoformat())
    return sched


# ----------------------------
# MAIN
# ----------------------------
def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Set it in environment variables.")

    # Ensure daily quote exists for today on boot as well
    compute_daily_if_needed()

    # Start cron scheduler
    start_scheduler()

    application: Application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot started.")
    application.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
