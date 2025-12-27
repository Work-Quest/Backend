# services/project_service.py
from django.db import transaction
from Backend.api.models.ProjectMember import ProjectMember
from models.Project import Project as ProjectModel 
from domains.project import Project as ProjectDomain
from Backend.api.domains.project import Project

class ProjectService:

    @transaction.atomic
    def create_project(self, project_data):
        """
        Create project in DB and return ProjectDomain
        """
        project = ProjectModel.objects.create(
            name=project_data["name"],
            description=project_data.get("description", ""),
            start_date=project_data.get("start_date"),
            end_date=project_data.get("end_date"),
            status=project_data.get("status", "PLANNING"),
        )

        return ProjectDomain(project)

    @transaction.atomic
    def edit_project(self, project_id, project_data):
        """
        Load project, apply domain logic, persist changes
        """
        project = ProjectModel.objects.select_for_update().get(id=project_id)

        domain = ProjectDomain(project)
        domain.edit_project_metadata(project_data)

        return domain
    
    def delete_project(self, project_id):
        """
        Delete project and all related data (tasks, boss, etc.)
        """
        project = ProjectModel.objects.select_for_update().get(id=project_id)

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
            .filter(user__id=user_id)
            .select_related("project")
        )

        projects = [ProjectDomain(m.project) for m in members]
        return projects

    @transaction.atomic
    def join_project(self, project_id, user):
        """
        Add user to project as ProjectMember
        """
        project = ProjectModel.objects.select_for_update().get(id=project_id)
        domain = ProjectDomain(project)

        # prevent duplicate membership
        existing_member = project.members.filter(user=user).first()
        if existing_member:
            return {"message": "User is already a member of the project."}

        member = domain.member_management.add_member({
            "user": user
        })

        return {"member" : member, "message": "User successfully added to the project."}
    
    @transaction.atomic
    def leave_project(self, project_id, user):
        """
        Remove user from project as ProjectMember
        """
        project = ProjectModel.objects.select_for_update().get(id=project_id)
        domain = ProjectDomain(project)

        # prevent removing non-members
        existing_member = project.members.filter(user=user).first()
        if existing_member:
            member = domain.member_management.remove_member({
                "user": user
            })
            return {"message": "User successfully removed from the project."}

        return {"message": "User is not a member of the project."}