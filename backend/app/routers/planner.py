import json
import secrets
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..agents.orchestrator import orchestrator
from ..db import get_db
from ..dependencies import get_current_user, require_consent
from ..models import (
    User, Movie, Profile, PlannerActivity, ProfileWatchEvent, CalendarConnection,
    CalendarBusySlot, ActiveProfile,
)
from ..schemas import (
    MoodCheckInRequest, CalendarLocalConnectRequest, CalendarBusySlotRequest,
    CalendarFreeWindowRequest, CalendarPlanEventRequest,
)
from ..security import encrypt_text, decrypt_text
from ..services.profiles import active_profile_id
from ..config import get_settings

router = APIRouter(prefix="/api", tags=["planner"])
settings = get_settings()

MOOD_EMOJI = {
    "Happy": "😊",
    "Relaxed": "😌",
    "Sad/Cathartic": "🥲",
    "Thrilled": "⚡",
    "Romantic": "💗",
    "Nostalgic": "✨",
}


def _aware(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(400, "Please provide a valid date and time.")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _utc_iso(value: datetime) -> str:
    # SQLite returns naive datetimes even for timezone=True columns.
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat()


def _active_profile(db: Session, user: User) -> int:
    return active_profile_id(db, user)


def _movie_for_event(db: Session, event: ProfileWatchEvent):
    try:
        return db.get(Movie, int(decrypt_text(event.movie_id_enc)))
    except Exception:
        return None


def _history_context(db: Session, user: User, days: int = 90) -> dict:
    profile_id = _active_profile(db, user)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    activities = (
        db.query(PlannerActivity)
        .filter(
            PlannerActivity.user_id == user.id,
            PlannerActivity.profile_id == profile_id,
            PlannerActivity.created_at >= cutoff,
        )
        .order_by(PlannerActivity.created_at.desc())
        .all()
    )
    moods = Counter(a.mood for a in activities if a.mood)
    genres = Counter()
    by_weekday = defaultdict(Counter)
    by_weekday_genre = defaultdict(Counter)
    for activity in activities:
        if activity.mood:
            by_weekday[activity.created_at.strftime("%A")][activity.mood] += 1
        try:
            for genre in json.loads(activity.genres_json or "[]"):
                genres[genre] += 1
                by_weekday_genre[activity.created_at.strftime("%A")][genre] += 1
        except Exception:
            pass
    return {
        "profile_id": profile_id,
        "activities": activities,
        "moods": moods,
        "genres": genres,
        "by_weekday": by_weekday,
        "by_weekday_genre": by_weekday_genre,
    }


@router.post("/planner/mood-check")
def mood_check(
    data: MoodCheckInRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_consent),
):
    selected = data.selected_mood if data.selected_mood in MOOD_EMOJI else None
    analysis = orchestrator.mood.analyze(
        db,
        orchestrator._env(
            secrets.token_hex(12),
            "mood_preference",
            "planner_check_in",
            {"has_text": bool(data.text), "manual_confirmation": bool(selected)},
        ),
        data.text or "",
        mood_override=selected,
    )
    mood = selected or analysis.get("mood")
    return {
        "mood": mood,
        "emoji": MOOD_EMOJI.get(mood, "🙂"),
        "detected_moods": analysis.get("detected_moods", []),
        "genres": analysis.get("genres", []),
        "time_available": analysis.get("time_available"),
        "confirmed": bool(selected),
        "message": (
            f"Got it — I’ll plan for a {mood.lower()} mood." if selected and mood
            else (f"I’m reading your mood as {mood}. You can confirm or change it." if mood else "Choose the mood that feels closest, or describe how you feel in a few words.")
        ),
    }


@router.get("/planner/insights")
def planner_insights(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ctx = _history_context(db, user, 120)
    insights = []
    for day, counts in sorted(ctx["by_weekday"].items()):
        if counts:
            mood, count = counts.most_common(1)[0]
            if count >= 2:
                insights.append(f"You most often plan {mood.lower()} movies on {day} evenings.")
    for day, counts in sorted(ctx["by_weekday_genre"].items()):
        if counts:
            genre, count = counts.most_common(1)[0]
            if count >= 2:
                insights.append(f"{genre} is your most common {day}-night planner choice.")
    if not insights and ctx["moods"]:
        mood, _ = ctx["moods"].most_common(1)[0]
        insights.append(f"Your most common recent planning mood is {mood}.")
    if not insights:
        insights.append("Create a few watch plans and mark movies as watched to unlock personal mood patterns.")

    return {
        "total_plans": len(ctx["activities"]),
        "top_mood": ctx["moods"].most_common(1)[0][0] if ctx["moods"] else None,
        "top_genre": ctx["genres"].most_common(1)[0][0] if ctx["genres"] else None,
        "insights": insights[:4],
    }


@router.get("/planner/weekly-summary")
def weekly_summary(
    days: int = Query(7, ge=0, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile_id = _active_profile(db, user)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days) if days else None
    events_query = (
        db.query(ProfileWatchEvent)
        .filter(
            ProfileWatchEvent.user_id == user.id,
            ProfileWatchEvent.profile_id == profile_id,
            ProfileWatchEvent.watched.is_(True),
        )
    )
    if cutoff:
        events_query = events_query.filter(ProfileWatchEvent.created_at >= cutoff)
    events = events_query.order_by(ProfileWatchEvent.created_at.desc()).all()
    valid_events = [(e, m) for e in events if (m := _movie_for_event(db, e))]
    movies = [m for _, m in valid_events]
    genre_counts = Counter()
    total_minutes = 0
    for movie in movies:
        total_minutes += movie.runtime or 0
        for genre in [x.strip() for x in (movie.genres or "").split("|") if x.strip()]:
            genre_counts[genre] += 1

    # Planner mood gives a more faithful signal of how the user actually felt.
    activities_query = db.query(PlannerActivity).filter(
            PlannerActivity.user_id == user.id,
            PlannerActivity.profile_id == profile_id,
        )
    if cutoff:
        activities_query = activities_query.filter(PlannerActivity.created_at >= cutoff)
    activities = activities_query.order_by(PlannerActivity.created_at.desc()).all()
    activity_moods = Counter(a.mood for a in activities if a.mood)
    planning_genres = Counter()
    planned_ids = []
    for activity in activities:
        try:
            planning_genres.update(json.loads(activity.genres_json or "[]"))
            planned_ids.extend(json.loads(activity.movie_ids_json or "[]"))
        except (ValueError, TypeError):
            continue
    recent_planned = []
    seen = set()
    for movie_id in planned_ids:
        if movie_id in seen:
            continue
        seen.add(movie_id)
        movie = db.get(Movie, movie_id)
        if movie:
            recent_planned.append({"id": movie.id, "title": movie.title, "runtime": movie.runtime,
                                   "watched_in_period": any(m.id == movie.id for m in movies)})
        if len(recent_planned) >= 6:
            break
    avg = round(total_minutes / len(movies)) if movies else None
    profile = db.get(Profile, profile_id)
    return {
        "period_days": days,
        "profile_id": profile_id,
        "profile_name": decrypt_text(profile.name_enc) if profile else None,
        "movies_watched": len(movies),
        "watch_minutes": total_minutes,
        "watch_time_label": f"{total_minutes // 60}h {total_minutes % 60:02d}m",
        "most_common_mood": activity_moods.most_common(1)[0][0] if activity_moods else None,
        "mood_source": "planning" if activity_moods else None,
        "favourite_genre": genre_counts.most_common(1)[0][0] if genre_counts else None,
        "average_movie_length": avg,
        "plans_created": len(activities),
        "planned_movie_slots": len(planned_ids),
        "planned_minutes": sum(a.used_minutes or 0 for a in activities),
        "favourite_planned_genre": planning_genres.most_common(1)[0][0] if planning_genres else None,
        "recent_planned_movies": recent_planned,
        "recent_watches": [{"id": m.id, "title": m.title, "runtime": m.runtime,
                           "watched_at": e.created_at.replace(tzinfo=timezone.utc) if e.created_at.tzinfo is None else e.created_at}
                           for e, m in valid_events[:6]],
    }


@router.get("/calendar/status")
def calendar_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.query(CalendarConnection).filter(CalendarConnection.user_id == user.id).first()
    google_available = bool(settings.google_client_id and settings.google_client_secret)
    return {
        "connected": bool(row and row.connected),
        "provider": row.provider if row and row.connected else None,
        "google_available": google_available,
        "google_redirect_uri": settings.google_redirect_uri if google_available else None,
    }


@router.post("/calendar/connect")
def connect_local_calendar(
    data: CalendarLocalConnectRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.provider == "google":
        if not settings.google_client_id or not settings.google_client_secret:
            raise HTTPException(503, "Google Calendar credentials are not configured. You can still use the built-in CineSense calendar.")
        raise HTTPException(400, "Use the Google Calendar connect button to start OAuth.")
    row = db.query(CalendarConnection).filter(CalendarConnection.user_id == user.id).first()
    if not row:
        row = CalendarConnection(user_id=user.id)
        db.add(row)
    row.provider = "local"
    row.connected = True
    row.calendar_id = "cinesense"
    db.commit()
    return {"connected": True, "provider": "local", "message": "CineSense Calendar connected. Add busy times so the planner can find free windows."}


@router.post("/calendar/disconnect")
def disconnect_calendar(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.query(CalendarConnection).filter(CalendarConnection.user_id == user.id).first()
    if row:
        row.connected = False
        row.access_token_enc = ""
        row.refresh_token_enc = ""
        db.commit()
    return {"connected": False}


@router.get("/calendar/google/connect")
def google_connect(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(503, "Google Calendar OAuth is not configured on this deployment.")
    state = secrets.token_urlsafe(32)
    row = db.query(CalendarConnection).filter(CalendarConnection.user_id == user.id).first()
    if not row:
        row = CalendarConnection(user_id=user.id)
        db.add(row)
    row.oauth_state = state
    row.provider = "google"
    db.commit()
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/calendar.events",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return {"auth_url": "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)}


@router.get("/calendar/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    row = db.query(CalendarConnection).filter(CalendarConnection.oauth_state == state).first()
    if not row or not row.oauth_state or not secrets.compare_digest(row.oauth_state, state):
        raise HTTPException(400, "Calendar connection state is invalid or expired.")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if response.status_code >= 400:
        raise HTTPException(502, "Google Calendar connection failed.")
    payload = response.json()
    row.access_token_enc = encrypt_text(payload.get("access_token", ""))
    if payload.get("refresh_token"):
        row.refresh_token_enc = encrypt_text(payload["refresh_token"])
    row.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(payload.get("expires_in", 3600)))
    row.connected = True
    row.provider = "google"
    row.oauth_state = ""
    db.commit()
    return RedirectResponse(settings.public_app_url + "?calendar=connected")


async def _google_token(db: Session, row: CalendarConnection) -> str:
    token = decrypt_text(row.access_token_enc)
    if token and row.token_expires_at and row.token_expires_at > datetime.now(timezone.utc) + timedelta(minutes=2):
        return token
    refresh = decrypt_text(row.refresh_token_enc)
    if not refresh:
        raise HTTPException(401, "Google Calendar needs to be connected again.")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            },
        )
    if response.status_code >= 400:
        raise HTTPException(502, "Could not refresh Google Calendar access.")
    payload = response.json()
    token = payload["access_token"]
    row.access_token_enc = encrypt_text(token)
    row.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(payload.get("expires_in", 3600)))
    db.commit()
    return token


@router.get("/calendar/busy-slots")
def list_busy_slots(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.query(CalendarBusySlot).filter(CalendarBusySlot.user_id == user.id).order_by(CalendarBusySlot.start_at).all()
    return [
        {
            "id": row.id,
            "title": decrypt_text(row.title_enc),
            "start_at": _utc_iso(row.start_at),
            "end_at": _utc_iso(row.end_at),
            "source": row.source,
        }
        for row in rows
    ]


@router.post("/calendar/busy-slots")
def create_busy_slot(
    data: CalendarBusySlotRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start = _aware(data.start_at)
    end = _aware(data.end_at)
    if end <= start:
        raise HTTPException(400, "End time must be after start time.")
    row = CalendarBusySlot(
        user_id=user.id,
        title_enc=encrypt_text(data.title),
        start_at=start,
        end_at=end,
        source="local",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "title": data.title, "start_at": _utc_iso(row.start_at), "end_at": _utc_iso(row.end_at), "source": row.source}


@router.delete("/calendar/busy-slots/{slot_id}")
def delete_busy_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.get(CalendarBusySlot, slot_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Calendar item not found.")
    db.delete(row)
    db.commit()
    return {"ok": True}


def _window_bounds(data: CalendarFreeWindowRequest):
    try:
        day = datetime.strptime(data.date, "%Y-%m-%d").date()
        sh, sm = map(int, data.window_start.split(":"))
        eh, em = map(int, data.window_end.split(":"))
    except Exception:
        raise HTTPException(400, "Please provide valid calendar date/time values.")
    # JavaScript getTimezoneOffset is minutes UTC - local; UTC = local + offset.
    offset = timedelta(minutes=data.timezone_offset_minutes)
    try:
        start = datetime(day.year, day.month, day.day, sh, sm, tzinfo=timezone.utc) + offset
        end = datetime(day.year, day.month, day.day, eh, em, tzinfo=timezone.utc) + offset
    except ValueError:
        raise HTTPException(400, "Please provide valid calendar date/time values.")
    if end <= start:
        end += timedelta(days=1)
    return start, end


def _free_from_busy(start: datetime, end: datetime, busy: list[tuple[datetime, datetime]], min_minutes: int):
    merged = []
    for bstart, bend in sorted(busy):
        bstart = max(bstart, start)
        bend = min(bend, end)
        if bend <= start or bstart >= end or bend <= bstart:
            continue
        if merged and bstart <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], bend))
        else:
            merged.append((bstart, bend))
    cursor = start
    free = []
    for bstart, bend in merged:
        if bstart > cursor:
            free.append((cursor, bstart))
        cursor = max(cursor, bend)
    if cursor < end:
        free.append((cursor, end))
    return [(a, b) for a, b in free if (b - a).total_seconds() >= min_minutes * 60]


@router.post("/calendar/free-windows")
async def calendar_free_windows(
    data: CalendarFreeWindowRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start, end = _window_bounds(data)
    row = db.query(CalendarConnection).filter(CalendarConnection.user_id == user.id, CalendarConnection.connected.is_(True)).first()
    local_rows = db.query(CalendarBusySlot).filter(
        CalendarBusySlot.user_id == user.id,
        CalendarBusySlot.end_at > start, CalendarBusySlot.start_at < end,
    ).all()
    busy = [(r.start_at.replace(tzinfo=r.start_at.tzinfo or timezone.utc),
             r.end_at.replace(tzinfo=r.end_at.tzinfo or timezone.utc)) for r in local_rows]
    provider = "local"
    if row and row.provider == "google":
        token = await _google_token(db, row)
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://www.googleapis.com/calendar/v3/freeBusy",
                headers={"Authorization": f"Bearer {token}"},
                json={"timeMin": start.isoformat(), "timeMax": end.isoformat(), "items": [{"id": row.calendar_id or "primary"}]},
            )
        if response.status_code >= 400:
            raise HTTPException(502, "Could not read Google Calendar availability.")
        entries = response.json().get("calendars", {}).get(row.calendar_id or "primary", {}).get("busy", [])
        for item in entries:
            busy.append((_aware(item["start"]), _aware(item["end"])))
        provider = "google"
    free = _free_from_busy(start, end, busy, data.min_minutes)
    offset = timedelta(minutes=data.timezone_offset_minutes)
    windows = []
    for a, b in free:
        local_a = a - offset
        local_b = b - offset
        minutes = int((b - a).total_seconds() // 60)
        windows.append({
            "start_at": a.isoformat(),
            "end_at": b.isoformat(),
            "minutes": minutes,
            "label": f"{(local_a.hour % 12) or 12}:{local_a.minute:02d} {'AM' if local_a.hour < 12 else 'PM'}–{(local_b.hour % 12) or 12}:{local_b.minute:02d} {'AM' if local_b.hour < 12 else 'PM'} · {minutes // 60}h {minutes % 60:02d}m",
        })
    return {"provider": provider, "windows": windows}


@router.post("/calendar/add-plan")
async def add_plan_to_calendar(
    data: CalendarPlanEventRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start = _aware(data.start_at)
    end = _aware(data.end_at)
    if end <= start:
        raise HTTPException(400, "Calendar event end time must be after the start time.")
    row = db.query(CalendarConnection).filter(CalendarConnection.user_id == user.id, CalendarConnection.connected.is_(True)).first()
    provider = row.provider if row else "local"
    external_event_id = None
    if row and row.provider == "google":
        token = await _google_token(db, row)
        body = {
            "summary": data.title,
            "description": data.description,
            "start": {"dateTime": start.isoformat()},
            "end": {"dateTime": end.isoformat()},
        }
        if data.reminder_minutes is not None:
            body["reminders"] = {"useDefault": False, "overrides": [{"method": "popup", "minutes": data.reminder_minutes}]}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"https://www.googleapis.com/calendar/v3/calendars/{quote(row.calendar_id or 'primary', safe='')}/events",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=body,
            )
        if response.status_code >= 400:
            raise HTTPException(502, "Could not add the watch plan to Google Calendar.")
        external_event_id = response.json().get("id")
    else:
        db.add(CalendarBusySlot(
            user_id=user.id,
            title_enc=encrypt_text(data.title),
            start_at=start,
            end_at=end,
            source="watch-plan",
        ))
        db.commit()

    def ics_dt(dt: datetime) -> str:
        return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    uid = f"cinesense-{secrets.token_hex(8)}@cinesense.local"
    safe_title = data.title.replace("\n", " ").replace(",", "\\,")
    safe_desc = data.description.replace("\n", "\\n").replace(",", "\\,")
    ics = "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//CineSense AI//Watch Planner//EN",
        "BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{ics_dt(datetime.now(timezone.utc))}",
        f"DTSTART:{ics_dt(start)}", f"DTEND:{ics_dt(end)}", f"SUMMARY:{safe_title}", f"DESCRIPTION:{safe_desc}",
        "END:VEVENT", "END:VCALENDAR", ""
    ])
    google_url = "https://calendar.google.com/calendar/render?" + urlencode({
        "action": "TEMPLATE",
        "text": data.title,
        "dates": f"{ics_dt(start).replace('Z','Z')}/{ics_dt(end).replace('Z','Z')}",
        "details": data.description,
    })
    return {
        "ok": True,
        "provider": provider,
        "external_event_id": external_event_id,
        "ics": ics,
        "google_calendar_url": google_url,
        "message": "Watch plan added to your connected calendar." if provider == "google" else "Watch plan saved to CineSense Calendar. You can also download the calendar file.",
    }
