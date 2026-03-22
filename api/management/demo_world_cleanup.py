"""
Remove all data created by `seed_mock_user`: users `<prefix>_NN`, every project they
own or are members of, and related rows (TaskLog, ProjectEndSummary, ActivityLog, etc.).

Does **not** delete shared catalog rows (Boss, Effect, Item) that the seed may have
ensured exist via get_or_create.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import DatabaseError, transaction

from api.models.ActivityLog import ActivityLog
from api.models.BusinessUser import BusinessUser
from api.models.Project import Project
from api.models.ProjectEndSummary import ProjectEndSummary
from api.models.ProjectMember import ProjectMember
from api.models.TaskLog import TaskLog

User = get_user_model()


def _delete_active_status_effects_for_users(bus) -> None:
    """
    If `api_activestatuseffect` exists (legacy DB), clear rows for these members *before*
    deleting projects/members so FK constraints don't fail.
    """
    try:
        from api.models.ActiveStatus import ActiveStatusEffect

        ActiveStatusEffect.objects.filter(project_member__user__in=bus).delete()
    except DatabaseError:
        pass


def wipe_demo_world(*, username_prefix: str) -> dict:
    """
    Delete all mock demo users matching ``<prefix>_`` and every project they own or join.

    Returns counts for logging (best-effort; some steps may delete cascaded rows).
    """
    summary = {
        "username_prefix": username_prefix.strip(),
        "business_users_matched": 0,
        "projects_deleted": 0,
        "task_logs_deleted": 0,
        "activity_logs_deleted": 0,
        "project_end_summaries_deleted": 0,
        "django_users_deleted": 0,
    }

    prefix = username_prefix.strip()
    if not prefix:
        return summary

    pattern = f"{prefix}_"

    with transaction.atomic():
        bus = BusinessUser.objects.filter(username__startswith=pattern)
        summary["business_users_matched"] = bus.count()

        if not bus.exists():
            qs = User.objects.filter(username__startswith=pattern)
            summary["django_users_deleted"] = qs.count()
            qs.delete()
            return summary

        bu_ids = list(bus.values_list("user_id", flat=True))
        owned_pids = list(Project.objects.filter(owner__in=bus).values_list("project_id", flat=True))
        member_pids = list(
            ProjectMember.objects.filter(user__in=bus)
            .values_list("project_id", flat=True)
            .distinct()
        )
        all_pids = list(set(owned_pids) | set(member_pids))
        summary["projects_deleted"] = len(all_pids)

        if all_pids:
            pid_strs = [str(p) for p in all_pids]
            summary["task_logs_deleted"] = TaskLog.objects.filter(project_id__in=pid_strs).delete()[0]
            summary["activity_logs_deleted"] = ActivityLog.objects.filter(
                project_id__in=all_pids
            ).delete()[0]
            summary["project_end_summaries_deleted"] += ProjectEndSummary.objects.filter(
                project_id__in=all_pids
            ).delete()[0]

        if bu_ids:
            summary["project_end_summaries_deleted"] += ProjectEndSummary.objects.filter(
                user_id__in=bu_ids
            ).delete()[0]

        _delete_active_status_effects_for_users(bus)

        if all_pids:
            Project.objects.filter(project_id__in=all_pids).delete()

        uqs = User.objects.filter(username__startswith=pattern)
        summary["django_users_deleted"] = uqs.count()
        uqs.delete()

    return summary
