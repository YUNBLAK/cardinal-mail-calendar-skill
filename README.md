# Cardinal Mail to Calendar — Hermes skill

Validate appointment candidates extracted from email before a host creates calendar events.
A confirmed date and time must be grounded in an exact source quotation. Ambiguous or unsupported
candidates return `review`; explicit non-events return `ignored`. The validator handles timezone
conversion and reports its supported-format limits rather than inventing missing meeting details.

This portable skill has no mailbox credentials, network calls, calendar writes or notifications.
The separate Cardinal application supplies those integrations. Installing this skill does not start
automatic email polling. A `ready` result is validation, not proof of sender authenticity or permission
to write an external calendar.

## Install with Hermes

Public tap: `yunblack/cardinal-mail-calendar-skill`. Use the repository-backed installation:

```sh
hermes skills tap add yunblack/cardinal-mail-calendar-skill
hermes skills install yunblack/cardinal-mail-calendar-skill/skills/cardinal-mail-calendar
```

Record the installed `source_revision` from Hermes' skill lock as the immutable submission commit.
A raw SKILL.md URL does not install the complete package. The full directory includes scripts, three
examples and the pinned dependency.

## Run

From the installed skill directory, use an isolated Python environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/validate.py examples/confirmed.json
.venv/bin/python scripts/validate.py examples/ambiguous.json
.venv/bin/python scripts/validate.py examples/ungrounded.json
```

Expected statuses, in order: `ready`, `review`, `review`. The examples include an explicit fixed clock
for reproducibility. For current data, omit `now` or supply the actual timezone-aware time. Inputs are
`message`, `suggestion`, `timezone`, and optional `now`; see the example JSON files and SKILL.md.

## Attribution and evidence

Original CS599 project work prepared by yunblack with OpenAI Codex assistance. The validator is
extracted from the project's `calendar_policy.py`. Hermes is a separate Nous Research project and
is not bundled here. The standalone examples have passed locally; a clean public installation and
execution transcript will be recorded after publication. No public-installation success is claimed yet.
