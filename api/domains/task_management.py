from api.models.Task import Task
from api.models.TaskLog import TaskLog
from api.models.UserTask import UserTask
from api.models.ProjectMember import ProjectMember
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .task import Task as TaskDomain
from api.domains.project_member import ProjectMember as ProjectMemberDomain


class TaskManagement:
    def __init__(self, project_model):
        self.project = project_model
        self._tasks = None

    @property
    def tasks(self):
        """
        Return list of Task domain objects.
        """
        if self._tasks is None:
            model_tasks = Task.objects.filter(project=self.project)
            self._tasks = [TaskDomain(task) for task in model_tasks]
        return self._tasks

    def get_all_tasks(self):
        return Task.objects.filter(project=self.project)

    def create_task(self, task_data, user):
        new_task = Task.objects.create(
            project=self.project,
            priority=task_data.get("priority", 0),
            task_name=task_data.get("task_name"),
            description=task_data.get("description"),
            status=task_data.get("status", "backlog"),
            deadline=task_data.get("deadline")
        )
        new_task_domain = TaskDomain(new_task)
        self._tasks = None
        self.project.total_tasks += 1
        self.project.save()

        project_member = ProjectMember.objects.get(
                        user=user, project=self.project)

        log = TaskLog.objects.create(
            project_member=project_member,
            task=new_task,
            action_type="USER",
            event="TASK_CREATED"
        )   
        return new_task_domain

    def get_task(self, task_id):
        # If tasks cache is already loaded, do an in-memory lookup (no DB hit).
        if self._tasks is not None:
            for t in self._tasks:
                if str(t.task_id) == str(task_id):
                    return t
            return None

        # Otherwise, fall back to DB lookup (always fresh).
        try:
            task = Task.objects.get(task_id=task_id, project=self.project)
            return TaskDomain(task)
        except Task.DoesNotExist:
            return None
        
        
    def edit_task(self, task_id, task_data):
        task = self.get_task(task_id)
        if not task:
            return None

        if "priority" in task_data:
            task.priority = task_data["priority"]
        if "task_name" in task_data:
            task.task_name = task_data["task_name"]
        if "description" in task_data:
            task.description = task_data["description"]
        if "status" in task_data:
            task.status = task_data["status"]
        if "deadline" in task_data:
            task.deadline = task_data["deadline"]

        self._tasks = None
        return task
    
    def move_task(self, task_id, task_data, user):
        EVENT = "TASK_UPDATED"
        task = self.get_task(task_id)
        if not task:
            return None

        cur_status = task.status

        if cur_status == "done":
            raise ValueError("Cannot move a completed task back to an active status.")
        
        task_status = task_data.get("status")

        if task_status == "done":
            # ensure done date exists for downstream mechanics (e.g., trust-score alignment)
            task._task.status = "done"
            task._task.completed_at = timezone.now()
            task._task.save(update_fields=["status", "completed_at"])
            self.project.completed_tasks += 1
            self.project.save(update_fields=["completed_tasks"])

            EVENT = "TASK_COMPLETED"
        else:
            task.status = task_status
        
        project_member = task.get_assigned_members()
        # get current user if not assigned, assign to user making the move
        if not project_member:
            # task.get_assigned_members() returns ProjectMember *domain* objects,
            # so keep the same shape here.
            project_member = [
                ProjectMemberDomain(
                    ProjectMember.objects.get(user=user, project=self.project)
                )
            ]

        for i in project_member:
            log = TaskLog.objects.create(
                project_member=i.project_member,
                task=task._task,
                action_type="USER",
                event=EVENT
            )   
        
        return task


    def delete_task(self, task_id, user):
        with transaction.atomic():
            task = self.get_task(task_id)
            if not task:
                return False
            
            project_member = ProjectMember.objects.get( user=user, project=self.project)
        
            log = TaskLog.objects.create(
                task_priority_snapshot=task.priority,
                project_member=project_member,
                action_type="USER",
                event="TASK_DELETED"
            )   
            
            # delete any UserTask assignments that reference this task
            UserTask.objects.filter(task=task._task).delete()

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

    def assign_user_to_task(self, task_id, project_member_id, user):
        with transaction.atomic():
            task_domain = self.get_task(task_id)
            if not task_domain:
                raise Exception("Task not found")
            project_member = get_object_or_404(ProjectMember, project_member_id=project_member_id, project=self.project)

            user_task, created = UserTask.objects.get_or_create(
                project_member=project_member,
                task=task_domain._task
            )


            assigned_project_member = ProjectMember.objects.get(
                user=user, project=self.project)

            log = TaskLog.objects.create(
                project_member=assigned_project_member,
                task=task_domain._task,
                action_type="USER",
                event="ASSIGN_USER"
            )   

            return user_task, created

    def unassign_user_from_task(self, task_id, project_member_id, user):
        with transaction.atomic():
            task_domain = self.get_task(task_id)
            if not task_domain:
                raise Exception("Task not found")
            project_member = get_object_or_404(ProjectMember, project_member_id=project_member_id, project=self.project)

            deleted_count, _ = UserTask.objects.filter(
                project_member=project_member,
                task=task_domain._task
            ).delete()

            unassigned_project_member = ProjectMember.objects.get(
                user=user, project=self.project)


            log = TaskLog.objects.create(
                project_member=unassigned_project_member,
                task=task_domain._task,
                action_type="USER",
                event="UNASSIGN_USER"
            )   
            return deleted_count > 0
        

