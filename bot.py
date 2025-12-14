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
import time as pytime
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
from telegram.error import BadRequest, Conflict


# ----------------------------
# CONFIG
# ----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADSGRAM_PLATFORM_ID = os.getenv("ADSGRAM_PLATFORM_ID", "16417").strip()  # dashboard PlatformID (informational)
ADSGRAM_BLOCK_ID = os.getenv("ADSGRAM_BLOCK_ID", "bot-17933").strip()  # dashboard Block UnitID  # example: bot-17933

# Europe/Istanbul is UTC+3 (no DST)
TZ = timezone(timedelta(hours=3))

STATE_FILE = "state.json"  # persisted daily quote (in working dir)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("quote-masters-bot")

async def safe_edit_message_text(query, text: str, **kwargs):
    """Edit message text but ignore Telegram 'message is not modified' errors."""
    try:
        return await query.edit_message_text(text, **kwargs)
    except BadRequest as e:
        if 'Message is not modified' in str(e):
            logger.info('Edit skipped (message is not modified).')
            try:
                await query.answer()
            except Exception:
                pass
            return None
        raise


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
# ADSGRAM (Telegram bot integration)
# ----------------------------
# IMPORTANT:
# AdsGram's official bot endpoint expects:
#   https://api.adsgram.ai/advbot?tgid={TELEGRAM_USER_ID}&blockid={BLOCK_ID}[&language=tr|en]
# and BLOCK_ID should be numeric (WITHOUT the 'bot-' prefix).  See docs:
# https://docs.adsgram.ai/bots/block-integration

import asyncio
import re


def _normalize_adsgram_blockid(raw: str) -> str:
    raw = (raw or "").strip()
    raw = raw.replace("bot-", "").strip()
    # keep digits only
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits


ADSGRAM_ENABLED = os.getenv("ADSGRAM_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
ADSGRAM_SHOW_EVERY = int(os.getenv("ADSGRAM_SHOW_EVERY", "3"))  # show an ad every N quote views (0=never)
ADSGRAM_MIN_INTERVAL_SEC = int(os.getenv("ADSGRAM_MIN_INTERVAL_SEC", "90"))  # per-user minimum seconds between ads
DEBUG_ADSGRAM = os.getenv("DEBUG_ADSGRAM", "0").strip().lower() in ("1", "true", "yes", "on")
ADSGRAM_LANG_MODE = os.getenv("ADSGRAM_LANG_MODE", "auto").strip().lower()  # auto|force|none


ADSGRAM_INCLUDE_LABEL = os.getenv("ADSGRAM_INCLUDE_LABEL", "0").strip() == "1"  # optional "🟣 Sponsored" prefix


def _adsgram_gate_check(context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, str]:
    """Per-user frequency cap (stored in user_data). Also bumps quote view counter.

    Returns: (allowed, reason)
    """
    views = int(context.user_data.get("quote_views", 0)) + 1
    context.user_data["quote_views"] = views

    if (not ADSGRAM_ENABLED) or (not ADSGRAM_BLOCK_ID):
        return False, "disabled_or_missing_blockid"

    if ADSGRAM_SHOW_EVERY <= 0:
        return False, "show_every<=0"

    if views % ADSGRAM_SHOW_EVERY != 0:
        return False, f"not_nth_view (views={views}, every={ADSGRAM_SHOW_EVERY})"

    now_ts = int(datetime.now(TZ).timestamp())
    last_ts = int(context.user_data.get("last_ad_ts", 0) or 0)
    if last_ts and (now_ts - last_ts) < ADSGRAM_MIN_INTERVAL_SEC:
        return False, f"min_interval (delta={now_ts-last_ts}s < {ADSGRAM_MIN_INTERVAL_SEC}s)"

    return True, "ok"


def _mark_ad_sent(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["last_ad_ts"] = int(datetime.now(TZ).timestamp())


def fetch_adsgram_ad_sync(tgid: int, lang: str) -> Optional[dict]:
    """Fetch an ad from AdsGram. Returns a dict or None.

    Endpoint:
      https://api.adsgram.ai/advbot?tgid={TELEGRAM_USER_ID}&blockid={BLOCK_ID}[&language=tr|en]
    """
    if not ADSGRAM_BLOCK_ID:
        logger.info("AdsGram: ADSGRAM_BLOCK_ID not set; skipping.")
        return None

    blockid = _normalize_adsgram_blockid(ADSGRAM_BLOCK_ID)
    if not blockid:
        logger.info("AdsGram: invalid blockid=%r; skipping.", ADSGRAM_BLOCK_ID)
        return None

    url = "https://api.adsgram.ai/advbot"
    params = {"tgid": str(int(tgid)), "blockid": blockid}
    if ADSGRAM_LANG_MODE == "force" and lang in ("tr", "en"):
        params["language"] = lang
    elif ADSGRAM_LANG_MODE == "auto" and lang == "en":
        params["language"] = "en"

    if DEBUG_ADSGRAM:
        logger.info("AdsGram request params: %s", params)

    try:
        r = requests.get(url, params=params, timeout=10)
        if DEBUG_ADSGRAM:
            ct = (r.headers.get('content-type') or '').split(';')[0].strip()
            logger.info('AdsGram response: status=%s content_type=%s len=%s', r.status_code, ct, len(r.text or ''))
    except Exception as e:
        logger.warning("AdsGram request failed: %s", e)
        return None

    body = (r.text or "").strip()

    if r.status_code != 200:
        logger.info("AdsGram non-200: status=%s body=%r", r.status_code, body[:160])
        return None

    if not body:
        logger.info("AdsGram empty response (no ad fill?) for tgid=%s blockid=%s", tgid, blockid)
        return None

    try:
        data = r.json()
    except Exception:
        logger.info("AdsGram non-JSON response (treat as no ad): %r", body[:200])
        return None

    if not isinstance(data, dict):
        logger.info("AdsGram unexpected JSON type: %s", type(data))
        return None

    if not (data.get("text_html") or "").strip():
        logger.info("AdsGram JSON without text_html (no ad).")
        return None

    logger.info(
        "AdsGram OK: tgid=%s blockid=%s html_len=%s img=%s",
        tgid,
        blockid,
        len((data.get("text_html") or "")),
        bool(data.get("image_url")),
    )
    return data


async def fetch_adsgram_ad(tgid: int, lang: str) -> Optional[dict]:
    # requests is blocking; offload to thread
    return await asyncio.to_thread(fetch_adsgram_ad_sync, tgid, lang)


def _adsgram_reply_markup(ad: dict) -> Optional[InlineKeyboardMarkup]:
    rows = []
    btn = (ad.get("button_name") or "").strip()
    url = (ad.get("click_url") or "").strip()
    if btn and url:
        rows.append([InlineKeyboardButton(btn, url=url)])

    btn2 = (ad.get("button_reward_name") or "").strip()
    url2 = (ad.get("reward_url") or "").strip()
    if btn2 and url2:
        rows.append([InlineKeyboardButton(btn2, url=url2)])

    return InlineKeyboardMarkup(rows) if rows else None


async def maybe_send_adsgram(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lang: str,
    reply_to_message_id: Optional[int] = None,
) -> None:
    """Call this after you show a quote. It will decide (rate-limit) and send an AdsGram ad as a reply."""
    allowed, reason = _adsgram_gate_check(context)
    if not allowed:
        if DEBUG_ADSGRAM:
            logger.info("AdsGram gate blocked: %s", reason)
        return

    if not update.effective_user or not update.effective_chat:
        return

    ad = await fetch_adsgram_ad(update.effective_user.id, lang=lang)
    if not ad:
        return

    text_html = (ad.get("text_html") or "").strip()
    if ADSGRAM_INCLUDE_LABEL:
        text_html = f"🟣 <b>Sponsored</b>\n\n{text_html}"

    markup = _adsgram_reply_markup(ad)
    image_url = (ad.get("image_url") or "").strip()

    try:
        if image_url:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=image_url,
                caption=text_html,
                parse_mode="HTML",
                reply_markup=markup,
                protect_content=True,
                reply_to_message_id=reply_to_message_id,
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text_html,
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=False,
                protect_content=True,
                reply_to_message_id=reply_to_message_id,
            )

        _mark_ad_sent(context)
        return

    except Exception as e:
        logger.warning("AdsGram send failed (fallback to text): %s", e)
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=re.sub(r"<[^>]+>", "", text_html),
                disable_web_page_preview=False,
                protect_content=True,
                reply_to_message_id=reply_to_message_id,
            )
            _mark_ad_sent(context)
        except Exception as e2:
            logger.warning("AdsGram fallback send failed: %s", e2)
        return

# ----------------------------
# QUOTE HELPERS
# ----------------------------
def all_quotes(lang: str) -> List[Tuple[str, str]]:
    """Return list of (category, quote) for a language.

    If TOPICS exist in quotes.py, we prefer limiting the pool to those topic categories.
    Falls back to all categories if none of the topic keys are found.
    """
    src = QUOTES_TR if lang == "tr" else QUOTES_EN

    # Try to limit to the configured TOPICS first (more consistent UX)
    topic_keys: List[str] = []
    for t in TOPICS:
        # pick the first matching key for this language
        for cand in _category_candidates(lang, t["id"]):
            if cand and cand in src:
                topic_keys.append(cand)
                break
    # de-duplicate while keeping order
    seen = set()
    topic_keys = [k for k in topic_keys if not (k in seen or seen.add(k))]

    use_keys = topic_keys if topic_keys else list(src.keys())

    out: List[Tuple[str, str]] = []
    for cat in use_keys:
        arr = src.get(cat) or []
        if not arr:
            continue
        for q in arr:
            q = str(q).strip()
            if q:
                out.append((cat, q))
    return out

def random_quote_from_category(lang: str, category: str) -> Optional[str]:
    """Random quote from an explicit category key (as it exists in QUOTES_TR/QUOTES_EN)."""
    src = QUOTES_TR if lang == "tr" else QUOTES_EN
    arr = src.get(category) or []
    arr = [str(x).strip() for x in arr if str(x).strip()]
    if not arr:
        return None
    return random.choice(arr)


def random_quote_from_topic(lang: str, topic_id: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (category_key_used, quote). Tries multiple category key candidates."""
    src = QUOTES_TR if lang == "tr" else QUOTES_EN
    key = _pick_existing_category_key(lang, topic_id)
    if not key:
        return None, None
    arr = src.get(key) or []
    arr = [str(x).strip() for x in arr if str(x).strip()]
    if not arr:
        return key, None
    return key, random.choice(arr)


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



TOPICS = [
    {"id": "love", "tr": "Aşk", "en": "Love"},
    {"id": "life", "tr": "Hayat", "en": "Life"},
    {"id": "motivation_inspiration", "tr": "Motivasyon & İlham", "en": "Motivation & Inspiration"},
    {"id": "success", "tr": "Başarı", "en": "Success"},
    {"id": "friendship", "tr": "Dostluk", "en": "Friendship"},
    {"id": "happiness", "tr": "Mutluluk", "en": "Happiness"},
    {"id": "wisdom", "tr": "Bilgelik", "en": "Wisdom"},
    {"id": "leadership", "tr": "Liderlik", "en": "Leadership"},
    {"id": "confidence", "tr": "Özgüven", "en": "Confidence"},
    {"id": "funny", "tr": "Komik", "en": "Funny"},
]


def _topic_by_id(topic_id: str) -> Optional[dict]:
    for t in TOPICS:
        if t["id"] == topic_id:
            return t
    return None


def _category_candidates(lang: str, topic_id: str) -> List[str]:
    """Return possible category keys for QUOTES_TR / QUOTES_EN.

    We try:
      1) Language-specific label (e.g., 'Aşk' for TR, 'Love' for EN)
      2) Bilingual key 'Aşk / Love' (in case quotes.py uses bilingual keys)
      3) The other language label as fallback
    """
    t = _topic_by_id(topic_id) or {}
    tr_label = (t.get("tr") or "").strip()
    en_label = (t.get("en") or "").strip()
    bilingual = f"{tr_label} / {en_label}".strip(" /")
    if lang == "tr":
        return [tr_label, bilingual, en_label]
    return [en_label, bilingual, tr_label]


def _pick_existing_category_key(lang: str, topic_id: str) -> Optional[str]:
    src = QUOTES_TR if lang == "tr" else QUOTES_EN
    for cand in _category_candidates(lang, topic_id):
        if cand and cand in src:
            return cand
    return None


def categories_buttons(lang: str) -> InlineKeyboardMarkup:
    """Topic picker keyboard: 5 rows × 2 columns, stable layout."""
    rows: List[List[InlineKeyboardButton]] = []
    # 5x2 grid (10 topics)
    for i in range(0, len(TOPICS), 2):
        pair = TOPICS[i : i + 2]
        row: List[InlineKeyboardButton] = []
        for t in pair:
            # Show in selected language only (keeps buttons shorter and more stable)
            label = t["tr"] if lang == "tr" else t["en"]
            row.append(InlineKeyboardButton(label, callback_data=f"topic:{t['id']}"))
        rows.append(row)

    t = TEXTS[lang]
    rows.append([InlineKeyboardButton(f"⬅️ {t['back']}", callback_data="back_language")])
    return InlineKeyboardMarkup(rows)




def menu_buttons(lang: str, quote_text: str = "") -> InlineKeyboardMarkup:
    t = TEXTS[lang]

    quote_plain = (quote_text or "").strip()

    if lang == "tr":
        support_line = "💫 Destek olmak için @QuoteMastersBot’a katıl:\nhttps://t.me/QuoteMastersBot"
    else:
        support_line = "💫 Support @QuoteMastersBot:\nhttps://t.me/QuoteMastersBot"

    share_text = (quote_plain + "\n\n" + support_line).strip()
    encoded = requests.utils.quote(share_text)

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
                InlineKeyboardButton(f"🧩 {t['change_topic']}", callback_data="change_topic"),
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
# Invisible padding to keep the message height more stable on short quotes.
# U+3164 HANGUL FILLER renders as "blank" in Telegram.
_PAD_CHAR = "\u3164"
QUOTE_MIN_LINES = int(os.getenv("QUOTE_MIN_LINES", "8"))


def _pad_to_min_lines(msg: str) -> str:
    lines = (msg or "").splitlines()
    line_count = max(1, len(lines))
    if QUOTE_MIN_LINES <= 1:
        return msg
    if line_count >= QUOTE_MIN_LINES:
        return msg
    need = QUOTE_MIN_LINES - line_count
    return msg + ("\n" + _PAD_CHAR) * need


def build_quote_message(quote: str, sponsored: str = "") -> str:
    quote = (quote or "").strip()
    msg = f"{quote}\n\n{ sponsored }" if sponsored else quote
    return _pad_to_min_lines(msg)


def user_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang") or "tr"


def user_topic(context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
    # New: store topic id under "topic_id"
    return context.user_data.get("topic_id") or context.user_data.get("topic")


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
        await safe_edit_message_text(
            query,
            TEXTS[lang]["pick_topic"],
            reply_markup=categories_buttons(lang),
        )
        return

    lang = user_lang(context)

        # ----- Topic selection -----
    if data.startswith("topic:"):
        topic_id = data.split(":", 1)[1].strip()
        if not _topic_by_id(topic_id):
            await safe_edit_message_text(query, TEXTS[lang]["pick_topic"], reply_markup=categories_buttons(lang))
            return

        context.user_data["topic_id"] = topic_id

        cat_key, q = random_quote_from_topic(lang, topic_id)
        if not q:
            await safe_edit_message_text(query, TEXTS[lang]["no_quotes"])
            return

        # save last quote for sharing buttons
        context.user_data["last_quote"] = q
        msg = build_quote_message(q)

        await safe_edit_message_text(
            query,
            msg,
            parse_mode="Markdown",
            disable_web_page_preview=False,
            reply_markup=menu_buttons(lang, quote_text=q),
        )
        # AdsGram ad as a reply under the quote (rate-limited)
        reply_to = query.message.message_id if query.message else None
        await maybe_send_adsgram(update, context, lang, reply_to_message_id=reply_to)
        return

        # ----- Legacy category buttons (backward compatibility) -----
    if data.startswith("cat:"):
        category = data.split(":", 1)[1].strip()
        context.user_data["topic"] = category

        q = random_quote_from_category(lang, category)
        if not q:
            await safe_edit_message_text(query, TEXTS[lang]["no_quotes"])
            return

        context.user_data["last_quote"] = q
        msg = build_quote_message(q)

        await safe_edit_message_text(
            query,
            msg,
            parse_mode="Markdown",
            disable_web_page_preview=False,
            reply_markup=menu_buttons(lang, quote_text=q),
        )
        reply_to = query.message.message_id if query.message else None
        await maybe_send_adsgram(update, context, lang, reply_to_message_id=reply_to)
        return

# ----- Daily quote button -----
    if data == "daily":
        dq = get_daily_quote(lang)
        if not dq:
            await query.answer("No daily quote.", show_alert=False)
            return

        context.user_data["last_quote"] = dq
        msg = build_quote_message(dq)

        await safe_edit_message_text(
            query,
            msg,
            parse_mode="Markdown",
            disable_web_page_preview=False,
            reply_markup=menu_buttons(lang, quote_text=dq),
        )
        # AdsGram ad as a reply under the quote (rate-limited)
        reply_to = query.message.message_id if query.message else None
        await maybe_send_adsgram(update, context, lang, reply_to_message_id=reply_to)
        return

    # ----- New quote (within topic) -----
    if data == "new_quote":
        topic_id = user_topic(context)
        if not topic_id:
            # if topic not set, ask topic
            await safe_edit_message_text(
                query,
                TEXTS[lang]["pick_topic"],
                reply_markup=categories_buttons(lang),
            )
            return

        # Backward compat: if "topic_id" is actually a category key, use it directly.
        if _topic_by_id(topic_id):
            _, q = random_quote_from_topic(lang, topic_id)
        else:
            q = random_quote_from_category(lang, topic_id)

        if not q:
            await safe_edit_message_text(query, TEXTS[lang]["no_quotes"])
            return

        context.user_data["last_quote"] = q
        msg = build_quote_message(q)

        await safe_edit_message_text(
            query,
            msg,
            parse_mode="Markdown",
            disable_web_page_preview=False,
            reply_markup=menu_buttons(lang, quote_text=q),
        )
        # AdsGram ad as a reply under the quote (rate-limited)
        reply_to = query.message.message_id if query.message else None
        await maybe_send_adsgram(update, context, lang, reply_to_message_id=reply_to)
        return

    # ----- Change topic -----
    if data == "change_topic":
        await safe_edit_message_text(
            query,
            TEXTS[lang]["pick_topic"],
            reply_markup=categories_buttons(lang),
        )
        return

    # ----- Settings -----
    if data == "settings":
        await safe_edit_message_text(
            query,
            TEXTS[lang]["settings"],
            reply_markup=settings_buttons(lang),
        )
        return

    if data == "settings:lang":
        # language change from settings
        context.user_data["awaiting_lang"] = True
        await safe_edit_message_text(
            query,
            TEXTS[lang]["pick_lang"],
            reply_markup=language_keyboard(),
        )
        return

    if data == "back_language":
        # Return to language selection screen
        await safe_edit_message_text(
            query,
            TEXTS[lang]["pick_lang"],
            reply_markup=language_keyboard(),
        )
        return

    if data == "back_menu":
        # return to last quote if present, else topic selection
        last = (context.user_data.get("last_quote") or "").strip()
        if last:
            msg = build_quote_message(last)
            await safe_edit_message_text(
                query,
                msg,
                parse_mode="Markdown",
                disable_web_page_preview=False,
                reply_markup=menu_buttons(lang, quote_text=last),
            )
            # AdsGram ad as a reply under the quote (rate-limited)
            reply_to = query.message.message_id if query.message else None
            await maybe_send_adsgram(update, context, lang, reply_to_message_id=reply_to)
        else:
            await safe_edit_message_text(
                query,
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

async def adtest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manual AdsGram test: forces a request and shows result (useful for debugging)."""
    lang = (context.user_data.get("lang") or "tr").strip().lower()
    if lang not in ("tr", "en"):
        lang = "tr"

    if not update.effective_user or not update.effective_chat or not update.message:
        return

    ad = await fetch_adsgram_ad(update.effective_user.id, lang=lang)
    if not ad:
        await update.message.reply_text(
            f"AdsGram: No ad returned. blockid={_normalize_adsgram_blockid(ADSGRAM_BLOCK_ID)}\n"
            "Not: Block onaylı mı? Dashboard’da Approved olmalı. Bazen fill-rate 0 olabilir.",
            disable_web_page_preview=True,
        )
        return

    text_html = (ad.get("text_html") or "").strip()
    if ADSGRAM_INCLUDE_LABEL:
        text_html = f"🟣 <b>Sponsored</b>\n\n{text_html}"
    markup = _adsgram_reply_markup(ad)
    image_url = (ad.get("image_url") or "").strip()

    if image_url:
        await update.message.reply_photo(
            photo=image_url,
            caption=text_html,
            parse_mode="HTML",
            reply_markup=markup,
            protect_content=True,
        )
    else:
        await update.message.reply_text(
            text_html,
            parse_mode="HTML",
            reply_markup=markup,
            protect_content=True,
            disable_web_page_preview=False,
        )


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Set it in environment variables.")

    # Ensure daily quote exists for today on boot as well
    compute_daily_if_needed()

    # Start cron scheduler
    start_scheduler()

    def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Prevents "No error handlers are registered" and logs exceptions clearly
        logger.exception("Unhandled exception while processing an update", exc_info=context.error)

    def _build_application() -> Application:
        app: Application = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("adtest", adtest))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_error_handler(_error_handler)
        return app

    # Start polling with conflict-retry (helps during rolling deploy overlap)
    while True:
        application = _build_application()
        logger.info("Bot started.")
        try:
            application.run_polling(close_loop=False)
            break
        except Conflict:
            logger.warning("Polling conflict (409). Another instance is polling. Retrying in 10s...")
            pytime.sleep(10)
        except Exception:
            logger.exception("Polling crashed. Retrying in 5s...")
            pytime.sleep(5)


if __name__ == "__main__":
    main()