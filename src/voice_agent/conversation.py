"""Claude-driven dialog manager with tool-use for calendar operations.

Keeps tool definitions colocated with the system prompt so changes don't
drift. The Anthropic client is injected — pass a real one in production,
a mock in tests.
"""
from datetime import datetime
from typing import Any, Protocol

from .state import CallPhase, CallSession


SYSTEM_PROMPT = """Eres una asistente virtual de {business_name}, atendiendo
llamadas en español. Tu rol:

1. Saludar y preguntar en qué puedes ayudar.
2. Si el cliente quiere reservar: pedir fecha + hora preferida, verificar
   disponibilidad con check_availability, ofrecer 2-3 opciones reales.
3. Si confirma una opción, llamar book_appointment con los datos.
4. Si la consulta es médica/técnica/sensible, derivar a un humano con
   request_handoff y razón.
5. NUNCA inventes horarios. NUNCA reserves sin confirmar.

Formato: respuestas cortas (1-2 oraciones), tono cálido pero profesional,
español argentino neutro. Si no entendiste, pide que repita una vez antes
de derivar a humano."""


TOOLS = [
    {
        "name": "check_availability",
        "description": "Check open slots for a specific date and duration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date_iso": {"type": "string", "description": "YYYY-MM-DD"},
                "duration_min": {"type": "integer", "default": 30},
            },
            "required": ["date_iso"],
        },
    },
    {
        "name": "book_appointment",
        "description": "Book a confirmed slot. Only call after caller confirms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "start_iso": {"type": "string"},
                "duration_min": {"type": "integer"},
                "caller_phone": {"type": "string"},
            },
            "required": ["summary", "start_iso", "caller_phone"],
        },
    },
    {
        "name": "request_handoff",
        "description": "Transfer the call to a human. Use when query is out of scope.",
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
            "required": ["reason"],
        },
    },
]


class LLMClient(Protocol):
    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> Any: ...


class ToolHandler(Protocol):
    def check_availability(self, date_iso: str, duration_min: int) -> list[str]: ...
    def book_appointment(self, summary: str, start_iso: str,
                         duration_min: int, caller_phone: str) -> dict: ...


class Conversation:
    def __init__(self, llm: LLMClient, tools: ToolHandler, business_name: str):
        self.llm = llm
        self.tools = tools
        self.business_name = business_name

    def respond(self, session: CallSession, user_text: str) -> str:
        session.append_user(user_text)

        system = SYSTEM_PROMPT.format(business_name=self.business_name)
        result = self.llm.complete(
            system=system,
            messages=session.transcript,
            tools=TOOLS,
        )

        if result.get("type") == "tool_use":
            return self._handle_tool(session, result)

        text = result["text"]
        session.append_agent(text)
        return text

    def _handle_tool(self, session: CallSession, tool_call: dict) -> str:
        name = tool_call["name"]
        args = tool_call["input"]

        if name == "check_availability":
            slots = self.tools.check_availability(args["date_iso"], args.get("duration_min", 30))
            if not slots:
                reply = f"No hay turnos disponibles ese día. ¿Querés probar otra fecha?"
            else:
                opts = ", ".join(slots[:3])
                reply = f"Tengo disponibles: {opts}. ¿Cuál te queda mejor?"
            session.advance_to(CallPhase.BOOKING)
            session.append_agent(reply)
            return reply

        if name == "book_appointment":
            booking = self.tools.book_appointment(
                summary=args["summary"],
                start_iso=args["start_iso"],
                duration_min=args.get("duration_min", 30),
                caller_phone=args["caller_phone"],
            )
            session.booking_draft = booking
            session.advance_to(CallPhase.CONFIRMING)
            reply = f"Listo, te confirmo turno para {args['start_iso']}. Te llega un SMS con los detalles. ¿Algo más?"
            session.append_agent(reply)
            return reply

        if name == "request_handoff":
            session.request_handoff(args["reason"])
            return "Te paso con una persona del equipo, no cortes."

        raise ValueError(f"Unknown tool: {name}")
