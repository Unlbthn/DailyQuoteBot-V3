from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import random

from .ads_logic import register_action, should_show_on_start, can_show_rewarded, register_rewarded_shown
from .data import (
    QUOTES,
    DEFAULT_TOPIC,
    USER_STATE,
    USER_FAVORITES,
)
from .models import (
    StartRequest, StartResponse,
    UserAction, UserActionWithTopic,
    QuoteResponse,
    RewardQuoteResponse,
    FavoriteAddRequest,
    FavoriteListResponse,
    DailyTasksResponse,
    TestStartResponse,
    TestSubmitRequest,
    TestSubmitResponse,
    ReferralStartInfo,
    ReferralInfoResponse,
)
from .tasks_logic import increment_counter, get_daily_tasks
from .referral_logic import handle_referral_start, build_referral_link

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # prod'da domain ile sınırla
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_USERNAME = "YourBotUsernameHere"  # kendi bot kullanıcı adınla değiştir


def detect_lang(language_code: str | None) -> str:
    if not language_code:
        return "tr"
    if language_code.lower().startswith("tr"):
        return "tr"
    return "en"


def get_random_quote(topic: str, lang: str) -> str:
    topic_data = QUOTES.get(topic) or QUOTES[DEFAULT_TOPIC]
    lang_quotes = topic_data.get(lang) or topic_data.get("en") or []
    if not lang_quotes:
        return "No quotes available."
    return random.choice(lang_quotes)


@app.post("/api/start", response_model=StartResponse)
def start_app(payload: StartRequest):
    lang = detect_lang(payload.language_code)

    state = USER_STATE.get(payload.user_id, {})
    if "lang" not in state:
        state["lang"] = lang
    if "topic" not in state:
        state["topic"] = DEFAULT_TOPIC
    USER_STATE[payload.user_id] = state

    show_ad = should_show_on_start(payload.user_id)
    quote = get_random_quote(state["topic"], state["lang"])

    return StartResponse(
        show_ad=show_ad,
        lang=state["lang"],
        current_topic=state["topic"],
        initial_quote=quote,
    )


@app.post("/api/new_quote", response_model=QuoteResponse)
def new_quote(payload: UserActionWithTopic):
    state = USER_STATE.get(payload.user_id, {})
    lang = state.get("lang", "tr")
    if payload.topic:
        state["topic"] = payload.topic
    topic = state.get("topic", DEFAULT_TOPIC)
    USER_STATE[payload.user_id] = state

    quote = get_random_quote(topic, lang)
    show_ad = register_action(payload.user_id)

    increment_counter(payload.user_id, "quotes")

    return QuoteResponse(quote=quote, show_ad=show_ad)


@app.post("/api/change_topic", response_model=QuoteResponse)
def change_topic(payload: UserActionWithTopic):
    """
    Konu değiştir + yeni söz getir.
    """
    state = USER_STATE.get(payload.user_id, {})
    lang = state.get("lang", "tr")
    topic = payload.topic or state.get("topic", DEFAULT_TOPIC)

    state["topic"] = topic
    USER_STATE[payload.user_id] = state

    quote = get_random_quote(topic, lang)
    show_ad = register_action(payload.user_id)

    return QuoteResponse(quote=quote, show_ad=show_ad)


@app.post("/api/favorites/add")
def add_favorite(payload: FavoriteAddRequest):
    USER_FAVORITES[payload.user_id].append(payload.quote)
    return {"status": "ok"}


@app.post("/api/favorites/list", response_model=FavoriteListResponse)
def list_favorites(payload: UserAction):
    favs = USER_FAVORITES.get(payload.user_id, [])
    return FavoriteListResponse(favorites=favs)


@app.post("/api/tasks", response_model=DailyTasksResponse)
def get_tasks(payload: UserAction):
    state = USER_STATE.get(payload.user_id, {})
    lang = state.get("lang", "tr")
    tasks = get_daily_tasks(payload.user_id, lang=lang)
    return DailyTasksResponse(tasks=tasks)


@app.post("/api/tasks/share")
def track_share(payload: UserAction):
    increment_counter(payload.user_id, "shares")
    return {"status": "ok"}


@app.post("/api/test/start", response_model=TestStartResponse)
def test_start(payload: UserAction):
    """
    Basit 3 soruluk motivasyon testi.
    """
    questions = [
        {
            "id": 1,
            "text_tr": "Bugün kendini nasıl hissediyorsun?",
            "text_en": "How do you feel today?",
            "options_tr": ["Yorgun", "Normal", "Harika"],
            "options_en": ["Tired", "Normal", "Great"]
        },
        {
            "id": 2,
            "text_tr": "Hedeflerine ne kadar odaklı hissediyorsun?",
            "text_en": "How focused do you feel on your goals?",
            "options_tr": ["Düşük", "Orta", "Yüksek"],
            "options_en": ["Low", "Medium", "High"]
        }
    ]
    return TestStartResponse(questions=questions)


@app.post("/api/test/submit", response_model=TestSubmitResponse)
def test_submit(payload: TestSubmitRequest):
    # basitçe toplam puan = seçilen şıkların toplam indexi
    score = sum(payload.answers)
    if score <= 1:
        msg_tr = "Biraz yorgun görünüyorsun, bugün kendine küçük bir ödül ver."
        msg_en = "You seem a bit tired, give yourself a small reward today."
    elif score <= 3:
        msg_tr = "Fena değilsin, ama biraz daha odak ekleyebilirsin."
        msg_en = "You’re doing okay, but you can add a bit more focus."
    else:
        msg_tr = "Harikasın! Bu motivasyonu koru."
        msg_en = "You’re doing great! Keep this motivation up."

    state = USER_STATE.get(payload.user_id, {})
    lang = state.get("lang", "tr")
    message = msg_tr if lang == "tr" else msg_en

    # test de oturum süresini uzattığı için bir aksiyon sayabiliriz
    register_action(payload.user_id)

    return TestSubmitResponse(score=score, message=message)


@app.post("/api/reward-quote", response_model=RewardQuoteResponse)
def reward_quote(payload: UserAction):
    """
    Ödüllü reklam başarıyla izlendikten sonra çağrılır.
    """
    if not can_show_rewarded(payload.user_id):
        return RewardQuoteResponse(
            quote="",
            message="Günlük ödüllü reklam limitine ulaştın."
        )

    register_rewarded_shown(payload.user_id)
    state = USER_STATE.get(payload.user_id, {})
    lang = state.get("lang", "tr")
    topic = state.get("topic", DEFAULT_TOPIC)
    quote = get_random_quote(topic, lang)

    # rewarded izlenince görev sayacı da artar
    from .tasks_logic import increment_counter
    increment_counter(payload.user_id, "rewarded_ads")

    return RewardQuoteResponse(
        quote=quote,
        message="Bonus söz açıldı!"
    )


@app.post("/api/referral/info", response_model=ReferralInfoResponse)
def referral_info(payload: ReferralStartInfo):
    """
    Referral iskeleti: kimin yönlendirdiğini ve kendi linkini gösterir.
    """
    ref_by = handle_referral_start(payload.user_id, payload.ref_param)
    link = build_referral_link(BOT_USERNAME, payload.user_id)
    return ReferralInfoResponse(
        referred_by=ref_by,
        referral_link=link
    )
