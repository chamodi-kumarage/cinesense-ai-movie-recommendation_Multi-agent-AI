from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name_enc: Mapped[str] = mapped_column(Text, default="")
    consented: Mapped[bool] = mapped_column(Boolean, default=False)
    plan: Mapped[str] = mapped_column(String(30), default="free")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Movie(Base):
    __tablename__ = "movies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    year: Mapped[int] = mapped_column(Integer)
    genres: Mapped[str] = mapped_column(Text)
    runtime: Mapped[int] = mapped_column(Integer)
    overview: Mapped[str] = mapped_column(Text)
    rating: Mapped[float] = mapped_column(Float, default=0)
    language: Mapped[str] = mapped_column(String(50), default="English")
    studio: Mapped[str] = mapped_column(String(120), default="Independent")
    director: Mapped[str] = mapped_column(String(120), default="")
    cast: Mapped[str] = mapped_column(Text, default="")
    moods: Mapped[str] = mapped_column(Text, default="")
    pace: Mapped[str] = mapped_column(String(30), default="Moderate")
    keywords: Mapped[str] = mapped_column(Text, default="")
    tmdb_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    poster_url: Mapped[str] = mapped_column(Text, default="")
    backdrop_url: Mapped[str] = mapped_column(Text, default="")

class ChatTurn(Base):
    __tablename__ = "chat_turns"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content_enc: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class WatchEvent(Base):
    __tablename__ = "watch_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), index=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    watched: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class SavedPlan(Base):
    __tablename__ = "saved_plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), index=True)
    reason: Mapped[str] = mapped_column(String(255), default="Not a good fit")
    details_enc: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AIUsage(Base):
    __tablename__ = "ai_usage"
    __table_args__ = (UniqueConstraint("user_id", "usage_date", name="uq_usage_user_date"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    usage_date: Mapped[str] = mapped_column(String(10), index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)

class AgentTrace(Base):
    __tablename__ = "agent_traces"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    sender: Mapped[str] = mapped_column(String(60))
    receiver: Mapped[str] = mapped_column(String(60))
    intent: Mapped[str] = mapped_column(String(80))
    payload_safe: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ConversationState(Base):
    __tablename__ = "conversation_states"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    last_query_enc: Mapped[str] = mapped_column(Text, default="")
    prefs_json: Mapped[str] = mapped_column(Text, default="{}")
    movie_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (UniqueConstraint("user_id", "name_enc", name="uq_profile_user_name_enc"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name_enc: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class ActiveProfile(Base):
    __tablename__ = "active_profiles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class ProfileWatchEvent(Base):
    __tablename__ = "profile_watch_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), index=True)
    movie_id_enc: Mapped[str] = mapped_column(Text, default="")
    rating_enc: Mapped[str] = mapped_column(Text, default="")
    watched: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(30), default="stripe")
    provider_customer_id: Mapped[str] = mapped_column(String(255), default="")
    provider_subscription_id: Mapped[str] = mapped_column(String(255), default="")
    plan: Mapped[str] = mapped_column(String(30), default="free")
    status: Mapped[str] = mapped_column(String(40), default="inactive")
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class BillingProfile(Base):
    __tablename__ = "billing_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    cardholder_name_enc: Mapped[str] = mapped_column(Text, default="")
    card_last4: Mapped[str] = mapped_column(String(4), default="")
    card_brand: Mapped[str] = mapped_column(String(30), default="Card")
    expiry_month: Mapped[int] = mapped_column(Integer)
    expiry_year: Mapped[int] = mapped_column(Integer)
    billing_address_enc: Mapped[str] = mapped_column(Text, default="")
    billing_city_enc: Mapped[str] = mapped_column(Text, default="")
    billing_country_enc: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class B2BUsage(Base):
    __tablename__ = "b2b_usage"
    __table_args__ = (UniqueConstraint("api_key_hash", "usage_month", name="uq_b2b_key_month"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    api_key_hash: Mapped[str] = mapped_column(String(64), index=True)
    usage_month: Mapped[str] = mapped_column(String(7), index=True)
    call_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class MonitoringEvent(Base):
    __tablename__ = "monitoring_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    level: Mapped[str] = mapped_column(String(20), default="info", index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    detail_safe: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class B2BClient(Base):
    __tablename__ = "b2b_clients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_enc: Mapped[str] = mapped_column(Text, default="")
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    monthly_included_calls: Mapped[int] = mapped_column(Integer, default=10000)
    overage_per_1000_usd: Mapped[float] = mapped_column(Float, default=6.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class PlannerActivity(Base):
    __tablename__ = "planner_activities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("profiles.id"), nullable=True, index=True)
    mood: Mapped[str] = mapped_column(String(40), default="")
    genres_json: Mapped[str] = mapped_column(Text, default="[]")
    movie_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    free_minutes: Mapped[int] = mapped_column(Integer, default=0)
    used_minutes: Mapped[int] = mapped_column(Integer, default=0)
    buffer_minutes: Mapped[int] = mapped_column(Integer, default=0)
    finish_by: Mapped[str] = mapped_column(String(20), default="")
    plan_type: Mapped[str] = mapped_column(String(20), default="single")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class CalendarConnection(Base):
    __tablename__ = "calendar_connections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(30), default="local")
    connected: Mapped[bool] = mapped_column(Boolean, default=False)
    calendar_id: Mapped[str] = mapped_column(String(255), default="primary")
    access_token_enc: Mapped[str] = mapped_column(Text, default="")
    refresh_token_enc: Mapped[str] = mapped_column(Text, default="")
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    oauth_state: Mapped[str] = mapped_column(String(128), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class CalendarBusySlot(Base):
    __tablename__ = "calendar_busy_slots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title_enc: Mapped[str] = mapped_column(Text, default="")
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(30), default="local")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class ProfilePreference(Base):
    __tablename__ = "profile_preferences"
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    preferred_genres_json: Mapped[str] = mapped_column(Text, default="[]")
    disliked_genres_json: Mapped[str] = mapped_column(Text, default="[]")
    preferred_moods_json: Mapped[str] = mapped_column(Text, default="[]")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class GroupSession(Base):
    __tablename__ = "group_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    selected_profile_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    request_text: Mapped[str] = mapped_column(Text, default="")
    mood: Mapped[str] = mapped_column(String(40), default="")
    free_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_scores_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    winner_movie_id: Mapped[int | None] = mapped_column(ForeignKey("movies.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class GroupVote(Base):
    __tablename__ = "group_votes"
    __table_args__ = (UniqueConstraint("session_id", "profile_id", name="uq_group_vote_session_profile"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("group_sessions.id"), index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class AdminAccount(Base):
    __tablename__ = "admin_accounts"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(30), default="admin")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class MovieMedia(Base):
    __tablename__ = "movie_media"
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), primary_key=True)
    trailer_youtube_url: Mapped[str] = mapped_column(Text, default="")
    featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class LoginSecurityState(Base):
    __tablename__ = "login_security_states"
    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class SecurityEvent(Base):
    __tablename__ = "security_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="info", index=True)
    detail_safe: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class MovieProducer(Base):
    __tablename__ = "movie_producers"
    __table_args__ = (UniqueConstraint("movie_id", "producer_name", name="uq_movie_producer_name"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), index=True)
    producer_name: Mapped[str] = mapped_column(String(160), index=True)
    source: Mapped[str] = mapped_column(String(30), default="tmdb")
