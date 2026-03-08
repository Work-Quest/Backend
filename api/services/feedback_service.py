from django.conf import settings
from django.db import transaction

import requests
from requests import exceptions as req_exc

from api.models.Project import Project
from api.models.ProjectMember import ProjectMember
from api.models.UserFeedback import UserFeedback


class feedbackService:
    def __init__(self):
        self.AI_SERVICE_URL = settings.AI_SERVICE_URL

    @transaction.atomic
    def get_feedback(self, project_member_id, project_id):
        """
        Get personalize feedback from AI_service
        """

        user_feedback = UserFeedback.objects.filter(user_id=project_member_id, project_id=project_id).first()
        # if don't have feedback existed then call AI service to get feedback and save to database
        if not user_feedback:
            # get user name 
            member = ProjectMember.objects.get(project_member_id=project_member_id)
            user_name = member.user.username
            project = Project.objects.get(project_id=project_id)
            
            data = {
                "project_member_id": str(project_member_id),
                "user_name": user_name
            }

            url = (self.AI_SERVICE_URL or "").strip()
            if not url:
                raise Exception("AI_SERVICE_URL is not configured")
            if not url.rstrip("/").endswith("/feedback"):
                url = url.rstrip("/") + "/feedback"

            try:
                response = requests.post(
                    url,
                    json=data,
                    timeout=10,
                )
            except req_exc.RequestException as e:
                raise Exception(f"AI service is unreachable at {url}: {e}")
            if response.status_code != 200:
                raise Exception("AI service error")

            try:
                response_data = response.json() or {}
            except Exception as e:
                raise Exception(f"AI service returned invalid JSON: {e}")
            
            user_feedback = UserFeedback.objects.create(
                user=member,
                project=project,
                feedback_text=response_data.get("feedback"),
                overall_quality_score=response_data.get("overall_quality_score"),
                team_work=response_data.get("team_work"),
                strength=response_data.get("work_category"),
                work_load_per_day=response_data.get("work_load_per_day"),
                work_speed=response_data.get("work_speed"),
                role_assigned=response_data.get("assigned_role"),
                diligence=response_data.get("diligence"),
                )   
            
        return user_feedback

        
