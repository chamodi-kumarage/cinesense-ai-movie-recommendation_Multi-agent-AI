from typing import Any
from pydantic import BaseModel, EmailStr, Field, field_validator

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)
    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str):
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must contain letters and numbers.")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class ConsentRequest(BaseModel):
    accepted: bool

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=3000)
    mood_override: str | None = Field(default=None, max_length=40)
    dismissed_moods: list[str] = Field(default_factory=list, max_length=10)

class CompareRequest(BaseModel):
    movie_ids: list[int] = Field(min_length=2, max_length=4)
    mood: str | None = Field(default=None, max_length=40)
    user_note: str | None = Field(default=None, max_length=500)
    mode: str = Field(default="best_mood", pattern="^(best_mood|best_quality|shortest|most_exciting|safest_group|different)$")
    free_minutes: int | None = Field(default=None, ge=30, le=600)
    scenario: str | None = Field(default=None, max_length=300)

class PlanRequest(BaseModel):
    genres: list[str] = Field(default_factory=list, max_length=5)
    mood: str | None = Field(default=None, max_length=40)
    free_minutes: int = Field(default=120, ge=30, le=600)
    finish_by: str | None = Field(default=None, max_length=80)
    buffer_minutes: int = Field(default=0, ge=0, le=60)
    query: str | None = Field(default=None, max_length=500)

    @field_validator("free_minutes", mode="before")
    @classmethod
    def normalize_free_minutes(cls, value):
        # Browser number/range controls can briefly produce blank/null values.
        # Treat those as the normal planner default instead of returning a 422.
        if value is None or value == "":
            return 120
        try:
            return max(30, min(600, int(float(value))))
        except (TypeError, ValueError):
            return 120

    @field_validator("buffer_minutes", mode="before")
    @classmethod
    def normalize_buffer_minutes(cls, value):
        if value is None or value == "":
            return 0
        try:
            return max(0, min(60, int(float(value))))
        except (TypeError, ValueError):
            return 0

    @field_validator("genres", mode="before")
    @classmethod
    def normalize_genres(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            value = [value] if value.strip() else []
        if isinstance(value, (list, tuple)):
            return [str(item).strip()[:60] for item in value if str(item).strip()][:5]
        return []

    @field_validator("mood", mode="before")
    @classmethod
    def normalize_mood(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text[:40] or None

    @field_validator("finish_by", mode="before")
    @classmethod
    def normalize_finish_by(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text[:80] or None

    @field_validator("query", mode="before")
    @classmethod
    def normalize_query(cls, value):
        if value is None:
            return None
        text = str(value).strip()
        return text[:500] or None

class SavePlanRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    plan: dict[str, Any]

class WatchEventRequest(BaseModel):
    movie_id: int
    rating: float | None = Field(default=None, ge=0, le=5)
    watched: bool = True

class FeedbackRequest(BaseModel):
    movie_id: int
    reason: str = Field(min_length=2, max_length=255)
    details: str = Field(default="", max_length=1000)

class ProfileCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    preferred_genres: list[str] = Field(default_factory=list, max_length=8)
    disliked_genres: list[str] = Field(default_factory=list, max_length=8)
    preferred_moods: list[str] = Field(default_factory=list, max_length=6)

class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    preferred_genres: list[str] | None = Field(default=None, max_length=8)
    disliked_genres: list[str] | None = Field(default=None, max_length=8)
    preferred_moods: list[str] | None = Field(default=None, max_length=6)

class ProfileSwitchRequest(BaseModel):
    profile_id: int

class GroupChoiceRequest(BaseModel):
    profile_ids: list[int] = Field(min_length=2, max_length=5)
    free_minutes: int | None = Field(default=None, ge=30, le=600)
    mood: str | None = Field(default=None, max_length=40)
    request_text: str = Field(default="", max_length=500)

class GroupCompareRequest(BaseModel):
    movie_ids: list[int] = Field(min_length=2, max_length=4)

class GroupVoteRequest(BaseModel):
    profile_id: int
    movie_id: int

class FamilyInviteCreateRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern="^member$")

class FamilyInviteAcceptRequest(BaseModel):
    token: str = Field(min_length=20, max_length=300)

class FamilyMemberRoleRequest(BaseModel):
    role: str = Field(pattern="^member$")

class CheckoutRequest(BaseModel):
    plan: str = Field(pattern="^(premium|family)$")

class SummarizeRequest(BaseModel):
    movie_id: int
    max_sentences: int = Field(default=3, ge=1, le=5)

class B2BClientCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class SimulatedBillingProfileRequest(BaseModel):
    cardholder_name: str = Field(min_length=2, max_length=100)
    card_number: str = Field(min_length=13, max_length=23)
    expiry_month: int = Field(ge=1, le=12)
    expiry_year: int = Field(ge=2026, le=2100)
    cvv: str = Field(min_length=3, max_length=4)
    billing_address: str = Field(min_length=3, max_length=180)
    billing_city: str = Field(min_length=2, max_length=80)
    billing_country: str = Field(min_length=2, max_length=80)

    @field_validator("card_number")
    @classmethod
    def validate_card_number(cls, value: str):
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) != 16:
            raise ValueError("Card number must contain exactly 16 digits.")
        # Luhn check for realistic university-project validation.
        total = 0
        for index, digit in enumerate(reversed(digits)):
            n = int(digit)
            if index % 2 == 1:
                n *= 2
                if n > 9: n -= 9
            total += n
        if total % 10 != 0:
            raise ValueError("Card number is not valid.")
        return digits

    @field_validator("cvv")
    @classmethod
    def validate_cvv(cls, value: str):
        if not value.isdigit() or len(value) not in {3,4}:
            raise ValueError("CVV must be 3 or 4 digits.")
        return value

class SimulatedSubscribeRequest(BaseModel):
    plan: str = Field(pattern="^(premium|family)$")

class MoodCheckInRequest(BaseModel):
    text: str = Field(default="", max_length=500)
    selected_mood: str | None = Field(default=None, max_length=40)

class PlannerHistoryQuery(BaseModel):
    days: int = Field(default=30, ge=7, le=365)

class CalendarLocalConnectRequest(BaseModel):
    provider: str = Field(default="local", pattern="^(local|google)$")

class CalendarBusySlotRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    start_at: str = Field(min_length=16, max_length=40)
    end_at: str = Field(min_length=16, max_length=40)

class CalendarFreeWindowRequest(BaseModel):
    date: str = Field(min_length=10, max_length=10)
    window_start: str = Field(default="18:00", max_length=5)
    window_end: str = Field(default="23:59", max_length=5)
    min_minutes: int = Field(default=30, ge=15, le=600)
    timezone_offset_minutes: int = Field(default=0, ge=-840, le=840)

class CalendarPlanEventRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    start_at: str = Field(min_length=16, max_length=40)
    end_at: str = Field(min_length=16, max_length=40)
    description: str = Field(default="", max_length=1000)
    reminder_minutes: int | None = Field(default=15, ge=0, le=1440)

class SimilarityRequest(BaseModel):
    movie_id: int
    modes: list[str] = Field(default_factory=lambda: ["story", "genre"])
    weights: dict[str, float] = Field(default_factory=dict)
    preset: str | None = Field(default="overall", max_length=40)
    required_genre: str | None = Field(default=None, max_length=50)
    year_mode: str = Field(default="within_5", max_length=30)
    custom_year_min: int | None = Field(default=None, ge=1880, le=2100)
    custom_year_max: int | None = Field(default=None, ge=1880, le=2100)
    mood: str | None = Field(default=None, max_length=40)
    free_minutes: int | None = Field(default=None, ge=30, le=600)
    limit: int = Field(default=12, ge=1, le=30)
