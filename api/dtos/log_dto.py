from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from api.models.ProjectMember import ProjectMember
from api.models.Task import Task
import django.db
from api.models.ProjectBoss import ProjectBoss


@dataclass(frozen=True)
class TaskLogReadDTO:
    task_id: Optional[int]
    project_member_id: int
    action_type: str
    event: str
    priority_snapshot: Optional[int]
    created_at: datetime


@dataclass(frozen=True)
class GameLogReadDTO:
    task_id: int
    project_member_id: Optional[int]
    received_project_member_id: Optional[int]
    project_boss_id: Optional[int]
    action_type: str
    event: str
    damage_point: Optional[int]
    score_change: Optional[int]
    created_at: datetime

