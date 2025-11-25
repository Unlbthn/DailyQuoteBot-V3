from collections import defaultdict
from datetime import date

# Basit söz depoları (topic + lang)
QUOTES = {
    "motivation": {
        "tr": [
            "Bugün kendine iyi davranmayı unutma.",
            "Her gün, yeni bir başlangıçtır.",
            "Vazgeçmeyenler, kazananlardır."
        ],
        "en": [
            "Be kind to yourself today.",
            "Every day is a new beginning.",
            "Those who never give up are the ones who win."
        ],
    },
    "love": {
        "tr": [
            "Sevgi emek ister.",
            "Kalpten gelen her söz, yerine ulaşır."
        ],
        "en": [
            "Love requires effort.",
            "Words from the heart always find their way."
        ],
    },
    "sports": {
        "tr": [
            "Bugün ter, yarın zafer.",
            "Vücudun sınırlarını zorla, ruhun güçlensin."
        ],
        "en": [
            "Sweat today, victory tomorrow.",
            "Push your limits so your spirit can grow stronger."
        ],
    },
}

DEFAULT_TOPIC = "motivation"

# Kullanıcı bazlı in-memory state (örnek)
USER_STATE = defaultdict(dict)           # {user_id: {"lang": "tr", "topic": "motivation", ...}}
USER_FAVORITES = defaultdict(list)      # {user_id: [quote1, quote2, ...]}
USER_DAILY_COUNTERS = defaultdict(dict) # { (user_id, date): {"quotes": 0, "shares": 0, "rewarded_ads": 0} }
USER_DAILY_TASK_REWARDS = defaultdict(dict)  # { (user_id, date): {"read_3_quotes": True/False, ...} }

# Referral takibi (basit)
USER_REFERRALS = defaultdict(set)       # {referrer_id: {new_user_ids}}
USER_REWARDED_ADS = defaultdict(dict)   # { (user_id, date): {"count": int} }

MAX_DAILY_REWARDED = 5
