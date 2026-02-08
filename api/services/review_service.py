from __future__ import annotations

from django.db import transaction

from api.models import TaskLog
from api.domains.project import Project as ProjectDomain
from api.models.Report import Report
from api.domains.report import Report as ReportDomain
from api.domains.review import Review as ReviewDomain
# from api.dtos.review_types import TaskFacts
from api.models import (
    Project as ProjectModel,
    ProjectMember as ProjectMemberModel,
    UserReport,
    Effect,
)
from api.services.ai_service import AIService


class ReviewService:
    """
    Application service for POST /review/report
    Coordinates:
    - load project + members + task
    - create Report + UserReport
    - compute trust + quality signals
    - compute review scores
    - apply buff/debuff to receiver (via Effect/UserEffect + HP change)
    """

    def __init__(
        self,
        review_domain: ReviewDomain | None = None,
    ):
        self.review_domain = review_domain or ReviewDomain()

    def create_review_report(self, payload, business_user, project_id):
        """
        Expected payload (skeleton):
        {
          "task_id": "uuid",
          "description": "string"
        }
        """

        task_id = (payload or {}).get("task_id")
        description = (payload or {}).get("description")

        if not project_id or not task_id:
            raise ValueError("project_id and task_id are required")
        if not description or not str(description).strip():
            raise ValueError("description is required")

        project = ProjectModel.objects.get(project_id=project_id)
        project_domain = ProjectDomain(project)

        if not project_domain.check_access(business_user):
            raise PermissionError("User does not have access to this project.")

        task_domain = project_domain.TaskManagement.get_task(task_id)
        if not task_domain:
            raise ValueError("Task not found")

        receivers = task_domain.get_assigned_members()
        reviewer_member_model = ProjectMemberModel.objects.get(project=project, user=business_user)
        valid_receivers = [
            m for m in receivers
            if m.project_member_id != reviewer_member_model.project_member_id
        ]

        if not valid_receivers:
            raise ValueError("Cannot create report: reviewer cannot review themselves")

        result = AIService().analyze_sentiment(str(description))
        sentiment_score = int(result.get("score", 0))

        with transaction.atomic():
            report_model = Report.objects.create(
                task=task_domain.task,
                reporter=reviewer_member_model,
                description=description,
                sentiment_score=sentiment_score,
            )
            report_domain = ReportDomain(report_model)
            report = report_domain.report

            user_reports = []

            for i in valid_receivers:
                receiver_member_model = ProjectMemberModel.objects.get(
                    project_member_id=i.project_member_id,
                    project=project,
                )
                user_report = UserReport.objects.create(
                    report=report,
                    reviewer=reviewer_member_model,
                    receiver=receiver_member_model,
                )
                user_reports.append(user_report)
                TaskLog.objects.create(
                    project_member=reviewer_member_model,
                    received_project_member=receiver_member_model,
                    task=task_domain.task,
                    report=report_model,
                    action_type="USER",
                    event="TASK_REVIEW",
                )

            return report, user_reports

    # def _build_task_facts(self, task_domain) -> TaskFacts:
    #     """
    #     Convert Task domain object to TaskFacts for trust-score alignment checks.
    #     """
    #     t = task_domain._task  # existing domain style in this repo

    #     def _ts(dt):
    #         return dt.timestamp() if dt is not None else None

    #     return TaskFacts(
    #         priority=int(getattr(t, "priority", 1) or 1),
    #         created_at_ts=float(t.created_at.timestamp()),
    #         completed_at_ts=_ts(getattr(t, "completed_at", None)),
    #         deadline_ts=_ts(getattr(t, "deadline", None)),
    #     )

    # def _apply_effect(self, receiver_member_model, effect_decision):
    #     """
    #     Skeleton implementation:
    #     - BUFF/DEBUFF => create Effect row + attach via ProjectMemberDomain.applied()
    #     - heal/hp decrease => directly mutate hp
    #     """

    #     from api.domains.project_member import ProjectMember as ProjectMemberDomain

    #     receiver = ProjectMemberDomain(receiver_member_model)

    #     if effect_decision.kind == "NONE":
    #         return {"kind": "NONE"}

    #     if effect_decision.kind == "BUFF":
    #         # damage buff (one-time; consumed on next attack per Game domain)
    #         if effect_decision.damage_modifier_pct:
    #             eff = Effect.objects.create(
    #                 effect_type=Effect.EffectType.DAMAGE_BUFF,
    #                 value=float(effect_decision.damage_modifier_pct),
    #                 description="Review buff: +damage next attack (one-time)",
    #             )
    #             receiver.applied(eff)

    #         # immediate heal
    #         if effect_decision.heal_pct:
    #             heal_amount = int(receiver.max_hp * float(effect_decision.heal_pct))
    #             if heal_amount > 0:
    #                 receiver.heal(heal_amount)

    #         # TODO: item rewards (reduce revive cost, heal item, etc.)
    #         return {"kind": "BUFF"}

    #     if effect_decision.kind == "DEBUFF":
    #         if effect_decision.damage_modifier_pct:
    #             eff = Effect.objects.create(
    #                 effect_type=Effect.EffectType.DAMAGE_DEBUFF,
    #                 value=float(effect_decision.damage_modifier_pct),
    #                 description="Review debuff: -damage next attack (one-time)",
    #             )
    #             receiver.applied(eff)

    #         if effect_decision.hp_delta_pct:
    #             dmg = int(receiver.max_hp * float(effect_decision.hp_delta_pct))
    #             if dmg > 0:
    #                 receiver.attacked(dmg)

    #         return {"kind": "DEBUFF"}

    #     return {"kind": effect_decision.kind}


