"""Twilio webhook entrypoint. Receives /incoming-call, manages session,
streams TTS responses back.

In production you want this behind gunicorn with multiple workers and
shared Redis state. For local dev, the in-memory dict is fine.
"""
import os
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather

from .state import CallSession, CallPhase

app = Flask(__name__)
SESSIONS: dict[str, CallSession] = {}


@app.route("/incoming-call", methods=["POST"])
def incoming_call():
    call_sid = request.form["CallSid"]
    from_number = request.form["From"]

    SESSIONS[call_sid] = CallSession(call_sid=call_sid, caller_number=from_number)
    business_name = os.getenv("BUSINESS_NAME", "el consultorio")

    resp = VoiceResponse()
    gather = Gather(
        input="speech",
        action=f"/handle-speech?call_sid={call_sid}",
        speech_timeout="auto",
        language="es-AR",
    )
    gather.say(f"Hola, gracias por llamar a {business_name}. ¿En qué puedo ayudarte?",
               language="es-AR", voice="Polly.Mia-Neural")
    resp.append(gather)
    return Response(str(resp), mimetype="application/xml")


@app.route("/handle-speech", methods=["POST"])
def handle_speech():
    call_sid = request.args["call_sid"]
    user_text = request.form.get("SpeechResult", "")

    session = SESSIONS.get(call_sid)
    if not session:
        return _hangup_response("Disculpá, hubo un error. Llamá de nuevo en un momento.")

    if session.phase == CallPhase.HANDOFF:
        return _transfer_response()

    # In a real deployment, swap _stub_response for Conversation.respond
    # bound to a real Anthropic client + GCal-backed ToolHandler.
    reply = _stub_response(user_text, session)

    resp = VoiceResponse()
    if session.phase == CallPhase.GOODBYE:
        resp.say(reply, language="es-AR", voice="Polly.Mia-Neural")
        resp.hangup()
    else:
        gather = Gather(
            input="speech",
            action=f"/handle-speech?call_sid={call_sid}",
            speech_timeout="auto",
            language="es-AR",
        )
        gather.say(reply, language="es-AR", voice="Polly.Mia-Neural")
        resp.append(gather)
    return Response(str(resp), mimetype="application/xml")


def _stub_response(user_text: str, session: CallSession) -> str:
    """Stand-in for tests / local dev without Anthropic key configured.

    Swap with Conversation.respond in production wiring.
    """
    session.append_user(user_text)
    if any(w in user_text.lower() for w in ["humano", "persona", "operador"]):
        session.request_handoff("user requested human")
        return "Te paso con una persona del equipo."
    if any(w in user_text.lower() for w in ["chau", "gracias", "nada"]):
        session.advance_to(CallPhase.GOODBYE)
        return "Gracias por llamar. ¡Que tengas buen día!"
    reply = "Entendido. ¿Para qué fecha querés el turno?"
    session.append_agent(reply)
    return reply


def _hangup_response(message: str) -> Response:
    resp = VoiceResponse()
    resp.say(message, language="es-AR", voice="Polly.Mia-Neural")
    resp.hangup()
    return Response(str(resp), mimetype="application/xml")


def _transfer_response() -> Response:
    resp = VoiceResponse()
    transfer_to = os.getenv("HUMAN_HANDOFF_NUMBER")
    if transfer_to:
        resp.dial(transfer_to)
    else:
        resp.say("Te llamamos en unos minutos.", language="es-AR")
        resp.hangup()
    return Response(str(resp), mimetype="application/xml")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
