# Use case — after-hours emergency service handoff

## Customer

Plumbing service. After-hours calls that mention specific keywords need
to be routed to the on-call plumber's mobile immediately.

## Implementation

The base `request_handoff` tool already supports this. The customization
is in the system prompt:

```
Si el cliente menciona alguna de estas situaciones:
- pérdida de agua activa, inundación, sin agua
- sin gas, olor a gas
- urgencia, ahora mismo, ya
→ llamar request_handoff inmediatamente con razón "emergency: <palabra clave>"

Para todo lo demás (cambio de canilla, presupuesto, consulta general)
→ tomar mensaje y agendar callback el día siguiente.
```

The handoff route in `app.py` reads `HUMAN_HANDOFF_NUMBER` and
`<Dial>`s it. In production you want this to be a Twilio call queue or
a TwiML number that tries 3 numbers in sequence.

## Why a state machine for this and not "just check keywords in the prompt"

The state machine logs `handoff_reason` to the call session, which gets
written to the customer's CRM at end of call. They use this to track
which call subjects are most common emergencies — informs whether they
need to add staff for those use cases.

A pure-prompt approach loses this signal. State + tools + LLM working
together is more verbose but the data flow is observable.
