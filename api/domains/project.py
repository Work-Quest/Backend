from api.models import TaskLog
from api.domains.project_member_management import ProjectMemberManagement
from api.domains.boss import Boss as BossDomain
from api.models.ProjectBoss import ProjectBoss
from api.models.Boss import Boss
from .task_management import TaskManagement
import random
from django.utils import timezone


class Project:
    def __init__(self, project_model):
        self._project = project_model
        self._project_member_management = ProjectMemberManagement(project_model)
        self._task_management = TaskManagement(project_model)

        project_boss_model = ProjectBoss.objects.create(project=project_model, boss=None, hp=0, max_hp=0, status="Alive")
        self._boss = BossDomain(project_boss_model)

        self.BASE_BOSS_HP = 100

    @property
    def project(self):
        return self._project
    
    @property
    def TaskManagement(self):
        return self._task_management

    def edit_project_metadata(self, project_data):
        if "project_name" in project_data:
            self._project.project_name = project_data["project_name"]

        if "deadline" in project_data:
            self._project.deadline = project_data["deadline"]

        if "status" in project_data:
            self._project.status = project_data["status"]

        if "total_tasks" in project_data:
            self._project.total_tasks = project_data["total_tasks"]

        if "completed_tasks" in project_data:
            self._project.completed_tasks = project_data["completed_tasks"]

        self._project.save()
        
        return self._project
    
    def initail_boss_set_up(self):
        all_boss = list(Boss.objects.all())
        selected_boss = random.choice(all_boss)  
        self._boss.boss = selected_boss

        all_tasks = self._task_management.tasks
        boss_hp = sum(task.priority for task in all_tasks) * self.BASE_BOSS_HP
        self._boss.max_hp = boss_hp
        self._boss.hp = boss_hp
        self._boss.updated_at = timezone.now()

    def next_phase_boss_setup(self):
        add_log = TaskLog.objects.filter(
            project_member__project=self._project,
            action_type="USER",
            event="TASK_CREATED",
            created_at__gt=self._boss.updated_at
        )

        delete_log = TaskLog.objects.filter(
            project_member__project=self._project,
            action_type="USER",
            event="TASK_DELETED",
            created_at__gt=self._boss.updated_at
        )

        add_value = sum(add_log.Task.priority for add_log in add_log)
        delete_value = sum(delete_log.Task.priority for delete_log in delete_log)
        net_change = add_value - delete_value
        hp_change = net_change * self.BASE_BOSS_HP
        
        # set up boss next phase
        self._boss.max_hp = hp_change
        self._boss.hp = hp_change

        self._boss.updated_at = timezone.now()

    def close_project(self):
        self._project.status = "closed"
        self._project.save()
        return self._project

    def check_access(self, user):
        is_member = self._project_member_management.is_member(user)
        return is_member and self._project.status == "Working"