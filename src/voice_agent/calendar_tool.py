from datetime import datetime, timedelta, timezone
from typing import Protocol


class CalendarClient(Protocol):
    def list_events(self, start: datetime, end: datetime) -> list[dict]: ...
    def create_event(self, summary: str, start: datetime, duration_min: int,
                     attendee_phone: str) -> dict: ...


def find_open_slots(
    cal: CalendarClient,
    on_date: datetime,
    duration_min: int = 30,
    business_hours: tuple[int, int] = (9, 18),
) -> list[datetime]:
    """Return start times of available slots on the given date.

    Slots are aligned to the half-hour. A slot is "open" when no existing
    event overlaps the [slot, slot + duration) window.
    """
    day_start = on_date.replace(hour=business_hours[0], minute=0, second=0, microsecond=0)
    day_end = on_date.replace(hour=business_hours[1], minute=0, second=0, microsecond=0)

    existing = cal.list_events(day_start, day_end)
    busy_ranges = [
        (datetime.fromisoformat(e["start"]), datetime.fromisoformat(e["end"]))
        for e in existing
    ]

    slots: list[datetime] = []
    cursor = day_start
    while cursor + timedelta(minutes=duration_min) <= day_end:
        slot_end = cursor + timedelta(minutes=duration_min)
        overlaps = any(bs < slot_end and be > cursor for bs, be in busy_ranges)
        if not overlaps:
            slots.append(cursor)
        cursor += timedelta(minutes=30)

    return slots


def book_slot(
    cal: CalendarClient,
    summary: str,
    start: datetime,
    duration_min: int,
    attendee_phone: str,
) -> dict:
    """Create the calendar event. Returns the created event dict.

    The caller is responsible for verifying the slot is still open via
    find_open_slots immediately before calling this — Google Calendar's
    API does not provide native conflict-detection on insert.
    """
    return cal.create_event(
        summary=summary,
        start=start,
        duration_min=duration_min,
        attendee_phone=attendee_phone,
    )


def to_local_human(slot: datetime, locale: str = "es-AR") -> str:
    """Format a slot for the LLM to read aloud."""
    if locale == "es-AR":
        weekdays = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        return f"{weekdays[slot.weekday()]} {slot.day} a las {slot.hour}:{slot.minute:02d}"
    return slot.strftime("%A %B %d at %I:%M %p")
