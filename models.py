# Data models for smart_scheduler_v2

# models.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class MeetingRequestState:
    """Manages the state of a single meeting request conversation."""
    conversation_id: str = "default_session"
    duration_minutes: Optional[int] = None
    time_range_start: Optional[str] = None
    time_range_end: Optional[str] = None
    user_timezone: Optional[str] = None
    suggested_slots: List[str] = field(default_factory=list)
    confirmed_slot_start: Optional[str] = None
    meeting_title: Optional[str] = None
    status: str = "needs_info" # e.g., 'needs_info', 'pending_confirmation', 'confirmed'

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data):
        return cls(**data)