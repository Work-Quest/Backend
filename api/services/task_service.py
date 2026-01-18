from api.models.Project import Project as ProjectModel
from api.domains.project import Project

class TaskService:
    def __init__(self, project_id, user):
        project = ProjectModel.objects.get(project_id=project_id)
        self._domain = Project(project)
        self._task_management = self._domain._task_management
        self._user = user

    def get_all_tasks(self):
        if not self._domain.check_access(self._user):
            raise PermissionError("User does not have access to this project.")
        return self._task_management.get_all_tasks()

    def create_task(self, task_data):
        if not self._domain.check_access(self._user):
            raise PermissionError("User does not have access to this project.")
        return self._task_management.create_task(task_data)
    def get_task(self, task_id):
        if not self._domain.check_access(self._user):
            raise PermissionError("User does not have access to this project.")
        return self._task_management.get_task(task_id)

    def edit_task(self, task_id, task_data):
        if not self._domain.check_access(self._user):
            raise PermissionError("User does not have access to this project.")
        return self._task_management.edit_task(task_id, task_data)
    
    def move_task(self, task_id, task_data):
        if not self._domain.check_access(self._user):
            raise PermissionError("User does not have access to this project.")
        return self._task_management.move_task(task_id, task_data, self._user)

    def delete_task(self, task_id):
        if not self._domain.check_access(self._user):
            raise PermissionError("User does not have access to this project.")
        return self._task_management.delete_task(task_id, self._user)

    def assign_user_to_task(self, task_id, project_member_id):
        if not self._domain.check_access(self._user):
            raise PermissionError("User does not have access to this project.")
        return self._task_management.assign_user_to_task(task_id, project_member_id, self._user)

    def unassign_user_from_task(self, task_id, project_member_id):
        if not self._domain.check_access(self._user):
            raise PermissionError("User does not have access to this project.")
        return self._task_management.unassign_user_from_task(task_id, project_member_id, self._user)

