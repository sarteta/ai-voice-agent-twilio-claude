from datetime import datetime, timezone

from voice_agent.calendar_tool import find_open_slots, to_local_human


class FakeCalendar:
    def __init__(self, events: list[dict]):
        self._events = events

    def list_events(self, start, end):
        return [e for e in self._events
                if datetime.fromisoformat(e["start"]) < end
                and datetime.fromisoformat(e["end"]) > start]

    def create_event(self, summary, start, duration_min, attendee_phone):
        return {"id": "evt_test", "summary": summary, "start": start.isoformat()}


def test_open_slots_when_no_events():
    cal = FakeCalendar([])
    on = datetime(2026, 5, 1, tzinfo=timezone.utc)
    slots = find_open_slots(cal, on, duration_min=30, business_hours=(9, 18))
    assert len(slots) == 18  # 9am to 6pm in 30-min steps
    assert slots[0].hour == 9
    assert slots[-1].hour == 17 and slots[-1].minute == 30


def test_open_slots_skips_busy_window():
    busy_start = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
    busy_end = datetime(2026, 5, 1, 11, 0, tzinfo=timezone.utc)
    cal = FakeCalendar([{"start": busy_start.isoformat(), "end": busy_end.isoformat()}])
    slots = find_open_slots(cal, datetime(2026, 5, 1, tzinfo=timezone.utc),
                            duration_min=30, business_hours=(9, 18))
    busy_starts = [s for s in slots if 10 <= s.hour < 11]
    assert busy_starts == []


def test_partial_overlap_blocks_slot():
    busy_start = datetime(2026, 5, 1, 10, 15, tzinfo=timezone.utc)
    busy_end = datetime(2026, 5, 1, 10, 45, tzinfo=timezone.utc)
    cal = FakeCalendar([{"start": busy_start.isoformat(), "end": busy_end.isoformat()}])
    slots = find_open_slots(cal, datetime(2026, 5, 1, tzinfo=timezone.utc),
                            duration_min=30, business_hours=(9, 18))
    assert datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc) not in slots
    assert datetime(2026, 5, 1, 10, 30, tzinfo=timezone.utc) not in slots


def test_back_to_back_meetings_dont_block_slot_at_end():
    e1 = {"start": "2026-05-01T10:00:00+00:00", "end": "2026-05-01T10:30:00+00:00"}
    cal = FakeCalendar([e1])
    slots = find_open_slots(cal, datetime(2026, 5, 1, tzinfo=timezone.utc),
                            duration_min=30, business_hours=(9, 18))
    assert datetime(2026, 5, 1, 10, 30, tzinfo=timezone.utc) in slots


def test_human_format_es_ar():
    slot = datetime(2026, 5, 4, 14, 30)  # Monday
    assert to_local_human(slot, locale="es-AR") == "lunes 4 a las 14:30"


def test_human_format_default_english():
    slot = datetime(2026, 5, 4, 14, 30)
    out = to_local_human(slot, locale="en")
    assert "May" in out
    assert "02:30 PM" in out


def test_short_business_hours_returns_few_slots():
    cal = FakeCalendar([])
    slots = find_open_slots(cal, datetime(2026, 5, 1, tzinfo=timezone.utc),
                            duration_min=30, business_hours=(14, 16))
    assert len(slots) == 4  # 14:00, 14:30, 15:00, 15:30


def test_long_appointment_fewer_slots_fit():
    cal = FakeCalendar([])
    slots = find_open_slots(cal, datetime(2026, 5, 1, tzinfo=timezone.utc),
                            duration_min=90, business_hours=(9, 12))
    assert len(slots) == 4  # 9:00, 9:30, 10:00, 10:30 — last must end <=12
