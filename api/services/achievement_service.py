from __future__ import annotations

from typing import List
from datetime import timedelta

from api.models import Task, UserTask, ProjectMember, TaskLog
from api.models.UserFeedback import UserFeedback


def _compute_task_stats_for_member_project(feedback: UserFeedback) -> dict:
    """
    Aggregate basic task timing stats for the project member on this project.

    This uses ONLY existing backend data (no new fields), via Task/UserTask.
    """
    member = feedback.user  # ProjectMember
    project = feedback.project

    user_tasks = (
        UserTask.objects.select_related("task")
        .filter(project_member=member, task__project=project)
    )

    total = 0
    completed = 0
    late = 0
    near_deadline = 0

    for ut in user_tasks:
        task: Task = ut.task  # type: ignore[assignment]
        total += 1

        if not task.completed_at:
            continue

        completed += 1

        if not task.deadline:
            continue

        created = task.created_at
        deadline = task.deadline
        done = task.completed_at

        # Completed after deadline
        if done > deadline:
            late += 1
            continue

        # Completed very close to the deadline (last 10% of available time window)
        total_window = max(
            timedelta(seconds=1),
            deadline - created,
        )
        slack = deadline - done
        slack_ratio = slack.total_seconds() / total_window.total_seconds()

        if 0.0 <= slack_ratio <= 0.10:
            near_deadline += 1

    return {
        "total_assigned": total,
        "completed": completed,
        "late": late,
        "near_deadline": near_deadline,
    }


def _member_game_context(feedback: UserFeedback) -> dict:
    """
    Collect lightweight game context (deaths, revives, kill boss, hp/score snapshot).
    """
    member: ProjectMember = feedback.user
    project_id = feedback.project.project_id
    member_id = member.project_member_id

    # Game logs for this project/player
    logs = TaskLog.objects.filter(
        project_id=project_id,
        actor_id=member_id,
    ).order_by("created_at")

    killed_by_boss = TaskLog.objects.filter(
        project_id=project_id,
        event_type=TaskLog.EventType.KILL_PLAYER,
        payload__receiver_id=str(member_id),
    ).exists()

    revived = TaskLog.objects.filter(
        project_id=project_id,
        event_type=TaskLog.EventType.USER_REVIVE,
        payload__player_id=str(member_id),
    ).exists()

    killed_boss = TaskLog.objects.filter(
        project_id=project_id,
        event_type=TaskLog.EventType.KILL_BOSS,
        payload__player_id=str(member_id),
    ).exists()

    # Snapshot final hp/score from ProjectMember
    hp = int(member.hp or 0)
    max_hp = int(member.max_hp or 0)
    score = int(member.score or 0)

    return {
        "logs": logs,
        "killed_by_boss": killed_by_boss,
        "revived": revived,
        "killed_boss": killed_boss,
        "hp": hp,
        "max_hp": max_hp,
        "score": score,
        "member": member,
    }


def compute_achievement_ids(feedback: UserFeedback) -> List[str]:
    """
    Derive unlocked achievement IDs using a hybrid of:
    - AI-Service derived metrics stored on UserFeedback, and
    - existing backend task timing data (Task/UserTask).

    The IDs correspond to:
      01: Zombie of the group
      02: Last-minute Bestfriend
      03: Ghost helper
      04: The Last Stand
      05: One HP Legend
      06: MVP
    """
    quality = float(feedback.overall_quality_score or 0.0)
    teamwork = float(feedback.team_work or 0.0)
    diligence = float(feedback.diligence or 0.0)

    task_stats = _compute_task_stats_for_member_project(feedback)
    total_assigned = task_stats["total_assigned"]
    completed = task_stats["completed"]
    late = task_stats["late"]
    near_deadline = task_stats["near_deadline"]

    game_ctx = _member_game_context(feedback)
    hp = game_ctx["hp"]
    max_hp = game_ctx["max_hp"]
    score = game_ctx["score"]
    killed_by_boss = game_ctx["killed_by_boss"]
    revived = game_ctx["revived"]
    killed_boss = game_ctx["killed_boss"]
    member_model: ProjectMember = game_ctx["member"]

    unlocked: list[str] = []

    # 01 - Zombie of the group:
    # Die in the game and then get revived at least once.
    if killed_by_boss and revived:
        unlocked.append("01")

    # 02 - Last-minute Bestfriend:
    # Often saves the day right before deadlines (keep hybrid timing rule).
    if (
        teamwork >= 60
        and near_deadline >= max(1, completed // 4)
        and late == 0
    ):
        unlocked.append("02")

    # 03 - Ghost helper:
    # Die but still help -> died at least once, but has good teamwork.
    if killed_by_boss and teamwork >= 65:
        unlocked.append("03")

    # 04 - The Last Stand:
    # Last one in project (with >1 members) still alive when boss dies.
    project = feedback.project
    member_count = project.members.count()
    if member_count > 1 and killed_boss:
        # Re-check current member statuses in DB
        alive_members = ProjectMember.objects.filter(
            project=project,
            status="Alive",
        ).count()
        if alive_members == 1 and member_model.status == "Alive":
            unlocked.append("04")

    # 05 - One HP Legend:
    # End project (kill boss) with 1 HP (or extremely low HP).
    if killed_boss and hp > 0 and max_hp > 0:
        # Use percentage so different max_hp values behave similarly
        hp_ratio = float(hp) / float(max_hp)
        if hp_ratio <= 0.05:
            unlocked.append("05")

    # 06 - MVP:
    # Highest score in project with strong AI metrics.
    # TODO: need to collect MVP status in each project
    if completed >= 1 and quality >= 75 and teamwork >= 75 and diligence >= 70:
        top_score = (
            ProjectMember.objects.filter(project=project)
            .order_by("-score")
            .values_list("score", flat=True)
            .first()
        )
        if top_score is not None and score >= int(top_score):
            unlocked.append("06")

    # Use dict to preserve order while deduplicating
    return list(dict.fromkeys(unlocked))


def get_overall_achievement_ids_for_user(business_user) -> List[str]:
    """
    Return achievement IDs the user has unlocked across all projects.
    Uses all UserFeedback for this user's project memberships and unions
    achievement_ids from each.
    """
    members = ProjectMember.objects.filter(user=business_user).values_list(
        "project_member_id", flat=True
    )
    feedbacks = UserFeedback.objects.filter(user_id__in=members).select_related(
        "user", "project"
    )
    seen: set[str] = set()
    for fb in feedbacks:
        for aid in compute_achievement_ids(fb):
            seen.add(aid)
    canonical = ["01", "02", "03", "04", "05", "06"]
    return [a for a in canonical if a in seen]

