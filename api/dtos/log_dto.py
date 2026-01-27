from dataclasses import dataclass
from datetime import datetime
from api.models.ProjectMember import ProjectMember
from api.models.Task import Task
import django.db
from api.models.ProjectBoss import ProjectBoss


@dataclass(frozen=True)
class TaskLogReadDTO:
    task_id: int | None
    project_member_id: int
    action_type: str
    event: str
    priority_snapshot: int | None
    created_at: datetime


@dataclass(frozen=True)
class GameLogReadDTO:
    task_id: int
    project_member_id: int | None
    received_project_member_id: int | None
    project_boss_id: int | None
    action_type: str
    event: str
    damage_point: int | None
    score_change: int | None
    created_at: datetime

