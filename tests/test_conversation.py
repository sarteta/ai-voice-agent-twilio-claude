from voice_agent.conversation import Conversation
from voice_agent.state import CallPhase, CallSession


class FakeLLM:
    def __init__(self, responses: list[dict]):
        self._responses = list(responses)

    def complete(self, system, messages, tools):
        return self._responses.pop(0)


class FakeTools:
    def __init__(self):
        self.bookings_made = []
        self.availability_responses = []

    def check_availability(self, date_iso: str, duration_min: int):
        return self.availability_responses.pop(0) if self.availability_responses else []

    def book_appointment(self, summary, start_iso, duration_min, caller_phone):
        booking = {"summary": summary, "start": start_iso, "phone": caller_phone}
        self.bookings_made.append(booking)
        return {"id": f"evt_{len(self.bookings_made)}", **booking}


def _new_session():
    return CallSession(call_sid="CA1", caller_number="+5491123456789")


def test_simple_text_response_appends_to_transcript():
    llm = FakeLLM([{"type": "text", "text": "¿Para qué día querés el turno?"}])
    tools = FakeTools()
    conv = Conversation(llm, tools, business_name="Consultorio Demo")

    s = _new_session()
    reply = conv.respond(s, "Quiero un turno")
    assert reply == "¿Para qué día querés el turno?"
    assert len(s.transcript) == 2
    assert s.transcript[0]["role"] == "user"


def test_check_availability_tool_returns_options():
    llm = FakeLLM([{
        "type": "tool_use",
        "name": "check_availability",
        "input": {"date_iso": "2026-05-04"},
    }])
    tools = FakeTools()
    tools.availability_responses = [["10:00", "11:30", "15:00"]]
    conv = Conversation(llm, tools, business_name="Demo")

    s = _new_session()
    reply = conv.respond(s, "Quiero un turno el lunes")
    assert "10:00" in reply
    assert "11:30" in reply
    assert s.phase == CallPhase.BOOKING


def test_check_availability_no_slots_offers_alternative():
    llm = FakeLLM([{
        "type": "tool_use",
        "name": "check_availability",
        "input": {"date_iso": "2026-05-04"},
    }])
    tools = FakeTools()
    tools.availability_responses = [[]]
    conv = Conversation(llm, tools, business_name="Demo")

    s = _new_session()
    reply = conv.respond(s, "Lunes a las 10")
    assert "no hay turnos" in reply.lower() or "otra fecha" in reply.lower()


def test_book_appointment_creates_event_and_advances_phase():
    llm = FakeLLM([{
        "type": "tool_use",
        "name": "book_appointment",
        "input": {
            "summary": "Consulta",
            "start_iso": "2026-05-04T10:00",
            "caller_phone": "+5491123456789",
        },
    }])
    tools = FakeTools()
    conv = Conversation(llm, tools, business_name="Demo")

    s = _new_session()
    reply = conv.respond(s, "Confirmo el de las 10")
    assert "2026-05-04T10:00" in reply
    assert s.phase == CallPhase.CONFIRMING
    assert len(tools.bookings_made) == 1
    assert tools.bookings_made[0]["phone"] == "+5491123456789"


def test_handoff_request_sets_phase():
    llm = FakeLLM([{
        "type": "tool_use",
        "name": "request_handoff",
        "input": {"reason": "complex medical question"},
    }])
    conv = Conversation(llm, FakeTools(), business_name="Demo")

    s = _new_session()
    conv.respond(s, "tengo dolor agudo, qué hago")
    assert s.needs_human
    assert s.handoff_reason == "complex medical question"


def test_unknown_tool_raises():
    llm = FakeLLM([{"type": "tool_use", "name": "delete_database", "input": {}}])
    conv = Conversation(llm, FakeTools(), business_name="Demo")

    import pytest
    with pytest.raises(ValueError, match="Unknown tool"):
        conv.respond(_new_session(), "what happens?")


def test_full_booking_flow_three_turns():
    llm = FakeLLM([
        {"type": "text", "text": "¿Para qué fecha?"},
        {"type": "tool_use", "name": "check_availability",
         "input": {"date_iso": "2026-05-04"}},
        {"type": "tool_use", "name": "book_appointment",
         "input": {"summary": "Consulta", "start_iso": "2026-05-04T10:00",
                   "caller_phone": "+5491123456789"}},
    ])
    tools = FakeTools()
    tools.availability_responses = [["10:00", "11:30"]]
    conv = Conversation(llm, tools, business_name="Demo")

    s = _new_session()
    conv.respond(s, "Hola, quiero turno")
    conv.respond(s, "El lunes")
    conv.respond(s, "Confirmo el de 10")

    assert s.phase == CallPhase.CONFIRMING
    assert len(tools.bookings_made) == 1
