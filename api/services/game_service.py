# services/game_service.py
from django.db import transaction
from api.models.ProjectBoss import ProjectBoss
from api.models.Project import Project as ProjectModel
from api.models.Task import Task
from api.domains.project import Project as ProjectDomain
from api.domains.task import Task as TaskDomain

class GameService:

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










