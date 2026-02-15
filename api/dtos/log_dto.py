from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any


@dataclass(frozen=True)
class ProjectLogReadDTO:
    id: str
    project_id: str
    actor_type: str
    actor_id: Optional[str]
    event_type: str
    payload: dict[str, Any]
    created_at: datetime

