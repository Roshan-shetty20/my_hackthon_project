import time
from datetime import datetime, timedelta
from typing import List, Optional

from backend.models import NormalizedEvent

class DeterministicSimulator:
    """A deterministic event sequencer that provides a fixed simulation timeline."""

    def __init__(self):
        self.current_idx = 0
        self.start_time = datetime.now()
        self.events: List[NormalizedEvent] = self._build_event_stream()

    def _build_event_stream(self) -> List[NormalizedEvent]:
        import json
        import os
        
        scenario_path = os.path.join(os.path.dirname(__file__), "..", "data", "scenarios", "surat_monsoon.json")
        try:
            with open(scenario_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []
            
        base_time = self.start_time
        def _ts(minutes_offset: int) -> str:
            return (base_time + timedelta(minutes=minutes_offset)).strftime("%H:%M:%S")

        events = []
        for d in data:
            events.append(NormalizedEvent(
                event_id=d["event_id"],
                timestamp=_ts(d["offset_minutes"]),
                source=d["source"],
                source_type=d["source_type"],
                event_type=d["event_type"],
                location=d["location"],
                payload=d.get("payload", {})
            ))
        return events

    def reset(self):
        """Resets the simulator back to the start of the timeline."""
        self.current_idx = 0
        self.start_time = datetime.now()
        self.events = self._build_event_stream()

    def has_next(self) -> bool:
        """Returns True if there are more events in the stream."""
        return self.current_idx < len(self.events)

    def next_event(self) -> Optional[NormalizedEvent]:
        """Returns the next deterministic event and advances the pointer."""
        if not self.has_next():
            return None
        ev = self.events[self.current_idx]
        self.current_idx += 1
        return ev

    def current_index(self) -> int:
        return self.current_idx

    def events_remaining(self) -> int:
        return len(self.events) - self.current_idx

# Global instance for easy import and state sharing
simulator = DeterministicSimulator()
