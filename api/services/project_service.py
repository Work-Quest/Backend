# services/project_service.py
from django.db import transaction
from api.models.ProjectMember import ProjectMember
from api.models.Project import Project as ProjectModel 
from api.domains.project import Project as ProjectDomain
from api.domains.project import Project
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from api.services.game_service import GameService
from api.models import TaskLog, ProjectBoss


class ProjectService:

    @transaction.atomic
    def create_project(self, project_data, user):
        """
        Create project in DB and return ProjectDomain
        """

        deadline_str = project_data.get("deadline")

        if deadline_str:
            deadline_dt = parse_datetime(deadline_str)

        project = ProjectModel.objects.create(
            owner=user,
            project_name=project_data.get("project_name"),
            deadline=deadline_dt,
            total_tasks=0,
            completed_tasks=0,
            status="Working")

        project_domain = ProjectDomain(project)
        # add owner as member
        project_domain._project_member_management.add_member(user)
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

    def get_project_end_summary(self, user, project_id):

        project = ProjectModel.objects.get(project_id=project_id)
        # Check if user is a member of the project
        if not ProjectMember.objects.filter(project=project, user=user).exists():
            raise ValueError("User is not a member of this project.")

        domain = ProjectDomain(project)
        members = domain._project_member_management.members

        # Calculate delay days if deadline passed
        delay_days = None
        if project.deadline:
            today = timezone.now()
            if project.deadline < today:
                delay_days = (today - project.deadline).days

        # Build user scores with damage stats
        user_scores = []

        for member in members:

            # Calculate damage dealt and received from logs
            damage_dealt = TaskLog.objects.filter(
                project_id=project_id,
                event_type=TaskLog.EventType.USER_ATTACK,
                actor_id=str(member.project_member_id)
            ).values_list("payload", flat=True)

            damage_received = TaskLog.objects.filter(
                project_id=project_id,
                event_type=TaskLog.EventType.BOSS_ATTACK,
                actor_id=str(member.project_member_id)
            ).values_list("payload", flat=True)

            damage_list = [p["damage"] for p in damage_dealt]
            print(damage_list)
            damage_received_list = [p["damage"] for p in damage_received]
            total_damage_dealt = sum(damage_list)
            total_damage_received = sum(damage_received_list)

            score = member.score
            reduction_percent = None
            # If project was continued after deadline, calculate original score
            if project.deadline_decision == 'continued' and delay_days:
                reduction_percent = min(delay_days * 5, 50)

                if reduction_percent > 0:
                    score = int(score / (1 - reduction_percent / 100))


            user_scores.append({
                'order': len(user_scores) + 1,
                'name': member.user.name or member.user.username,
                'username': member.user.username,
                'score': score,
                'damageDeal': total_damage_dealt,
                'damageReceive': total_damage_received,
                'status': member.status,
                'isMVP': False,  # Will be calculated based on highest score
            })

        # Sort by score descending and assign MVP
        user_scores.sort(key=lambda x: x['score'], reverse=True)
        if user_scores:
            user_scores[0]['isMVP'] = True
            # Update order
            for i, user in enumerate(user_scores, 1):
                user['order'] = i

        boss = ProjectBoss.objects.filter(project=project, status="Dead")
        boss_list = [
            {
                "id": b.boss.boss_id,
                "name": b.boss.boss_name,
                "type": b.boss.boss_type
            }
            for b in boss
        ]


        return {
                "users": user_scores,
                "boss_count": boss.count(),
                "boss": boss_list,
                'reduction_percent': reduction_percent
        }

