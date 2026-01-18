# services/project_service.py
from django.db import transaction
from api.models.ProjectMember import ProjectMember
from api.models.Project import Project as ProjectModel 
from api.domains.project import Project as ProjectDomain
from api.domains.project import Project
from django.utils import timezone
from django.utils.dateparse import parse_datetime

class ProjectService:

    @transaction.atomic
    def create_project(self, project_data, user):
        """
        Create project in DB and return ProjectDomain
        """
        project = ProjectModel.objects.create(
            owner=user,
            project_name=project_data.get("project_name"),
            deadline=project_data.get("deadline"),
            total_tasks=0,
            completed_tasks=0,
            status="Working")

        project_domain = ProjectDomain(project)
        # add owner as member
        project_domain._project_member_management.add_member(user)
        # setup boss for the project
        project_domain.setup_boss()
        return project_domain

    @transaction.atomic
    def edit_project(self, project_id, project_data, user):
        """
        Load project, apply domain logic, persist changes
        """
        project = ProjectModel.objects.select_for_update().get(project_id=project_id)
        if user != project.owner:
            raise PermissionError("Only the project owner can close the project.")  
        
        deadline_str = project_data.get("deadline")

        if deadline_str:
            deadline_dt = parse_datetime(deadline_str)

        if deadline_dt is None:
            raise ValueError("Invalid deadline format")

        if timezone.is_naive(deadline_dt):
            deadline_dt = timezone.make_aware(deadline_dt)

        created_at = project.created_at
        if timezone.is_naive(created_at):
            created_at = timezone.make_aware(created_at)

        if deadline_dt < created_at:
            raise ValueError(
                "Deadline cannot be earlier than project creation date."
            )
        domain = ProjectDomain(project)
        domain.edit_project_metadata(project_data)

        return domain
    
    def delete_project(self, project_id):
        """
        Delete project and all related data (tasks, boss, etc.)
        """
        project = ProjectModel.objects.get(project_id=project_id)

        try:
            domain = ProjectDomain(project)
            # Delete all tasks related to the project
            for task in domain.TaskManagement.tasks:
                task.delete()
            #TODO: Additional cleanup added here (e.g., deleting bosses, resources, etc.)
            project.delete()
            del domain
            return {"message" : "Project and related data deleted successfully"}
        except Exception as e:
            return {"error" : str(e)}
            
    def get_projects(self, user_id):
        """
        Get current User's project domain
        """
        members = (
            ProjectMember.objects
            .filter(user_id=user_id)
            .select_related("project")
        )

        projects = [ProjectDomain(m.project) for m in members]
        return projects

    @transaction.atomic
    def join_project(self, project_id, user):
        """
        Add user to project as ProjectMember
        """
        try: 
            project = ProjectModel.objects.select_for_update().get(project_id=project_id)
            domain = ProjectDomain(project)

            # prevent duplicate membership
            if ProjectMember.objects.filter(user=user, project=project).exists():
                return {"error": "User is already a member of the project."}

            member = domain._project_member_management.add_member(user)

            return {"member" : member, "message": "User successfully added to the project."}
        except Exception as e:
            return {"error" : str(e)}
    
    @transaction.atomic
    def leave_project(self, project_id, user):
        """
        Remove user from project as ProjectMember
        """
        project = ProjectModel.objects.select_for_update().get(project_id=project_id)
        domain = ProjectDomain(project)

        project_members = ProjectMember.objects.filter(user=user, project=project)

        # prevent removing non-members
        if project_members.exists():
            project_member = project_members.first()
            member = domain._project_member_management.remove_member(project_member.project_member_id)
            return True
        return False
    
    def close_project(self, project_id, user):
        """
        Close the project
        """
        project = ProjectModel.objects.get(project_id=project_id)
        domain = ProjectDomain(project)
        if user != project.owner:
            raise PermissionError("Only the project owner can close the project.")
        domain.close_project()
        return domain 
    
    def check_project_access(self, project_id, user):
        project = ProjectModel.objects.get(project_id=project_id)
        domain = ProjectDomain(project)
        return domain.check_access(user)
    
    def get_all_project_members(self, project_id):
        """
        Get all members of the project
        """
        project = ProjectModel.objects.get(project_id=project_id)
        domain = ProjectDomain(project)
        members = domain._project_member_management.members
        return members