from typing import Optional
from .data import USER_REFERRALS, USER_STATE

def handle_referral_start(user_id: int, ref_param: Optional[str]):
    """
    ?start=ref_123 formatındaki parametreyi işlemek için iskelet.
    Gerçekte bu parametre bot tarafında gelir; burada mini-app için örnek sunuyorum.
    """
    if not ref_param:
        return None

    if not ref_param.startswith("ref_"):
        return None

    try:
        referrer_id = int(ref_param.replace("ref_", ""))
    except ValueError:
        return None

    if referrer_id == user_id:
        return None  # kendini refer etme

    # referrer için listeye ekle
    USER_REFERRALS[referrer_id].add(user_id)

    # kullanıcı state'ine "referred_by" yaz
    state = USER_STATE.get(user_id, {})
    state["referred_by"] = referrer_id
    USER_STATE[user_id] = state

    return referrer_id

def build_referral_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref_{user_id}"
