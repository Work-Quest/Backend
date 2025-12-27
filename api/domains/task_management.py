from Backend.api.models.Task import Task
from Backend.api.domains.task_management import TaskManagement
from Backend.api.views.auth_view import check_auth_status

class TaskManagement:
    def __init__(self, project_model):
        self.project = project_model
        self._tasks = None

    @property
    def tasks(self):
        if self._tasks is None:
            self._tasks = list(
                Task.objects.filter(project=self.project)
            )
        return self._tasks
    
    def create_task(self, task_data):
        new_task = Task.objects.create(
            project=self.project,
            title=task_data.get("title"),
            description=task_data.get("description"),
            status=task_data.get("status", "To Do"),
            assignee=task_data.get("assignee"))
        # clear cache for updated tasks
        self._tasks = None
        return new_task 
    
    def get_task(self, task_id):
        try:
            task = Task.objects.get(id=task_id, project=self.project)
            return task
        except Task.DoesNotExist:
            return None
    
    def edit_task(self, task_id, task_data):
        task = self.get_task(task_id)
        if not task:
            return None
        
        task.title = task_data.get("title", task.title)
        task.description = task_data.get("description", task.description)
        task.status = task_data.get("status", task.status)
        task.assignee = task_data.get("assignee", task.assignee)
        task.save()
        
        # clear cache for updated tasks
        self._tasks = None
        return task
    
    def delete_task(self, task_id):
        task = self.get_task(task_id)
        if not task:
            return False
        
        task.delete()
        
        # clear cache for updated tasks
        self._tasks = None
        return True
