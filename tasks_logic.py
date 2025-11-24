from datetime import date
from typing import List
from .data import USER_DAILY_COUNTERS, USER_DAILY_TASK_REWARDS
from .models import DailyTask

def _get_daily_key(user_id: int):
    return (user_id, date.today())

def increment_counter(user_id: int, key: str):
    dkey = _get_daily_key(user_id)
    counters = USER_DAILY_COUNTERS.get(dkey, {"quotes": 0, "shares": 0, "rewarded_ads": 0})
    counters[key] = counters.get(key, 0) + 1
    USER_DAILY_COUNTERS[dkey] = counters

def get_daily_tasks(user_id: int, lang: str = "tr") -> List[DailyTask]:
    dkey = _get_daily_key(user_id)
    counters = USER_DAILY_COUNTERS.get(dkey, {"quotes": 0, "shares": 0, "rewarded_ads": 0})
    rewards = USER_DAILY_TASK_REWARDS.get(dkey, {})

    # Basit 3 görev:
    # 1) 3 söz oku
    # 2) 1 paylaşım yap
    # 3) 1 ödüllü reklam izle
    tasks_def = [
        {
            "id": "read_3_quotes",
            "target": 3,
            "progress": counters.get("quotes", 0),
        },
        {
            "id": "share_1",
            "target": 1,
            "progress": counters.get("shares", 0),
        },
        {
            "id": "watch_1_rewarded",
            "target": 1,
            "progress": counters.get("rewarded_ads", 0),
        },
    ]

    titles_tr = {
        "read_3_quotes": "Bugün 3 söz oku",
        "share_1": "1 sözü arkadaşınla paylaş",
        "watch_1_rewarded": "1 ödüllü reklam izle",
    }
    titles_en = {
        "read_3_quotes": "Read 3 quotes today",
        "share_1": "Share 1 quote with a friend",
        "watch_1_rewarded": "Watch 1 rewarded ad",
    }
    titles = titles_tr if lang == "tr" else titles_en

    tasks: List[DailyTask] = []
    for t in tasks_def:
        tid = t["id"]
        completed = t["progress"] >= t["target"]
        reward_claimed = rewards.get(tid, False)
        tasks.append(DailyTask(
            id=tid,
            title=titles.get(tid, tid),
            progress=t["progress"],
            target=t["target"],
            completed=completed,
            reward_claimed=reward_claimed,
        ))
    return tasks

def claim_task_reward(user_id: int, task_id: str) -> bool:
    """
    Görev tamamlanmışsa ödül claim edilir -> True,
    değilse False döner.
    """
    dkey = _get_daily_key(user_id)
    counters = USER_DAILY_COUNTERS.get(dkey, {"quotes": 0, "shares": 0, "rewarded_ads": 0})
    rewards = USER_DAILY_TASK_REWARDS.get(dkey, {})

    required = {
        "read_3_quotes": 3,
        "share_1": 1,
        "watch_1_rewarded": 1,
    }.get(task_id)

    if required is None:
        return False

    if counters.get(task_id.split("_")[0], 0) < required:
        return False

    if rewards.get(task_id, False):
        return False  # zaten almış

    rewards[task_id] = True
    USER_DAILY_TASK_REWARDS[dkey] = rewards
    return True
