# services/game_service.py
from django.db import transaction
from api.models.ProjectBoss import ProjectBoss
from api.models.Project import Project as ProjectModel
from api.domains.project import Project as ProjectDomain

class GameService:

    def get_project_boss(self, project_id):
        """
        Get the boss for a specific project
        """
        try:
            project = ProjectModel.objects.get(project_id=project_id)
            domain = ProjectDomain(project)
            return domain._boss
        except ProjectModel.DoesNotExist:
            raise ValueError("Project not found")

    def setup_boss_for_project(self, project_id):
        """
        Setup boss for a project (select random boss and set HP based on tasks)
        """
        try:
            project = ProjectModel.objects.get(project_id=project_id)
            domain = ProjectDomain(project)
            domain.setup_boss()
            return domain._boss
        except ProjectModel.DoesNotExist:
            raise ValueError("Project not found")

    # def get_all_bosses(self):
    #     """
    #     Get all available bosses from the database
    #     """
    #     from api.models.Boss import Boss
    #     return list(Boss.objects.all())

    # def attack_boss(self, project_id, damage):
    #     """
    #     Deal damage to the project boss
    #     """
    #     try:
    #         project = ProjectModel.objects.get(project_id=project_id)
    #         domain = ProjectDomain(project)

    #         current_hp = domain._boss.hp
    #         new_hp = max(0, current_hp - damage)

    #         domain._boss.hp = new_hp

    #         # Check if boss is defeated
    #         if new_hp <= 0:
    #             domain._boss.status = False  # Assuming status is boolean for alive/dead

    #         return {
    #             "damage_dealt": damage,
    #             "remaining_hp": new_hp,
    #             "boss_defeated": new_hp <= 0
    #         }
    #     except ProjectModel.DoesNotExist:
    #         raise ValueError("Project not found")

