# Cardinal Mail to Calendar

A Hermes skill that validates meeting details extracted from email. It checks exact source quotes, dates, times and timezones, then returns `ready`, `review` or `ignored`.

## Install

```sh
hermes skills tap add YUNBLAK/cardinal-mail-calendar-skill
hermes skills install YUNBLAK/cardinal-mail-calendar-skill/skills/cardinal-mail-calendar
```

## Run

From the installed `cardinal-mail-calendar` skill directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/validate.py examples/confirmed.json
.venv/bin/python scripts/validate.py examples/ambiguous.json
.venv/bin/python scripts/validate.py examples/ungrounded.json
```

Expected results: `ready`, `review`, `review`. The examples use a fixed clock for repeatability. For current email, omit `now` or supply the actual timezone-aware time.

## Scope

Inputs are `message`, `suggestion`, `timezone` and optional `now`; see the example JSON files. The validator checks source-grounded, future appointments within 180 days, lasting 1 minute to 12 hours. Unsupported or incomplete details require review.

The package performs validation only. Inbox access, calendar writes and notifications belong to the host application. A `ready` result does not authorize a calendar write.
