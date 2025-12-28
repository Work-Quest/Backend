from api.domains.project_member_management import ProjectMemberManagement
from .task_management import TaskManagement

class Project:
    def __init__(self, project_model):
        self._project = project_model
        self._project_member_management = ProjectMemberManagement(project_model)
        self._task_management = TaskManagement(project_model)

    @property
    def project(self):
        return self._project
    
    @property
    def TaskManagement(self):
        return self._task_management

    def edit_project_metadata(self, project_data):
        self._project.project_name = project_data.get(
            "project_name", self._project.project_name
        )

        self._project.deadline = project_data.get(
            "deadline", self._project.deadline
        )

        self._project.status = project_data.get(
            "status", self._project.status
        )

        self._project.total_tasks = project_data.get(
            "total_tasks", self._project.total_tasks
        )

        self._project.completed_tasks = project_data.get(
            "completed_tasks", self._project.completed_tasks
        )

        self._project.save()
        
        return self._project
    