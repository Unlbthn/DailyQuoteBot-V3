from typing import Optional

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from db import log_stat

ADSGRAM_BLOCK_ID = 16417
ADMIN_ID = 5664983086


async def send_adsgram_ad(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
    lang: Optional[str] = None,
):
    """
    AdsGram API'den reklam çekip, varsa ayrı bir Sponsored mesajı olarak gönderir.
    Reklam yoksa, admin'e debug mesajı gösterebilir.
    """
    try:
        params = {
            "tgid": str(user_id),
            "blockid": str(ADSGRAM_BLOCK_ID),
        }
        if lang == "en":
            params["language"] = "en"
        elif lang == "tr":
            params["language"] = "tr"

        resp = requests.get(
            "https://api.adsgram.ai/advbot",
            params=params,
            timeout=3,
        )

        print("AdsGram status:", resp.status_code)
        print("AdsGram response (ilk 300 karakter):", resp.text[:300])

        if resp.status_code != 200:
            if chat_id == ADMIN_ID:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"AdsGram HTTP hata kodu: {resp.status_code}",
                    )
                except Exception as e:
                    print("AdsGram admin hata mesajı gönderilemedi:", e)
            return

        raw = resp.text.strip()

        if not raw.startswith("{"):
            print("AdsGram: JSON yerine düz metin döndü (muhtemelen reklam yok).")
            if chat_id == ADMIN_ID:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="Şu an AdsGram reklamı yok (JSON yerine düz metin döndü).",
                    )
                except Exception as e:
                    print("AdsGram admin info mesajı gönderilemedi:", e)
            return

        data = resp.json()

    except Exception as e:
        print("AdsGram hata:", e)
        if chat_id == ADMIN_ID:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"AdsGram istek hatası: {e}",
                )
            except Exception as ee:
                print("AdsGram admin exception mesajı gönderilemedi:", ee)
        return

    text_html = data.get("text_html")
    click_url = data.get("click_url")
    button_name = data.get("button_name")
    reward_name = data.get("button_reward_name")
    reward_url = data.get("reward_url")
    image_url = data.get("image_url")

    if not text_html and not image_url:
        print("AdsGram: gösterilecek içerik yok (text_html ve image_url boş).")
        if chat_id == ADMIN_ID:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="AdsGram JSON geldi ama text_html/image_url boş. Gösterilecek reklam yok.",
                )
            except Exception as e:
                print("AdsGram admin boş içerik mesajı gönderilemedi:", e)
        return

    buttons = []
    if button_name and click_url:
        buttons.append([InlineKeyboardButton(button_name, url=click_url)])
    if reward_name and reward_url:
        buttons.append([InlineKeyboardButton(reward_name, url=reward_url)])

    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

    full_text = f"Sponsored\n\n{text_html or ''}"

    try:
        if image_url:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=image_url,
                caption=full_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=True,
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=full_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=True,
            )
        log_stat("ad_shown", user_id, None)
    except Exception as e:
        print("AdsGram gönderim hata:", e)
        if chat_id == ADMIN_ID:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"AdsGram mesajı gönderilirken hata oluştu: {e}",
                )
            except Exception as ee:
                print("AdsGram admin gönderim hata mesajı gönderilemedi:", ee)
