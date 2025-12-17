# -*- coding: utf-8 -*-
"""
QuoteMastersBot - FINAL bot.py
Features:
- TR/EN language selection on /start (and from Settings)
- Fixed 10 topics in a 5x2 grid
- Stable quote "card" height via invisible padding lines
- AdsGram ads:
  - Sent automatically right after each quote (reply under the quote)
  - "Sponsored" label is underlined + bold (HTML)
  - Ad text trimmed to max 4 lines
  - Open / Reward buttons (if present)
  - Menu includes a 📣 Sponsored button to fetch an ad on demand
- Push ads (opt-out):
  - Default ON for all users
  - Sends 1 ad per hour between 12:00–18:00 (Europe/Istanbul)
  - Users can disable from Settings

Env vars:
- BOT_TOKEN (required)
- ADSGRAM_BLOCK_ID (e.g. "bot-17933" or "17933")
- ADSGRAM_SHOW_EVERY (default 1)
- ADSGRAM_MIN_INTERVAL_SEC (default 0)
- ADSGRAM_MAX_LINES (default 4)
- QUOTE_MIN_LINES (default 10)
- PUSH_ADS_ENABLED (default 1)
- PUSH_ADS_START_HOUR (default 12)
- PUSH_ADS_END_HOUR (default 18)  # inclusive
- DEBUG_ADSGRAM (default 0)
"""

from __future__ import annotations

import asyncio
import html as _html
import json
import logging
import os
import random
import re
import textwrap
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional, Tuple

import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, Conflict, Forbidden, NetworkError, TimedOut
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# --- Quotes store (your repo should include quotes.py) ---
# QUOTES_TR / QUOTES_EN = dict[str, list[str]]
from quotes import QUOTES_TR, QUOTES_EN  # type: ignore

# ----------------------------
# CONFIG
# ----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

ADSGRAM_BLOCK_ID_RAW = os.getenv("ADSGRAM_BLOCK_ID", "bot-17933").strip()
# AdsGram requires numeric blockid (without "bot-")
ADSGRAM_BLOCK_ID = re.sub(r"^bot-", "", ADSGRAM_BLOCK_ID_RAW).strip()

ADSGRAM_SHOW_EVERY = int(os.getenv("ADSGRAM_SHOW_EVERY", "1") or "1")
ADSGRAM_MIN_INTERVAL_SEC = int(os.getenv("ADSGRAM_MIN_INTERVAL_SEC", "0") or "0")
ADSGRAM_MAX_LINES = int(os.getenv("ADSGRAM_MAX_LINES", "4") or "4")

QUOTE_MIN_LINES = int(os.getenv("QUOTE_MIN_LINES", "10") or "10")

PUSH_ADS_ENABLED = (os.getenv("PUSH_ADS_ENABLED", "1").strip() != "0")
PUSH_ADS_START_HOUR = int(os.getenv("PUSH_ADS_START_HOUR", "12") or "12")
PUSH_ADS_END_HOUR = int(os.getenv("PUSH_ADS_END_HOUR", "18") or "18")  # inclusive

DEBUG_ADSGRAM = (os.getenv("DEBUG_ADSGRAM", "0").strip() == "1")

STATE_FILE = "state.json"
TZ_NAME = "Europe/Istanbul"
TZ = ZoneInfo(TZ_NAME)

# ----------------------------
# LOGGING
# ----------------------------
logger = logging.getLogger("quote-masters-bot")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# ----------------------------
# UI TEXTS
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
        "push_ads": "Reklam Bildirimleri",
        "push_on": "Açık",
        "push_off": "Kapalı",
        "sponsored_btn": "📣 Sponsored",
        "no_quotes": "Bu kategoride henüz söz yok.",
        "support_line": "Destek olmak için @QuoteMastersBot’u takip et 💫",
        "bot_link": "https://t.me/QuoteMastersBot",
    },
    "en": {
        "pick_lang": "Please choose a language:",
        "pick_topic": "Choose a topic:",
        "daily_title": "Daily Quote",
        "new_quote": "New Quote",
        "change_topic": "Change topic",
        "settings": "Settings",
        "share_whatsapp": "Share on WhatsApp",
        "share_telegram": "Share on Telegram",
        "back": "Back",
        "lang": "Change Language",
        "push_ads": "Ad Notifications",
        "push_on": "On",
        "push_off": "Off",
        "sponsored_btn": "📣 Sponsored",
        "no_quotes": "No quotes in this category yet.",
        "support_line": "Support by following @QuoteMastersBot 💫",
        "bot_link": "https://t.me/QuoteMastersBot",
    },
}

# ----------------------------
# TOPICS (fixed 10, 5x2 grid)
# ----------------------------
TOPIC_KEYS = [
    "love",
    "life",
    "motivation",
    "success",
    "friendship",
    "happiness",
    "wisdom",
    "leadership",
    "confidence",
    "funny",
]

TOPIC_LABELS = {
    "tr": {
        "love": "Aşk",
        "life": "Hayat",
        "motivation": "Motivasyon & İlham",
        "success": "Başarı",
        "friendship": "Dostluk",
        "happiness": "Mutluluk",
        "wisdom": "Bilgelik",
        "leadership": "Liderlik",
        "confidence": "Özgüven",
        "funny": "Komik",
    },
    "en": {
        "love": "Love",
        "life": "Life",
        "motivation": "Motivation & Inspiration",
        "success": "Success",
        "friendship": "Friendship",
        "happiness": "Happiness",
        "wisdom": "Wisdom",
        "leadership": "Leadership",
        "confidence": "Confidence",
        "funny": "Funny",
    },
}

# ----------------------------
# STATE
# ----------------------------
def _load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Failed to save state: %s", e)


STATE: dict = _load_state()


def _user_key(user_id: int) -> str:
    return str(user_id)


def get_user(state: dict, user_id: int) -> dict:
    users = state.setdefault("users", {})
    u = users.setdefault(
        _user_key(user_id),
        {
            "lang": None,
            "topic": "motivation",
            "last_quote": "",
            "quote_count": 0,
            "last_ad_ts": 0,
            "chat_id": None,
            "push_ads_disabled": False,  # default ON (opt-out)
            "last_push_slot": "",  # e.g. "2025-12-17T12"
        },
    )
    return u


def set_user(state: dict, user_id: int, u: dict) -> None:
    state.setdefault("users", {})[_user_key(user_id)] = u


# ----------------------------
# QUOTE HELPERS
# ----------------------------
def _quotes_dict(lang: str) -> Dict[str, List[str]]:
    return QUOTES_TR if lang == "tr" else QUOTES_EN


def resolve_category(lang: str, topic_key: str) -> Optional[str]:
    """
    Resolve the category key that exists inside QUOTES_TR/QUOTES_EN.
    Tries exact match first, then fuzzy match, then bilingual key match.
    """
    src = _quotes_dict(lang)
    desired = TOPIC_LABELS[lang][topic_key]

    if desired in src:
        return desired

    # try bilingual "Aşk / Love" style
    for k in src.keys():
        k_norm = str(k).lower().strip()
        if desired.lower() in k_norm:
            return k

    # last resort: any category
    return None


def all_quotes(lang: str) -> List[Tuple[str, str]]:
    src = _quotes_dict(lang)
    out: List[Tuple[str, str]] = []
    for cat, arr in src.items():
        if not arr:
            continue
        for q in arr:
            q = str(q).strip()
            if q:
                out.append((str(cat), q))
    return out


def pick_random_quote(lang: str, topic_key: str) -> Optional[str]:
    src = _quotes_dict(lang)
    cat = resolve_category(lang, topic_key)
    if cat and cat in src and src[cat]:
        return random.choice(src[cat]).strip()

    # fallback: random from all
    pool = all_quotes(lang)
    if not pool:
        return None
    _, q = random.choice(pool)
    return q.strip()


def compute_daily_if_needed() -> None:
    """Ensure STATE['daily'] exists for today (TR and EN)."""
    global STATE
    now = datetime.now(TZ)
    today = now.date().isoformat()
    daily = STATE.get("daily", {})
    if daily.get("date") == today and daily.get("tr") and daily.get("en"):
        return

    for lang in ("tr", "en"):
        pool = all_quotes(lang)
        if not pool:
            chosen = {"category": "", "text": ""}
        else:
            cat, q = random.choice(pool)
            chosen = {"category": cat, "text": q}
        daily[lang] = chosen

    daily["date"] = today
    STATE["daily"] = daily
    _save_state(STATE)
    logger.info("Daily quote computed for %s", today)


def get_daily_quote(lang: str) -> Optional[str]:
    compute_daily_if_needed()
    daily = STATE.get("daily", {})
    payload = daily.get(lang, {})
    q = (payload or {}).get("text", "")
    q = str(q).strip()
    return q or None


# ----------------------------
# RENDER / FORMATTING
# ----------------------------
def pad_to_min_lines(text: str, min_lines: int) -> str:
    # add extra invisible lines to keep message height stable
    lines = text.splitlines()
    if len(lines) >= min_lines:
        return text
    missing = min_lines - len(lines)
    # each added line has a zero-width char to prevent Telegram from trimming empty lines
    return text + ("\n\u200b" * missing)


def format_quote_html(lang: str, quote: str) -> str:
    # Escape user-visible quote to avoid HTML injection
    q = _html.escape(quote.strip())
    # Use consistent structure for stable sizing
    if lang == "tr":
        body = f"“{q}”"
    else:
        body = f"“{q}”"

    msg = f"{body}"
    return pad_to_min_lines(msg, QUOTE_MIN_LINES)


def build_share_text(lang: str, quote: str) -> str:
    t = TEXTS[lang]
    q = quote.strip()
    return f"{q}\n\n{t['support_line']}\n{t['bot_link']}"


def whatsapp_share_url(lang: str, quote: str) -> str:
    import urllib.parse

    txt = build_share_text(lang, quote)
    return "https://wa.me/?text=" + urllib.parse.quote(txt)


def telegram_share_url(lang: str, quote: str) -> str:
    import urllib.parse

    txt = build_share_text(lang, quote)
    # Telegram share: include text only
    return "https://t.me/share/url?text=" + urllib.parse.quote(txt)


# ----------------------------
# KEYBOARDS
# ----------------------------
def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang:tr")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")],
        ]
    )


def topic_keyboard(lang: str) -> InlineKeyboardMarkup:
    # 5 rows x 2 columns
    rows: List[List[InlineKeyboardButton]] = []
    keys = TOPIC_KEYS[:]
    for i in range(0, len(keys), 2):
        k1 = keys[i]
        k2 = keys[i + 1]
        rows.append(
            [
                InlineKeyboardButton(TOPIC_LABELS[lang][k1], callback_data=f"topic:{k1}"),
                InlineKeyboardButton(TOPIC_LABELS[lang][k2], callback_data=f"topic:{k2}"),
            ]
        )
    # back -> language selection
    rows.append([InlineKeyboardButton(f"⬅️ {TEXTS[lang]['back']}", callback_data="back_lang")])
    return InlineKeyboardMarkup(rows)


def menu_keyboard(lang: str, quote_text: str) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(f"📅 {t['daily_title']}", callback_data="daily"),
                InlineKeyboardButton(f"🔁 {t['new_quote']}", callback_data="new"),
            ],
            [
                InlineKeyboardButton(f"🧩 {t['change_topic']}", callback_data="change_topic"),
                InlineKeyboardButton(t["sponsored_btn"], callback_data="show_ad"),
            ],
            [
                InlineKeyboardButton(f"📤 {t['share_whatsapp']}", url=whatsapp_share_url(lang, quote_text)),
                InlineKeyboardButton(f"📨 {t['share_telegram']}", url=telegram_share_url(lang, quote_text)),
            ],
            [InlineKeyboardButton(f"⚙️ {t['settings']}", callback_data="settings")],
        ]
    )


def settings_keyboard(lang: str, push_disabled: bool) -> InlineKeyboardMarkup:
    t = TEXTS[lang]
    status = t["push_off"] if push_disabled else t["push_on"]
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"🌐 {t['lang']}", callback_data="settings:lang")],
            [InlineKeyboardButton(f"📣 {t['push_ads']}: {status}", callback_data="settings:toggle_push")],
            [InlineKeyboardButton(f"⬅️ {t['back']}", callback_data="back_menu")],
        ]
    )


# ----------------------------
# SAFE EDIT HELPERS
# ----------------------------
async def safe_edit_message_text(query, *, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None, parse_mode: Optional[str] = None, disable_web_page_preview: bool = True) -> None:
    try:
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
        )
    except BadRequest as e:
        # Ignore: "Message is not modified"
        msg = str(e).lower()
        if "message is not modified" in msg:
            return
        raise


# ----------------------------
# ADSGRAM
# ----------------------------
def _strip_html_to_text(s: str) -> str:
    # Remove tags, keep inner text. AdsGram text_html can contain multiple <a> blocks.
    s = s.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    s = re.sub(r"<[^>]+>", "", s)
    s = _html.unescape(s)
    # Normalize whitespace
    s = re.sub(r"\r\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _truncate_to_lines(s: str, max_lines: int, width: int = 52) -> str:
    # Wrap paragraphs into lines with fixed width, then take first max_lines
    lines_out: List[str] = []
    for para in s.splitlines():
        para = para.strip()
        if not para:
            # keep a single blank line only if we still have room
            if lines_out and lines_out[-1] != "":
                lines_out.append("")
            continue
        wrapped = textwrap.wrap(para, width=width, break_long_words=False, replace_whitespace=True)
        lines_out.extend(wrapped if wrapped else [para])

    # Remove leading/trailing blank lines
    while lines_out and lines_out[0] == "":
        lines_out.pop(0)
    while lines_out and lines_out[-1] == "":
        lines_out.pop()

    if len(lines_out) <= max_lines:
        return "\n".join(lines_out)

    trimmed = lines_out[:max_lines]
    # Add ellipsis to last line if original had more
    last = trimmed[-1]
    if len(last) > 0 and not last.endswith("…"):
        if len(last) >= width - 1:
            last = last[: max(0, width - 2)].rstrip() + "…"
        else:
            last = last.rstrip() + "…"
    trimmed[-1] = last
    return "\n".join(trimmed)


def fetch_adsgram(user_id: int, lang: Optional[str]) -> Optional[dict]:
    if not ADSGRAM_BLOCK_ID:
        return None
    url = "https://api.adsgram.ai/advbot"
    params: Dict[str, Any] = {"tgid": user_id, "blockid": ADSGRAM_BLOCK_ID}
    if lang in ("tr", "en"):
        params["language"] = lang

    try:
        r = requests.get(url, params=params, timeout=12)
        ct = r.headers.get("content-type", "")
        body = (r.text or "").strip()
        if DEBUG_ADSGRAM:
            logger.info("AdsGram request params=%s", params)
            logger.info("AdsGram response status=%s content_type=%s len=%s", r.status_code, ct, len(body))
        if r.status_code != 200 or not body:
            return None
        data = r.json()
        if not isinstance(data, dict):
            return None
        if not data.get("text_html"):
            return None
        return data
    except Exception as e:
        logger.warning("AdsGram error: %s", e)
        return None


def build_ad_message(data: dict) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    # Sponsored label (underlined + bold)
    sponsored = "<u><b>Sponsored</b></u>"

    raw_html = str(data.get("text_html", "") or "")
    plain = _strip_html_to_text(raw_html)
    if plain:
        plain = _truncate_to_lines(plain, max_lines=max(1, ADSGRAM_MAX_LINES))
        plain = _html.escape(plain)
    else:
        plain = ""

    text = sponsored + ("\n" + plain if plain else "")

    buttons: List[List[InlineKeyboardButton]] = []
    btn_name = data.get("button_name")
    click_url = data.get("click_url")
    if btn_name and click_url:
        buttons.append([InlineKeyboardButton(str(btn_name), url=str(click_url))])

    reward_name = data.get("button_reward_name")
    reward_url = data.get("reward_url")
    if reward_name and reward_url:
        buttons.append([InlineKeyboardButton(str(reward_name), url=str(reward_url))])

    markup = InlineKeyboardMarkup(buttons) if buttons else None
    return text, markup


async def maybe_send_ad(
    *,
    app: Application,
    chat_id: int,
    user_id: int,
    lang: Optional[str],
    reply_to_message_id: Optional[int],
    force: bool = False,
) -> None:
    """
    Show an ad if available.
    - Enforces show-every + min-interval unless force=True
    """
    global STATE
    u = get_user(STATE, user_id)

    now_ts = int(datetime.now(TZ).timestamp())
    last_ts = int(u.get("last_ad_ts") or 0)

    if not force:
        if ADSGRAM_MIN_INTERVAL_SEC > 0 and (now_ts - last_ts) < ADSGRAM_MIN_INTERVAL_SEC:
            return
        # show-every gating uses quote_count; if called from quote flow, quote_count already incremented
        qc = int(u.get("quote_count") or 0)
        if ADSGRAM_SHOW_EVERY > 1 and (qc % ADSGRAM_SHOW_EVERY) != 0:
            return

    data = await asyncio.to_thread(fetch_adsgram, user_id=user_id, lang=lang)
    if not data:
        return

    ad_text, ad_markup = build_ad_message(data)

    try:
        await app.bot.send_message(
            chat_id=chat_id,
            text=ad_text,
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_to_message_id,
            protect_content=True,
            disable_web_page_preview=True,
            reply_markup=ad_markup,
        )
        u["last_ad_ts"] = now_ts
        set_user(STATE, user_id, u)
        _save_state(STATE)
    except Forbidden:
        # user blocked bot
        u["chat_id"] = None
        set_user(STATE, user_id, u)
        _save_state(STATE)
    except Exception as e:
        logger.warning("Failed to send ad: %s", e)


# ----------------------------
# PUSH ADS (12-18 hourly, opt-out)
# ----------------------------
def _push_slot(now: datetime) -> str:
    # slot string per hour
    return now.strftime("%Y-%m-%dT%H")


async def push_ads_tick(app: Application) -> None:
    if not PUSH_ADS_ENABLED:
        return

    global STATE
    now = datetime.now(TZ)
    hour = now.hour

    if hour < PUSH_ADS_START_HOUR or hour > PUSH_ADS_END_HOUR:
        return

    slot = _push_slot(now)

    users = (STATE.get("users") or {})
    if not isinstance(users, dict) or not users:
        return

    # sequential sending with small delay to reduce flood risk
    sent = 0
    for user_id_str, u in list(users.items()):
        try:
            user_id = int(user_id_str)
        except Exception:
            continue

        chat_id = u.get("chat_id")
        if not chat_id:
            continue

        if bool(u.get("push_ads_disabled")):
            continue

        if str(u.get("last_push_slot") or "") == slot:
            continue  # already pushed this hour

        lang = u.get("lang") or None

        await maybe_send_ad(
            app=app,
            chat_id=int(chat_id),
            user_id=user_id,
            lang=lang if lang in ("tr", "en") else None,
            reply_to_message_id=None,
            force=True,
        )

        # mark slot even if no ad fill? -> we prefer to retry next hour, but not spam within same hour
        u["last_push_slot"] = slot
        users[user_id_str] = u
        sent += 1

        _save_state(STATE)
        await asyncio.sleep(0.12)

    if DEBUG_ADSGRAM:
        logger.info("Push ads tick done. users_processed=%s", sent)


# ----------------------------
# USER FLOW
# ----------------------------
def user_lang_from_state(u: dict) -> Optional[str]:
    lang = (u.get("lang") or "").strip().lower()
    return lang if lang in ("tr", "en") else None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Always start with language selection."""
    if not update.effective_user or not update.effective_chat:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    global STATE
    u = get_user(STATE, user_id)
    u["chat_id"] = chat_id
    # force language selection on every /start
    u["lang"] = None
    set_user(STATE, user_id, u)
    _save_state(STATE)

    await update.effective_message.reply_text(TEXTS["tr"]["pick_lang"], reply_markup=language_keyboard())


async def adtest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manual ad test: sends an ad (if available) to current chat."""
    if not update.effective_user or not update.effective_chat:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    global STATE
    u = get_user(STATE, user_id)
    lang = user_lang_from_state(u)

    await maybe_send_ad(
        app=context.application,
        chat_id=chat_id,
        user_id=user_id,
        lang=lang,
        reply_to_message_id=None,
        force=True,
    )
    await update.effective_message.reply_text("✅ adtest done (if AdsGram had fill).")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.callback_query or not update.effective_user:
        return

    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    chat_id = query.message.chat_id if query.message else None

    global STATE
    u = get_user(STATE, user_id)

    # keep chat_id updated for push ads
    if chat_id is not None:
        u["chat_id"] = chat_id
        set_user(STATE, user_id, u)
        _save_state(STATE)

    data = query.data or ""
    lang = user_lang_from_state(u)

    # --- Back to language selection ---
    if data == "back_lang":
        # show language picker (always in TR prompt is OK; user will pick)
        await safe_edit_message_text(
            query,
            text=TEXTS["tr"]["pick_lang"],
            reply_markup=language_keyboard(),
            parse_mode=None,
        )
        return

    # --- Language selection ---
    if data.startswith("lang:"):
        chosen = data.split(":", 1)[1].strip().lower()
        if chosen not in ("tr", "en"):
            return
        u["lang"] = chosen
        lang = chosen
        set_user(STATE, user_id, u)
        _save_state(STATE)

        await safe_edit_message_text(
            query,
            text=TEXTS[lang]["pick_topic"],
            reply_markup=topic_keyboard(lang),
            parse_mode=None,
        )
        return

    # if no language yet, force language selection
    if not lang:
        await safe_edit_message_text(
            query,
            text=TEXTS["tr"]["pick_lang"],
            reply_markup=language_keyboard(),
            parse_mode=None,
        )
        return

    # --- Topic selection ---
    if data.startswith("topic:"):
        topic_key = data.split(":", 1)[1].strip()
        if topic_key not in TOPIC_KEYS:
            return
        u["topic"] = topic_key
        # Show a first quote for the selected topic
        quote = pick_random_quote(lang, topic_key)
        if not quote:
            await safe_edit_message_text(
                query,
                text=TEXTS[lang]["no_quotes"],
                reply_markup=topic_keyboard(lang),
                parse_mode=None,
            )
            return

        u["last_quote"] = quote
        u["quote_count"] = int(u.get("quote_count") or 0) + 1
        set_user(STATE, user_id, u)
        _save_state(STATE)

        msg = format_quote_html(lang, quote)
        await safe_edit_message_text(
            query,
            text=msg,
            reply_markup=menu_keyboard(lang, quote),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        # Ad comes right under the quote
        if query.message:
            await maybe_send_ad(
                app=context.application,
                chat_id=query.message.chat_id,
                user_id=user_id,
                lang=lang,
                reply_to_message_id=query.message.message_id,
                force=False,
            )
        return

    # --- Menu actions ---
    if data == "daily":
        quote = get_daily_quote(lang)
        if not quote:
            await safe_edit_message_text(
                query,
                text=TEXTS[lang]["no_quotes"],
                reply_markup=menu_keyboard(lang, u.get("last_quote", "")),
                parse_mode=None,
            )
            return

        u["last_quote"] = quote
        u["quote_count"] = int(u.get("quote_count") or 0) + 1
        set_user(STATE, user_id, u)
        _save_state(STATE)

        msg = format_quote_html(lang, quote)
        await safe_edit_message_text(
            query,
            text=msg,
            reply_markup=menu_keyboard(lang, quote),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        if query.message:
            await maybe_send_ad(
                app=context.application,
                chat_id=query.message.chat_id,
                user_id=user_id,
                lang=lang,
                reply_to_message_id=query.message.message_id,
                force=False,
            )
        return

    if data == "new":
        topic_key = (u.get("topic") or "motivation")
        quote = pick_random_quote(lang, topic_key)
        if not quote:
            await safe_edit_message_text(
                query,
                text=TEXTS[lang]["no_quotes"],
                reply_markup=menu_keyboard(lang, u.get("last_quote", "")),
                parse_mode=None,
            )
            return

        u["last_quote"] = quote
        u["quote_count"] = int(u.get("quote_count") or 0) + 1
        set_user(STATE, user_id, u)
        _save_state(STATE)

        msg = format_quote_html(lang, quote)
        await safe_edit_message_text(
            query,
            text=msg,
            reply_markup=menu_keyboard(lang, quote),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        if query.message:
            await maybe_send_ad(
                app=context.application,
                chat_id=query.message.chat_id,
                user_id=user_id,
                lang=lang,
                reply_to_message_id=query.message.message_id,
                force=False,
            )
        return

    if data == "change_topic":
        await safe_edit_message_text(
            query,
            text=TEXTS[lang]["pick_topic"],
            reply_markup=topic_keyboard(lang),
            parse_mode=None,
        )
        return

    if data == "show_ad":
        # Send an ad under the current quote (force=True)
        if query.message:
            await maybe_send_ad(
                app=context.application,
                chat_id=query.message.chat_id,
                user_id=user_id,
                lang=lang,
                reply_to_message_id=query.message.message_id,
                force=True,
            )
        return

    if data == "settings":
        await safe_edit_message_text(
            query,
            text=f"⚙️ {TEXTS[lang]['settings']}",
            reply_markup=settings_keyboard(lang, bool(u.get("push_ads_disabled"))),
            parse_mode=None,
        )
        return

    if data == "settings:lang":
        # Return to language selection
        u["lang"] = None
        set_user(STATE, user_id, u)
        _save_state(STATE)
        await safe_edit_message_text(
            query,
            text=TEXTS["tr"]["pick_lang"],
            reply_markup=language_keyboard(),
            parse_mode=None,
        )
        return

    if data == "settings:toggle_push":
        u["push_ads_disabled"] = not bool(u.get("push_ads_disabled"))
        set_user(STATE, user_id, u)
        _save_state(STATE)
        await safe_edit_message_text(
            query,
            text=f"⚙️ {TEXTS[lang]['settings']}",
            reply_markup=settings_keyboard(lang, bool(u.get("push_ads_disabled"))),
            parse_mode=None,
        )
        return

    if data == "back_menu":
        last = str(u.get("last_quote") or "").strip()
        if not last:
            await safe_edit_message_text(
                query,
                text=TEXTS[lang]["pick_topic"],
                reply_markup=topic_keyboard(lang),
                parse_mode=None,
            )
            return
        msg = format_quote_html(lang, last)
        await safe_edit_message_text(
            query,
            text=msg,
            reply_markup=menu_keyboard(lang, last),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return


# ----------------------------
# APP INIT + SCHEDULER
# ----------------------------
async def post_init(app: Application) -> None:
    # Start AsyncIO scheduler in the bot loop
    sched = AsyncIOScheduler(timezone=TZ_NAME)

    # Daily quote at 10:00
    sched.add_job(
        compute_daily_if_needed,
        trigger=CronTrigger(hour=10, minute=0, timezone=TZ_NAME),
        id="compute_daily",
        replace_existing=True,
    )

    # Push ads at every hour between 12-18 inclusive
    if PUSH_ADS_ENABLED:
        sched.add_job(
            lambda: asyncio.create_task(push_ads_tick(app)),
            trigger=CronTrigger(hour=f"{PUSH_ADS_START_HOUR}-{PUSH_ADS_END_HOUR}", minute=0, timezone=TZ_NAME),
            id="push_ads",
            replace_existing=True,
        )

    sched.start()
    app.bot_data["scheduler"] = sched
    logger.info("Scheduler started (daily=10:00, push=%s %02d-%02d).", PUSH_ADS_ENABLED, PUSH_ADS_START_HOUR, PUSH_ADS_END_HOUR)


def build_application() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing.")

    return (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )


def main() -> None:
    application = build_application()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("adtest", adtest))
    application.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot started.")

    # Robust polling: retry on Conflict / transient network errors.
    while True:
        try:
            application.run_polling(
                close_loop=False,
                allowed_updates=Update.ALL_TYPES,
            )
        except Conflict as e:
            logger.warning("409 Conflict (another getUpdates is running). Waiting 15s then retrying... (%s)", e)
            import time
            time.sleep(15)
            continue
        except (NetworkError, TimedOut) as e:
            logger.warning("Network error. Waiting 10s then retrying... (%s)", e)
            import time
            time.sleep(10)
            continue
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.exception("Fatal error: %s", e)
            import time
            time.sleep(10)
            continue


if __name__ == "__main__":
    main()
