from collections import defaultdict
from datetime import date
from .data import USER_REWARDED_ADS, MAX_DAILY_REWARDED

# Aksiyon sayacı (interstitial frekansı için)
USER_ACTIONS = defaultdict(int)

FREQUENCY = 3  # her 3 aksiyonda 1 reklam

def register_action(user_id: int) -> bool:
    """
    Kullanıcı bir aksiyon (yeni söz, konu değiştir vb.) yaptığında çağır.
    True → interstitial reklam göster.
    """
    USER_ACTIONS[user_id] += 1
    if USER_ACTIONS[user_id] % FREQUENCY == 0:
        return True
    return False

def should_show_on_start(user_id: int) -> bool:
    """
    Uygulamaya ilk girişte 1 kere reklam göstermek için basit kontrol.
    İstersen bunu 'bugün gösterildi mi' şeklinde geliştirebilirsin.
    """
    if USER_ACTIONS[user_id] == 0:
        USER_ACTIONS[user_id] += 1
        return True
    return False

def can_show_rewarded(user_id: int) -> bool:
    """
    Günlük ödüllü reklam limiti.
    """
    today = date.today()
    key = (user_id, today)
    entry = USER_REWARDED_ADS.get(key, {"count": 0})
    return entry.get("count", 0) < MAX_DAILY_REWARDED

def register_rewarded_shown(user_id: int):
    today = date.today()
    key = (user_id, today)
    entry = USER_REWARDED_ADS.get(key, {"count": 0})
    entry["count"] = entry.get("count", 0) + 1
    USER_REWARDED_ADS[key] = entry
