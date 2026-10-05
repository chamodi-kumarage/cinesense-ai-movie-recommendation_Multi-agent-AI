from datetime import datetime, timezone
from test_watch_insights import history
from app.models import CalendarBusySlot
from app.security import encrypt_text


def test_saved_events_have_explicit_utc_and_correct_round_trip(history):
    c, _, _, _, _ = history
    body = {"title": "Evening class", "start_at": "2026-10-05T18:00:00+05:30", "end_at": "2026-10-05T19:00:00+05:30"}
    result = c.post("/api/calendar/busy-slots", json=body)
    assert result.status_code == 200
    event = result.json()
    assert event["start_at"] == "2026-10-05T12:30:00+00:00"
    listed = c.get("/api/calendar/busy-slots").json()
    assert listed[0]["start_at"] == event["start_at"]
    assert listed[0]["title"] == "Evening class"
    assert c.delete("/api/calendar/busy-slots/"+str(event["id"])).status_code == 200
    assert c.get("/api/calendar/busy-slots").json() == []


def test_invalid_times_return_client_errors(history):
    c, _, _, _, _ = history
    assert c.post("/api/calendar/busy-slots", json={"title": "Invalid", "start_at": "2026-10-05T19:00:00Z", "end_at": "2026-10-05T18:00:00Z"}).status_code == 400
    for date, start in [("2026-10-05", "25:00"), ("2026-02-30", "18:00"), ("not-a-date", "18:00")]:
        result = c.post("/api/calendar/free-windows", json={"date": date, "window_start": start})
        assert result.status_code == 400


def test_free_windows_merge_overlaps_in_local_timezone(history):
    c, _, _, _, _ = history
    for start, end in [("18:30", "19:30"), ("19:00", "20:00")]:
        assert c.post("/api/calendar/busy-slots", json={"title": "Busy", "start_at": "2026-10-05T"+start+":00+05:30", "end_at": "2026-10-05T"+end+":00+05:30"}).status_code == 200
    result = c.post("/api/calendar/free-windows", json={"date": "2026-10-05", "window_start": "18:00", "window_end": "22:00", "timezone_offset_minutes": -330})
    assert result.status_code == 200
    windows = result.json()["windows"]
    assert [w["minutes"] for w in windows] == [30, 120]
    assert windows[0]["start_at"] == "2026-10-05T12:30:00+00:00"
    assert windows[1]["start_at"] == "2026-10-05T14:30:00+00:00"
    other_day = c.post("/api/calendar/free-windows", json={"date": "2026-10-06", "window_start": "18:00", "window_end": "22:00", "timezone_offset_minutes": -330})
    assert other_day.json()["windows"][0]["minutes"] == 240


def test_watch_plan_is_marked_and_blocks_free_time(history):
    c, _, _, _, _ = history
    result = c.post("/api/calendar/add-plan", json={"title": "Watch movie", "start_at": "2026-10-05T18:00:00Z", "end_at": "2026-10-05T20:00:00Z"})
    assert result.status_code == 200 and "BEGIN:VEVENT" in result.json()["ics"]
    slots = c.get("/api/calendar/busy-slots").json()
    assert slots[0]["source"] == "watch-plan" and slots[0]["title"] == "Watch movie"
    free = c.post("/api/calendar/free-windows", json={"date": "2026-10-05", "window_start": "18:00", "window_end": "22:00", "timezone_offset_minutes": 0})
    assert [w["minutes"] for w in free.json()["windows"]] == [120]


def test_calendar_ownership_and_cross_midnight_events(history):
    c, Session, user, _, _ = history
    own = c.post("/api/calendar/busy-slots", json={"title": "Night shift", "start_at": "2026-10-05T23:00:00Z", "end_at": "2026-10-06T02:00:00Z"}).json()
    with Session() as db:
        other = CalendarBusySlot(user_id=user.id+999, title_enc=encrypt_text("Other account"), start_at=datetime(2026,10,5,18,tzinfo=timezone.utc), end_at=datetime(2026,10,5,20,tzinfo=timezone.utc), source="local")
        db.add(other);db.commit();other_id=other.id
    assert [e["id"] for e in c.get("/api/calendar/busy-slots").json()] == [own["id"]]
    assert c.delete("/api/calendar/busy-slots/"+str(other_id)).status_code == 404
    free = c.post("/api/calendar/free-windows", json={"date": "2026-10-05", "window_start": "22:00", "window_end": "03:00", "timezone_offset_minutes": 0})
    assert [w["minutes"] for w in free.json()["windows"]] == [60,60]
