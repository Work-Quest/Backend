from Backend.api.domains.project import Project
from Backend.api.domains.project_member_management import ProjectMemberManagement
from .task_management import TaskManagement
from models import Task

class Project:
    def __init__(self, project_model):
        self._project = project_model
        self._project_member_management = ProjectMemberManagement(project_model)
        self._task_management = TaskManagement(project_model)

    @property
    def ProjectModel(self):
        return self._project
    
    @property
    def TaskManagement(self):
        return self._task_management

    def edit_project_metadata(self, project_data):
        self._project.name = project_data.get("name", self._project.name)
        self._project.description = project_data.get("description", self._project.description)
        self._project.start_date = project_data.get("start_date", self._project.start_date)
        self._project.end_date = project_data.get("end_date", self._project.end_date)
        self._project.save()
        return self._project
    