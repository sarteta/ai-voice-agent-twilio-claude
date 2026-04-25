from voice_agent.state import CallPhase, CallSession


def test_session_starts_in_greeting():
    s = CallSession(call_sid="CA1", caller_number="+5491123456789")
    assert s.phase == CallPhase.GREETING
    assert s.transcript == []
    assert not s.needs_human


def test_advance_through_phases():
    s = CallSession(call_sid="CA1", caller_number="+5491123456789")
    s.advance_to(CallPhase.INTENT_DETECTION)
    assert s.phase == CallPhase.INTENT_DETECTION
    s.advance_to(CallPhase.BOOKING)
    assert s.phase == CallPhase.BOOKING


def test_handoff_flag():
    s = CallSession(call_sid="CA1", caller_number="+5491123456789")
    assert not s.needs_human
    s.request_handoff("medical question outside scope")
    assert s.needs_human
    assert s.phase == CallPhase.HANDOFF
    assert s.handoff_reason == "medical question outside scope"


def test_transcript_append_order():
    s = CallSession(call_sid="CA1", caller_number="+5491123456789")
    s.append_user("Hola, quiero un turno")
    s.append_agent("Claro, ¿para qué día?")
    s.append_user("Mañana a las 10")
    assert len(s.transcript) == 3
    assert s.transcript[0]["role"] == "user"
    assert s.transcript[1]["role"] == "assistant"
    assert s.transcript[2]["content"] == "Mañana a las 10"


def test_booking_draft_persists_across_appends():
    s = CallSession(call_sid="CA1", caller_number="+5491123456789")
    s.booking_draft = {"slot": "2026-05-01T10:00", "duration": 30}
    s.append_user("perfecto")
    assert s.booking_draft == {"slot": "2026-05-01T10:00", "duration": 30}


def test_handoff_overrides_phase_even_mid_booking():
    s = CallSession(call_sid="CA1", caller_number="+5491123456789")
    s.advance_to(CallPhase.BOOKING)
    s.request_handoff("caller asked for owner")
    assert s.phase == CallPhase.HANDOFF
    assert s.needs_human
