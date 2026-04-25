# Use case — hair salon, multi-stylist scheduling

## Customer

Salon with 3 stylists, each with separate calendars. Customers usually
ask for "Marian" or "el chico nuevo" (no name yet for the new stylist).

## Configuration changes from base setup

- One Google Calendar per stylist, configured in `STYLIST_CALENDARS` env
  var as JSON: `{"marian": "marian@salon.com", "lucia": "lucia@salon.com"}`
- Tool definitions extended: `check_availability` accepts a
  `stylist_preference` arg (optional), defaults to "any"
- Custom prompt addition: "Si el cliente menciona nombre de estilista,
  usá ese calendario. Si no menciona, ofrecé el primer slot disponible
  de cualquiera y mencioná quién es."

## What this teaches

The same code skeleton handles multi-resource scheduling without changes
to the state machine. The flexibility is in the tools layer + system
prompt — exactly where you want it.

## Caveats

- Caller asks for a specific stylist who's on vacation: tool returns
  empty slots. Agent should offer to book with any other stylist.
  Implemented via second prompt instruction.
- Callers often say "el de barba" or "la chica del pelo violeta". This
  doesn't map to a stylist ID without a custom resolver. Out of scope
  for the base repo; document it in the deployment guide for the
  customer to maintain.
