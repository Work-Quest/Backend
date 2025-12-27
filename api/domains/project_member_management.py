from Backend.api.domains.project import Project
from Backend.api.models.ProjectMember import ProjectMember
from .task_management import TaskManagement
from models import Task

class ProjectMemberManagement:
    def __init__(self, project_model):
        self.project = project_model
        self._members = None

    @property
    def members(self):
        if self._members is None:
            self._members = list(
                ProjectMember.objects.filter(project=self.project)
            )
        return self._members

    def add_member(self, member_data):
        new_member = ProjectMember.objects.create(
            project=self.project,
            user=member_data["user"],
            hp=member_data.get("hp", 100),
            status=member_data.get("status", "Alive"),
        )
        self._members = None
        return new_member

    def get_member(self, member_id):
        try:
            return ProjectMember.objects.get(
                project=self.project,
                project_member_id=member_id
            )
        except ProjectMember.DoesNotExist:
            return None

    def edit_member(self, member_id, member_data):
        member = self.get_member(member_id)
        if not member:
            return None

        member.hp = member_data.get("hp", member.hp)
        member.status = member_data.get("status", member.status)
        member.save()

        self._members = None
        return member

    def remove_member(self, member_id):
        member = self.get_member(member_id)
        if not member:
            return False

        member.delete()
        self._members = None
        return True
