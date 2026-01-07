from api.models.Task import Task
from api.models.UserTask import UserTask
from api.models.ProjectMember import ProjectMember
from django.db import transaction
from django.shortcuts import get_object_or_404


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

    def get_all_tasks(self):
        return Task.objects.filter(project=self.project)

    def create_task(self, task_data):
        new_task = Task.objects.create(
            project=self.project,
            priority=task_data.get("priority", 0),
            task_name=task_data.get("task_name"),
            description=task_data.get("description"),
            status=task_data.get("status", "backlog"),
            deadline=task_data.get("deadline")
        )
        self._tasks = None
        self.project.total_tasks += 1
        self.project.save()
        return new_task

    def get_task(self, task_id):
        try:
            task = Task.objects.get(task_id=task_id, project=self.project)
            return task
        except Task.DoesNotExist:
            return None

    def edit_task(self, task_id, task_data):
        task = self.get_task(task_id)
        if not task:
            return None

        task.priority = task_data.get("priority", task.priority)
        task.task_name = task_data.get("task_name", task.task_name)
        task.description = task_data.get("description", task.description)
        task.status = task_data.get("status", task.status)
        task.deadline = task_data.get("deadline", task.deadline)
        task.save()

        self._tasks = None
        return task

    def delete_task(self, task_id):
        with transaction.atomic():
            task = self.get_task(task_id)
            if not task:
                return False

            # delete any UserTask assignments that reference this task
            UserTask.objects.filter(task=task).delete()

            task.delete()
            self._tasks = None

            # decrement project's total tasks count if present
            try:
                if hasattr(self.project, "total_tasks") and self.project.total_tasks > 0:
                    self.project.total_tasks -= 1
                    self.project.save()
            except Exception:
                # ensure deletion isn't blocked by count update failures
                pass

            return True

    def assign_user_to_task(self, task_id, project_member_id):
        with transaction.atomic():
            task = get_object_or_404(Task, task_id=task_id, project=self.project)
            project_member = get_object_or_404(ProjectMember, project_member_id=project_member_id, project=self.project)

            user_task, created = UserTask.objects.get_or_create(
                project_member=project_member,
                task=task
            )
            return user_task, created

    def unassign_user_from_task(self, task_id, project_member_id):
        with transaction.atomic():
            task = get_object_or_404(Task, task_id=task_id, project=self.project)
            project_member = get_object_or_404(ProjectMember, project_member_id=project_member_id, project=self.project)

            deleted_count, _ = UserTask.objects.filter(
                project_member=project_member,
                task=task
            ).delete()
            return deleted_count > 0
        

