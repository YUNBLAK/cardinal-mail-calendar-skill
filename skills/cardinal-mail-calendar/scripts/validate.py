#!/usr/bin/env python3
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from calendar_policy import EventSuggestion, grounded_event

data = json.loads(Path(sys.argv[1]).read_text())
try:
    suggestion = EventSuggestion.model_validate(data['suggestion'])
    if suggestion.decision == 'ignore':
        result = {'status': 'ignored', 'reason': suggestion.reason}
    else:
        now = datetime.fromisoformat(data['now']) if data.get('now') else datetime.now(UTC)
        event = grounded_event(suggestion.model_dump(), data['message'], data['timezone'], now)
        result = {'status': 'ready', 'event': event}
except (ValueError, KeyError) as error:
    result = {'status': 'review', 'reason': str(error)}
print(json.dumps(result, ensure_ascii=False, indent=2))
