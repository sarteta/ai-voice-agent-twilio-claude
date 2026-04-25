# Use case — dental office, after-hours booking

## Customer

Independent dentist in Córdoba, Argentina. One reception desk that closes
at 19:00. Calls after hours go to voicemail; ~40% never call back. They
estimate ~30 missed bookings/month.

## Setup

- Twilio number: forwards from the office line after 19:00 and on weekends
- Business hours configured in calendar: 9:00-19:00 weekdays, 9:00-13:00 Sat
- Appointment types: cleaning (30 min), checkup (30 min), filling (60 min)
- Handoff: any question with words "dolor", "urgencia", "sangre",
  "infección" → routes to dentist's mobile via Twilio dial

## What works

- 70-80% of after-hours calls successfully book a slot for the next
  available day
- Caller hears agent within 1 second of pickup (TTS streaming)
- Spanish argentino feels natural (Polly.Mia-Neural voice)

## Edge cases caught during pilot

1. **Calls in the middle of an appointment block.** Agent was offering the
   exact slot a current patient was in. Fix: `find_open_slots` reads
   busy from calendar, didn't account for the calendar entry being
   "tentative". Now requires status="confirmed".
2. **Caller spells out date as "tipo el martes próximo".** Claude handles
   this naturally — converts to ISO date in the tool call. No regex needed.
3. **Caller lists multiple constraints.** "Tiene que ser después del
   colegio, alrededor de 16hs, pero no martes." Claude juggles all three
   constraints in tool args.

## What doesn't work yet

- Cancellations. Currently the agent can only book. Cancellations route
  to handoff. Next iteration adds a cancel tool with a confirmation step.
- Multiple appointments in one call (family of 4 booking together). The
  state machine handles one booking at a time. Workaround: agent
  explicitly says "te reservo el primero, después llamame para los otros".

## Cost (Twilio + Anthropic + ElevenLabs, monthly)

For ~150 calls/month averaging 90 seconds each:

- Twilio voice: ~$3
- Twilio number: $1.15
- Anthropic (Sonnet, ~2k tokens/call): ~$15
- ElevenLabs (~150 chars/call avg, output): ~$5
- Total: **~$25/month**

Compared to a human receptionist part-time at $400/month for the same
hours, ROI is obvious.
