from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CallPhase(str, Enum):
    GREETING = "greeting"
    INTENT_DETECTION = "intent_detection"
    BOOKING = "booking"
    CONFIRMING = "confirming"
    HANDOFF = "handoff"
    GOODBYE = "goodbye"


@dataclass
class CallSession:
    call_sid: str
    caller_number: str
    phase: CallPhase = CallPhase.GREETING
    transcript: list[dict[str, str]] = field(default_factory=list)
    booking_draft: dict[str, Any] = field(default_factory=dict)
    handoff_reason: str | None = None

    def append_user(self, text: str) -> None:
        self.transcript.append({"role": "user", "content": text})

    def append_agent(self, text: str) -> None:
        self.transcript.append({"role": "assistant", "content": text})

    def advance_to(self, phase: CallPhase) -> None:
        self.phase = phase

    def request_handoff(self, reason: str) -> None:
        self.handoff_reason = reason
        self.phase = CallPhase.HANDOFF

    @property
    def needs_human(self) -> bool:
        return self.phase == CallPhase.HANDOFF
