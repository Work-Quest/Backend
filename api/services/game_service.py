from __future__ import annotations

from typing import Optional

from django.db import transaction

from api.domains.project import Project as ProjectDomain
from api.domains.report import Report as ReportDomain
from api.models.Boss import Boss
from api.models.Project import Project as ProjectModel
from api.models.ProjectMember import ProjectMember
from api.models.Report import Report as ReportModel
from api.models.UserEffect import UserEffect
from api.models.UserItem import UserItem


class GameService:
    def _get_project_and_domain(self, project_id):
        try:
            project = ProjectModel.objects.get(project_id=project_id)
        except ProjectModel.DoesNotExist:
            raise ValueError("Project not found")
        return project, ProjectDomain(project)

    def _require_access(self, domain: ProjectDomain, business_user):
        if business_user is None:
            return
        if not domain.check_access(business_user):
            raise PermissionError("User does not have access to this project.")

    def _get_requester_member(self, project: ProjectModel, business_user):
        try:
            return ProjectMember.objects.get(project=project, user=business_user)
        except ProjectMember.DoesNotExist:
            raise PermissionError("User is not a member of this project.")

    # -----------------
    # Boss
    # -----------------

    def get_project_boss(self, project_id):
        project, domain = self._get_project_and_domain(project_id)
        boss = domain.game.boss
        if boss is None:
            raise ValueError("Boss not initialized")
        return boss

    def get_all_bosses(self):
        return list(Boss.objects.all())

    def setup_boss_for_project(self, project_id):
        project, domain = self._get_project_and_domain(project_id)
        return domain.setup_boss()

    def setup_special_boss(self, project_id):
        project, domain = self._get_project_and_domain(project_id)
        return domain.game.special_boss_setup()

    def get_boss_status(self, project_id):
        project, domain = self._get_project_and_domain(project_id)
        boss = domain.game.boss
        if boss is None:
            raise ValueError("Boss not initialized")
        return {
            "project_boss_id": str(boss.project_boss.project_boss_id),
            "project_id": str(project.project_id),
            "boss_id": str(boss.boss.boss_id) if boss.boss else None,
            "boss_name": boss.name if boss.boss else None,
            "boss_image": boss.image if boss.boss else None,
            "hp": boss.hp,
            "max_hp": boss.max_hp,
            "status": boss.status,
            "phase": boss.phase,
            "updated_at": boss.updated_at,
        }

    # -----------------
    # Status
    # -----------------

    def get_user_statuses(self, project_id):
        project, domain = self._get_project_and_domain(project_id)
        members = domain.project_member_management.members

        user_statuses = []
        for member in members:
            user_statuses.append(
                {
                    "project_member_id": str(member.project_member_id),
                    "user_id": str(member.user.user_id),
                    "username": member.user.auth_user.username,
                    "hp": member.hp,
                    "max_hp": member.max_hp,
                    "score": member.score,
                    "status": member.status,
                }
            )

        return {"project_id": str(project.project_id), "user_statuses": user_statuses}

    def get_game_status(self, project_id):
        boss_status = self.get_boss_status(project_id)
        user_statuses = self.get_user_statuses(project_id)
        return {
            "project_id": str(project_id),
            "boss_status": boss_status,
            "user_statuses": user_statuses["user_statuses"],
        }

    # -----------------
    # Game actions
    # -----------------

    def player_attack(self, project_id, task_id):
        """
        Resolve attacker(s) from task assignee(s) (UserTask) and perform one attack per assignee.
        """
        project, domain = self._get_project_and_domain(project_id)
        task = domain.TaskManagement.get_task(task_id)
        if not task:
            raise ValueError("Task not found")

        if domain.game.boss is None:
            raise ValueError("Boss not initialized")

        assignees = task.get_assigned_members()
        if not assignees:
            raise ValueError("No players assigned to this task")

        attacks = []
        skipped = []
        total_damage = 0.0

        with transaction.atomic():
            for assignee in assignees:
                pid = str(assignee.project_member_id)
                try:
                    res = domain.game.player_attack(pid, task)
                    attacks.append(res)
                    total_damage += float(res.get("damage", 0) or 0)
                except ValueError as e:
                    skipped.append({"player_id": pid, "reason": str(e)})

        if not attacks:
            raise ValueError("No assignees were able to attack")

        boss_hp = attacks[-1].get("boss_hp")
        boss_max_hp = attacks[-1].get("boss_max_hp")

        return {
            "task_id": str(task.task_id),
            "attacks": attacks,
            "skipped": skipped,
            "total_damage": total_damage,
            "boss_hp": boss_hp,
            "boss_max_hp": boss_max_hp,
        }

    def boss_attack(self, project_id, task_id):
        project, domain = self._get_project_and_domain(project_id)
        task = domain.TaskManagement.get_task(task_id)
        if not task:
            raise ValueError("Task not found")
        if domain.game.boss is None:
            raise ValueError("Boss not initialized")
        return domain.game.boss_attack(task)

    def player_heal(self, project_id, healer_id, player_id, heal_value):
        project, domain = self._get_project_and_domain(project_id)
        return domain.game.player_heal(healer_id, player_id, heal_value)

    def revive_player(self, project_id, player_id):
        project, domain = self._get_project_and_domain(project_id)
        return domain.game.player_revive(player_id)

    def player_support(self, project_id, report_id, business_user=None):
        project, domain = self._get_project_and_domain(project_id)
        self._require_access(domain, business_user)

        try:
            report_model = (
                ReportModel.objects.select_related("task", "reporter", "task__project").get(report_id=report_id)
            )
        except ReportModel.DoesNotExist:
            raise ValueError("Report not found")

        if str(report_model.task.project_id) != str(project.project_id):
            raise ValueError("Report does not belong to this project")

        report_domain = ReportDomain(report_model)
        return domain.game.player_support(report_domain)

    # -----------------
    # Items / effects
    # -----------------

    def get_project_member_items(self, project_id, business_user, *, player_id: Optional[str] = None):
        project, domain = self._get_project_and_domain(project_id)
        self._require_access(domain, business_user)

        requester_member = self._get_requester_member(project, business_user)
        target_member_id = str(requester_member.project_member_id) if player_id is None else str(player_id)

        if target_member_id != str(requester_member.project_member_id) and business_user != project.owner:
            raise PermissionError("Not allowed to view other members' items.")

        items = (
            UserItem.objects.filter(project_member_id=target_member_id, project_member__project=project)
            .select_related("item", "item__effects")
            .order_by("-created_at")
        )

        def _effect_payload(effect):
            if effect is None:
                return None
            return {
                "effect_id": str(effect.effect_id),
                "effect_type": effect.effect_type,
                "effect_value": effect.value,
                "effect_polarity": effect.effect_polarity,
                "effect_description": effect.description,
            }

        return {
            "project_id": str(project.project_id),
            "project_member_id": target_member_id,
            "items": [
                {
                    "user_item_id": str(ui.item_id),
                    "item": {
                        "item_id": str(ui.item.item_id),
                        "name": ui.item.name,
                        "description": ui.item.description,
                        "effect": _effect_payload(ui.item.effects),
                    },
                    "created_at": ui.created_at,
                }
                for ui in items
            ],
        }

    def use_project_member_item(self, project_id, business_user, *, item_id: str, player_id: Optional[str] = None):
        project, domain = self._get_project_and_domain(project_id)
        self._require_access(domain, business_user)

        requester_member = self._get_requester_member(project, business_user)
        target_member_id = str(requester_member.project_member_id) if player_id is None else str(player_id)

        if target_member_id != str(requester_member.project_member_id):
            raise PermissionError("Not allowed to use items for other members.")

        return domain.game.player_use_item(target_member_id, item_id)

    def get_project_member_status_effects(self, project_id, business_user, *, player_id: Optional[str] = None):
        project, domain = self._get_project_and_domain(project_id)
        self._require_access(domain, business_user)

        target_member_id = str(player_id) if player_id is not None else None

        if target_member_id is not None:
            requester_member = self._get_requester_member(project, business_user)
            if target_member_id != str(requester_member.project_member_id) and business_user != project.owner:
                raise PermissionError("Not allowed to view other members' status/effects.")

        members_qs = ProjectMember.objects.filter(project=project).select_related("user", "user__auth_user")
        if target_member_id is not None:
            members_qs = members_qs.filter(project_member_id=target_member_id)

        effects = (
            UserEffect.objects.filter(project_member__project=project)
            .select_related("project_member", "effect")
            .order_by("-created_at")
        )
        if target_member_id is not None:
            effects = effects.filter(project_member_id=target_member_id)

        effects_by_member: dict[str, list[dict]] = {}
        for ue in effects:
            mid = str(ue.project_member_id)
            effects_by_member.setdefault(mid, []).append(
                {
                    "user_effect_id": str(ue.user_effect_id),
                    "effect_id": str(ue.effect.effect_id),
                    "effect_type": ue.effect.effect_type,
                    "effect_value": ue.effect.value,
                    "effect_polarity": ue.effect.effect_polarity,
                    "effect_description": ue.effect.description,
                    "created_at": ue.created_at,
                }
            )

        members_list = [
            {
                "project_member_id": str(m.project_member_id),
                "user_id": str(m.user.user_id),
                "username": m.user.auth_user.username,
                "hp": m.hp,
                "max_hp": m.max_hp,
                "score": m.score,
                "status": m.status,
                "effects": effects_by_member.get(str(m.project_member_id), []),
            }
            for m in members_qs
        ]

        if target_member_id is not None:
            return {"project_id": str(project.project_id), "member": (members_list[0] if members_list else None)}

        return {"project_id": str(project.project_id), "members": members_list}
