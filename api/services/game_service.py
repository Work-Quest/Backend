# services/game_service.py
from typing import Optional

from django.db import transaction
from api.models.ProjectBoss import ProjectBoss
from api.models.Project import Project as ProjectModel
from api.models.ProjectMember import ProjectMember
from api.models.UserItem import UserItem
from api.models.UserEffect import UserEffect
from api.models.Task import Task
from api.models.Report import Report as ReportModel
from api.domains.project import Project as ProjectDomain
from api.domains.task import Task as TaskDomain
from api.domains.report import Report as ReportDomain

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

    def get_project_boss(self, project_id):
        """
        Get the boss for a specific project
        """
        try:
            project = ProjectModel.objects.get(project_id=project_id)
            domain = ProjectDomain(project)
            return domain.game.boss
        except ProjectModel.DoesNotExist:
            raise ValueError("Project not found")

    def setup_boss_for_project(self, project_id):
        """
        Setup boss for a project (select random boss and set HP based on tasks)
        """
        try:
            project = ProjectModel.objects.get(project_id=project_id)
            domain = ProjectDomain(project)
            return domain.setup_boss()
        except ProjectModel.DoesNotExist:
            raise ValueError("Project not found")

    def player_attack(self, project_id, player_id, task_id):
        """
        Player attacks the boss using a completed task
        """
        try:
            project = ProjectModel.objects.get(project_id=project_id)
            domain = ProjectDomain(project)
            task = domain.TaskManagement.get_task(task_id)
            print("DEBUG task in service.py:", task.task_id, type(task))
            if not task:
                raise ValueError("Task not found")
            return domain.game.player_attack(player_id, task)
        except ProjectModel.DoesNotExist:
            raise ValueError("Project not found")

    def boss_attack(self, project_id, task_id):
        """
        Boss attacks players assigned to a task
        """
        try:
            project = ProjectModel.objects.get(project_id=project_id)
            domain = ProjectDomain(project)
            task = domain.TaskManagement.get_task(task_id)
            if not task:
                raise ValueError("Task not found")
            return domain.game.boss_attack(task)
        except ProjectModel.DoesNotExist:
            raise ValueError("Project not found")

    def player_heal(self, project_id, healer_id, player_id, heal_value):
        """
        Player heals another player
        """
        try:
            project = ProjectModel.objects.get(project_id=project_id)
            domain = ProjectDomain(project)
            return domain.game.player_heal(healer_id, player_id, heal_value)
        except ProjectModel.DoesNotExist:
            raise ValueError("Project not found")

    def player_support(self, project_id, report_id, business_user=None):
        """
        Apply support (buff/effect or item) based on a created review Report.

        Request expects an existing Report ID.
        """
        try:
            project = ProjectModel.objects.get(project_id=project_id)
            domain = ProjectDomain(project)

            if business_user is not None and not domain.check_access(business_user):
                raise PermissionError("User does not have access to this project.")

            report_model = (
                ReportModel.objects
                .select_related("task", "reporter", "task__project")
                .get(report_id=report_id)
            )

            if report_model.task.project_id != project.project_id:
                raise ValueError("Report does not belong to this project")

            report_domain = ReportDomain(report_model)
            return domain.game.player_support(report_domain)
        except ProjectModel.DoesNotExist:
            raise ValueError("Project not found")
        except ReportModel.DoesNotExist:
            raise ValueError("Report not found")

    def get_boss_status(self, project_id):
        """
        Get real-time boss status for a project
        """
        try:
            project = ProjectModel.objects.get(project_id=project_id)
            domain = ProjectDomain(project)
            boss = domain.game.boss

            return {
                "project_boss_id": boss.project_boss.project_boss_id,
                "project_id": project.project_id,
                "boss_id": boss.boss.boss_id if boss.boss else None,
                "boss_name": boss.name if boss.boss else None,
                "boss_image": boss.image if boss.boss else None,
                "hp": boss.hp,
                "max_hp": boss.max_hp,
                "status": boss.status,
                "phase": boss.phase,
                "updated_at": boss.updated_at
            }
        except ProjectModel.DoesNotExist:
            raise ValueError("Project not found")

    def get_user_statuses(self, project_id):
        """
        Get real-time status for all users in a project
        """
        try:
            project = ProjectModel.objects.get(project_id=project_id)
            domain = ProjectDomain(project)
            members = domain.project_member_management.members

            user_statuses = []
            for member in members:
                user_statuses.append({
                    "project_member_id": member.project_member_id,
                    "user_id": member.user.user_id,
                    "username": member.user.auth_user.username,
                    "hp": member.hp,
                    "max_hp": member.max_hp,
                    "score": member.score,
                    "status": member.status
                })

            return {
                "project_id": project.project_id,
                "user_statuses": user_statuses
            }
        except ProjectModel.DoesNotExist:
            raise ValueError("Project not found")

    def get_game_status(self, project_id):
        """
        Get comprehensive real-time game status including boss and all users
        """
        try:
            boss_status = self.get_boss_status(project_id)
            user_statuses = self.get_user_statuses(project_id)

            return {
                "project_id": project_id,
                "boss_status": boss_status,
                "user_statuses": user_statuses["user_statuses"]
            }
        except ValueError as e:
            raise ValueError(str(e))

    def setup_special_boss(self, project_id):
        """
        Setup special boss for a project
        """
        try:
            project = ProjectModel.objects.get(project_id=project_id)
            domain = ProjectDomain(project)
            return domain.game.special_boss_setup()
        except ProjectModel.DoesNotExist:
            raise ValueError("Project not found")

    def revive_player(self, project_id, player_id):
        """
        Revive a dead player in a project
        """
        try:
            project = ProjectModel.objects.get(project_id=project_id)
            domain = ProjectDomain(project)
            return domain.game.player_revive(player_id)
        except ProjectModel.DoesNotExist:
            raise ValueError("Project not found")

    # -----------------
    # Project member inventory / effects
    # -----------------

    def get_project_member_items(self, project_id, business_user, *, player_id: Optional[str] = None):
        """
        List owned items for a project member.

        If player_id is None, returns the requesting user's own items.
        """
        project, domain = self._get_project_and_domain(project_id)
        self._require_access(domain, business_user)

        requester_member = self._get_requester_member(project, business_user)
        target_member_id = str(requester_member.project_member_id) if player_id is None else str(player_id)

        # only owner can inspect other members' inventories
        if target_member_id != str(requester_member.project_member_id) and business_user != project.owner:
            raise PermissionError("Not allowed to view other members' items.")

        items = (
            UserItem.objects
            .filter(project_member_id=target_member_id, project_member__project=project)
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
                    "user_item_id": str(ui.user_item_id),
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
        """
        Use/consume an owned item and apply its effect.

        If player_id is None, uses the requesting user's ProjectMember.
        """
        project, domain = self._get_project_and_domain(project_id)
        self._require_access(domain, business_user)

        requester_member = self._get_requester_member(project, business_user)
        target_member_id = str(requester_member.project_member_id) if player_id is None else str(player_id)

        # item usage is restricted to self
        if target_member_id != str(requester_member.project_member_id):
            raise PermissionError("Not allowed to use items for other members.")

        # domain method expects player_id + (owned) user_item_id
        return domain.game.player_use_item(target_member_id, item_id)

    def get_project_member_status_effects(self, project_id, business_user, *, player_id: Optional[str] = None):
        """
        Get project members' status plus their current effects (UserEffect).

        If player_id is provided, returns only that member (must be requester or project owner).
        """
        project, domain = self._get_project_and_domain(project_id)
        self._require_access(domain, business_user)

        target_member_id = str(player_id) if player_id is not None else None

        if target_member_id is not None:
            requester_member = self._get_requester_member(project, business_user)
            if target_member_id != str(requester_member.project_member_id) and business_user != project.owner:
                raise PermissionError("Not allowed to view other members' status/effects.")

        members_qs = (
            ProjectMember.objects
            .filter(project=project)
            .select_related("user", "user__auth_user")
        )
        if target_member_id is not None:
            members_qs = members_qs.filter(project_member_id=target_member_id)

        effects = (
            UserEffect.objects
            .filter(project_member__project=project)
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

        # if filtering to one member, return a single object for simpler client usage
        if target_member_id is not None:
            return {
                "project_id": str(project.project_id),
                "member": (members_list[0] if members_list else None),
            }

        return {
            "project_id": str(project.project_id),
            "members": members_list,
        }














