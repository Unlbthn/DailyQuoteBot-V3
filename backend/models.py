from pydantic import BaseModel
from typing import List, Optional

class UserAction(BaseModel):
    user_id: int

class UserActionWithTopic(BaseModel):
    user_id: int
    topic: Optional[str] = None  # motivation, love, sports

class StartRequest(BaseModel):
    user_id: int
    language_code: Optional[str] = None   # Telegram'dan gelen lang (ör: 'tr', 'en')

class StartResponse(BaseModel):
    show_ad: bool
    lang: str
    current_topic: str
    initial_quote: str

class QuoteResponse(BaseModel):
    quote: str
    show_ad: bool

class RewardQuoteResponse(BaseModel):
    quote: str
    message: str

class FavoriteAddRequest(BaseModel):
    user_id: int
    quote: str

class FavoriteListResponse(BaseModel):
    favorites: List[str]

class DailyTask(BaseModel):
    id: str
    title: str
    progress: int
    target: int
    completed: bool
    reward_claimed: bool

class DailyTasksResponse(BaseModel):
    tasks: List[DailyTask]

class TestStartResponse(BaseModel):
    questions: List[dict]

class TestSubmitRequest(BaseModel):
    user_id: int
    answers: List[int]  # index of selected options

class TestSubmitResponse(BaseModel):
    score: int
    message: str

class ReferralStartInfo(BaseModel):
    ref_param: Optional[str] = None
    user_id: int

class ReferralInfoResponse(BaseModel):
    referred_by: Optional[int]
    referral_link: str
