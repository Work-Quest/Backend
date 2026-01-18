from api.models import UserTask


class Task:
    def __init__(self, task_model):
        self._task = task_model

    @property
    def task_id(self):
        return self._task.task_id

    @property
    def project(self):
        return self._task.project

    @property
    def priority(self):
        return self._task.priority

    @priority.setter
    def priority(self, value):
        self._task.priority = value
        self._task.save(update_fields=["priority"])

    @property
    def task_name(self):
        return self._task.task_name

    @task_name.setter
    def task_name(self, value):
        self._task.task_name = value
        self._task.save(update_fields=["task_name"])

    @property
    def description(self):
        return self._task.description

    @description.setter
    def description(self, value):
        self._task.description = value
        self._task.save(update_fields=["description"])

    @property
    def status(self):
        return self._task.status

    @status.setter
    def status(self, value):
        self._task.status = value
        self._task.save(update_fields=["status"])

    @property
    def deadline(self):
        return self._task.deadline

    @deadline.setter
    def deadline(self, value):
        self._task.deadline = value
        self._task.save(update_fields=["deadline"])

    @property
    def created_at(self):
        return self._task.created_at

    @property
    def completed_at(self):
        return self._task.completed_at

    def delete(self):
        self._task.delete()

    def save(self):
        self._task.save()

    def get_project_member(self):
        user_task = UserTask.objects.get(
            task=self._task
        )
        return user_task.project_member



