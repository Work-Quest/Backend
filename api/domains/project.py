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
    
    def setup_boss(self):
        self._project.status = "Working"
        all_tasks = self._task_management.get
        
    
    def close_project(self):
        self._project.status = "closed"
        self._project.save()
        return self._project

    def check_access(self, user):
        is_member = self._project_member_management.is_member(user)
        return is_member and self._project.status == "Working"