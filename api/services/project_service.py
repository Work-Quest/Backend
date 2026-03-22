# services/project_service.py
from django.db import transaction
from api.models.ProjectMember import ProjectMember
from api.models.Project import Project as ProjectModel 
from api.domains.project import Project as ProjectDomain
from api.domains.project import Project
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from api.services.game_service import GameService
from api.models import TaskLog, ProjectBoss, ProjectEndSummary
from api.models.BusinessUser import BusinessUser
from api.models.Task import Task
from datetime import timedelta
from collections import defaultdict
from django.db.models import Max, OuterRef, Subquery, Sum


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

        # Check membership
        if not ProjectMember.objects.filter(project=project, user=user).exists():
            raise ValueError("User is not a member of this project.")

        # CHECK IF SUMMARY ALREADY EXISTS
        existing = ProjectEndSummary.objects.filter(project_id=project_id)
        if existing.exists():
            first = existing.first()
            rows = list(
                existing.order_by("order").values(
                    "order",
                    "user_id",
                    "name",
                    "username",
                    "score",
                    "damage_deal",
                    "damage_receive",
                    "status",
                    "is_mvp",
                )
            )
            user_ids = [r["user_id"] for r in rows]
            profiles = {
                str(u.user_id): u
                for u in BusinessUser.objects.filter(user_id__in=user_ids).only(
                    "user_id", "selected_character_id", "bg_color_id"
                )
            }

            def _avatar_fields(uid):
                p = profiles.get(str(uid))
                if not p:
                    return {"selected_character_id": 1, "bg_color_id": 1}
                return {
                    "selected_character_id": p.selected_character_id,
                    "bg_color_id": p.bg_color_id,
                }

            return {
                "users": [
                    {
                        "order": item["order"],
                        "user_id": str(item["user_id"]),  # Convert UUID to string
                        "name": item["name"],
                        "username": item["username"],
                        "score": item["score"],
                        "damageDeal": item["damage_deal"],
                        "damageReceive": item["damage_receive"],
                        "status": item["status"],
                        "isMVP": item["is_mvp"],
                        **_avatar_fields(item["user_id"]),
                    }
                    for item in rows
                ],
                "boss_count": first.boss_count,
                "boss": first.boss,
                "reduction_percent": first.reduction_percent,
            }

        domain = ProjectDomain(project)
        members = domain._project_member_management.members

        delay_days = None
        reduction_percent = None

        if project.deadline:
            today = timezone.now()
            if project.deadline < today:
                delay_days = (today - project.deadline).days

        user_scores = []

        for member in members:

            damage_dealt = TaskLog.objects.filter(
                project_id=project_id,
                event_type=TaskLog.EventType.USER_ATTACK,
                actor_id=str(member.project_member_id),
            ).values_list("payload", flat=True)

            damage_received = TaskLog.objects.filter(
                project_id=project_id,
                event_type=TaskLog.EventType.BOSS_ATTACK,
                actor_id=str(member.project_member_id),
            ).values_list("payload", flat=True)

            damage_list = [p["damage"] for p in damage_dealt]
            damage_received_list = [p["damage"] for p in damage_received]

            total_damage_dealt = sum(damage_list)
            total_damage_received = sum(damage_received_list)

            score = member.score

            if project.deadline_decision == "continued" and delay_days:
                reduction_percent = min(delay_days * 5, 50)

                if reduction_percent > 0:
                    score = int(score / (1 - reduction_percent / 100))

            user_scores.append(
                {
                    "order": len(user_scores) + 1,
                    "user_id": str(member.user.user_id),  # Convert UUID to string
                    "name": member.user.name or member.user.username,
                    "username": member.user.username,
                    "score": score,
                    "damageDeal": total_damage_dealt,
                    "damageReceive": total_damage_received,
                    "status": member.status,
                    "isMVP": False,
                    "member_id": str(member.project_member_id),  # Convert UUID to string
                    "selected_character_id": member.user.selected_character_id,
                    "bg_color_id": member.user.bg_color_id,
                }
            )

        user_scores.sort(key=lambda x: x["score"], reverse=True)

        if user_scores:
            user_scores[0]["isMVP"] = True

            for i, user_data in enumerate(user_scores, 1):
                user_data["order"] = i

        boss = ProjectBoss.objects.filter(project=project, status="Dead")

        boss_list = [
            {
                "id": str(b.boss.boss_id),  # Convert UUID to string
                "name": b.boss.boss_name,
                "type": b.boss.boss_type,
            }
            for b in boss
        ]

        boss_count = boss.count()

        with transaction.atomic():

            for user_data in user_scores:
                ProjectEndSummary.objects.create(
                    project_member_id=user_data["member_id"],
                    project_id=project_id,
                    user_id=user_data["user_id"],
                    order=user_data["order"],
                    name=user_data["name"],
                    username=user_data["username"],
                    score=user_data["score"],
                    damage_deal=user_data["damageDeal"],
                    damage_receive=user_data["damageReceive"],
                    status=user_data["status"],
                    is_mvp=user_data["isMVP"],
                    boss=boss_list,
                    boss_count=boss_count,
                    reduction_percent=reduction_percent,
                )

        return {
            "users": user_scores,
            "boss_count": boss_count,
            "boss": boss_list,
            "reduction_percent": reduction_percent,
        }

    def get_dashboard_data(self, project_id: str, business_user=None):
        """
        Get dashboard visualization data including task status counts, burn down chart data, and project details.
        When ``business_user`` is set, includes ``achievementIds`` for that member on this project.
        """
        project = ProjectModel.objects.get(project_id=project_id)
        
        # Get all tasks for the project
        all_tasks = Task.objects.filter(project_id=project_id)
        
        # Calculate task status counts
        task_status_counts = {
            'backlog': all_tasks.filter(status='backlog').count(),
            'todo': all_tasks.filter(status='todo').count(),
            'inProgress': all_tasks.filter(status='inProgress').count(),
            'done': all_tasks.filter(status='done').count(),
        }
        
        # Calculate burn down chart data
        # Get project start date (created_at) and today
        project_start = project.created_at.date()
        today = timezone.now().date()
        
        # Get all completed tasks with their completion dates
        completed_tasks = all_tasks.filter(
            status='done',
            completed_at__isnull=False
        ).values('completed_at')
        
        # Group completed tasks by date
        completed_by_date = defaultdict(int)
        for task in completed_tasks:
            completion_date = task['completed_at'].date()
            if project_start <= completion_date <= today:
                completed_by_date[completion_date] += 1
        
        # Calculate total tasks
        total_tasks = all_tasks.count()
        
        # Generate burn down data for each day from project start to today (max 30 days)
        burn_down_data = []
        days_to_show = min((today - project_start).days + 1, 30)
        
        if days_to_show > 0:
            cumulative_completed = 0
            for i in range(days_to_show):
                current_date = project_start + timedelta(days=i)
                # Add tasks completed on this date
                cumulative_completed += completed_by_date.get(current_date, 0)
                remaining_tasks = total_tasks - cumulative_completed
                burn_down_data.append({
                    'date': current_date.isoformat(),
                    'remainingTasks': max(0, remaining_tasks)
                })
        else:
            # If project just started, show current state
            completed_count = task_status_counts['done']
            burn_down_data.append({
                'date': today.isoformat(),
                'remainingTasks': max(0, total_tasks - completed_count)
            })
        
        # Calculate days left
        days_left = None
        if project.deadline:
            deadline_date = project.deadline.date()
            if deadline_date >= today:
                days_left = (deadline_date - today).days
        
        # Get estimated finish time (reuse logic from get_estimate_finish_time endpoint)
        estimated_finish_time = None
        completed_tasks_for_estimate = all_tasks.filter(
            status='done',
            completed_at__isnull=False
        )
        
        if completed_tasks_for_estimate.exists():
            total_duration = timedelta(0)
            for task in completed_tasks_for_estimate:
                duration = task.completed_at - task.created_at
                total_duration += duration
            
            average_duration = total_duration / completed_tasks_for_estimate.count()
            average_days = average_duration.total_seconds() / (24 * 60 * 60)
            
            remaining_tasks = all_tasks.filter(
                status__in=['backlog', 'todo', 'inProgress']
            ).count()
            
            if remaining_tasks > 0:
                estimated_finish_time = round(average_days * remaining_tasks)
        
        # Format deadline for display
        formatted_deadline = None
        if project.deadline:
            formatted_deadline = project.deadline.strftime('%m/%d/%Y')

        achievement_ids: list[str] = []
        if business_user is not None:
            try:
                member = ProjectMember.objects.get(project=project, user=business_user)
            except ProjectMember.DoesNotExist:
                member = None
            if member is not None:
                from api.models.UserFeedback import UserFeedback
                from api.services.achievement_service import compute_achievement_ids

                fb = (
                    UserFeedback.objects.filter(user=member, project=project)
                    .select_related("user", "project")
                    .first()
                )
                if fb is not None:
                    unlocked = set(compute_achievement_ids(fb))
                    canonical = ["01", "02", "03", "04", "05", "06"]
                    achievement_ids = [a for a in canonical if a in unlocked]

        return {
            'taskStatusCounts': task_status_counts,
            'burnDownData': burn_down_data,
            'projectDetails': {
                'deadline': formatted_deadline,
                'daysLeft': days_left,
                'estimatedFinishTime': estimated_finish_time,
                'totalTasks': total_tasks,
                'completedTasks': task_status_counts['done']
            },
            'achievementIds': achievement_ids,
        }

    def get_global_leaderboard(self):
        """
        Get global leaderboard with top 10 users based on their highest score across all projects.
        For each user, selects the record with their maximum score.
        """
        from django.db.models import F, Window, Max as MaxFunc
        from django.db.models.functions import RowNumber
        
        # Get max score per user using window function
        # This is more efficient than multiple queries
        user_max_scores = (
            ProjectEndSummary.objects
            .values('user_id')
            .annotate(max_score=MaxFunc('score'))
        )
        
        # Create a mapping of user_id to max_score
        max_score_map = {item['user_id']: item['max_score'] for item in user_max_scores}
        
        # Resolve profile customizations for leaderboard avatars.
        from api.models import BusinessUser
        users_by_id = {str(u.user_id): u for u in BusinessUser.objects.all()}

        # Get one record per user with their max score
        # Use distinct on user_id with ordering to get the most recent record if there are ties
        leaderboard_data = []
        seen_users = set()
        
        # Query all records, ordered by score descending, then by updated_at descending
        # This ensures we get the highest scores first, and for ties, the most recent record
        all_records = ProjectEndSummary.objects.order_by('-score', '-updated_at')
        
        for record in all_records:
            user_id = record.user_id
            if user_id not in seen_users:
                # Check if this record has the max score for this user
                if record.score == max_score_map.get(user_id):
                    user_key = str(user_id)
                    user_profile = users_by_id.get(user_key)
                    leaderboard_data.append({
                        'order': len(leaderboard_data) + 1,
                        'name': record.name,
                        'username': record.username,
                        'user_id': user_key,  # Add user_id for profile navigation
                        'score': record.score,
                        'damageDeal': record.damage_deal,
                        'damageReceive': record.damage_receive,
                        'status': record.status,
                        'isMVP': False,  # Global leaderboard doesn't have MVP
                        'selected_character_id': user_profile.selected_character_id if user_profile else 1,
                        'bg_color_id': user_profile.bg_color_id if user_profile else 1,
                    })
                    seen_users.add(user_id)
                    
                    # Stop when we have 10 users
                    if len(leaderboard_data) >= 10:
                        break
        
        return leaderboard_data

    def get_user_finished_projects(self, user=None, user_id=None):
        """
        Get finished projects for a user from ProjectEndSummary table.
        Returns list of projects with project_name, score, and boss_count.
        Accepts either a BusinessUser object or user_id string.
        """
        from api.models import BusinessUser
        
        # Resolve user object if user_id is provided
        if user_id and not user:
            try:
                user = BusinessUser.objects.get(user_id=user_id)
            except BusinessUser.DoesNotExist:
                return []
        
        if not user:
            return []
        
        # Get unique project IDs for this user with their most recent updated_at
        summaries = ProjectEndSummary.objects.filter(
            user_id=user.user_id
        ).values('project_id').annotate(
            latest_updated=Max('updated_at')
        ).order_by('-latest_updated')
        
        finished_projects = []
        
        for summary in summaries:
            project_id = summary['project_id']
            try:
                # Get project details
                project = ProjectModel.objects.get(project_id=project_id)
                
                # Get user's most recent summary for this project
                user_summary = ProjectEndSummary.objects.filter(
                    user_id=user.user_id,
                    project_id=project_id
                ).order_by('-updated_at').first()
                
                if user_summary:
                    finished_projects.append({
                        'project_id': str(project_id),
                        'project_name': project.project_name,
                        'score': user_summary.score,
                        'boss_count': user_summary.boss_count,
                    })
            except ProjectModel.DoesNotExist:
                # Skip if project doesn't exist
                continue
        
        return finished_projects

    def get_user_profile_stats(self, user=None, user_id=None):
        """
        Get user profile statistics from ProjectEndSummary table.
        Returns highest score, project count, total bosses defeated, and achievement progress.
        Accepts either a BusinessUser object or user_id string.
        """
        from api.models import BusinessUser
        from api.services.achievement_service import get_overall_achievement_ids_for_user

        achievements_total = 6  # canonical IDs 01–06, matches frontend ACHIEVEMENT_IDS

        def stats_base(**kwargs):
            base = {
                'highest_score': 0,
                'project_count': 0,
                'total_bosses_defeated': 0,
                'achievements_unlocked': 0,
                'achievements_total': achievements_total,
            }
            base.update(kwargs)
            return base

        # Resolve user object if user_id is provided
        if user_id and not user:
            try:
                user = BusinessUser.objects.get(user_id=user_id)
            except BusinessUser.DoesNotExist:
                return stats_base()

        if not user:
            return stats_base()

        achievement_ids = get_overall_achievement_ids_for_user(user)
        achievements_unlocked = len(achievement_ids)

        summaries = ProjectEndSummary.objects.filter(user_id=user.user_id)

        if not summaries.exists():
            return stats_base(achievements_unlocked=achievements_unlocked)

        # Calculate highest score
        highest_score = summaries.aggregate(max_score=Max('score'))['max_score'] or 0

        # Count unique projects
        project_count = ProjectMember.objects.filter(user=user).count()

        # Sum total bosses defeated (sum of boss_count from all records)
        total_bosses_defeated = summaries.aggregate(total=Sum('boss_count'))['total'] or 0

        return {
            'highest_score': highest_score,
            'project_count': project_count,
            'total_bosses_defeated': total_bosses_defeated,
            'achievements_unlocked': achievements_unlocked,
            'achievements_total': achievements_total,
        }

    def get_user_defeated_bosses(self, user=None, user_id=None):
        """
        Get unique bosses defeated by user from ProjectEndSummary table.
        Extracts bosses from the boss JSONField and returns unique list.
        Accepts either a BusinessUser object or user_id string.
        """
        from api.models import BusinessUser
        
        # Resolve user object if user_id is provided
        if user_id and not user:
            try:
                user = BusinessUser.objects.get(user_id=user_id)
            except BusinessUser.DoesNotExist:
                return []
        
        if not user:
            return []
        
        summaries = ProjectEndSummary.objects.filter(user_id=user.user_id)
        
        defeated_bosses = []
        seen_boss_ids = set()
        
        for summary in summaries:
            if summary.boss and isinstance(summary.boss, list):
                for boss in summary.boss:
                    boss_id = str(boss.get('id', ''))
                    if boss_id and boss_id not in seen_boss_ids:
                        defeated_bosses.append({
                            'id': boss_id,
                            'name': boss.get('name', 'Unknown Boss'),
                            'type': boss.get('type', 'Normal'),
                        })
                        seen_boss_ids.add(boss_id)
        
        return defeated_bosses

