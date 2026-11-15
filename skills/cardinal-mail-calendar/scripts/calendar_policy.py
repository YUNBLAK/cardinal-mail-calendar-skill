"""Validate event suggestions against exact email evidence before any calendar write."""
import hashlib
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field


class EventSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern=r"^(confirmed|review|ignore)$")
    title: str = Field(default="", max_length=160)
    date_text: str = Field(default="", max_length=60)
    start_text: str = Field(default="", max_length=40)
    end_text: str = Field(default="", max_length=40)
    timezone_text: str = Field(default="", max_length=60)
    location: str = Field(default="", max_length=200)
    evidence: str = Field(default="", max_length=1200)
    reason: str = Field(default="", max_length=300)


ZONE_ALIASES = {"PST": "America/Los_Angeles", "PDT": "America/Los_Angeles",
                "EST": "America/New_York", "EDT": "America/New_York",
                "KST": "Asia/Seoul", "UTC": "UTC", "GMT": "UTC"}
MONTHS = {name.lower(): i for i, name in enumerate(
    ["", "January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"]) if name}
MONTHS.update({name[:3]: month for name, month in list(MONTHS.items())})


def normalized_title(value):
    return re.sub(r"[\W_]+", "", value.casefold())


def source_key(mailbox, message):
    identity = message.get("message_id", "").strip() or message["uid_key"]
    return hashlib.sha256((mailbox.lower() + "\n" + identity).encode()).hexdigest()


def content_key(message):
    # Message-ID can change on redelivery. Do not use a model-generated title to recognize that case.
    identity = "\0".join(str(message.get(k, "")) for k in ("from", "subject", "body", "truncated"))
    return hashlib.sha256(identity.encode()).hexdigest()


def event_id(calendar_id, event):
    # Same event mentioned in a new message also maps to the same Calendar ID.
    identity = "\n".join([calendar_id, normalized_title(event["title"]),
                           event["start"], event["end"], normalized_title(event.get("location", ""))])
    return "a3" + hashlib.sha256(identity.encode()).hexdigest()


def parse_day(value, reference):
    value = value.strip()
    match = re.fullmatch(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", value)
    if match:
        year, month, day = map(int, match.groups())
    else:
        match = re.fullmatch(r"(?:(\d{4})년\s*)?(\d{1,2})월\s*(\d{1,2})일", value)
        if match:
            year, month, day = match.groups()
            year, month, day = int(year or reference.year), int(month), int(day)
        else:
            match = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?", value)
            if not match or match[1].lower() not in MONTHS:
                raise ValueError("Please confirm the date in YYYY-MM-DD format.")
            year, month, day = int(match[3] or reference.year), MONTHS[match[1].lower()], int(match[2])
    return datetime(year, month, day).date()


def parse_clock(value, inherited_meridiem=None):
    text = re.sub(r"\s+", "", value).lower().replace(".", "")
    marker = "am" if "am" in text or "오전" in text else "pm" if "pm" in text or "오후" in text else None
    text = re.sub(r"am|pm|오전|오후", "", text)
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2})|시(?:(\d{1,2})분)?)?", text)
    if not match:
        raise ValueError("Please confirm the start and end times.")
    hour, minute = int(match[1]), int(match[2] or match[3] or 0)
    marker = marker or (inherited_meridiem if hour <= 12 else None)
    if marker:
        if not 1 <= hour <= 12:
            raise ValueError("The hour does not match the AM/PM marker.")
        hour = hour % 12 + (12 if marker == "pm" else 0)
    elif not (":" in text or "시" in text):
        raise ValueError("Use an AM/PM marker or a 24-hour time.")
    if hour > 23 or minute > 59:
        raise ValueError("Invalid time.")
    return hour, minute, marker


def validate_range(start, end, now):
    if not start.tzinfo or not end.tzinfo:
        raise ValueError("A timezone is required.")
    if start <= now or start > now + timedelta(days=180):
        raise ValueError("The appointment must be in the future and within 180 days.")
    if not timedelta(minutes=1) <= end - start <= timedelta(hours=12):
        raise ValueError("The end time must be between 1 minute and 12 hours after the start.")
    # Round trip rejects nonexistent DST wall times; ambiguous fall-back times need a person.
    for moment in (start, end):
        if moment.astimezone(ZoneInfo("UTC")).astimezone(moment.tzinfo).replace(tzinfo=None) != moment.replace(tzinfo=None):
            raise ValueError("This time does not exist because of a daylight-saving transition.")
        if moment.replace(fold=0).utcoffset() != moment.replace(fold=1).utcoffset():
            raise ValueError("Please clarify this ambiguous daylight-saving transition time.")


def grounded_event(suggestion, message, timezone, now):
    candidate = EventSuggestion.model_validate(suggestion)
    if candidate.decision != "confirmed":
        raise ValueError(candidate.reason or "Please confirm that this appointment is scheduled.")
    source = message["subject"] + "\n" + message["body"]
    if message.get("truncated"):
        raise ValueError("This long email was truncated and needs review.")
    if not candidate.evidence or candidate.evidence not in source:
        raise ValueError("The appointment evidence could not be found in the source email.")
    for field in (candidate.date_text, candidate.start_text, candidate.end_text):
        if not field or field not in candidate.evidence:
            raise ValueError("The date and both times must appear in the same source quote.")
    if candidate.location and candidate.location not in source:
        raise ValueError("The location could not be found in the source email.")
    zone_text = candidate.timezone_text
    if zone_text and zone_text not in source:
        raise ValueError("The timezone could not be found in the source email.")
    zone = ZoneInfo(ZONE_ALIASES.get(zone_text.upper(), zone_text) if zone_text else timezone)
    reference = datetime.fromisoformat(message["received_at"]).astimezone(zone)
    day = parse_day(candidate.date_text, reference)
    sh, sm, meridiem = parse_clock(candidate.start_text)
    eh, em, _ = parse_clock(candidate.end_text, meridiem)
    start = datetime(day.year, day.month, day.day, sh, sm, tzinfo=zone)
    end = datetime(day.year, day.month, day.day, eh, em, tzinfo=zone)
    if zone_text.upper() in {"PST", "PDT", "EST", "EDT"} and start.tzname() != zone_text.upper():
        raise ValueError("The timezone abbreviation does not match the appointment date.")
    validate_range(start, end, now)
    if not candidate.title.strip():
        raise ValueError("An event title is required.")
    return {"title": candidate.title.strip(), "start": start.isoformat(), "end": end.isoformat(),
            "timezone": str(zone), "location": candidate.location, "evidence": candidate.evidence}


def manual_event(title, date, start, end, timezone, now):
    zone = ZoneInfo(timezone)
    begin = datetime.fromisoformat(date + "T" + start).replace(tzinfo=zone)
    finish = datetime.fromisoformat(date + "T" + end).replace(tzinfo=zone)
    validate_range(begin, finish, now)
    return {"title": title[:160], "start": begin.isoformat(), "end": finish.isoformat(),
            "timezone": timezone, "location": "", "evidence": "The user supplied the date and times through Telegram or authenticated chat."}
