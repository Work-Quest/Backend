from api.domains.task_management import TaskManagement
from api.models.Project import Project
from django.shortcuts import get_object_or_404


class TaskService:
    def __init__(self, project_id):
        self.project = get_object_or_404(Project, project_id=project_id)
        self.task_management = TaskManagement(self.project)

    def get_all_tasks(self):
        return self.task_management.get_all_tasks()

    def create_task(self, task_data):
        return self.task_management.create_task(task_data)

    def get_task(self, task_id):
        return self.task_management.get_task(task_id)

    def edit_task(self, task_id, task_data):
        return self.task_management.edit_task(task_id, task_data)

    def delete_task(self, task_id):
        return self.task_management.delete_task(task_id)

    def assign_user_to_task(self, task_id, project_member_id):
        return self.task_management.assign_user_to_task(task_id, project_member_id)

    def unassign_user_from_task(self, task_id, project_member_id):
        return self.task_management.unassign_user_from_task(task_id, project_member_id)

