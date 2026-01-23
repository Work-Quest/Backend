from api.models.ProjectMember import ProjectMember as ProjectMemberModel
from .project_member import ProjectMember as ProjectMemberDomain

class ProjectMemberManagement:
    def __init__(self, project_model):
        self.project = project_model
        self._members = None

    @property
    def members(self):
        """
        Return list of ProjectMember domain objects.
        """
        if self._members is None:
            model_members = ProjectMemberModel.objects.filter(project=self.project)
            self._members = [ProjectMemberDomain(member) for member in model_members]
        return self._members


    def add_member(self, member):
        new_member = ProjectMemberModel.objects.create(
            project=self.project,
            user=member,
            hp=100,
            status="Alive"
        )
        new_member_domain = ProjectMemberDomain(new_member)
        self._members = None
        return new_member_domain

    def get_member(self, member_id):
        if self._members is None:
            _ = self.members

        for member in self._members:
            if str(member.project_member_id) == member_id:
                return member

        return None
    
    def edit_member(self, member_id, member_data):
        member = self.get_member(member_id)
        if not member:
            return None

        member.hp = member_data.get("hp", member.hp)
        member.status = member_data.get("status", member.status)

        self._members = None
        return member

    def remove_member(self, member_id):
        for idx, member in enumerate(self._members):
            if member.id == member_id:
                member.delete()          
                del self._members[idx]   
                return True
    
    def is_member(self, user):
        for i in self.members:
            if i.user == user:
                return True
        return False 